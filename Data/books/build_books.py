#!/usr/bin/env python3
"""Builds books.html from the reading list in this folder.

    python3 Data/books/build_books.py

Input:   books.csv (one row per book; pages and pub_year from Open Library and
         publisher listings, blank where unknown)
Output:  ../../books.html (charts are inline SVG, no JavaScript)
"""
import csv, datetime as dt, html, os, re, statistics as st
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'books.html')
UPDATED = dt.date(2026, 11, 3)            # last edit to the list
ACCENT_AUTHOR = 'Peter Heller'            # the one author in every year
CURRENT = dict(title='Regenesis', author='George Church', pages=294)   # being read now, not yet counted
INK, SOFT, FAINT, RULE, BLAZE, GREY = '#111', '#555', '#888', '#e8e2d6', '#b4462b', '#8a857a'
PAPER, TINT, EDGE = '#fffff8', '#f4eee3', '#cfc6b4'

books = []
for r in csv.DictReader(open(os.path.join(HERE, 'books.csv'))):
    books.append(dict(year=int(r['year_read']), title=r['title'], author=r['author'],
                      series=r['series'], genre=r['genre'],
                      pub=int(r['pub_year']) if r['pub_year'] else None,
                      pages=int(r['pages']) if r['pages'] else None))
YEARS = sorted({b['year'] for b in books})
N = len(books)


def surname(a):
    return 'Le Guin' if a.endswith('Le Guin') else a.split()[-1]


def esc(s):
    return html.escape(s, quote=True).replace("&#x27;", '&rsquo;')


# ---------------------------------------------------------------- svg helpers
def svg(w, h, body, label):
    return ('<svg class="chart" viewBox="0 0 %d %d" role="img" aria-label="%s" '
            'xmlns="http://www.w3.org/2000/svg">%s</svg>' % (w, h, esc(label), ''.join(body)))


def text(x, y, s, anchor='start', cls='', fill=None, size=None, rot=None):
    a = ''
    if anchor != 'start': a += ' text-anchor="%s"' % anchor
    if cls: a += ' class="%s"' % cls
    css = ('fill:%s;' % fill if fill else '') + ('font-size:%spx;' % size if size else '')
    if css: a += ' style="%s"' % css          # inline style: the page CSS outranks attributes
    if rot is not None: a += ' transform="rotate(%d %.1f %.1f)"' % (rot, x, y)
    return '<text x="%.1f" y="%.1f"%s>%s</text>' % (x, y, a, esc(s))


def line(x1, y1, x2, y2, stroke=FAINT, w=1.0):
    return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"/>' % (
        x1, y1, x2, y2, stroke, w)


def tip(b):
    return '<title>%s, %s%s%s</title>' % (esc(b['title']), esc(b['author']),
                                          ' (%d)' % b['pub'] if b['pub'] else '',
                                          ', %d pages' % b['pages'] if b['pages'] else '')


# ---------------------------------------------------------------- figure 1: the shelf
def shelved(year):
    """Author groups for one year, largest first; list order breaks ties."""
    groups = OrderedDict()
    for b in books:
        if b['year'] == year:
            groups.setdefault(b['author'], []).append(b)
    out = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    for _, bs in out:                      # keep each series together within an author
        order = list(OrderedDict.fromkeys(b['series'] for b in bs if b['series'])) + ['']
        bs.sort(key=lambda b: order.index(b['series']))
    return out


