"""Rules that sort a place name into ford, bridge or other.

The rules are explicit and auditable. A name is split into tokens on spaces and hyphens.
Tokens after a linking word (on, upon, in, under, by, le, de, cum, juxta, next, the, of when
not a "Bridge of X" name) are ignored, so "Bradford on Avon" is judged on "Bradford".

1. "Bridge of X" / "Brig o' X" (a Scottish pattern): bridge.
2. The last remaining token that ends in a crossing word decides:
   ford, fords, forth  -> ford       (-forth is a northern spelling of ford, e.g. Garforth)
   bridge, bridges, brig, brigg -> bridge
   So "Stamford Bridge" and "Fordingbridge" are bridges, "Great Bridgeford" is a ford.
3. Welsh names in Wales put the generic word first: a name beginning Pont (or Pen-y-bont,
   "head of the bridge") is a bridge; a name beginning Rhyd is a ford.
4. Gaelic names (OS name in Gaelic) beginning Ath / Àth are fords.
5. English names where the crossing word comes first: a short curated list for bridges (Bridgend,
   Bridgnorth, Brigg, Brighouse, and transparent compounds such as Bridgefoot and Bridgetown), and
   for fords "Ford" followed by a common English generic (Fordham, Fordwich, Fordcombe).
6. The curated exceptions file (data/name_exceptions.csv) then overrides: names that look like
   fords or bridges but are not (Telford, Gifford), and names whose origin is disputed
   (Bridgwater, Seaforth), which are kept but flagged "uncertain" so results can be rerun
   without them. Every row there has a source note.

If name1 gives nothing, name2 (the Welsh, Gaelic or English alternative) is tried.
"""
import re

LINK = {"on", "upon", "in", "under", "by", "le", "la", "de", "cum", "juxta", "next", "the", "en", "with", "super", "sub"}
FORD = re.compile(r"(ford|fords|forth)$")
BRIDGE = re.compile(r"(bridge|bridges|brig|brigg)$")
# crossing word first (English), transparent modern compounds
BRIDGE_FIRST = {"bridgend", "bridgefoot", "bridgetown", "bridgeton", "bridgtown", "bridgehill",
                "bridgehouse", "bridgeyate", "bridgemead", "bridgnorth", "brigg", "brighouse"}
# ford first, followed by a common English generic word (Fordham, Fordwich, Fordcombe)
FORD_FIRST = re.compile(r"^ford(ham|wich|combe|gate|houses|street|ton|wells|ington|ley|moor)$")


def tokens(name):
    return [t for t in re.split(r"[\s\-]+", name.strip()) if t]


def classify_one(name, country, lang=""):
    """Return (cls, element, rule) for one name string, cls in ford/bridge/None."""
    if not name:
        return None, "", ""
    t = tokens(name)
    tl = [x.lower().strip("'’.,()") for x in t]
    # 1. Bridge of X / Brig o' X
    if len(tl) >= 2 and tl[0] in ("bridge", "brig") and tl[1] in ("of", "o", "o'", "o’"):
        return "bridge", t[0], "bridge-of"
    if tl and tl[0].startswith("brig") and "o'" in tl[0]:
        return "bridge", t[0], "bridge-of"
    # 4. Gaelic ath
    if lang == "gla" and re.match(r"^[aà]th\b", tl[0]):
        return "ford", t[0], "gaelic-ath"
    # 3. Welsh first element
    if country == "Wales":
        flat = re.sub(r"[\s\-']", "", name.lower())
        if flat.startswith("penybont") or flat.startswith("pont"):
            return "bridge", t[0], "welsh-pont"
        if flat.startswith("rhyd"):
            return "ford", t[0], "welsh-rhyd"
    # 2. last crossing token before any linking word
    head = []
    for x in tl:
        if x in LINK or x in ("of",):
            break
        head.append(x)
    best = None
    for i, x in enumerate(head):
        if FORD.search(x) and len(x) >= 4:
            best = ("ford", t[i], "ends-ford")
        elif BRIDGE.search(x) and len(x) >= 4:
            best = ("bridge", t[i], "ends-bridge")
    if best:
        return best
    # 5. crossing word first
    if tl[0] in BRIDGE_FIRST or tl[0] == "bridge-end":
        return "bridge", t[0], "bridge-first"
    if FORD_FIRST.match(tl[0]) and country == "England":
        return "ford", t[0], "ford-first"
    return None, "", ""


def classify(name1, name2, lang1, lang2, country):
    c, e, r = classify_one(name1, country, lang1)
    if c:
        # check the alternative name for a conflict
        c2, _, _ = classify_one(name2, country, lang2)
        conflict = bool(c2 and c2 != c)
        return c, e, r, conflict
    c, e, r = classify_one(name2, country, lang2)
    return c, e, (r + "-name2") if c else "", False


if __name__ == "__main__":
    tests = [("Bradford", "England", "ford"), ("Bradford on Avon", "England", "ford"), ("Stamford Bridge", "England", "bridge"),
             ("Fordingbridge", "England", "bridge"), ("Bridge of Allan", "Scotland", "bridge"), ("Brig o'Turk", "Scotland", "bridge"),
             ("Pontypridd", "Wales", "bridge"), ("Pen-y-bont ar Ogwr", "Wales", "bridge"), ("Rhydaman", "Wales", "ford"),
             ("Bridgend", "Wales", "bridge"), ("Garforth", "England", "ford"), ("Ponteland", "England", None),
             ("Brighton", "England", None), ("Bridport", "England", None), ("Great Bridgeford", "England", "ford"),
             ("Stratford-upon-Avon", "England", "ford"), ("Hebden Bridge", "England", "bridge"), ("Ford", "England", "ford"),
             ("Milford Haven", "Wales", "ford"), ("Haverfordwest", "Wales", None)]
    for n, ct, want in tests:
        got = classify_one(n, ct)[0]
        print(("ok  " if got == want else "DIFF"), n, got)
