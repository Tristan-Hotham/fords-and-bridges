"""Step 2. Link every classified place to size (Census 2021), wealth (ONS small-area income),
region, Domesday, medieval bridges, Roman roads and rivers.

Inputs (read in place, never copied):
  data/places_classified.csv                               (step 1)
  /home/claude/hist/_data8/ons_geo.json                    (ONS: BUA22, MSOA centroids, MSOA to BUA lookup)
  /home/claude/hist/_data8/lsoa21_bua22_lookup.json        (ONS: LSOA to BUA22 best fit)
  /home/claude/hist/_data8/census/census2021-ts001-*.csv   (Census 2021 usual residents)
  /home/claude/hist/_data8/ons_msoa_income_fye2023.xlsx    (ONS income estimates for small areas, FYE2023)
  /home/claude/hist/_data8/uk_bundle_wikidata_osm.json     (Wikidata CC0 and OpenStreetMap ODbL extracts)
  /home/claude/hist/domesday-destiny/data/domesday_places.csv
  /home/claude/hist/how-roman-is-your-road/results/itinere_gb_corrected.geojson
  /home/claude/hist/osrivers/Data/oprvrs_gb.gpkg
Outputs:
  data/places_linked.csv   one row per place (Great Britain), with every linked figure
  data/bua_ew.csv          one row per Built-up Area in England and Wales with population and income
  data/bridges_dated.csv   dated bridges (Wikidata and OpenStreetMap) used for the medieval-bridge test
"""
import json
import os
import re
import sqlite3
import struct

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely import wkb
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D8 = "/home/claude/hist/_data8"
DD = "/home/claude/hist/domesday-destiny/data/domesday_places.csv"
ROMAN = "/home/claude/hist/how-roman-is-your-road/results/itinere_gb_corrected.geojson"
RIVERS = "/home/claude/hist/osrivers/Data/oprvrs_gb.gpkg"
T = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)


def norm(s):
    s = str(s or "").lower().replace("&", " and ").replace("’", "'")
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"[^a-z0-9àáâäèéêëìíîïòóôöùúûüŵŷ ]+", " ", s.replace("-", " ").replace(".", ""))
    return re.sub(r"\s+", " ", s).strip()


P = pd.read_csv(os.path.join(ROOT, "data", "places_classified.csv"), keep_default_na=False)
print("places", len(P))

# ---------- Census 2021 populations ----------
ls = pd.read_csv(os.path.join(D8, "census", "census2021-ts001-lsoa.csv"))
ls = ls.rename(columns={"geography code": "LSOA21CD", "Residence type: Total; measures: Value": "pop"})[["LSOA21CD", "pop"]]
ms = pd.read_csv(os.path.join(D8, "census", "census2021-ts001-msoa.csv"))
ms = ms.rename(columns={"geography code": "MSOA21CD", "Residence type: Total; measures: Value": "pop"})[["MSOA21CD", "pop"]]
lk = pd.DataFrame(json.load(open(os.path.join(D8, "lsoa21_bua22_lookup.json"))))
lk = lk.merge(ls, on="LSOA21CD", how="left")
bua_pop = lk[lk.BUA22CD.notna() & (lk.BUA22CD != "")].groupby("BUA22CD").agg(pop=("pop", "sum"), n_lsoa=("pop", "size")).reset_index()

G = json.load(open(os.path.join(D8, "ons_geo.json")))
bua = pd.DataFrame(G["bua22_gb"])[["BUA22CD", "BUA22NM", "BUA22NMW", "LAT", "LONG", "BNG_E", "BNG_N", "Shape__Area"]]
bua["r_eq_km"] = np.sqrt(bua.Shape__Area / np.pi) / 1000
bua = bua.merge(bua_pop, on="BUA22CD", how="left")
bua["pop"] = bua["pop"].fillna(0)
bua["n_lsoa"] = bua["n_lsoa"].fillna(0).astype(int)

