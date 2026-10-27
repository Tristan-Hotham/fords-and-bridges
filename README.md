# Ford or Bridge?

Which British place-name type is richer today, the fords or the bridges, in total and per household? And did having a bridge help places grow? Every ford and bridge name in OS Open Names, set against the 2021 census, ONS small-area income estimates and Domesday Book.

**Interactive version:** https://tristan-hotham.github.io/fords-and-bridges/

**Paper:** Hotham, T. (2026) *Ford or Bridge? Crossing names and wealth in Britain today.* Zenodo. https://doi.org/10.5281/zenodo.23688579

This repository holds the interactive page, the place-level datasets, the computed results and the analysis code for a data study by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349).

## Headline results

- Great Britain has 1,129 ford places and 643 bridge places among 43,274 populated places. England has 1,034 fords to 434 bridges; Wales (110 to 50) and Scotland (99 to 45) have more bridges.
- In total, ford built-up areas in England and Wales (outside London) hold 2,290,193 people (3.8% of the population) against 867,692 (1.5%) for bridges: 2.6 times as many people and 2.6 times as much household income.
- Per household, the median ford town has a mean household income of £58,732, the median bridge town £51,752. Population-weighted, it is a tie (£55,537 against £55,664), because of Cambridge.
- Across all 37,191 named places in England and Wales, bridge places have household incomes 8.5% lower than ford places; 3.6% lower once region and size are held equal (95% interval 2.1% to 5.2%). On net equivalised income after housing costs the gap disappears (bridges 1.8% ahead, not significant).
- 57% of English ford-named towns and villages are recorded in Domesday Book, against 21% of bridge-named ones. Bridge names are younger; there is no evidence that they made places bigger.
- Only 26 bridges in Wikidata carry a date before 1540, too few for a direct test of medieval bridges.

## Files

- `index.html`: the interactive page (Leaflet map, charts). The data is embedded, so it works as a single file.
- `header.png`: social card (1200 by 630).
- `data/places_classified.csv`: every OS Open Names populated place in Great Britain with its class (ford, bridge, other), the name element and rule that decided it, and a confidence flag.
- `data/places_linked.csv`: the same places with their matched Built-up Area, Census 2021 population, income, region, Domesday match, nearby dated bridges, distance to a Roman road and to a named river.
- `data/settlements_ew.csv`: the 3,944 built-up areas in England and Wales (outside London) used for the totals, with population and income.
- `data/bua_ew.csv`: every Built-up Area in England and Wales with its population and income.
- `data/bridges_dated.csv`: bridges from Wikidata and OpenStreetMap with any start date.
- `data/name_exceptions.csv`: the curated corrections, each with a source.
- `data/results.json`: every number quoted on the page, the paper, the blog post and the collage.
- `code/name_rules.py`: the classification rules (run it to test them on examples).
- `code/01_classify.py`, `code/02_link.py`, `code/03_analyse.py`, `code/04_build_page.py`, `code/05_header.py`: run in that order.

## How to rerun

The scripts read the shared source files in place (paths at the top of each script): OS Open Names (compact TSV), ONS Built-up Areas 2022 and lookups, Census 2021 TS001, ONS income estimates for small areas FYE2023, a Wikidata and OpenStreetMap extract, the Domesday places table from the domesday-destiny project, the Itiner-e Roman roads and OS Open Rivers. Python 3 with pandas, numpy, scipy, shapely, pyproj, statsmodels, openpyxl and (for the header) playwright.

```
python3 code/01_classify.py
python3 code/02_link.py
python3 code/03_analyse.py
python3 code/04_build_page.py
python3 code/05_header.py
```

## Method in brief and limits

- A name is a ford if its last main word ends in -ford, -fords or -forth, a bridge if it ends in -bridge, -bridges, -brig or -brigg; "Bridge of" names are bridges; Welsh names beginning Pont or Pen-y-bont are bridges and Rhyd fords; Gaelic names beginning Àth are fords; a few crossing-first names (Bridgend, Brigg, Brighouse, Fordham, Fordwich) are included. 13 names were checked against a source and corrected or flagged; 6 are flagged as uncertain, and dropping them changes nothing.
- Population: the Census 2021 residents of the LSOAs whose best-fit Built-up Area (2022) has the place's name, within 3 km. Income: the population-weighted mean of mean total household income (FYE2023) over the MSOAs whose best-fit BUA it is, or the nearest MSOA by population-weighted centroid.
- London is split by borough in BUA22, so it is left out of the totals. Scotland has no comparable income data here.
- Correlation, not causation. Wikidata bridge dates cover a small, famous minority. Domesday matching is by name and misses renamed places.

## Sources and licences

- OS Open Names and OS Open Rivers: Contains OS data © Crown copyright and database right 2026. Open Government Licence v3.0.
- Census 2021 (TS001), Built-up Areas 2022, LSOA and MSOA lookups and population-weighted centroids, Income estimates for small areas, England and Wales, financial year ending 2023: Source: Office for National Statistics licensed under the Open Government Licence v3.0. Contains OS data © Crown copyright and database right 2026.
- Domesday: Hull Domesday Project, Professor J.J.N. Palmer, George Slater and the University of Hull (CC BY-NC-SA), via the realm-domesday repository (https://github.com/embabel-worlds/realm-domesday) and Open Domesday (https://opendomesday.org/).
- Wikidata (CC0) and OpenStreetMap (© OpenStreetMap contributors, ODbL), retrieved 27 October 2026.
- Roman roads: de Soto, P., Pažout, A., Brughmans, T. and others (2025). Itiner-e: a high-resolution dataset of roads of the Roman Empire. Scientific Data. https://zenodo.org/records/17122148 (CC BY 4.0).
- Base map tiles © Esri.

Because the Domesday figures are CC BY-NC-SA, the derived data (`data/`) and the page text are released under CC BY-NC-SA 4.0. The code (`code/`) is released under the MIT licence (see `LICENSE`).

## Citation

Hotham, T. (2026) *Ford or Bridge? Crossing names and wealth in Britain today.* Zenodo. https://doi.org/10.5281/zenodo.23688579

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
