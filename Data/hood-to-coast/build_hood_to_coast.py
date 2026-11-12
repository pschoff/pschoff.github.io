#!/usr/bin/env python3
"""Builds hood-to-coast.html from the Strava exports in this folder.

    python3 Data/hood-to-coast/build_hood_to_coast.py

Inputs:  legs.json (the three relay legs: summary, route polyline, time/distance/altitude streams)
         runs_2019.csv (every run Strava has from 2019)
Output:  ../../hood-to-coast.html (charts are inline SVG, no JavaScript)
"""
import csv, datetime as dt, json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'hood-to-coast.html')
INK, SOFT, FAINT, RULE, BLAZE, GREY, TINT = '#111', '#555', '#888', '#e8e2d6', '#b4462b', '#8a857a', '#f1ebdf'

MI, FT = 1609.344, 3.28084
COURSE_MI = 199                      # official length of the relay
HALF_2025 = 5888 / 13.1              # Dallas Half Marathon 2025, 1:38:08, seconds per mile
BEST_5K_2025 = 21 * 60 + 50
# Sunset 23 Aug and sunrise 24 Aug 2019 in Portland, to the nearest few minutes.
SUNSET = dt.datetime(2019, 8, 23, 20, 5)
SUNRISE = dt.datetime(2019, 8, 24, 6, 22)


# ---------------------------------------------------------------- data
def decode(s):                       # Google encoded polyline -> [(lat, lng)]
    out, i, lat, lng = [], 0, 0, 0
    while i < len(s):
        for which in (0, 1):
            shift = result = 0
            while True:
                b = ord(s[i]) - 63
                i += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            d = ~(result >> 1) if result & 1 else result >> 1
            if which == 0:
                lat += d
            else:
                lng += d
        out.append((lat / 1e5, lng / 1e5))
    return out


LEGS = json.load(open(os.path.join(HERE, 'legs.json')))['legs']
for L in LEGS:
    L['start'] = dt.datetime.fromisoformat(L['start_local'])
    L['end'] = L['start'] + dt.timedelta(seconds=L['elapsed_time_s'])
    L['mi'] = L['distance_m'] / MI
    L['pace'] = L['moving_time_s'] / L['mi']
    L['route'] = decode(L['polyline'])
    L['pts'] = [(d / MI, a * FT, t) for d, a, t in zip(L['distance'], L['altitude'], L['time'])]

runs = []
for r in csv.DictReader(open(os.path.join(HERE, 'runs_2019.csv'))):
    runs.append(dict(when=dt.datetime.fromisoformat(r['start_local']), mi=float(r['miles']),
                     t=int(r['moving_time_s']), leg=r['leg'], where=r['where']))
for r in runs:
    r['pace'] = r['t'] / r['mi']
TRAIN = [r for r in runs if not r['leg'] and r['when'] < LEGS[0]['start']]
AFTER = [r for r in runs if not r['leg'] and r['when'] > LEGS[0]['start']]


