#!/usr/bin/env python3
"""Builds running.html from the Strava exports in this folder.

    python3 Data/running/build_running.py

Inputs:  runs.csv (one row per run), race_2025_splits.csv (mile splits)
Output:  ../../running.html (charts are inline SVG, no JavaScript)
"""
import csv, datetime as dt, os, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'running.html')

RACE = {2025: dt.date(2025, 12, 14), 2026: dt.date(2026, 12, 13)}
FIRST_WEEK = -22          # the 2025 plan started 22 weeks before race day
INK, SOFT, FAINT, RULE, BLAZE, GREY = '#111', '#555', '#888', '#e8e2d6', '#b4462b', '#8a857a'

# ---------------------------------------------------------------- data
runs = []
for r in csv.DictReader(open(os.path.join(HERE, 'runs.csv'))):
    runs.append(dict(
        when=dt.datetime.fromisoformat(r['start_local']),
        date=dt.date.fromisoformat(r['start_local'][:10]),
        mi=float(r['miles']), t=int(r['moving_time_s']), pace=float(r['pace_s_per_mi']),
        temp=float(r['temp_f']) if r['temp_f'] else None, tm=r['treadmill'] == '1'))
splits = [(int(r['mile']), int(r['split_s']), float(r['avg_hr']))
          for r in csv.DictReader(open(os.path.join(HERE, 'race_2025_splits.csv')))]
course = [(int(r['time_s']), float(r['distance_m']) / 1609.34, float(r['altitude_m']) * 3.28084)
          for r in csv.DictReader(open(os.path.join(HERE, 'race_2025_course.csv')))]
TODAY = runs[-1]['date']


