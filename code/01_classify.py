"""Step 1. Classify every OS Open Names populated place as ford, bridge or other.

Input : /home/claude/hist/osnames_gb.tsv (OS Open Names, compact; OGL v3)
        data/name_exceptions.csv (curated corrections, each with a source)
Output: data/places_classified.csv (one row per populated place in Great Britain)

Usage: python3 code/01_classify.py [path/to/osnames_gb.tsv]
"""
import os
import sys
import pandas as pd
from name_rules import classify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/hist/osnames_gb.tsv"
TYPES = ["City", "Town", "Village", "Hamlet", "Suburban Area", "Other Settlement"]

d = pd.read_csv(SRC, sep="\t", dtype=str, keep_default_na=False)
d = d[(d.type == "populatedPlace") & d.local_type.isin(TYPES)].copy()
d["lat"] = d.lat.astype(float)
d["lon"] = d.lon.astype(float)
d["x"] = d.x.astype(float)
d["y"] = d.y.astype(float)

out = []
for r in d.itertuples(index=False):
    c, el, rule, conflict = classify(r.name1, r.name2, r.lang1, r.lang2, r.country)
    out.append((c or "other", el, rule, conflict))
d["cls"] = [o[0] for o in out]
d["element"] = [o[1] for o in out]
d["rule"] = [o[2] for o in out]
d["name_conflict"] = [o[3] for o in out]
d["confidence"] = "sure"
d["exception_note"] = ""

ex = pd.read_csv(os.path.join(ROOT, "data", "name_exceptions.csv"))
for e in ex.itertuples():
    m = ((d.name1 == e.name) | (d.name2 == e.name)) & (d.country == e.country)
    if e.decision in ("exclude", "add", "keep"):
        d.loc[m, "cls"] = e.cls
        d.loc[m, "confidence"] = e.confidence
        if e.decision != "keep":
            d.loc[m, "rule"] = "curated"
        d.loc[m, "exception_note"] = e.note
    elif e.decision == "checked":
        d.loc[m, "exception_note"] = e.note
# The rule result for Scottish "-forth" names other than Forth-like cases is less certain
# (Scots/Gaelic naming); flag a plain "Forth" village as uncertain.
d.loc[(d.name1 == "Forth") & (d.country == "Scotland"), "confidence"] = "uncertain"
# In Wales an English "-ford" name can be an anglicised Welsh "ffordd" (road), e.g. Brynffordd/Brynford.
wf = (d.country == "Wales") & (d.cls == "ford") & (d.name1.str.contains("ffordd") | d.name2.str.contains("ffordd"))
d.loc[wf, "confidence"] = "uncertain"
d.loc[wf, "exception_note"] = "Welsh form contains ffordd 'road'; the English -ford may be an anglicisation, so flagged"
# Places whose two names disagree are flagged too.
d.loc[d.name_conflict, "confidence"] = "uncertain"

d["place_id"] = range(1, len(d) + 1)
cols = ["place_id", "name1", "name2", "local_type", "country", "region", "county", "district", "lat", "lon", "x", "y",
        "cls", "element", "rule", "confidence", "exception_note"]
d[cols].to_csv(os.path.join(ROOT, "data", "places_classified.csv"), index=False)
print(d.groupby(["country", "cls"]).size().unstack())
print(d[d.cls != "other"].groupby(["cls", "local_type"]).size().unstack())
print(d[d.confidence == "uncertain"][["name1", "cls", "local_type"]].to_string())