# ---------- income by MSOA ----------
inc = {}
for sheet, key in [("Total annual income", "inc_total"), ("Net income after housing costs", "inc_net_ahc")]:
    x = pd.read_excel(os.path.join(D8, "ons_msoa_income_fye2023.xlsx"), sheet_name=sheet, header=3)
    x = x.rename(columns={x.columns[0]: "MSOA21CD", x.columns[6]: key})
    inc[key] = x[["MSOA21CD", key]]
msoa = pd.DataFrame(G["msoa21_pwc"])[["MSOA21CD", "_x", "_y"]].rename(columns={"_x": "lon", "_y": "lat"})
ml = pd.DataFrame(G["msoa21_bua22_lookup"])[["MSOA21CD", "BUA22CD", "LAD22NM", "RGN22NM"]]
msoa = msoa.merge(ml, on="MSOA21CD", how="left").merge(ms, on="MSOA21CD", how="left")
for k in inc:
    msoa = msoa.merge(inc[k], on="MSOA21CD", how="left")
msoa["RGN22NM"] = msoa.RGN22NM.fillna("").replace("", "Wales")
msoa.loc[msoa.MSOA21CD.str.startswith("W"), "RGN22NM"] = "Wales"
mx, my = T.transform(msoa.lon.values, msoa.lat.values)
msoa["E"], msoa["N"] = mx, my
print("MSOA", len(msoa), "with income", msoa.inc_total.notna().sum())
national = {
    "msoa_pop_total": float(msoa["pop"].sum()),
    "income_mass_total": float((msoa["pop"] * msoa.inc_total).sum()),
    "inc_total_popweighted": float((msoa["pop"] * msoa.inc_total).sum() / msoa["pop"].sum()),
}

# BUA income: population-weighted mean of the MSOAs whose best-fit BUA it is
g = msoa.dropna(subset=["BUA22CD"]).groupby("BUA22CD")
bua_inc = g.apply(lambda s: pd.Series({
    "inc_total": np.average(s.inc_total, weights=s["pop"]),
    "inc_net_ahc": np.average(s.inc_net_ahc, weights=s["pop"]),
    "n_msoa": len(s),
    "msoa_pop": s["pop"].sum(),
    "region": s.RGN22NM.mode().iloc[0],
}), include_groups=False).reset_index()
bua = bua.merge(bua_inc, on="BUA22CD", how="left")
ew = bua.BUA22CD.str[0].isin(["E", "W"])
mtree = cKDTree(msoa[["E", "N"]].values)
# region and fallback income for BUAs without an MSOA of their own: nearest MSOA centroid
d_, i_ = mtree.query(bua[["BNG_E", "BNG_N"]].values)
bua["near_msoa"] = msoa.MSOA21CD.values[i_]
bua["near_msoa_km"] = d_ / 1000
bua["region"] = bua.region.fillna(pd.Series(msoa.RGN22NM.values[i_], index=bua.index))
bua.loc[~ew, "region"] = "Scotland"
bua["income_source"] = np.where(bua.inc_total.notna(), "own MSOAs", "nearest MSOA")
bua["inc_total"] = bua.inc_total.fillna(pd.Series(msoa.inc_total.values[i_], index=bua.index))
bua["inc_net_ahc"] = bua.inc_net_ahc.fillna(pd.Series(msoa.inc_net_ahc.values[i_], index=bua.index))
bua.loc[~ew, ["inc_total", "inc_net_ahc"]] = np.nan
# BUA names carry a district in brackets when the name repeats, e.g. "Ashford (Ashford)"
bua["nbua"] = bua.BUA22NM.str.replace(r"\s*\(.*\)$", "", regex=True).map(norm)
bua["nbuaw"] = bua.BUA22NMW.fillna("").str.replace(r"\s*\(.*\)$", "", regex=True).map(norm)

# ---------- places: BNG, region, nearest MSOA ----------
P["E"], P["N"] = P.x.astype(float), P.y.astype(float)
d_, i_ = mtree.query(P[["E", "N"]].values)
P["msoa"] = msoa.MSOA21CD.values[i_]
P["msoa_km"] = (d_ / 1000).round(2)
P["region_ons"] = np.where(P.country == "Scotland", "Scotland", msoa.RGN22NM.values[i_])
P["msoa_inc_total"] = np.where(P.country == "Scotland", np.nan, msoa.inc_total.values[i_])