def mmss(s):
    s = round(s)
    return '%d:%02d' % (s // 60, s % 60)


def week_of(d, race):                      # 0 = race week (Mon-Sun), -1 the week before...
    return -((race - d).days // 7)


def build(year):
    race = RACE[year]
    wk = {w: [] for w in range(FIRST_WEEK, 1)}
    for r in runs:
        w = week_of(r['date'], race)
        if w in wk:
            wk[w].append(r)
    return wk


B = {y: build(y) for y in RACE}
LAST_FULL = week_of(TODAY, RACE[2026]) - 1          # last complete week of the 2026 build
miles = {y: {w: sum(r['mi'] for r in B[y][w]) for w in B[y]} for y in B}
longest = {y: {w: max([r['mi'] for r in B[y][w]] or [0]) for w in B[y]} for y in B}


def upto(y, w_end, w_start=FIRST_WEEK):
    rs = [r for w in range(w_start, w_end + 1) for r in B[y][w]]
    return dict(mi=sum(r['mi'] for r in rs), n=len(rs),
                pace=sum(r['t'] for r in rs) / sum(r['mi'] for r in rs),
                long=max(r['mi'] for r in rs),
                tens=sum(1 for r in rs if r['mi'] >= 9.95), twelves=sum(1 for r in rs if r['mi'] >= 11.95),
                temp=st.mean(r['temp'] for r in rs if r['temp'] is not None))


S25, S26 = upto(2025, LAST_FULL), upto(2026, LAST_FULL)
SPLIT = -10                                # early / late boundary used in the text
E25, E26 = upto(2025, SPLIT), upto(2026, SPLIT)
L25, L26 = upto(2025, LAST_FULL, SPLIT + 1), upto(2026, LAST_FULL, SPLIT + 1)
FULL25 = upto(2025, 0)
REST25 = upto(2025, 0, LAST_FULL + 1)

# heat: outdoor runs of 3+ miles, race excluded
heat = [r for r in runs if r['temp'] is not None and not r['tm'] and r['mi'] >= 3
        and r['pace'] < 620 and r['date'] != RACE[2025]]
hx, hy = [r['temp'] for r in heat], [r['pace'] for r in heat]
mx, my = st.mean(hx), st.mean(hy)
SLOPE = sum((x - mx) * (y - my) for x, y in zip(hx, hy)) / sum((x - mx) ** 2 for x in hx)
CORR = SLOPE * st.pstdev(hx) / st.pstdev(hy)
fit = lambda x: my + SLOPE * (x - mx)

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


def dot(x, y, r, fill, title=None, stroke=None, op=None):
    s = ' stroke="%s" stroke-width="1.4"' % stroke if stroke else ''
    o = ' fill-opacity="%s"' % op if op else ''
    t = '<title>%s</title>' % title if title else ''
    return '<circle cx="%.1f" cy="%.1f" r="%s" fill="%s"%s%s>%s</circle>' % (x, y, r, fill, s, o, t)


def scale(d0, d1, r0, r1):
    return lambda v: r0 + (v - d0) / (d1 - d0) * (r1 - r0)


def week_axis(o, X, y, weeks=(-22, -18, -14, -10, -5, 0)):
    o.append(line(X(FIRST_WEEK), y, X(0), y))
    for w in weeks:
        o.append(line(X(w), y, X(w), y + 4))
        o.append(text(X(w), y + 18, 'race week' if w == 0 else '%d' % -w, 'middle'))
    o.append(text(X(FIRST_WEEK), y + 36, 'weeks before race day', cls='it'))


# ---------------------------------------------------------------- fig 1: every run


def fig_timeline():
    W, H, l, r, t, b = 1000, 330, 34, 14, 26, 44
    d0, d1 = dt.date(2025, 7, 1), dt.date(2026, 12, 20)
    X = scale(0, (d1 - d0).days, l, W - r)
    x = lambda d: X((d - d0).days)
    Y = scale(0, 14.5, H - b, t)
    o = []
    for v, lab in ((5, '5'), (10, '10'), (13.1, '13.1 mi')):
        o.append(line(l, Y(v), W - r, Y(v), RULE))
        o.append(text(l - 6, Y(v) + 4, lab if v != 13.1 else '13.1', 'end'))
    o.append(text(l - 6, Y(14.5) + 2, 'miles', 'end', 'it'))
    o.append(line(l, H - b, W - r, H - b))
    m = dt.date(2025, 7, 1)
    while m < d1:
        o.append(line(x(m), H - b, x(m), H - b + 4))
        o.append(text(x(m) + 2, H - b + 18, m.strftime('%b')))
        if m.month == 1 or m == d0:
            o.append(text(x(m) + 2, H - b + 34, str(m.year), fill=INK))
        m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    for rr in runs:
        race = rr['date'] == RACE[2025]
        tip = '%s · %.1f mi at %s/mi' % (rr['date'].strftime('%-d %b %Y'), rr['mi'], mmss(rr['pace']))
        o.append(dot(x(rr['date']), Y(rr['mi']), 4 if race else 2.6, BLAZE if race else INK, tip,
                     op=None if race else '0.55'))
    # annotations
    o.append(text(x(RACE[2025]) + 2, Y(13.27) - 22, 'Dallas Half, 14 Dec · 1:38:08', 'end', fill=INK))
    o.append(dot(x(RACE[2026]), Y(13.1), 4, '#fffff8', stroke=BLAZE))
    o.append(text(x(RACE[2026]) - 8, Y(13.1) - 9, 'Dallas Half, 13 Dec', 'end', fill=INK))
    o.append(text(x(dt.date(2025, 7, 9)), Y(9.6), 'First run of the plan,'))
    o.append(text(x(dt.date(2025, 7, 9)), Y(9.6) + 15, '9 Jul, 87°F'))
    o.append(line(x(dt.date(2025, 7, 9)), Y(8.5), x(dt.date(2025, 7, 9)), Y(4.7), FAINT, 0.7))
    o.append(text(x(dt.date(2026, 1, 13)), Y(3.3), 'Mile trial, 5:39', 'middle'))
    o.append(line(x(dt.date(2026, 1, 13)), Y(2.9), x(dt.date(2026, 1, 13)), Y(1.5), FAINT, 0.7))
    g0, g1 = dt.date(2026, 2, 26), dt.date(2026, 3, 31)
    o.append(line(x(g0) + 4, Y(8.6), x(g1) - 4, Y(8.6), BLAZE, 1.4))
    o.append(text((x(g0) + x(g1)) / 2, Y(8.6) - 22, 'Broken leg:', 'middle', fill=INK))
    o.append(text((x(g0) + x(g1)) / 2, Y(8.6) - 7, '33 days off', 'middle', fill=INK))
    o.append(text(x(dt.date(2026, 9, 7)), Y(1.6), 'Paris', 'middle'))
    o.append(line(x(dt.date(2026, 9, 7)), Y(2.3), x(dt.date(2026, 9, 7)), Y(3.9), FAINT, 0.7))
    return svg(W, H, o, 'Every run from July 2025 to November 2026, plotted by date and distance')


# ---------------------------------------------------------------- fig 2: cumulative miles


def fig_cumulative():
    W, H, l, r, t, b = 720, 360, 40, 130, 24, 48
    X = scale(FIRST_WEEK - 1, 0, l, W - r)
    Y = scale(0, 450, H - b, t)
    o = []
    for v in (100, 200, 300, 400):
        o.append(line(l, Y(v), X(0), Y(v), RULE))
        o.append(text(l - 6, Y(v) + 4, str(v), 'end'))
    o.append(text(l - 6, Y(450) + 4, 'miles', 'end', 'it'))
    o.append(line(X(LAST_FULL), Y(0), X(LAST_FULL), Y(450), FAINT, 0.7, '2 3'))
    o.append(text(X(LAST_FULL) - 6, Y(450) + 4, 'five weeks out', 'end', 'it'))
    X2 = scale(FIRST_WEEK, 0, X(FIRST_WEEK), X(0))
    week_axis(o, X2, H - b)
    for y, col, last in ((2025, GREY, 0), (2026, BLAZE, LAST_FULL)):
        tot, pts = 0, [(X(FIRST_WEEK - 1), Y(0))]
        for w in range(FIRST_WEEK, last + 1):
            tot += miles[y][w]
            pts.append((X(w), Y(tot)))
            if w == LAST_FULL:
                at5 = (X(w), Y(tot), tot)
        o.append(path(pts, col, 2 if y == 2026 else 1.6))
        if y == 2025:
            o.append(dot(pts[-1][0], pts[-1][1], 3, col))
            o.append(text(pts[-1][0] + 9, pts[-1][1] + 1, '2025', fill=INK))
            o.append(text(pts[-1][0] + 9, pts[-1][1] + 17, '%.0f mi at the finish' % tot))
            o.append(dot(at5[0], at5[1], 3, col))
            o.append(text(at5[0] - 9, at5[1] - 9, '2025: %.0f mi' % at5[2], 'end'))
        else:
            o.append(dot(at5[0], at5[1], 4, col, stroke='#fffff8'))
            o.append(text(at5[0] + 10, at5[1] + 16, '2026: %.0f mi' % at5[2], fill=INK))
    return svg(W, H, o, 'Cumulative miles by week before race day, 2025 and 2026')


# ---------------------------------------------------------------- fig 3: weekly miles + long run


def fig_shape():
    W, l, r = 720, 40, 60
    ph, gap, t, b = 150, 46, 30, 48
    H = t + ph * 2 + gap + b
    X = scale(FIRST_WEEK, 0, l, W - r)
    o = []
    panels = (('Miles per week', miles, 36, (10, 20, 30), t),
              ('Longest run of the week', longest, 15, (5, 10, 13.1), t + ph + gap))
    for title, data, top, ticks, y0 in panels:
        Y = scale(0, top, y0 + ph, y0)
        o.append(text(l, y0 - 12, title, fill=INK, size=15))
        for v in ticks:
            o.append(line(l, Y(v), X(0), Y(v), RULE))
            o.append(text(l - 6, Y(v) + 4, ('%g' % v), 'end'))
        o.append(line(X(LAST_FULL), y0, X(LAST_FULL), y0 + ph, FAINT, 0.7, '2 3'))
        for y, col, last in ((2025, GREY, 0), (2026, BLAZE, LAST_FULL)):
            pts = [(X(w), Y(data[y][w])) for w in range(FIRST_WEEK, last + 1)]
            o.append(path(pts, col, 2 if y == 2026 else 1.4))
            for (px, py), w in zip(pts, range(FIRST_WEEK, last + 1)):
                o.append(dot(px, py, 2.4, col, '%d, %d weeks out: %.1f mi' % (y, -w, data[y][w])))
            if y == 2025:
                o.append(text(pts[-1][0] + 8, pts[-1][1] + 4, '2025', fill=INK))
            else:
                o.append(dot(pts[-1][0], pts[-1][1], 4, col, stroke='#fffff8'))
        if data is miles:
            o.append(text(X(-21), Y(23.8) - 9, '2026', 'middle', fill=INK))
            o.append(line(l, y0 + ph, X(0), y0 + ph))
        else:
            o.append(text(X(-21), Y(8.2) - 9, '2026', 'middle', fill=INK))
            week_axis(o, X, y0 + ph)
    return svg(W, H, o, 'Weekly mileage and longest run per week, 2025 and 2026 builds')


# ---------------------------------------------------------------- fig 4: heat


def fig_heat():
    W, H, l, r, t, b = 720, 380, 46, 30, 20, 48
    X = scale(28, 108, l, W - r)
    Y = scale(400, 600, t, H - b)          # faster at the top
    o = []
    for v in (420, 480, 540, 600):
        o.append(line(l, Y(v), W - r, Y(v), RULE))
        o.append(text(l - 6, Y(v) + 4, mmss(v), 'end'))
    o.append(text(l - 6, Y(400) + 2, 'min/mi', 'end', 'it'))
    o.append(line(X(min(hx)), H - b, X(max(hx)), H - b))
    for v in (32, 50, 70, 90, 105):
        o.append(line(X(v), H - b, X(v), H - b + 4))
        o.append(text(X(v), H - b + 18, '%d°F' % v, 'middle'))
    o.append(text(l, H - b + 36, 'temperature at the start of the run', cls='it'))
    for rr in heat:
        col = BLAZE if rr['date'].year == 2026 else GREY
        tip = '%s · %.1f mi at %s/mi, %.0f°F' % (rr['date'].strftime('%-d %b %Y'), rr['mi'], mmss(rr['pace']), rr['temp'])
        o.append(dot(X(rr['temp']), Y(rr['pace']), 3, col, tip, op='0.7'))
    o.append(path([(X(32), Y(fit(32))), (X(105), Y(fit(105)))], INK, 1))
    o.append(text(X(30), Y(548), 'Each 10°F costs about', fill=INK))
    o.append(text(X(30), Y(548) + 15, '%.0f seconds a mile' % (SLOPE * 10), fill=INK))
    race = [x for x in runs if x['date'] == RACE[2025]][0]
    o.append(dot(X(race['temp']), Y(race['pace']), 4, '#fffff8', stroke=INK))
    o.append(text(X(race['temp']) + 9, Y(race['pace']) - 6, 'Race day: 32°F, 7:31/mi', fill=INK))
    o.append(dot(X(80), Y(408), 3, GREY)); o.append(text(X(80) + 8, Y(408) + 4, '2025'))
    o.append(dot(X(90), Y(408), 3, BLAZE)); o.append(text(X(90) + 8, Y(408) + 4, '2026'))
    return svg(W, H, o, 'Average pace against temperature for every outdoor run of three miles or more')


# ---------------------------------------------------------------- fig 5: race splits


def fig_race():
    W, l, r = 720, 46, 96
    ph, gap, t, b = 150, 44, 30, 40
    H = t + ph + gap + 90 + b
    X = scale(1, 13, l, W - r)
    o = []
    Y = scale(400, 525, t, t + ph)
    o.append(text(l, t - 12, 'Pace for each mile', fill=INK, size=15))
    for v in (420, 450, 480, 510):
        o.append(line(l, Y(v), X(13), Y(v), RULE))
        o.append(text(l - 6, Y(v) + 4, mmss(v), 'end'))
    pts = [(X(m), Y(s)) for m, s, _ in splits]
    o.append(path(pts, BLAZE, 2))
    for (px, py), (m, s, h) in zip(pts, splits):
        o.append(dot(px, py, 3, BLAZE, 'Mile %d: %s, %.0f bpm' % (m, mmss(s), h)))
    fast = min(splits, key=lambda s: s[1])
    o.append(text(X(1) + 9, Y(splits[0][1]) + 4, mmss(splits[0][1]), fill=INK))
    o.append(text(X(fast[0]), Y(fast[1]) - 10, mmss(fast[1]), 'middle', fill=INK))
    o.append(text(X(13) + 9, Y(splits[-1][1]) + 4, mmss(splits[-1][1]) + ' uphill', fill=INK))
    y0 = t + ph + gap
    Y = scale(122, 170, y0 + 90, y0)
    o.append(text(l, y0 - 12, 'Average heart rate', fill=INK, size=15))
    pts = [(X(m), Y(h)) for m, _, h in splits]
    o.append(path(pts, GREY, 1.6))
    o.append(dot(pts[0][0], pts[0][1], 3, GREY)); o.append(dot(pts[-1][0], pts[-1][1], 3, GREY))
    o.append(text(pts[0][0] + 12, pts[0][1] + 12, '%.0f bpm' % splits[0][2]))
    o.append(text(pts[-1][0] + 9, pts[-1][1] + 4, '%.0f bpm' % splits[-1][2]))
    o.append(line(X(1), y0 + 90, X(13), y0 + 90))
    for m in range(1, 14):
        o.append(line(X(m), y0 + 90, X(m), y0 + 94))
        o.append(text(X(m), y0 + 108, str(m), 'middle'))
    o.append(text(l, y0 + 126, 'mile', cls='it'))
    return svg(W, H, o, 'Mile splits and heart rate from the 2025 Dallas Half Marathon')


# ---------------------------------------------------------------- fig 6: pace and elevation along the course
C_LOW1 = min(range(30), key=lambda i: course[i][2])            # bottom of the early drop
C_HIGH = max(range(len(course)), key=lambda i: course[i][2])
C_LOW2 = min(range(C_HIGH, len(course)), key=lambda i: course[i][2])
C_END = len(course) - 1


def leg(i0, i1):
    return dict(pace=(course[i1][0] - course[i0][0]) / (course[i1][1] - course[i0][1]),
                mi=course[i1][1] - course[i0][1], ft=course[i1][2] - course[i0][2])


LEGS = [leg(C_LOW1, C_HIGH), leg(C_HIGH, C_LOW2), leg(C_LOW2, C_END)]


def fig_course():
    W, l, r = 720, 46, 30
    ph, gap, eh, t, b = 190, 64, 110, 46, 44
    H = t + ph + gap + eh + b
    X = scale(0, 13.3, l, W - r)
    o = []
    cuts = [course[i][1] for i in (C_LOW1, C_HIGH, C_LOW2)]
    for c in cuts:
        o.append(line(X(c), t - 4, X(c), t + ph + gap + eh, FAINT, 0.7, '2 3'))
    # pace, smoothed over roughly 0.3 mile
    Y = scale(390, 570, t, t + ph)
    o.append(text(l, t - 30, 'Pace', fill=INK, size=15))
    for v in (420, 450, 480, 510, 540):
        o.append(line(l, Y(v), X(13.3), Y(v), RULE))
        o.append(text(l - 6, Y(v) + 4, mmss(v), 'end'))
    pts = []
    for i in range(1, len(course)):
        a, z = max(0, i - 2), min(C_END, i + 1)
        pc = (course[z][0] - course[a][0]) / (course[z][1] - course[a][1])
        pts.append((X((course[a][1] + course[z][1]) / 2), Y(pc)))
    o.append(path(pts, BLAZE, 1.8))
    names = ('the long climb', 'the descent', 'the last hill')
    spans = ((cuts[0], cuts[1]), (cuts[1], cuts[2]), (cuts[2], course[C_END][1]))
    for (a, z), lg, nm in zip(spans, LEGS, names):
        cx = (X(a) + X(z)) / 2
        o.append(text(cx, t - 14, '%s/mi' % mmss(lg['pace']), 'middle', fill=INK))
        o.append(text(cx, t - 29, nm, 'middle', 'it'))
    # elevation
    y0 = t + ph + gap
    Y = scale(380, 600, y0 + eh, y0)
    o.append(text(l, y0 - 14, 'Elevation', fill=INK, size=15))
    o.append(path([(X(m), Y(f)) for _, m, f in course], GREY, 1.6))
    for i, anchor, dx, dy in ((C_HIGH, 'middle', 0, -9), (C_LOW2, 'end', -8, -4)):
        o.append(dot(X(course[i][1]), Y(course[i][2]), 3, GREY))
        o.append(text(X(course[i][1]) + dx, Y(course[i][2]) + dy, '%.0f ft' % course[i][2], anchor, fill=INK))
    o.append(text(X(0) + 4, Y(course[0][2]) - 9, '%.0f ft' % course[0][2]))
    for (a, z), lg in zip(spans, LEGS):
        o.append(text((X(a) + X(z)) / 2, y0 - 14, '%+.0f ft' % lg['ft'], 'middle', 'it'))
    o.append(line(X(0), y0 + eh, X(13.1), y0 + eh))
    for m in list(range(0, 14)) :
        o.append(line(X(m), y0 + eh, X(m), y0 + eh + 4))
        if m: o.append(text(X(m), y0 + eh + 18, str(m), 'middle'))
    o.append(text(l, y0 + eh + 36, 'miles from the start', cls='it'))
    return svg(W, H, o, 'Pace and elevation along the 2025 Dallas Half Marathon course')


# ---------------------------------------------------------------- page
first6 = st.mean(s for _, s, _ in splits[:6])
last6 = st.mean(s for _, s, _ in splits[7:])
V = dict(
    f6=fig_course(), up=LEGS[0]['ft'], upmi=LEGS[0]['mi'], uppace=mmss(LEGS[0]['pace']), down=-LEGS[1]['ft'], downmi=LEGS[1]['mi'], downpace=mmss(LEGS[1]['pace']), lastft=LEGS[2]['ft'], lastpace=mmss(LEGS[2]['pace']), himi=course[C_HIGH][1],
    f1=fig_timeline(), f2=fig_cumulative(), f3=fig_shape(), f4=fig_heat(), f5=fig_race(),
    n=len(runs), total=sum(r['mi'] for r in runs),
    n25=sum(1 for r in runs if r['date'].year == 2025), n26=sum(1 for r in runs if r['date'].year == 2026),
    m25=S25['mi'], m26=S26['mi'], r25=S25['n'], r26=S26['n'], diff=abs(S25['mi'] - S26['mi']),
    p25=mmss(S25['pace']), p26=mmss(S26['pace']), pd=round(S25['pace'] - S26['pace']),
    t25=S25['temp'], t26=S26['temp'], lg25=S25['long'], lg26=S26['long'],
    tens25=S25['tens'], tens26=S26['tens'], tw25=S25['twelves'], tw26=S26['twelves'],
    e25=E25['mi'], e26=E26['mi'], ed=E26['mi'] - E25['mi'], l25=L25['mi'], l26=L26['mi'], ld=L25['mi'] - L26['mi'],
    full25=FULL25['mi'], rest25=REST25['mi'], restlong=REST25['long'],
    slope=SLOPE * 10, corr=CORR, nheat=len(heat), f50=mmss(fit(50)), f95=mmss(fit(95)),
    first6=mmss(first6), last6=mmss(last6), halfgap=round(first6 - last6),
    updated=TODAY.strftime('%-d %B %Y'),
)

PAGE = open(os.path.join(HERE, 'running_template.html')).read()
for k, v in V.items():
    for spec in ('.0f', '.1f', '.2f', ''):
        key = '{{%s%s}}' % (k, ':' + spec if spec else '')
        if key in PAGE:
            PAGE = PAGE.replace(key, format(v, spec) if spec else str(v))
assert '{{' not in PAGE, PAGE[PAGE.index('{{'):][:40]
open(OUT, 'w').write(PAGE)
print('wrote', os.path.normpath(OUT))
for k in sorted(V):
    if not (k.startswith('f') and len(k) == 2) or k in ('full25', 'first6', 'f50', 'f95'):
        print(' ', k, V[k] if isinstance(V[k], str) else round(V[k], 2))
