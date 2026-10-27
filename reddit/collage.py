"""r/dataisbeautiful collage: Ford or bridge? Run from this folder: python3 collage.py
Reads ../data/places_linked.csv, ../data/results.json and OS Open Rivers (named rivers, for the backdrop)."""
import json, sqlite3
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.collections import LineCollection
from shapely import wkb

F = '/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/'
for f in ['FrauncesVar.ttf', 'IBMPlexMono-Regular.ttf', 'IBMPlexMono-Medium.ttf', 'SourceSerif4-Regular.ttf', 'SourceSerif4-Semibold.ttf', 'SourceSerif4-It.ttf']:
    fm.fontManager.addfont(F + f)
DISP = fm.FontProperties(fname=F + 'FrauncesVar.ttf', weight=900)
SER = 'Source Serif 4'; MONO = 'IBM Plex Mono'
BG = '#E2EBF0'; FG = '#14202A'; MUT = '#566673'; RIV = '#9DBBD0'
FORD = '#B8621B'; BRIDGE = '#24578A'; OTHER = '#8E9AA3'
R = json.load(open('../data/results.json'))
P = pd.read_csv('../data/places_linked.csv', keep_default_na=False, na_values=[''], low_memory=False)
M = P[P.cls != 'other'].copy()
M['pop'] = np.where((M.bua_primary == True) & (M.bua_pop > 0) & (M.region_ons != 'London'), M.bua_pop, 0)
M = M.sort_values('pop', ascending=False)

# rivers: named rivers and tidal rivers from OS Open Rivers (British National Grid)
con = sqlite3.connect('file:/home/claude/hist/osrivers/Data/oprvrs_gb.gpkg?mode=ro', uri=True)
segs = []
for blob, in con.execute("select geometry from watercourse_link where form in ('inlandRiver','tidalRiver') and watercourse_name is not null"):
    env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(blob[3] >> 1) & 7]
    g = wkb.loads(bytes(blob[8 + env:]))
    segs.append(np.asarray(g.coords)[:, :2])
con.close()

fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BG)
t1 = fig.text(0.04, 0.968, 'Ford or bridge: ', fontproperties=DISP, fontsize=50, color=FORD, va='top')
bb = t1.get_window_extent(renderer=fig.canvas.get_renderer()).transformed(fig.transFigure.inverted())
fig.text(bb.x1, 0.968, 'which is richer?', fontproperties=DISP, fontsize=50, color=BRIDGE, va='top')
fig.text(0.04, 0.905, f"Every British place named after a river crossing, set against the 2021 census and ONS household income.\n"
         f"{R['counts']['GB']['ford']:,} fords (Oxford, Bradford, Welsh rhyd) and {R['counts']['GB']['bridge']:,} bridges (Cambridge, Tonbridge, Welsh pont).",
         family=SER, fontsize=15, color=FG, va='top', linespacing=1.4)

# hero map
ax = fig.add_axes([0.0, 0.25, 0.58, 0.62])
ax.add_collection(LineCollection(segs, colors=RIV, linewidths=0.35, rasterized=True))
sz = 4 + np.sqrt(M['pop']) / 5.5
ax.scatter(M.x, M.y, s=sz, c=np.where(M.cls == 'ford', FORD, BRIDGE), alpha=.88, lw=.4, edgecolors=BG, rasterized=True, zorder=3)
ax.set_xlim(90000, 660000); ax.set_ylim(5000, 990000); ax.set_aspect('equal'); ax.axis('off')
for nm, dx, dy in [('Bradford', 70000, 30000), ('Oxford', -170000, 15000), ('Cambridge', 40000, 70000), ('Bridgend', -125000, -60000), ('Watford', 60000, -95000)]:
    r = M[M.name1.eq(nm) | M.name2.eq(nm)].iloc[0]
    ax.annotate(nm, (r.x, r.y), (r.x + dx, r.y + dy), family=MONO, fontsize=11, color=FG, arrowprops=dict(arrowstyle='-', color=FG, lw=.8), zorder=5)
for t, c, y in [(f"ford   {R['counts']['GB']['ford']:,}", FORD, 0.70), (f"bridge {R['counts']['GB']['bridge']:,}", BRIDGE, 0.675)]:
    fig.text(0.40, y, '●', color=c, fontsize=16, va='center'); fig.text(0.425, y, t, family=MONO, fontsize=12, color=FG, va='center')
fig.text(0.40, 0.652, 'dot size = 2021 population\nfaint lines = named rivers', family=MONO, fontsize=10, color=MUT, va='top', linespacing=1.4)

