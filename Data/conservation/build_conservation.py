#!/usr/bin/env python3
"""Builds conservation.html from the three figure files one folder up.

    python3 Data/conservation/build_conservation.py

Input:   ../Figure_1.csv  Pittman-Robertson apportionments, FY1940-2018 (CRS R45667)
         ../Figure_2.csv  hunters as a share of the population, 1991-2016 (via NPR)
         ../Figure_3.csv  estimated gun sales, 2000-2017 (BuzzFeed News)
Output:  ../../conservation.html (charts are inline SVG, no JavaScript)
"""
import csv, html, os, re, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'conservation.html')
INK, SOFT, FAINT, RULE, BLAZE, GREY = '#111', '#555', '#888', '#e8e2d6', '#b4462b', '#8a857a'
REAL = 'Total Per Year (Real) Apportionments'


def rows(name):
    return list(csv.DictReader(open(os.path.join(HERE, '..', name), encoding='utf-8-sig')))


money = {int(r['Year of Fiscal Year']): float(r[REAL]) / 1e6 for r in rows('Figure_1.csv')}     # $M, 2012 dollars
nominal = {int(r['Year of Fiscal Year']): float(r['Total Per Year (Nominal Apportionments)']) / 1e6 for r in rows('Figure_1.csv')}
hunters = {int(r['Year']): float(r['Pct Pop']) for r in rows('Figure_2.csv')}
sales = {int(r['Year']): float(r['Annual Sales']) / 1e6 for r in rows('Figure_3.csv')}          # millions of guns


def esc(s):
    return html.escape(s, quote=True).replace("&#x27;", '&rsquo;')


# ---------------------------------------------------------------- svg helpers
def svg(w, h, body, label):
    return ('<svg class="chart" viewBox="0 0 %d %d" role="img" aria-label="%s" '
            'xmlns="http://www.w3.org/2000/svg">%s</svg>' % (w, h, esc(label), ''.join(body)))


def text(x, y, s, anchor='start', cls='', fill=None, size=None):
    a = ''
    if anchor != 'start': a += ' text-anchor="%s"' % anchor
    if cls: a += ' class="%s"' % cls
    css = ('fill:%s;' % fill if fill else '') + ('font-size:%spx;' % size if size else '')
    if css: a += ' style="%s"' % css          # inline style: the page CSS outranks attributes
    return '<text x="%.1f" y="%.1f"%s>%s</text>' % (x, y, a, esc(s))


def line(x1, y1, x2, y2, stroke=FAINT, w=1.0, dash=None):
    return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"%s/>' % (
        x1, y1, x2, y2, stroke, w, ' stroke-dasharray="%s"' % dash if dash else '')


def path(pts, stroke, w):
    return '<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round"/>' % (
        ' '.join('%.1f,%.1f' % p for p in pts), stroke, w)


def dot(x, y, fill, r=2.8, title=None):
    return '<circle cx="%.1f" cy="%.1f" r="%s" fill="%s">%s</circle>' % (
        x, y, r, fill, '<title>%s</title>' % esc(title) if title else '')


def dollars(m):
    return '$%.2f billion' % (m / 1000) if m >= 1000 else '$%.0f million' % m


