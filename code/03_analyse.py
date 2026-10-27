"""Step 3. Every number for the page, paper, blog and collage -> data/results.json.
Also writes data/settlements_ew.csv (one row per ford/bridge/other built-up area used in the totals)
and the compact page data _site_data.json (deleted by step 4).

Units:
  "Towns and villages with their own built-up area" (BUA unit): places in England and Wales that match a
  Built-up Area (2022) of the same name, one place per BUA, with a Census 2021 population summed from the
  LSOAs whose best-fit BUA it is (so very small BUAs, with no LSOA of their own, have no figure).
  "All named places" (place unit): every OS Open Names populated place in England and Wales, with the
  income of its own BUA where it has one with MSOAs, otherwise of the nearest MSOA (by population-weighted
  centroid).
"""
import json
import os

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = np.random.default_rng(2026)
P = pd.read_csv(os.path.join(ROOT, "data", "places_linked.csv"), keep_default_na=False, na_values=[""], low_memory=False)
# display name: Welsh and Gaelic places carry both names (Pen-y-bont ar Ogwr / Bridgend)
P["disp"] = [a if not isinstance(b, str) or not b else f"{a} / {b}" for a, b in zip(P.name1, P.name2)]
NAT = json.load(open(os.path.join(ROOT, "data", "_national.json")))
R = {}
CL = ["ford", "bridge", "other"]
REG_ORDER = ["London", "South East", "East of England", "South West", "West Midlands", "East Midlands",
             "Yorkshire and The Humber", "North West", "North East", "Wales"]
SIZE = [(0, "No figure (small place)"), (1, "Under 5,000"), (5000, "5,000 to 20,000"), (20000, "20,000 to 100,000"), (100000, "100,000 and over")]