def fig_shelf():
    W, SH, X0, PITCH, GAP = 1200, 215, 100, 267, 12
    MEDIAN = st.median(b['pages'] for b in books if b['pages'])
    pages = lambda b: b['pages'] or MEDIAN            # unknown length: draw it as a typical book
    widest = max(sum(pages(b) for b in books if b['year'] == y) + (CURRENT['pages'] if y == UPDATED.year else 0)
                 for y in YEARS)
    most_groups = max(len(shelved(y)) + (y == UPDATED.year) for y in YEARS)
    K = (W - X0 - GAP * (most_groups - 1) - 12) / widest      # pixels per page

    def spine(o, x, top, b, hot=False, single=False, ghost=False):
        w = pages(b) * K
        size = 11.5 if w >= 15 else 9.5
        tx = x + w / 2 - size * 0.33
        o.append('<g>%s<rect x="%.1f" y="%.1f" width="%.1f" height="%d" fill="%s" stroke="%s" stroke-width="1"%s/>' % (
            '<title>%s, %s, %d pages (reading now)</title>' % (esc(b['title']), esc(b['author']), b['pages']) if ghost else tip(b),
            x, top, w, SH - ghost, 'none' if ghost else BLAZE if hot else TINT,
            FAINT if ghost else BLAZE if hot else EDGE, ' stroke-dasharray="3 3"' if ghost else ''))
        o.append(text(tx, top + 9, b['title'], fill=PAPER if hot else None if ghost else INK, size=size, rot=90))
        if single:
            o.append(text(tx, top + SH - 9, surname(b['author']), anchor='end',
                          cls='' if hot else 'it', fill=PAPER if hot else None, size=size, rot=90))
        o.append('</g>')
        return x + w

    o = []
    for i, y in enumerate(YEARS):
        top = 8 + i * PITCH
        mine = [b for b in books if b['year'] == y]
        o.append(text(0, top + 16, str(y), fill=INK, size=17))
        o.append(text(0, top + 36, '%d books' % len(mine)))
        o.append(text(0, top + 53, '{:,} pages'.format(sum(b['pages'] or 0 for b in mine))))
        if y == UPDATED.year:
            o.append(text(0, top + 70, 'so far', cls='it'))
        x = X0
        for author, bs in shelved(y):
            gx0, prev = x, None
            hot = author == ACCENT_AUTHOR
            for b in bs:
                if prev is not None and b['series'] != prev:
                    x += 5
                prev = b['series']
                x = spine(o, x, top, b, hot, single=len(bs) == 1)
            if len(bs) > 1:
                o.append(text((gx0 + x) / 2, top + SH + 18, '%s %d' % (surname(author), len(bs)),
                              anchor='middle', fill=BLAZE if hot else SOFT))
            x += GAP
        if y == UPDATED.year:                  # the book in progress: an outline, not yet a spine
            spine(o, x, top, CURRENT, single=True, ghost=True)
        o.append(line(X0 - 6, top + SH + 0.5, W, top + SH + 0.5, FAINT, 1))
    return svg(W, 8 + len(YEARS) * PITCH - 22, o,
               'Every book read from 2024 to 2026, drawn as a spine as thick as its page count, on a shelf for each year')


# ---------------------------------------------------------------- figure 2: genre slopegraph
GENRES = ['Fantasy & sci-fi', 'Thriller', 'Literary', 'Nonfiction', 'Mystery']
gcount = {g: [sum(1 for b in books if b['year'] == y and b['genre'] == g) for y in YEARS] for g in GENRES}
GLABEL = {'Thriller': 'Thrillers'}


def fig_genre():
    W, H = 720, 350
    xs = [230, 380, 530]
    top_v = max(max(v) for v in gcount.values())
    Y = lambda v: 318 - v * (318 - 40) / top_v
    o = [text(x, 14, str(y), anchor='middle', fill=INK, size=15) for x, y in zip(xs, YEARS)]
    o.append(text(xs[-1] + 26, 14, 'so far', cls='it'))
    style = lambda g: (BLAZE, 1.8) if g == 'Thriller' else (INK, 1.6) if g == GENRES[0] else (GREY, 1.2)
    for g in reversed(GENRES):
        c, w = style(g)
        pts = ' '.join('%.1f,%.1f' % (x, Y(v)) for x, v in zip(xs, gcount[g]))
        o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (pts, c, w))
        for x, v in zip(xs, gcount[g]):
            o.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="%s"/>' % (x, Y(v), c))
    for col, anchor, dx in ((0, 'end', -10), (2, 'start', 10)):
        byv = OrderedDict()
        for g in GENRES:
            byv.setdefault(gcount[g][col], []).append(g)
        for v, gs in byv.items():
            names = ', '.join(GLABEL.get(g, g).lower() if i else GLABEL.get(g, g) for i, g in enumerate(gs))
            s = '%s  %d' % (names, v) if col == 0 else '%d  %s' % (v, names)
            fill = BLAZE if gs == ['Thriller'] else INK if GENRES[0] in gs else None
            o.append(text(xs[col] + dx, Y(v) + 4.5, s, anchor=anchor, fill=fill))
    for v in sorted(set(gcount[g][1] for g in GENRES)):
        o.append(text(xs[1], Y(v) + 18 if v == 0 else Y(v) - 8, str(v), anchor='middle', fill=INK if v == top_v else None))
    return svg(W, H, o, 'Books read per year by genre, 2024 to 2026')


# ---------------------------------------------------------------- figure 3: publication years
dated = [b for b in books if b['pub']]