# ---------------------------------------------------------------- figure 1: eighty years of money
def fig_money():
    W, H, L, R, T, B = 1200, 380, 60, 150, 24, 340
    y0, y1 = min(money), max(money)
    X = lambda yr: L + (yr - y0) * (W - L - R) / (y1 - y0)
    Y = lambda v: B - v * (B - T) / 800
    o = []
    for v in (200, 400, 600, 800):
        o.append(line(L, Y(v), X(y1), Y(v), RULE, 1))
        o.append(text(L - 8, Y(v) + 4, '$%dM' % v if v == 800 else str(v), anchor='end'))
    o.append(line(L, B + 0.5, X(y1), B + 0.5, FAINT, 1))
    for t in range(1940, 2011, 10):
        o.append(line(X(t), B, X(t), B + 5, FAINT, 1))
        o.append(text(X(t), B + 22, str(t), anchor='middle'))
    yrs = sorted(money)
    split = 2008
    o.append(path([(X(y), Y(money[y])) for y in yrs if y <= split], INK, 1.5))
    o.append(path([(X(y), Y(money[y])) for y in yrs if y >= split], BLAZE, 2))
    for y in yrs:                                    # invisible hover targets
        o.append('<circle cx="%.1f" cy="%.1f" r="6" fill="transparent"><title>%d: %s</title></circle>' % (
            X(y), Y(money[y]), y, dollars(money[y])))
    peak = max(money, key=money.get)
    o.append(dot(X(y0), Y(money[y0]), INK))
    o.append(text(X(y0) + 8, Y(money[y0]) - 16, '%d  %s' % (y0, dollars(money[y0])), fill=INK))
    o.append(dot(X(split), Y(money[split]), INK))
    o.append(text(X(split) - 10, Y(money[split]) - 8, '%d  %s' % (split, dollars(money[split])), anchor='end', fill=INK))
    o.append(dot(X(peak), Y(money[peak]), BLAZE))
    o.append(text(X(peak), Y(money[peak]) - 12, '%d  %s' % (peak, dollars(money[peak])), anchor='middle', fill=BLAZE))
    o.append(dot(X(y1), Y(money[y1]), BLAZE))
    o.append(text(X(y1) + 10, Y(money[y1]) + 4, '%d  %s' % (y1, dollars(money[y1])), fill=BLAZE))
    return svg(W, H, o, 'Pittman-Robertson apportionments per year in 2012 dollars, fiscal years 1940 to 2018')


# ---------------------------------------------------------------- figure 2: fewer hunters, more money
def fig_hunters():
    W, H, L, R, T, B = 720, 360, 150, 170, 30, 320
    yrs = sorted(hunters)
    base = yrs[0]
    hi = {y: 100 * hunters[y] / hunters[base] for y in yrs}
    mi = {y: 100 * money[y] / money[base] for y in yrs}
    X = lambda yr: L + (yr - base) * (W - L - R) / (yrs[-1] - base)
    Y = lambda v: B - v * (B - T) / 340
    o = [line(L, Y(100), X(yrs[-1]), Y(100), FAINT, 0.8, '2 4')]
    for y in yrs:
        o.append(line(X(y), B + 4, X(y), B + 9, FAINT, 1))
        o.append(text(X(y), B + 26, str(y), anchor='middle'))
    o.append(path([(X(y), Y(mi[y])) for y in yrs], BLAZE, 2))
    o.append(path([(X(y), Y(hi[y])) for y in yrs], INK, 1.6))
    for y in yrs:
        o.append(dot(X(y), Y(mi[y]), BLAZE, title='%d: %s' % (y, dollars(money[y]))))
        o.append(dot(X(y), Y(hi[y]), INK, title='%d: %.1f%% of Americans hunted' % (y, hunters[y])))
    a, z = yrs[0], yrs[-1]
    o.append(text(X(a) - 12, Y(100) - 8, dollars(money[a]), anchor='end', fill=BLAZE))
    o.append(text(X(a) - 12, Y(100) + 17, '%.1f%% hunt' % hunters[a], anchor='end', fill=INK))
    o.append(text(X(z) + 12, Y(mi[z]) - 3, dollars(money[z]), fill=BLAZE))
    o.append(text(X(z) + 12, Y(mi[z]) + 14, '%.1f times the %d money' % (mi[z] / 100, a), cls='it'))
    o.append(text(X(z) + 12, Y(hi[z]) - 3, '%.1f%% hunt' % hunters[z], fill=INK))
    o.append(text(X(z) + 12, Y(hi[z]) + 14, 'down %.0f%%' % (100 - hi[z]), cls='it'))
    o.append(text(X(1996) + 30, Y(100) - 7, '%d level' % a, cls='it'))
    return svg(W, H, o, 'Share of Americans who hunt and Pittman-Robertson funding, both indexed to 1991, through 2016')