# ---------- name match to BUA ----------
btree = cKDTree(bua[["BNG_E", "BNG_N"]].values)
names = {}
for j, r in bua.iterrows():
    for k in {r.nbua, r.nbuaw} - {""}:
        names.setdefault(k, []).append(j)
match = []
for r in P.itertuples():
    best = None
    for nm in {norm(r.name1), norm(r.name2)} - {""}:
        for j in names.get(nm, []):
            b = bua.loc[j]
            dist = np.hypot(b.BNG_E - r.E, b.BNG_N - r.N) / 1000
            if dist <= max(3.0, 2.5 * b.r_eq_km) and (best is None or dist < best[1]):
                best = (j, dist)
    match.append(best)
P["bua"] = [bua.BUA22CD[m[0]] if m else "" for m in match]
P["bua_name"] = [bua.BUA22NM[m[0]] if m else "" for m in match]
P["bua_km"] = [round(m[1], 2) if m else np.nan for m in match]
TYPE_RANK = {"City": 0, "Town": 1, "Suburban Area": 2, "Village": 3, "Other Settlement": 4, "Hamlet": 5}
P["trank"] = P.local_type.map(TYPE_RANK)
# one OS place per BUA: keep the highest-ranked, then nearest
P = P.sort_values(["trank", "bua_km"])
P["bua_primary"] = (P.bua != "") & ~P.duplicated("bua")
P = P.sort_values("place_id")
P = P.merge(bua[["BUA22CD", "pop", "n_lsoa", "inc_total", "inc_net_ahc", "income_source", "region", "r_eq_km"]]
            .rename(columns={"BUA22CD": "bua", "pop": "bua_pop", "inc_total": "bua_inc_total",
                             "inc_net_ahc": "bua_inc_net_ahc", "region": "bua_region"}), on="bua", how="left")

# ---------- Wikidata settlement populations (Scotland check) ----------
bundle = json.load(open(os.path.join(D8, "uk_bundle_wikidata_osm.json")))


def tsv(text):
    rows = [l.split("\t") for l in text.strip().split("\n")]
    return pd.DataFrame(rows[1:], columns=[c.strip("?") for c in rows[0]])


def lab(s):
    m = re.match(r'^"(.*)"@\w+', s)
    return m.group(1) if m else s


def pt(s):
    m = re.match(r"POINT\(([-\d.eE]+) ([-\d.eE]+)\)", s or "")
    return (float(m.group(1)), float(m.group(2))) if m else (np.nan, np.nan)


wp = tsv(bundle["wd_settlements_pop_tsv"])
wp["label"] = wp.label.map(lab)
wp[["lon", "lat"]] = pd.DataFrame(wp.coord.map(pt).tolist(), index=wp.index)
wp["population"] = pd.to_numeric(wp.population, errors="coerce")
wp = wp.dropna(subset=["lon", "lat", "population"]).sort_values("population", ascending=False).drop_duplicates("item")
wp["E"], wp["N"] = T.transform(wp.lon.values, wp.lat.values)
wp["n"] = wp.label.map(norm)
wtree = cKDTree(wp[["E", "N"]].values)
wd_pop = []
for r in P.itertuples():
    got = np.nan
    for i in wtree.query_ball_point([r.E, r.N], 3000):
        if wp.n.iat[i] in (norm(r.name1), norm(r.name2)):
            got = wp.population.iat[i] if np.isnan(got) else max(got, wp.population.iat[i])
    wd_pop.append(got)
P["wikidata_pop"] = wd_pop