# headline numbers
T = R['totals']
notes = [(f"{R['ford_bridge_pop_ratio']:.1f}×", FORD, f"as many people live in ford towns as in\nbridge towns ({T['ford']['pop'] / 1e6:.2f} million against\n{T['bridge']['pop'] / 1e6:.2f} million, England and Wales)."),
         (f"£{T['ford']['inc_median'] / 1000:.1f}k v £{T['bridge']['inc_median'] / 1000:.1f}k", FG, "median household income, typical ford\ntown against typical bridge town."),
         (f"{abs(R['premium']['both']['bridge']) * 100:.1f}%", BRIDGE, "lower household income in bridge places\nthan ford places, same region and size.\nAfter housing costs: no real gap."),
         (f"{R['domesday']['ford']['share_tv'] * 100:.0f}% v {R['domesday']['bridge']['share_tv'] * 100:.0f}%", FORD, "of ford and bridge towns and villages\nare in Domesday Book (1086). Bridge\nnames are younger, not bigger.")]
tx = fig.add_axes([0.6, 0.29, 0.38, 0.56]); tx.axis('off')
for (big, c, small), y in zip(notes, [1.0, 0.74, 0.52, 0.25]):
    tx.text(0, y, big, fontproperties=DISP, fontsize=30, color=c, va='top', transform=tx.transAxes)
    tx.text(0, y - 0.07, small, family=SER, fontsize=12.5, color=FG, va='top', transform=tx.transAxes, linespacing=1.3)

# bottom row 1: regions dumbbell
a = fig.add_axes([0.13, 0.095, 0.33, 0.15]); a.set_facecolor(BG)
rows = R['regions'][::-1]
for i, r in enumerate(rows):
    f, b = r['ford']['median'] / 1000, r['bridge']['median'] / 1000
    a.plot([f, b], [i, i], color=MUT, lw=1.2)
    a.scatter([f], [i], color=FORD, s=40, zorder=3); a.scatter([b], [i], color=BRIDGE, s=40, zorder=3)
a.set_yticks(range(len(rows))); a.set_yticklabels([r['region'].replace('Yorkshire and The Humber', 'Yorkshire') for r in rows], family=MONO, fontsize=9.5, color=FG)
a.set_xlabel('median household income, £k', family=MONO, fontsize=9.5, color=MUT)
a.tick_params(axis='x', labelsize=9.5, colors=MUT); a.tick_params(axis='y', length=0)
for s in ['top', 'right', 'left']: a.spines[s].set_visible(False)
a.spines['bottom'].set_color(MUT); a.grid(axis='x', color='#C7D5DE', lw=.6); a.set_axisbelow(True)
a.set_title(f"FORDS RICHER IN {R['regions_ford_ahead']} OF 10 REGIONS", family=MONO, fontsize=11, color=FG, loc='left', pad=8, x=-0.27)

# bottom row 2: bridge premium forest
b2 = fig.add_axes([0.70, 0.095, 0.27, 0.15]); b2.set_facecolor(BG)
Pm, Rb = R['premium'], R['robust']
rows = [('Raw', Pm['raw']), ('Same region', Pm['region']), ('Region + size', Pm['both']), ('England only', Rb['england']), ('After housing', Rb['net_ahc_bua'])][::-1]
for i, (t, e) in enumerate(rows):
    c = FORD if e['bridge'] < 0 else BRIDGE
    b2.plot([e['lo'] * 100, e['hi'] * 100], [i, i], color=c, lw=2.4, solid_capstyle='round'); b2.scatter([e['bridge'] * 100], [i], color=c, s=40, zorder=3)
b2.axvline(0, color=FG, lw=1)
b2.set_yticks(range(len(rows))); b2.set_yticklabels([r[0] for r in rows], family=MONO, fontsize=9.5, color=FG)
b2.set_xlim(-12, 8); b2.set_xticks([-10, -5, 0, 5]); b2.set_xticklabels(['-10', '-5', '0', '+5']); b2.set_xlabel('bridge v ford, % (95% interval)', family=MONO, fontsize=9.5, color=MUT)
b2.tick_params(axis='x', labelsize=9.5, colors=MUT); b2.tick_params(axis='y', length=0)
for s in ['top', 'right', 'left']: b2.spines[s].set_visible(False)
b2.spines['bottom'].set_color(MUT)
b2.set_title('THE "BRIDGE PREMIUM" IS NEGATIVE', family=MONO, fontsize=11, color=FG, loc='left', pad=8, x=-0.42)

fig.text(0.04, 0.012, "Data: OS Open Names and OS Open Rivers (contains OS data © Crown copyright and database right 2026, OGL v3); ONS Census 2021, Built-up Areas 2022 and\n"
         "Income estimates for small areas FYE2023 (OGL v3); Hull Domesday Project (CC BY-NC-SA). Income: mean total household income; England and Wales only;\n"
         "London left out of the totals. Correlation, not causation. Analysis and chart: Tristan Hotham, with Python and matplotlib.",
         family=MONO, fontsize=9, color=MUT, linespacing=1.45)
fig.savefig('ford_or_bridge.png', facecolor=BG, dpi=200)
print('ok')