def r2(x, n=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def size_class(p):
    if not (p > 0):
        return SIZE[0][1]
    lab = SIZE[1][1]
    for lo, l in SIZE[1:]:
        if p >= lo:
            lab = l
    return lab


# ------------------------------------------------------------ counts
R["places_gb"] = int(len(P))
cnt = P.groupby(["country", "cls"]).size().unstack(fill_value=0)
R["counts"] = {c: {k: int(cnt.loc[c, k]) for k in CL} for c in cnt.index}
R["counts"]["GB"] = {k: int((P.cls == k).sum()) for k in CL}
R["ford_per_bridge_gb"] = r2(R["counts"]["GB"]["ford"] / R["counts"]["GB"]["bridge"])
R["uncertain_n"] = int(((P.confidence == "uncertain") & (P.cls != "other")).sum())
R["uncertain_names"] = sorted(P[(P.confidence == "uncertain") & (P.cls != "other")].name1.unique().tolist())
R["rules"] = {k: int(v) for k, v in P[P.cls != "other"].rule.value_counts().items()}
R["welsh_pont"] = int(P.rule.str.startswith("welsh-pont", na=False).sum())
R["welsh_rhyd"] = int(P.rule.str.startswith("welsh-rhyd", na=False).sum())
R["bridge_of"] = int(P.rule.str.startswith("bridge-of", na=False).sum())
two_word = P.element.fillna("").str.lower().isin(["bridge", "ford", "bridges", "brig", "brigg", "fords"])
R["standalone_word"] = {k: int(((P.cls == k) & two_word).sum()) for k in ["ford", "bridge"]}
lt = P[P.cls != "other"].groupby(["cls", "local_type"]).size().unstack(fill_value=0)
R["by_type"] = {c: {k: int(v) for k, v in lt.loc[c].items()} for c in lt.index}

EW = P[P.country != "Scotland"].copy()
EW["region"] = EW.region_ons
EW["inc"] = np.where((EW.bua_primary == True) & (EW.income_source == "own MSOAs"), EW.bua_inc_total, EW.msoa_inc_total)
EW["size"] = [size_class(p) if b == True else SIZE[0][1] for p, b in zip(EW.bua_pop, EW.bua_primary)]
R["ew_places"] = int(len(EW))
R["ew_counts"] = {k: int((EW.cls == k).sum()) for k in CL}

# ------------------------------------------------------------ BUA unit
U = EW[(EW.bua_primary == True) & (EW.bua_pop > 0)].copy()
# London's built-up area is split by borough in BUA22: borough names are not settlements
lon_b = U.region == "London"
R["london_bua_dropped"] = U[lon_b & (U.cls != "other")].name1.tolist()
U = U[~lon_b]
U["inc"] = U.bua_inc_total
U["mass"] = U.bua_pop * U.inc
R["bua_unit_n"] = {k: int((U.cls == k).sum()) for k in CL}
R["bua_n_total_ew"] = int(len(U))
tot = {}
for k in CL:
    s = U[U.cls == k]
    tot[k] = {
        "n": int(len(s)), "pop": int(s.bua_pop.sum()),
        "pop_share": r2(s.bua_pop.sum() / NAT["msoa_pop_total"], 4),
        "income_share": r2(s.mass.sum() / NAT["income_mass_total"], 4),
        "inc_popweighted": r2(s.mass.sum() / s.bua_pop.sum(), 0),
        "inc_median": r2(s.inc.median(), 0), "pop_median": r2(s.bua_pop.median(), 0),
        "pop_mean": r2(s.bua_pop.mean(), 0),
        "inc_q25": r2(s.inc.quantile(.25), 0), "inc_q75": r2(s.inc.quantile(.75), 0),
        "n_over_20k": int((s.bua_pop >= 20000).sum()),
    }
R["totals"] = tot
for k, nm in [("ford", "Bradford"), ("bridge", "Cambridge")]:
    s = U[(U.cls == k) & (U.name1 != nm)]
    R[f"{k}_popweighted_without_{nm.lower()}"] = r2(s.mass.sum() / s.bua_pop.sum(), 0)
ms_ = pd.read_csv("/home/claude/hist/_data8/census/census2021-ts001-msoa.csv")
R["msoa_pop_median"] = int(ms_["Residence type: Total; measures: Value"].median())
R["ew_pop_total"] = int(NAT["msoa_pop_total"])
R["ew_inc_popweighted"] = r2(NAT["inc_total_popweighted"], 0)
R["ford_bridge_pop_ratio"] = r2(tot["ford"]["pop"] / tot["bridge"]["pop"])
R["ford_bridge_income_ratio"] = r2(tot["ford"]["income_share"] / tot["bridge"]["income_share"])
R["ford_bridge_n_ratio"] = r2(tot["ford"]["n"] / tot["bridge"]["n"])
R["bridge_minus_ford_popweighted"] = r2(tot["bridge"]["inc_popweighted"] - tot["ford"]["inc_popweighted"], 0)
R["bridge_minus_ford_median_bua"] = r2(tot["bridge"]["inc_median"] - tot["ford"]["inc_median"], 0)
# without the biggest place in each class
for k in ["ford", "bridge"]:
    s = U[U.cls == k].sort_values("bua_pop", ascending=False)
    R[f"top_{k}"] = [{"name": r.disp, "bua": r.bua_name, "pop": int(r.bua_pop), "inc": r2(r.inc, 0), "region": r.region,
                      "county": r.county if isinstance(r.county, str) else ""} for r in s.head(12).itertuples()]
    R[f"{k}_pop_without_top1"] = int(s.bua_pop.iloc[1:].sum())
    rich = s.sort_values("inc", ascending=False)
    R[f"richest_{k}"] = [{"name": r.disp, "pop": int(r.bua_pop), "inc": r2(r.inc, 0), "region": r.region} for r in rich.head(8).itertuples()]
    R[f"poorest_{k}"] = [{"name": r.disp, "pop": int(r.bua_pop), "inc": r2(r.inc, 0), "region": r.region} for r in rich.tail(8).iloc[::-1].itertuples()]
U.assign(inc=U.inc.round(0))[["place_id", "name1", "name2", "cls", "rule", "confidence", "local_type", "county", "region", "bua", "bua_name", "bua_pop",
   "inc", "bua_inc_net_ahc", "income_source", "lat", "lon"]].rename(columns={"inc": "mean_household_income_fye2023", "bua_inc_net_ahc": "net_equivalised_income_ahc"}) \
    .to_csv(os.path.join(ROOT, "data", "settlements_ew.csv"), index=False)

# ------------------------------------------------------------ place unit: distributions
A = EW.dropna(subset=["inc"]).copy()
R["place_unit_n"] = {k: int((A.cls == k).sum()) for k in CL}
R["place_median_inc"] = {k: r2(A[A.cls == k].inc.median(), 0) for k in CL}
bins = list(range(25000, 105001, 5000))
hist = {}
for k in CL:
    v = A[A.cls == k].inc.clip(25000, 104999)
    h, _ = np.histogram(v, bins=bins)
    hist[k] = [r2(x / h.sum(), 4) for x in h]
R["hist"] = {"bins": bins, **hist}
R["place_share_town"] = {k: r2(A[A.cls == k].local_type.isin(["Town", "City"]).mean(), 4) for k in CL}

# ------------------------------------------------------------ size-matched
sz = []
for _, lab in SIZE:
    row = {"size": lab}
    for k in CL:
        s = A[(A.cls == k) & (A["size"] == lab)]
        row[k] = {"n": int(len(s)), "median": r2(s.inc.median(), 0) if len(s) else None}
    sz.append(row)
R["size_matched"] = sz
R["size_share"] = {k: {lab: r2((A[A.cls == k]["size"] == lab).mean(), 4) for _, lab in SIZE} for k in CL}

# ------------------------------------------------------------ regions
rg = []
for reg in REG_ORDER:
    row = {"region": reg}
    for k in CL:
        s = A[(A.cls == k) & (A.region == reg)]
        row[k] = {"n": int(len(s)), "median": r2(s.inc.median(), 0) if len(s) else None}
    if row["ford"]["median"] and row["bridge"]["median"]:
        row["bridge_vs_ford"] = r2(row["bridge"]["median"] / row["ford"]["median"] - 1, 4)
    rg.append(row)
R["regions"] = rg
R["regions_bridge_ahead"] = sum(1 for r in rg if r.get("bridge_vs_ford", 0) > 0)
R["regions_ford_ahead"] = sum(1 for r in rg if r.get("bridge_vs_ford", 0) < 0)
se = ["London", "South East", "East of England"]
R["share_south_east"] = {k: r2(A[A.cls == k].region.isin(se).mean(), 4) for k in CL}
R["region_share"] = {k: {reg: r2((A[A.cls == k].region == reg).mean(), 4) for reg in REG_ORDER} for k in CL}

# ------------------------------------------------------------ bridge premium: models
A["linc"] = np.log(A.inc)
A["cls_f"] = pd.Categorical(A.cls, categories=["ford", "bridge", "other"])
A["size_f"] = A["size"]


def prem(formula, data):
    m = smf.ols(formula, data=data).fit(cov_type="HC1")
    b = m.params["cls_f[T.bridge]"]
    lo, hi = m.conf_int().loc["cls_f[T.bridge]"]
    o = m.params["cls_f[T.other]"]
    return {"bridge": r2(np.exp(b) - 1, 4), "lo": r2(np.exp(lo) - 1, 4), "hi": r2(np.exp(hi) - 1, 4),
            "p": r2(m.pvalues["cls_f[T.bridge]"], 4), "other": r2(np.exp(o) - 1, 4), "n": int(m.nobs), "r2": r2(m.rsquared, 3)}


R["premium"] = {
    "raw": prem("linc ~ cls_f", A),
    "size": prem("linc ~ cls_f + C(size_f)", A),
    "region": prem("linc ~ cls_f + C(region)", A),
    "both": prem("linc ~ cls_f + C(size_f) + C(region)", A),
    "both_plus_type": prem("linc ~ cls_f + C(size_f) + C(region) + C(local_type)", A),
}
Ub = U.copy()
Ub["linc"] = np.log(Ub.inc)
Ub["cls_f"] = pd.Categorical(Ub.cls, categories=["ford", "bridge", "other"])
Ub["lpop"] = np.log10(Ub.bua_pop)
R["premium_bua"] = {"raw": prem("linc ~ cls_f", Ub), "both": prem("linc ~ cls_f + lpop + C(region)", Ub)}
# bootstrap the ratio of medians (place unit)
f = A[A.cls == "ford"].inc.values
b = A[A.cls == "bridge"].inc.values
bs = [np.median(rng.choice(b, len(b))) / np.median(rng.choice(f, len(f))) - 1 for _ in range(2000)]
R["median_ratio_boot"] = {"est": r2(np.median(b) / np.median(f) - 1, 4), "lo": r2(np.percentile(bs, 2.5), 4), "hi": r2(np.percentile(bs, 97.5), 4)}

# robustness: drop uncertain names; drop stand-alone words (X Bridge, Ford End); England only
rob = {}
rob["no_uncertain"] = prem("linc ~ cls_f + C(size_f) + C(region)", A[A.confidence != "uncertain"])
rob["no_standalone"] = prem("linc ~ cls_f + C(size_f) + C(region)", A[~A.element.fillna("").str.lower().isin(["bridge", "ford", "bridges", "brig", "brigg", "fords"])])
rob["england"] = prem("linc ~ cls_f + C(size_f) + C(region)", A[A.country == "England"])
rob["net_ahc"] = None
A2 = EW.copy()
A2["inc2"] = np.where((A2.bua_primary == True) & (A2.income_source == "own MSOAs"), A2.bua_inc_net_ahc, np.nan)
A2 = A2.dropna(subset=["inc2"])
A2["linc"] = np.log(A2.inc2)
A2["cls_f"] = pd.Categorical(A2.cls, categories=["ford", "bridge", "other"])
A2["size_f"] = A2["size"]
rob["net_ahc_bua"] = prem("linc ~ cls_f + C(size_f) + C(region)", A2)
del rob["net_ahc"]
R["robust"] = rob

# ------------------------------------------------------------ size: did bridges make places big?
R["size_models"] = {}
for nm, d in [("bua", Ub)]:
    m = smf.ols("lpop ~ cls_f + C(region)", data=d).fit(cov_type="HC1")
    R["size_models"][nm] = {"bridge": r2(10 ** m.params["cls_f[T.bridge]"] - 1, 4), "lo": r2(10 ** m.conf_int().loc["cls_f[T.bridge]", 0] - 1, 4),
                            "hi": r2(10 ** m.conf_int().loc["cls_f[T.bridge]", 1] - 1, 4), "p": r2(m.pvalues["cls_f[T.bridge]"], 4), "n": int(m.nobs)}
R["has_bua_share"] = {k: r2(((EW.cls == k) & (EW.bua_primary == True) & (EW.bua_pop > 0)).sum() / (EW.cls == k).sum(), 4) for k in CL}

# ------------------------------------------------------------ Domesday (England)
E = P[P.country == "England"].copy()
E["dd"] = E.domesday.astype(str).str.lower().isin(["true", "1", "1.0"])
dd = {}
for k in CL:
    s = E[E.cls == k]
    s2 = s[s.dd]
    dd[k] = {"n": int(len(s)), "in_domesday": int(s.dd.sum()), "share": r2(s.dd.mean(), 4),
             "hh_median": r2(s2.domesday_households.median(), 1), "burgess_places": int((s2.domesday_burgesses > 0).sum()),
             "burgess_share_of_dd": r2((s2.domesday_burgesses > 0).mean(), 4)}
    # villages and towns only (hamlets and suburbs are often later)
    s3 = s[s.local_type.isin(["Town", "City", "Village"])]
    dd[k]["share_tv"] = r2(s3.dd.mean(), 4)
    dd[k]["n_tv"] = int(len(s3))
R["domesday"] = dd
# among English BUA-unit places: is 1086 status related to size today, and does the bridge gap remain?
Ue = U[U.country == "England"].copy()
Ue["dd"] = Ue.domesday.astype(str).str.lower().isin(["true", "1", "1.0"])
R["domesday_bua"] = {k: {"n": int((Ue.cls == k).sum()), "dd_share": r2(Ue[Ue.cls == k].dd.mean(), 4),
                         "pop_median_dd": r2(Ue[(Ue.cls == k) & Ue.dd].bua_pop.median(), 0),
                         "pop_median_notdd": r2(Ue[(Ue.cls == k) & ~Ue.dd].bua_pop.median(), 0)} for k in CL}
Ue["lpop"] = np.log10(Ue.bua_pop)
Ue["lhh"] = np.log10(Ue.domesday_households.clip(lower=1))
Ue["cls_f"] = pd.Categorical(Ue.cls, categories=["ford", "bridge", "other"])
sub = Ue[Ue.dd & Ue.domesday_households.notna()]
m = smf.ols("lpop ~ lhh + cls_f + C(region)", data=sub).fit(cov_type="HC1")
R["domesday_bridge_towns"] = Ue[(Ue.cls == "bridge") & Ue.dd].sort_values("bua_pop", ascending=False).name1.tolist()
R["domesday_size_model"] = {"n": int(m.nobs), "lhh": r2(m.params["lhh"], 3), "bridge": r2(10 ** m.params["cls_f[T.bridge]"] - 1, 4),
                            "bridge_p": r2(m.pvalues["cls_f[T.bridge]"], 4), "r2": r2(m.rsquared, 3)}
R["domesday_boroughs_named"] = {k: sorted(set(E[(E.cls == k) & E.dd & (E.domesday_burgesses > 0)].name1))[:40] for k in ["ford", "bridge"]}

# ------------------------------------------------------------ medieval bridges
Bd = pd.read_csv(os.path.join(ROOT, "data", "bridges_dated.csv"))
R["bridges_total"] = int(len(Bd))
R["bridges_wikidata"] = int((Bd.source == "Wikidata").sum())
R["bridges_wikidata_dated"] = int(((Bd.source == "Wikidata") & Bd.year.notna()).sum())
R["bridges_medieval"] = int(Bd.medieval.sum())
R["bridges_pre1700"] = int(Bd.pre1700.sum())
R["bridges_medieval_list"] = [{"name": r.label, "year": int(r.year)} for r in Bd[Bd.medieval].sort_values("year").itertuples()]
mb = {}
for k in CL:
    s = P[P.cls == k]
    mb[k] = {"n": int(len(s)), "with_medieval_1km": int((s.medieval_bridges_1km > 0).sum()),
             "with_pre1700_1km": int((s.pre1700_bridges_1km > 0).sum()),
             "share_medieval_1km": r2((s.medieval_bridges_1km > 0).mean(), 5),
             "with_any_bridge_record_1km": r2((s.any_bridges_1km > 0).mean(), 4)}
R["medieval_bridges"] = mb
# towns and cities with a dated medieval bridge within 1 km against those without (BUA unit, E&W)
U["mb"] = U.medieval_bridges_1km > 0
U["pb"] = U.pre1700_bridges_1km > 0
R["medieval_bridge_towns"] = {
    "with_n": int(U.mb.sum()), "with_pop_median": r2(U[U.mb].bua_pop.median(), 0), "with_inc_median": r2(U[U.mb].inc.median(), 0),
    "without_pop_median": r2(U[~U.mb].bua_pop.median(), 0), "without_inc_median": r2(U[~U.mb].inc.median(), 0),
    "with_names": U[U.mb].sort_values("bua_pop", ascending=False).name1.tolist(),
    "pre1700_n": int(U.pb.sum()), "pre1700_pop_median": r2(U[U.pb].bua_pop.median(), 0),
}

# ------------------------------------------------------------ Roman roads and rivers
rr = {}
for k in CL:
    s = P[(P.cls == k) & (P.country != "Scotland")]
    rr[k] = {"median_km": r2(s.roman_road_km.median(), 2), "within_1km": r2((s.roman_road_km <= 1).mean(), 4),
             "river_median_km": r2(s.river_km.median(), 3), "river_within_250m": r2((s.river_km <= .25).mean(), 4)}
R["roman_rivers"] = rr
strat = P[P.name1.str.lower().str.match(r"^(stret|strat|strad|stret)ford", na=False) | P.name1.str.lower().str.contains(r"\bstr[ae]tford", na=False)]
R["street_fords"] = {"n": int(len(strat)), "within_1km_roman": int((strat.roman_road_km <= 1).sum()),
                     "names": sorted(set(strat.name1))}
# control: does adding Roman road distance change the premium?
A["lroman"] = np.log1p(A.roman_road_km)
R["premium"]["both_roman"] = prem("linc ~ cls_f + C(size_f) + C(region) + lroman", A)

# ------------------------------------------------------------ Scotland (secondary)
S = P[(P.country == "Scotland") & (P.cls != "other")]
R["scotland"] = {k: {"n": int((S.cls == k).sum()), "with_wd_pop": int(S[(S.cls == k)].wikidata_pop.notna().sum()),
                     "wd_pop_sum": int(S[S.cls == k].wikidata_pop.sum()),
                     "biggest": S[S.cls == k].sort_values("wikidata_pop", ascending=False).head(4).name1.tolist()} for k in ["ford", "bridge"]}
# Wikidata check against Census in E&W BUA unit
chk = U[U.wikidata_pop > 0]
R["wikidata_check"] = {"n": int(len(chk)), "spearman": r2(chk[["bua_pop", "wikidata_pop"]].corr("spearman").iloc[0, 1], 3)}

# ------------------------------------------------------------ examples for text
def one(name, county=None):
    s = U[U.name1 == name]
    if county:
        s = s[s.county == county]
    r = s.iloc[0]
    return {"name": name, "pop": int(r.bua_pop), "inc": r2(r.inc, 0), "region": r.region}


R["ex"] = {n.replace(" ", "_").replace("'", ""): one(n) for n in ["Bradford", "Oxford", "Cambridge", "Weybridge", "Stourbridge", "Guildford", "Salford", "Bridgend" if False else "Tonbridge", "Pontypridd", "Castleford", "Stalybridge", "Watford"]}
tb = [r["pop"] for r in R["top_bridge"]]
R["bradford_beats_top_k_bridges"] = max(k for k in range(1, len(tb) + 1) if sum(tb[:k]) < R["top_ford"][0]["pop"])
R["bradford_vs_top_k_sum"] = int(sum(tb[:R["bradford_beats_top_k_bridges"]]))
sb = S[S.cls == "bridge"].sort_values("wikidata_pop", ascending=False)
R["scotland"]["bridge"]["top1_pop"] = int(sb.wikidata_pop.iloc[0])
R["scotland"]["bridge"]["top1_share"] = r2(sb.wikidata_pop.iloc[0] / sb.wikidata_pop.sum(), 4)
R["exceptions_n"] = int(len(pd.read_csv(os.path.join(ROOT, "data", "name_exceptions.csv"))))

json.dump(R, open(os.path.join(ROOT, "data", "results.json"), "w"), indent=1, ensure_ascii=False)

# ------------------------------------------------------------ compact page data
M = P[P.cls != "other"].copy()
M["inc"] = np.where((M.bua_primary == True) & (M.income_source == "own MSOAs"), M.bua_inc_total, M.msoa_inc_total)
M["pop"] = np.where((M.bua_primary == True) & (M.bua_pop > 0) & (M.region_ons != "London"), M.bua_pop, np.nan)
M["dd"] = M.domesday.astype(str).str.lower().isin(["true", "1", "1.0"])
rows = []
for r in M.itertuples():
    rows.append([round(r.lat, 4), round(r.lon, 4), r.name1, r.name2 if isinstance(r.name2, str) else "", 0 if r.cls == "ford" else 1,
                 r.local_type, r.county if isinstance(r.county, str) else (r.district if isinstance(r.district, str) else ""),
                 r.region_ons, None if np.isnan(r.pop) else int(r.pop), None if np.isnan(r.inc) else int(round(r.inc, -1)),
                 1 if r.bua_primary == True and r.income_source == "own MSOAs" else 0,
                 int(r.domesday_households) if r.dd and not np.isnan(r.domesday_households) else (0 if r.dd else None),
                 r.medieval_bridges_1km, r2(r.roman_road_km, 1), 1 if r.confidence == "uncertain" else 0,
                 r.exception_note if isinstance(r.exception_note, str) else "", r.rule])
json.dump({"p": rows}, open(os.path.join(ROOT, "_site_data.json"), "w"), separators=(",", ":"), ensure_ascii=False)
print(json.dumps({k: R[k] for k in ["counts", "totals", "premium", "median_ratio_boot", "robust", "domesday", "medieval_bridges", "roman_rivers"]}, indent=1))