# ---------- Domesday ----------
dd = pd.read_csv(DD, usecols=["placeId", "name", "lat", "lng", "households1086", "burgesses1086", "modernPlaceName", "openDomesdayPath"])
dd = dd.dropna(subset=["lat", "lng"])
dd["E"], dd["N"] = T.transform(dd.lng.values, dd.lat.values)
dd["n"] = dd.modernPlaceName.map(norm)
# Domesday's own name with the editorial brackets removed: "Bradford [on Avon]" -> "Bradford on Avon"
dd["n2"] = dd.name.str.replace(r"[\[\]]", "", regex=True).map(norm)
dtree = cKDTree(dd[["E", "N"]].values)
dd_hh, dd_bur, dd_name, dd_any = [], [], [], []
for r in P.itertuples():
    nn = (norm(r.name1), norm(r.name2))
    ids = [i for i in dtree.query_ball_point([r.E, r.N], 3000) if dd.n.iat[i] in nn or dd.n2.iat[i] in nn]
    dd_any.append(bool(ids))
    dd_hh.append(dd.households1086.iloc[ids].sum(min_count=1) if ids else np.nan)
    dd_bur.append(dd.burgesses1086.iloc[ids].sum(min_count=1) if ids else np.nan)
    dd_name.append("; ".join(dd.name.iloc[ids]) if ids else "")
P["domesday"] = pd.Series(dd_any, index=P.index, dtype=object)
P["domesday_households"] = dd_hh
P["domesday_burgesses"] = dd_bur
P["domesday_names"] = dd_name
P.loc[P.country != "England", "domesday"] = np.nan  # Domesday covers England only (and not the far north)

# ---------- dated bridges (Wikidata + OSM) ----------
ws = tsv(bundle["wd_structures_tsv"])
ws["clsLabel"] = ws.clsLabel.map(lab)
# bridge classes only ("college of the University of Cambridge" contains "bridge", so match the word)
ws = ws[ws.clsLabel.str.contains(r"(?<![a-z])(?:foot|)bridge\b|^bridge$", case=False, regex=True)
        & ~ws.clsLabel.str.contains("Cambridge|college", case=False)]
ws["label"] = ws.label.map(lab)
ws[["lon", "lat"]] = pd.DataFrame(ws.coord.map(pt).tolist(), index=ws.index)
ws["year"] = pd.to_numeric(ws.inception.str.extract(r'"?(-?\d{1,4})-')[0], errors="coerce")
wsb = ws.sort_values("year").groupby("item").agg(label=("label", "first"), lon=("lon", "first"), lat=("lat", "first"),
                                                year=("year", "min"), cls=("clsLabel", "first")).reset_index()
wsb["source"] = "Wikidata"
wsb["id"] = wsb["item"].str.extract(r"(Q\d+)")[0]