def fig_pub():
    W, H, BASE = 720, 150, 100
    lo, hi = 1940, UPDATED.year
    X = lambda yr: 24 + (yr - lo) * (W - 48) / (hi - lo)
    o = [line(X(lo), BASE + 8, X(hi), BASE + 8, FAINT, 1)]
    for t in range(1940, hi + 1, 10):
        o.append(line(X(t), BASE + 8, X(t), BASE + 12, FAINT, 1))
        o.append(text(X(t), BASE + 28, str(t), anchor='middle'))
    stack = Counter()
    for b in sorted(dated, key=lambda b: (b['pub'], b['author'] != ACCENT_AUTHOR)):
        k = stack[b['pub']]; stack[b['pub']] += 1
        hot = b['author'] == ACCENT_AUTHOR
        o.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="%s">%s</circle>' % (
            X(b['pub']), BASE - k * 7.6, BLAZE if hot else GREY, tip(b)))
    old = sorted(dated, key=lambda b: b['pub'])[:2]
    for b in old:
        o.append(text(X(b['pub']), BASE - 26, b['title'], anchor='middle', fill=INK))
        o.append(text(X(b['pub']), BASE - 11, str(b['pub']), anchor='middle'))
    med = st.median(b['pub'] for b in dated)
    o.append(line(X(med), BASE - 62, X(med), BASE - 86, FAINT, 0.7))
    o.append(text(X(med) - 6, BASE - 78, 'half published since %d' % med, anchor='end', cls='it'))
    return svg(W, H, o, 'Publication year of each book read, 1946 to 2025')


# ---------------------------------------------------------------- numbers for the prose
per_year = {y: [b for b in books if b['year'] == y] for y in YEARS}
by_author = Counter(b['author'] for b in books)
runs = sum(n for (y, s), n in Counter((b['year'], b['series']) for b in books if b['series']).items() if n > 1)
big = [a for a, n in by_author.most_common() if n >= 3]
apages = Counter()
for b in books:
    apages[b['author']] += b['pages'] or 0
PAGES = sum(apages.values())
top_author = by_author.most_common(1)[0][0]
rows = []
for a in big:
    cells = []
    for y in YEARS:
        n = sum(1 for b in per_year[y] if b['author'] == a)
        cells.append('<td>%d</td>' % n if n else '<td class="muted">&middot;</td>')
    hot = ' class="hi"' if a == ACCENT_AUTHOR else ''
    rows.append('<tr><td%s>%s</td>%s<td%s>%d</td><td%s>%s</td></tr>' % (
        hot, esc(a), ''.join(cells), hot, by_author[a], hot, '{:,}'.format(apages[a])))
last = UPDATED.year
V = dict(
    f1=fig_shelf(), f2=fig_genre(), f3=fig_pub(),
    N=N, nauth=len(by_author), updated='%d %s' % (UPDATED.day, UPDATED.strftime('%B %Y')),
    pace=UPDATED.timetuple().tm_yday / len(per_year[last]),
    runs=runs, runpct=100 * runs / N,
    nbig=len(big), bigbooks=sum(by_author[a] for a in big), nsingle=sum(1 for n in by_author.values() if n == 1),
    author_rows='\n            '.join(rows),
    nf=sum(1 for b in books if b['genre'] == 'Nonfiction'),
    thr=gcount['Thriller'][-1],
    medpub=st.median(b['pub'] for b in dated),
    recentpct=100 * sum(1 for b in dated if b['pub'] >= 2012) / len(dated),
    medage=st.median(b['year'] - b['pub'] for b in dated),
    undated_note=' %d books are left off because I don&rsquo;t have a year for them.' % (N - len(dated)) if N > len(dated) else '',
    pages_total='{:,}'.format(PAGES), top_pages='{:,}'.format(apages[top_author]), top_pct=100 * apages[top_author] / PAGES,
    longest=max(books, key=lambda b: b['pages'] or 0), shortest=min(books, key=lambda b: b['pages'] or 9e9),
    cur_title=CURRENT['title'], cur_author=CURRENT['author'],
)
for y in YEARS:
    V['n%d' % (y % 100)] = len(per_year[y])
    V['a%d' % (y % 100)] = len({b['author'] for b in per_year[y]})
    V['f%d' % (y % 100)] = gcount[GENRES[0]][YEARS.index(y)]
    pg = sum(b['pages'] or 0 for b in per_year[y])
    days = UPDATED.timetuple().tm_yday if y == UPDATED.year else (dt.date(y, 12, 31) - dt.date(y - 1, 12, 31)).days
    V['p%d' % (y % 100)] = '{:,}'.format(pg)
    V['d%d' % (y % 100)] = pg / days
for k in ('longest', 'shortest'):
    V[k + '_title'], V[k + '_pages'] = esc(V[k]['title']), V[k]['pages']
    del V[k]
V['th_years'] = ''.join('<th>%d</th>' % y for y in YEARS)


def fill(m):
    v = V[m.group(1)]
    return format(v, m.group(2)) if m.group(2) else str(v)


PAGE = open(os.path.join(HERE, 'books_template.html')).read()
open(OUT, 'w').write(re.sub(r'\{\{(\w+)(?::([^}]+))?\}\}', fill, PAGE))
print('wrote', os.path.normpath(OUT))
for k in sorted(V):
    if k not in ('f1', 'f2', 'f3', 'author_rows', 'th_years'):
        print('  %-10s %s' % (k, V[k]))