# ---------------------------------------------------------------- figure 3: guns, then money
def fig_guns():
    W, L, R = 720, 100, 120
    yrs = sorted(sales)
    X = lambda yr: L + (yr - yrs[0]) * (W - L - R) / (yrs[-1] - yrs[0])
    o = []

    def panel(top, bot, series, vmax, colour, name, fmt, marks):
        Y = lambda v: bot - v * (bot - top) / vmax
        o.append(line(L, bot + 0.5, X(yrs[-1]), bot + 0.5, FAINT, 1))
        o.append(text(L, top - 8, name, fill=colour, size=14))
        o.append(path([(X(y), Y(series[y])) for y in yrs], colour, 1.8))
        for y in yrs:
            o.append('<circle cx="%.1f" cy="%.1f" r="6" fill="transparent"><title>%d: %s</title></circle>' % (
                X(y), Y(series[y]), y, fmt(series[y])))
        for y, anchor, dx, dy in marks:
            o.append(dot(X(y), Y(series[y]), colour))
            o.append(text(X(y) + dx, Y(series[y]) + dy, fmt(series[y]), anchor=anchor, fill=colour))
        return Y

    g = lambda v: '%.1f million' % v
    m = lambda v: '$%.0f million' % v
    Ys = panel(40, 170, sales, 18, INK, 'Guns sold, estimated', g,
               [(2000, 'end', -8, 4), (2013, 'middle', 0, -10), (2016, 'middle', 0, -10), (2017, 'start', 10, 4)])
    Ym = panel(230, 360, money, 850, BLAZE, 'Pittman-Robertson apportionments', m,
               [(2000, 'end', -8, 4), (2014, 'start', -4, -11), (2017, 'start', 10, 4)])
    for a in (2008, 2012):                           # the two step changes: a thin rule from one panel to the other
        o.append(line(X(a), Ys(sales[a]) + 6, X(a + 1), Ym(money[a + 1]) - 6, FAINT, 0.7, '2 3'))
    for t in range(2000, 2018):
        o.append(line(X(t), 360, X(t), 364 if t % 4 else 367, FAINT, 1))
        if t % 4 == 0:
            o.append(text(X(t), 384, str(t), anchor='middle'))
    return svg(W, 394, o, 'Estimated annual gun sales and Pittman-Robertson apportionments, 2000 to 2017')


# ---------------------------------------------------------------- numbers for the prose
def corr(x, y):
    mx, my = st.mean(x), st.mean(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (
        sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5


gy = sorted(sales)
hy = sorted(hunters)
peak = max(money, key=money.get)
trs = []
for y in hy:
    hot = ' class="hi"' if y == hy[-1] else ''
    trs.append('<tr><td%s>%d</td><td%s>%.1f%%</td><td%s>$%.0f</td></tr>' % (hot, y, hot, hunters[y], hot, money[y]))
V = dict(
    f1=fig_money(), f2=fig_hunters(), f3=fig_guns(),
    first=min(money), last=max(money), nyears=max(money) - min(money) + 1,
    m_first=money[min(money)], m_last=money[max(money)], nom_last=nominal[max(money)],
    peak=peak, m_peak=money[peak],
    pre=st.mean(money[y] for y in range(2000, 2009)), post=st.mean(money[y] for y in range(2013, 2018)),
    h_first=hunters[hy[0]], h_last=hunters[hy[-1]], hy0=hy[0], hy1=hy[-1],
    h_drop=100 * (1 - hunters[hy[-1]] / hunters[hy[0]]), m_mult=money[hy[-1]] / money[hy[0]],
    hunter_rows='\n            '.join(trs),
    g_first=sales[gy[0]], g_peak=max(sales.values()), g_peak_year=max(sales, key=sales.get),
    g13=sales[2013], m08=money[2008], m09=money[2009], m12=money[2012], m13=money[2013],
    r_same=corr([sales[y] for y in gy], [money[y] for y in gy]),
    r_lag=corr([sales[y] for y in gy[:-1]], [money[y + 1] for y in gy[:-1]]),
)


def fill(m):
    v = V[m.group(1)]
    return format(v, m.group(2)) if m.group(2) else str(v)


PAGE = open(os.path.join(HERE, 'conservation_template.html')).read()
open(OUT, 'w').write(re.sub(r'\{\{(\w+)(?::([^}]+))?\}\}', fill, PAGE))
print('wrote', os.path.normpath(OUT))
for k in sorted(V):
    if k not in ('f1', 'f2', 'f3', 'hunter_rows'):
        print('  %-12s %s' % (k, V[k]))