def osm_year(s):
    s = str(s or "").strip()
    m = re.match(r"^~?(\d{4})", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^C(\d{1,2})", s, re.I)
    if m:
        return (int(m.group(1)) - 1) * 100
    m = re.match(r"^(early|mid|late)\s+C?(\d{1,2})", s, re.I)
    if m:
        return (int(m.group(2)) - 1) * 100 + {"early": 0, "mid": 40, "late": 70}[m.group(1).lower()]
    m = re.match(r"^(\d{1,2})(st|nd|rd|th) century", s, re.I)
    if m:
        return (int(m.group(1)) - 1) * 100
    return np.nan


osm = pd.DataFrame(bundle["osm_uk_features"])
ob = osm[(osm.kind.isin(["dated_bridge", "heritage_bridge"])) | (osm.hist == "bridge")].copy()
ob["year"] = ob.start.map(osm_year)
ob = ob.rename(columns={"name": "label"})[["osm", "label", "lon", "lat", "year", "wd"]]
ob["source"] = "OpenStreetMap"
ob["id"] = ob.osm
ob["cls"] = "bridge"
B = pd.concat([wsb[["id", "label", "lon", "lat", "year", "cls", "source"]], ob[["id", "label", "lon", "lat", "year", "cls", "source", "wd"]]], ignore_index=True)
B = B.dropna(subset=["lon", "lat"])
B["E"], B["N"] = T.transform(B.lon.values, B.lat.values)
# drop an OSM bridge that carries the Wikidata id of a bridge already in the list, or sits within 60 m of a Wikidata bridge
wd_ids = set(wsb.id)
B = B[~((B.source == "OpenStreetMap") & B.wd.isin(wd_ids))]
tw = cKDTree(B[B.source == "Wikidata"][["E", "N"]].values)
dup = np.zeros(len(B), bool)
for k, (s, e, n) in enumerate(zip(B.source, B.E, B.N)):
    if s == "OpenStreetMap" and tw.query_ball_point([e, n], 60):
        dup[k] = True
B = B[~dup].drop(columns=["wd"])
# Medieval = a Wikidata inception before 1540. OpenStreetMap start dates before 1540 are not used for this
# flag: the few there are errors (canal-era bridges carrying "1344").
B["medieval"] = (B.year < 1540) & (B.source == "Wikidata")
B["pre1700"] = (B.year < 1700) & (B.source == "Wikidata")
B["dated"] = B.year.notna()
print("bridges", len(B), "dated", B.dated.sum(), "medieval", B.medieval.sum())
B[["id", "label", "source", "year", "medieval", "pre1700", "lon", "lat", "cls"]].to_csv(os.path.join(ROOT, "data", "bridges_dated.csv"), index=False)
Bm = B[B.medieval]
mtree_b = cKDTree(Bm[["E", "N"]].values)
dtree_b = cKDTree(B[B.dated][["E", "N"]].values)
ptree_b = cKDTree(B[B.pre1700][["E", "N"]].values)
atree_b = cKDTree(B[["E", "N"]].values)
for km in (1, 2):
    P[f"medieval_bridges_{km}km"] = [len(mtree_b.query_ball_point([e, n], km * 1000)) for e, n in zip(P.E, P.N)]
P["pre1700_bridges_1km"] = [len(ptree_b.query_ball_point([e, n], 1000)) for e, n in zip(P.E, P.N)]
P["dated_bridges_1km"] = [len(dtree_b.query_ball_point([e, n], 1000)) for e, n in zip(P.E, P.N)]
P["any_bridges_1km"] = [len(atree_b.query_ball_point([e, n], 1000)) for e, n in zip(P.E, P.N)]
dmb, imb = mtree_b.query(P[["E", "N"]].values)
P["nearest_medieval_bridge_km"] = (dmb / 1000).round(2)
P["nearest_medieval_bridge"] = Bm.label.values[imb]
P["nearest_medieval_bridge_year"] = Bm.year.values[imb]

# ---------- Roman roads (Itiner-e, datum-corrected copy) ----------
rr = json.load(open(ROMAN))
lines = []
for f in rr["features"]:
    gm = shape(f["geometry"])
    parts = list(gm.geoms) if gm.geom_type.startswith("Multi") else [gm]
    for p_ in parts:
        xs, ys = T.transform(*np.array(p_.coords).T[:2])
        from shapely.geometry import LineString
        lines.append(LineString(np.c_[xs, ys]))
tree = STRtree(lines)
pts = [Point(e, n) for e, n in zip(P.E, P.N)]
idx = tree.nearest(pts)
P["roman_road_km"] = [round(pts[k].distance(lines[j]) / 1000, 2) for k, j in enumerate(idx)]

# ---------- rivers (OS Open Rivers): distance to nearest named river or tidal river ----------
con = sqlite3.connect(f"file:{RIVERS}?mode=ro", uri=True)
rl = []
for blob, form in con.execute("select geometry, form from watercourse_link where form in ('inlandRiver','tidalRiver','canal') and watercourse_name is not null"):
    flags = blob[3]
    env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(flags >> 1) & 7]
    rl.append(wkb.loads(bytes(blob[8 + env:])))
con.close()
rtree = STRtree(rl)
idx = rtree.nearest(pts)
P["river_km"] = [round(pts[k].distance(rl[j]) / 1000, 3) for k, j in enumerate(idx)]
print("rivers", len(rl))

P = P.drop(columns=["trank"])
P.to_csv(os.path.join(ROOT, "data", "places_linked.csv"), index=False)
keep = ["BUA22CD", "BUA22NM", "LAT", "LONG", "r_eq_km", "pop", "n_lsoa", "n_msoa", "inc_total", "inc_net_ahc", "income_source", "region"]
bua[ew][keep].round(4).to_csv(os.path.join(ROOT, "data", "bua_ew.csv"), index=False)
json.dump(national, open(os.path.join(ROOT, "data", "_national.json"), "w"))
print(P.groupby("cls").agg(n=("place_id", "size"), bua=("bua_primary", "sum")))
