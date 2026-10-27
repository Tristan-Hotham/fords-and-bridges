"""Step 4. Build index.html from code/page_template.html.

Every number in the text is a {{path|format}} token filled from data/results.json, so the page cannot
drift from the analysis. The map data (_site_data.json from step 3) and a slim copy of results.json are
embedded so the page works as a single file.

Usage: python3 code/04_build_page.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, "data", "results.json"), encoding="utf-8"))
SITE_PATH = os.path.join(ROOT, "_site_data.json")
SITE = open(SITE_PATH, encoding="utf-8").read()
tpl = open(os.path.join(ROOT, "code", "page_template.html"), encoding="utf-8").read()
WORDS = "zero one two three four five six seven eight nine ten eleven twelve".split()


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f is None or f == "raw":
        return str(v)
    if f == "int":
        return f"{round(v):,}"
    if f == "absint":
        return f"{abs(round(v)):,}"
    if f == "pct":
        return f"{round(v * 100)}%"
    if f == "apct":
        return f"{abs(round(v * 100))}%"
    if f == "pct1":
        return f"{v * 100:.1f}%"
    if f == "apct1":
        return f"{abs(v * 100):.1f}%"
    if f == "f1":
        return f"{v:.1f}"
    if f == "f2":
        return f"{v:.2f}"
    if f == "m":
        return f"{round(v * 100) * 10:,} m"
    if f == "words":
        return WORDS[v] if v < len(WORDS) else str(v)
    raise ValueError(f)


def sub(m):
    return fmt(get(m.group(1)), m.group(3))


html = re.sub(r"\{\{([^}|]+)(\|(\w+))?\}\}", sub, tpl)
slim = {k: R[k] for k in ["totals", "top_ford", "top_bridge", "hist", "size_matched", "regions", "premium", "robust", "domesday"]}
html = html.replace("/*SITE*/", SITE).replace("/*RESULTS*/", json.dumps(slim, ensure_ascii=False, separators=(",", ":")))
assert "{{" not in html
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("index.html", len(html.encode()), "bytes")
md = re.sub(r"\{\{([^}|]+)(\|(\w+))?\}\}", sub, open(os.path.join(ROOT, "code", "README_template.md"), encoding="utf-8").read())
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(md)
print("README.md written")