def mmss(s):
    s = round(s)
    return '%d:%02d' % (s // 60, s % 60)


def hm(seconds):
    m = round(seconds / 60)
    return '%d h %02d min' % (m // 60, m % 60)


def words(seconds):
    m = round(seconds / 60)
    return '%d hours %d minutes' % (m // 60, m % 60)


def hms(s):
    return '%d:%02d:%02d' % (s // 3600, s % 3600 // 60, s % 60)


def clock(d):
    return d.strftime('%-I:%M') + (' am' if d.hour < 12 else ' pm')


RUN_S = sum(L['moving_time_s'] for L in LEGS)
RUN_MI = sum(L['mi'] for L in LEGS)
SPAN_S = (LEGS[-1]['end'] - LEGS[0]['start']).total_seconds()
GAPS = [(LEGS[i + 1]['start'] - LEGS[i]['end']).total_seconds() for i in (0, 1)]
TRAIN_MI, TRAIN_S = sum(r['mi'] for r in TRAIN), sum(r['t'] for r in TRAIN)

# leg 22: the climb and the descent
P22 = LEGS[1]['pts']
TOP = max(range(len(P22)), key=lambda i: P22[i][1])


def stretch(p, i0, i1):
    return dict(mi=p[i1][0] - p[i0][0], ft=p[i1][1] - p[i0][1], pace=(p[i1][2] - p[i0][2]) / (p[i1][0] - p[i0][0]))


CLIMB, DROP = stretch(P22, 0, TOP), stretch(P22, TOP, len(P22) - 1)


# ---------------------------------------------------------------- svg helpers
def svg(w, h, body, label):
    return ('<svg class="chart" viewBox="0 0 %d %d" role="img" aria-label="%s" '
            'xmlns="http://www.w3.org/2000/svg">%s</svg>' % (w, h, label, ''.join(body)))


def text(x, y, s, anchor='start', cls='', fill=None, size=None):
    a = ' text-anchor="%s"' % anchor if anchor != 'start' else ''
    c = ' class="%s"' % cls if cls else ''
    f = ' fill="%s"' % fill if fill else ''
    z = ' font-size="%s"' % size if size else ''
    return '<text x="%.1f" y="%.1f"%s%s%s%s>%s</text>' % (x, y, a, c, f, z, s)


def line(x1, y1, x2, y2, stroke=FAINT, w=1, dash=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"%s/>' % (
        x1, y1, x2, y2, stroke, w, d)


def path(pts, stroke, w=1.6):
    d = 'M' + ' L'.join('%.1f %.1f' % p for p in pts)
    return '<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round"/>' % (d, stroke, w)


def rect(x, y, w, h, fill):
    return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>' % (x, y, w, h, fill)


def dot(x, y, r, fill, title=None, stroke=None):
    s = ' stroke="%s" stroke-width="1.4"' % stroke if stroke else ''
    t = '<title>%s</title>' % title if title else ''
    return '<circle cx="%.1f" cy="%.1f" r="%s" fill="%s"%s>%s</circle>' % (x, y, r, fill, s, t)


def scale(d0, d1, r0, r1):
    return lambda v: r0 + (v - d0) / (d1 - d0) * (r1 - r0)


# ---------------------------------------------------------------- fig 1: three marks on a map
PLACES = dict(timberline=(45.3311, -121.7110), portland=(45.5152, -122.6784), seaside=(45.9932, -123.9226))


def fig_map():
    W, l, r, t, b = 720, 20, 30, 34, 44
    lon0, lon1, lat0, lat1 = -124.0, -121.62, 45.27, 46.21
    k = math.cos(math.radians(45.65))
    px = (W - l - r) / ((lon1 - lon0) * k)                 # pixels per degree of latitude
    H = t + (lat1 - lat0) * px + b
    X = lambda lon: l + (lon - lon0) * k * px
    Y = lambda lat: t + (lat1 - lat) * px
    o = []
    for key, name, note, anchor, dx in (('timberline', 'Timberline Lodge', 'start, 6,000 ft', 'end', -9),
                                        ('seaside', 'Seaside', 'finish, the Pacific', 'start', 9)):
        la, lo = PLACES[key]
        o.append(dot(X(lo), Y(la), 3.5, 'none', stroke=INK))
        o.append(text(X(lo) + dx, Y(la) - 2, name, anchor, fill=INK))
        o.append(text(X(lo) + dx, Y(la) + 14, note, anchor, 'it'))
    la, lo = PLACES['portland']
    o.append(dot(X(lo), Y(la), 2, FAINT))
    o.append(text(X(lo), Y(la) + 18, 'Portland', 'middle', 'it'))
    for L in LEGS:
        o.append(path([(X(lo), Y(la)) for la, lo in L['route']], BLAZE, 2.4))
        xs = [X(lo) for _, lo in L['route']]
        ys = [Y(la) for la, _ in L['route']]
        when = '%s %s, %.1f mi' % (L['start'].strftime('%a'), clock(L['start']), L['mi'])
        if L['leg'] == 34:                                  # label beside the mark, clear of Seaside
            x, y, anchor = max(xs) + 10, (min(ys) + max(ys)) / 2 - 3, 'start'
        else:                                               # label above the mark
            x, y, anchor = (min(xs) + max(xs)) / 2, min(ys) - 25, 'middle'
        o.append(text(x, y, 'leg %d' % L['leg'], anchor, fill=BLAZE))
        o.append(text(x, y + 15, when, anchor, 'it'))
    # scale bar: 20 miles
    bar = 20 * MI / 111320 * px
    y = H - 22
    o.append(line(l + 6, y, l + 6 + bar, y, FAINT))
    o.append(line(l + 6, y - 3, l + 6, y + 3, FAINT))
    o.append(line(l + 6 + bar, y - 3, l + 6 + bar, y + 3, FAINT))
    o.append(text(l + 6 + bar + 8, y + 4, '20 miles', cls='it'))
    return svg(W, round(H), o, 'Map of north-west Oregon showing the three relay legs between Mount Hood and Seaside')


# ---------------------------------------------------------------- fig 2: the clock
def fig_clock():
    W, l, r, H = 720, 20, 20, 150
    t0, t1 = dt.datetime(2019, 8, 23, 19, 0), dt.datetime(2019, 8, 24, 15, 0)
    X = lambda d: l + (d - t0).total_seconds() / (t1 - t0).total_seconds() * (W - l - r)
    y = 84
    o = [rect(X(SUNSET), 30, X(SUNRISE) - X(SUNSET), y - 30, TINT)]
    o.append(text((X(SUNSET) + X(SUNRISE)) / 2, 24, 'night', 'middle', 'it'))
    o.append(text(X(SUNSET), 24, 'sunset', 'middle', 'it'))
    o.append(text(X(SUNRISE), 24, 'sunrise', 'middle', 'it'))
    o.append(line(X(t0), y, X(t1), y, FAINT))
    for L in LEGS:
        o.append(rect(X(L['start']), y - 12, max(X(L['end']) - X(L['start']), 2), 12, BLAZE))
        cx = (X(L['start']) + X(L['end'])) / 2
        o.append(text(cx, y - 34, 'leg %d' % L['leg'], 'middle', fill=BLAZE))
        o.append(text(cx, y - 19, mmss(L['moving_time_s']), 'middle', fill=INK))
    for i, g in enumerate(GAPS):
        cx = (X(LEGS[i]['end']) + X(LEGS[i + 1]['start'])) / 2
        o.append(text(cx, y - 19, hm(g) + ' off', 'middle', 'it'))
    h = t0
    while h <= t1:
        o.append(line(X(h), y, X(h), y + 4))
        if h.hour % 3 == 0:
            lab = {0: 'midnight', 12: 'noon'}.get(h.hour, h.strftime('%-I') + (' am' if h.hour < 12 else ' pm'))
            o.append(text(X(h), y + 19, lab, 'middle'))
        h += dt.timedelta(hours=1)
    o.append(text(X(dt.datetime(2019, 8, 23, 21, 0)), y + 37, 'Friday 23 August', 'middle', 'it'))
    o.append(text(X(dt.datetime(2019, 8, 24, 0, 0)) + 6, y + 37, 'Saturday 24 August', cls='it'))
    o.append(line(X(dt.datetime(2019, 8, 24, 0, 0)), y + 4, X(dt.datetime(2019, 8, 24, 0, 0)), y + 40, FAINT, 0.7, '2 3'))
    return svg(W, H, o, 'Timeline from Friday evening to Saturday afternoon showing three short runs separated by two long waits')


# ---------------------------------------------------------------- fig 3: the legs, small multiples
def smooth_pace(p, k=2):
    out = []
    for i in range(len(p)):
        a, z = max(0, i - k), min(len(p) - 1, i + k)
        out.append(((p[a][0] + p[z][0]) / 2, (p[z][2] - p[a][2]) / (p[z][0] - p[a][0])))
    return out[1:-1]


def fig_legs():
    W, l, r, gap = 720, 46, 14, 40
    t, ph, mid, eh, b = 58, 150, 58, 150, 44
    H = t + ph + mid + eh + b
    per_mi = (W - l - r - 2 * gap) / RUN_MI
    YP = scale(375, 555, t, t + ph)
    y0 = t + ph + mid
    YE = scale(0, 1300, y0 + eh, y0)
    o = []
    o.append(text(l, t - 42, 'Pace, minutes per mile', fill=INK, size=15))
    o.append(text(l, y0 - 14, 'Elevation, feet', fill=INK, size=15))
    for v in (390, 420, 450, 480, 510, 540):
        o.append(line(l, YP(v), W - r, YP(v), RULE))
        o.append(text(l - 6, YP(v) + 4, mmss(v), 'end'))
    for v in (0, 500, 1000):
        if v:
            o.append(line(l, YE(v), W - r, YE(v), RULE))
        o.append(text(l - 6, YE(v) + 4, '{:,}'.format(v), 'end'))
    x0 = l
    for L in LEGS:
        X = lambda m, x0=x0: x0 + m * per_mi
        p, x1 = L['pts'], x0 + L['mi'] * per_mi
        o.append(text(x0, t - 20, 'Leg %d' % L['leg'], fill=BLAZE))
        o.append(text(x0 + 46, t - 20, '%s/mi' % mmss(L['pace']), fill=INK))
        o.append(text(x0, t - 5, '%s, %s' % (L['start'].strftime('%a'), clock(L['start'])), cls='it'))
        o.append(line(x0, YP(L['pace']), x1, YP(L['pace']), FAINT, 0.8, '2 3'))
        o.append(path([(X(m), YP(min(max(s, 375), 555))) for m, s in smooth_pace(p) if m > 0.2], BLAZE, 1.8))
        o.append(path([(X(m), YE(f)) for m, f, _ in p], GREY, 1.6))
        rising = p[8][1] > p[0][1] + 40 and p[0][1] > 200
        o.append(text(x0 + 3, YE(p[0][1]) + (18 if rising else -8), '%.0f' % p[0][1]))
        o.append(text(x1 - 3, YE(p[-1][1]) - 8, '%.0f' % p[-1][1], 'end'))
        if L['leg'] == 22:
            o.append(dot(X(p[TOP][0]), YE(p[TOP][1]), 3, GREY))
            o.append(text(X(p[TOP][0]), YE(p[TOP][1]) - 9, '{:,.0f} ft'.format(p[TOP][1]), 'middle', fill=INK))
            o.append(line(X(p[TOP][0]), YP(555), X(p[TOP][0]), YE(p[TOP][1]) - 24, FAINT, 0.7, '2 3'))
        o.append(line(x0, y0 + eh, x1, y0 + eh))
        for m in range(0, int(L['mi']) + 1):
            o.append(line(X(m), y0 + eh, X(m), y0 + eh + 4))
            if m:
                o.append(text(X(m), y0 + eh + 18, str(m), 'middle'))
        x0 = x1 + gap
    o.append(text(l, y0 + eh + 36, 'miles into each leg', cls='it'))
    return svg(W, H, o, 'Pace and elevation along each of the three legs, drawn on shared scales')


# ---------------------------------------------------------------- fig 4: every run of 2019
def fig_log():
    W, l, r, t, H = 720, 46, 20, 40, 300
    yb = H - 62
    Y = scale(430, 580, t, yb)
    step = (W - l - r - 40) / (len(runs) - 1 + 1.2)        # extra room for two group gaps
    o = []
    for v in (450, 480, 510, 540, 570):
        o.append(line(l, Y(v), W - r, Y(v), RULE))
        o.append(text(l - 6, Y(v) + 4, mmss(v), 'end'))
    o.append(line(l, Y(HALF_2025), W - r, Y(HALF_2025), FAINT, 0.8, '2 3'))
    o.append(text(W - r, Y(HALF_2025) - 6, 'Dallas Half 2025, %s/mi' % mmss(HALF_2025), 'end', 'it'))
    x, xs = l + 26, []
    for i, rn in enumerate(runs):
        if i and (bool(rn['leg']) != bool(runs[i - 1]['leg'])):
            x += step * 0.6
        xs.append(x)
        race = bool(rn['leg'])
        tip = '%s, %s: %.1f mi at %s/mi' % (rn['when'].strftime('%-d %b'), rn['where'], rn['mi'], mmss(rn['pace']))
        o.append(dot(x, Y(rn['pace']), 4.5 if race else 3.5, BLAZE if race else GREY, tip))
        o.append(text(x, Y(rn['pace']) - 10, mmss(rn['pace']), 'middle', fill=BLAZE if race else SOFT))
        o.append(text(x, yb + 18, rn['when'].strftime('%-d %b'), 'middle', size=12))
        if race:
            o.append(text(x, yb + 33, 'leg ' + rn['leg'], 'middle', fill=BLAZE, size=12))
        x += step
    o.append(line(l, yb, W - r, yb))
    groups = ((0, len(TRAIN) - 1, 'five runs in eight days'), (len(TRAIN), len(TRAIN) + 2, 'the relay'),
              (len(TRAIN) + 3, len(runs) - 1, 'the rest of the year'))
    for a, z, name in groups:
        o.append(line(xs[a] - 14, yb + 44, xs[z] + 14, yb + 44, FAINT, 0.8))
        o.append(text((xs[a] + xs[z]) / 2, yb + 59, name, 'middle', 'it'))
    o.append(text(l, t - 22, 'Average pace, minutes per mile', fill=INK, size=15))
    return svg(W, H, o, 'Average pace of every run recorded in 2019, with the three relay legs highlighted')


# ---------------------------------------------------------------- page
def rows():
    out = []
    for L in LEGS:
        out.append('<tr><td>Leg %d</td><td>%s %s</td><td>%.1f</td><td>%s</td><td%s>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            L['leg'], L['start'].strftime('%a'), clock(L['start']), L['mi'], mmss(L['moving_time_s']),
            ' class="hi"' if L is LEGS[-1] else '', mmss(L['pace']), mmss(L['best_mile_s']), mmss(L['best_5k_s']),
            '{:,}'.format(L['gain_ft']) if L['gain_ft'] else '&mdash;'))
    out.append('<tr><td>All three</td><td></td><td>%.1f</td><td>%s</td><td>%s</td><td></td><td></td><td>%s</td></tr>' % (
        RUN_MI, hms(RUN_S), mmss(RUN_S / RUN_MI),
        '{:,}'.format(sum(L['gain_ft'] for L in LEGS))))
    return ''.join(out)


L10, L22, L34 = LEGS
V = dict(
    f1=fig_map(), f2=fig_clock(), f3=fig_legs(), f4=fig_log(), rows=rows(),
    run_mi=RUN_MI, course=COURSE_MI, share=100 * RUN_MI / COURSE_MI,
    span=words(SPAN_S), run_time=words(RUN_S), run_pct=100 * RUN_S / SPAN_S, off=words(SPAN_S - RUN_S),
    gap1=words(GAPS[0]), gap2=words(GAPS[1]),
    before_sunset=round((SUNSET - L10['start']).total_seconds() / 60), end10=clock(L10['end']),
    before_sunrise=round((SUNRISE - L22['start']).total_seconds() / 60),
    p10=mmss(L10['pace']), p22=mmss(L22['pace']), p34=mmss(L34['pace']),
    race_pace=mmss(RUN_S / RUN_MI),
    drop10=L10['pts'][0][1] - L10['pts'][-1][1],
    climb_ft=CLIMB['ft'], climb_mi=CLIMB['mi'], climb_pace=mmss(CLIMB['pace']), top=P22[TOP][1],
    drop_ft=-DROP['ft'], drop_mi=DROP['mi'], drop_pace=mmss(DROP['pace']),
    net34=L34['pts'][-1][1] - L34['pts'][0][1], hi34=max(f for _, f, _ in L34['pts']),
    k10=mmss(L10['best_5k_s']), k22=mmss(L22['best_5k_s']), k34=mmss(L34['best_5k_s']),
    m10=mmss(L10['best_mile_s']), m22=mmss(L22['best_mile_s']), m34=mmss(L34['best_mile_s']),
    train_n=len(TRAIN), train_mi=TRAIN_MI, train_pace=mmss(TRAIN_S / TRAIN_MI),
    train_days=(TRAIN[-1]['when'].date() - TRAIN[0]['when'].date()).days + 1,
    lead_days=(L10['start'].date() - TRAIN[0]['when'].date()).days,
    train_best=mmss(min(r['pace'] for r in TRAIN)), race_worst=mmss(max(L['pace'] for L in LEGS)),
    faster=round(TRAIN_S / TRAIN_MI - RUN_S / RUN_MI),
    year_n=len(runs), year_mi=sum(r['mi'] for r in runs), after_n=len(AFTER),
    half=mmss(HALF_2025), k2025=mmss(BEST_5K_2025), kgap=L34['best_5k_s'] - BEST_5K_2025,
)

PAGE = open(os.path.join(HERE, 'hood_to_coast_template.html')).read()
for k, v in V.items():
    for spec in ('.0f', '.1f', '.2f', ''):
        key = '{{%s%s}}' % (k, ':' + spec if spec else '')
        if key in PAGE:
            PAGE = PAGE.replace(key, format(v, spec) if spec else str(v))
assert '{{' not in PAGE, PAGE[PAGE.index('{{'):][:40]
open(OUT, 'w').write(PAGE)
print('wrote', os.path.normpath(OUT))
for k in sorted(V):
    if k not in ('f1', 'f2', 'f3', 'f4', 'rows'):
        print(' ', k, V[k] if isinstance(V[k], str) else round(V[k], 2))
for L in LEGS:
    km = sum(math.hypot((b[0] - a[0]) * 111.32, (b[1] - a[1]) * 111.32 * math.cos(math.radians(a[0])))
             for a, b in zip(L['route'], L['route'][1:]))
    print('  leg', L['leg'], 'route', L['route'][0], '->', L['route'][-1], '%.2f km on the map, %.2f km run' % (km, L['distance_m'] / 1000))
