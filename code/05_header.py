"""Step 5. Render header.png (1200x630 social card) with Playwright Chromium.

Fonts: set FONT_DIR to a folder holding Fraunces[SOFT,WONK,opsz,wght].ttf, SourceSerif4[opsz,wght].ttf and
IBMPlexMono-Regular.ttf / -Medium.ttf (github.com/google/fonts); otherwise system serif fonts are used.
Usage: python3 code/05_header.py   (after step 3, which writes _site_data.json)
"""
import json
import math
import os
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
S = json.load(open(os.path.join(ROOT, "_site_data.json")))["p"]
FD = os.environ.get("FONT_DIR", "")


def proj(lat, lon):
    return lon * math.cos(math.radians(54.5)), -lat


pts = [(proj(r[0], r[1]), r[4], r[8]) for r in S if r[0] < 58.8]  # leave out Shetland and Orkney for a bigger map
xs = [p[0][0] for p in pts]; ys = [p[0][1] for p in pts]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
H = 590; W = H * (x1 - x0) / (y1 - y0)
dots = []
for (x, y), t, pop in sorted(pts, key=lambda p: -(p[2] or 0)):
    r = 1.6 + (math.sqrt(pop) / 60 if pop else 0)
    dots.append(f'<circle cx="{(x - x0) / (y1 - y0) * H:.1f}" cy="{(y - y0) / (y1 - y0) * H:.1f}" r="{r:.1f}" fill="{"#2B5F8E" if t else "#B8621B"}" fill-opacity=".8" stroke="#EDF1F3" stroke-width=".6"/>')
ff = ""
if FD:
    ff = "".join(f"@font-face{{font-family:'{n}';src:url('file://{FD}/{f}');font-weight:{w};}}" for n, f, w in [
        ("Fraunces", "Fraunces[SOFT,WONK,opsz,wght].ttf", "100 900"), ("Source Serif 4", "SourceSerif4[opsz,wght].ttf", "200 900"),
        ("IBM Plex Mono", "IBMPlexMono-Regular.ttf", "400"), ("IBM Plex Mono", "IBMPlexMono-Medium.ttf", "500")])
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{ff}
body{{margin:0;width:1200px;height:630px;background:#EDF1F3;color:#16212A;overflow:hidden;position:relative;font-family:'Source Serif 4',Georgia,serif}}
.k{{position:absolute;left:70px;top:70px;font:500 15px/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#5D6B76;display:flex;gap:12px;align-items:center}}
.k b{{background:#2B5F8E;color:#fff;padding:7px 9px;font-weight:500}}
h1{{position:absolute;left:64px;top:118px;margin:0;font:900 128px/.9 Fraunces,Georgia,serif;letter-spacing:-.02em;font-variation-settings:"SOFT" 50}}
h1 .f{{color:#B8621B}} h1 .b{{color:#2B5F8E;display:block}}
p{{position:absolute;left:70px;top:380px;width:560px;margin:0;font-size:27px;line-height:1.36;color:#24323C}}
.ft{{position:absolute;left:70px;bottom:44px;font:400 14px/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#5D6B76}}
svg{{position:absolute;right:50px;top:20px}}
</style></head><body>
<div class="k"><b>Data study</b><span>History × data</span></div>
<h1><span class="f">Ford</span> or<span class="b">bridge?</span></h1>
<p>{R['counts']['GB']['ford']:,} fords, {R['counts']['GB']['bridge']:,} bridges. Ford towns hold {R['ford_bridge_pop_ratio']:.1f} times the people. Which is richer per household?</p>
<div class="ft">Dr Tristan Hotham · Independent researcher</div>
<svg width="{W:.0f}" height="{H}" viewBox="0 0 {W:.0f} {H}">{''.join(dots)}</svg>
</body></html>"""
tmp = os.path.join(ROOT, "_header.html"); open(tmp, "w").write(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 630})
    pg.goto("file://" + tmp); pg.wait_for_timeout(500)
    pg.screenshot(path=os.path.join(ROOT, "header.png")); b.close()
os.remove(tmp)
print("header.png written")
