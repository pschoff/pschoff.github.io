#!/usr/bin/env python3
"""Builds bikepacking.html from the Strava ride summaries in this folder.

    python3 Data/bikepacking/build_bikepacking.py

Inputs:  rides.csv (one row per day of each trip; a row with no miles is a day Strava has no ride for)
         bikepacking_template.html
Output:  ../../bikepacking.html (the chart is inline SVG, no JavaScript)
"""
import csv, datetime as dt, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'bikepacking.html')
INK, SOFT, FAINT, RULE, BLAZE, GREY = '#111', '#555', '#888', '#e8e2d6', '#b4462b', '#8a857a'

TRIPS = [('gap', 'Pittsburgh to DC', '2023'),
         ('verte', 'Montréal to Québec City and back', '2025'),
         ('p2c', 'Palouse to Cascades', '2026')]


def load():
    rows = []
    with open(os.path.join(HERE, 'rides.csv'), newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            r['date'] = dt.date.fromisoformat(r['start_local'][:10])
            r['miles'] = float(r['miles']) if r['miles'] else None
            for k in ('moving_time_s', 'elapsed_time_s', 'climb_ft'):
                r[k] = int(r[k]) if r[k] else None
            r['avg_mph'] = float(r['avg_mph']) if r['avg_mph'] else None
            rows.append(r)
    return rows


def hm(s):
    return f'{s // 3600}:{s % 3600 // 60:02d}'


def esc(s):
    return s.replace('&', '&amp;')


def chart(rows):
    W, H, top, base = 720, 300, 58, 232
    scale = (base - top) / 110.0                     # 110 miles is the top of the scale
    slot, bar, gap = 44, 30, 46
    slowest = min((r for r in rows if r['miles']), key=lambda r: r['avg_mph'])
    o = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Miles ridden on each day of the three trips" xmlns="http://www.w3.org/2000/svg">']
    for m in (50, 100):
        y = base - m * scale
        o.append(f'<line x1="34" y1="{y:.1f}" x2="{W}" y2="{y:.1f}" stroke="{RULE}" stroke-width="1"/>')
        o.append(f'<text x="28" y="{y + 4:.1f}" text-anchor="end">{m}</text>')
    o.append(f'<text x="28" y="{top - 26}" text-anchor="end" class="it">mi</text>')
    x = 44
    for key, name, year in TRIPS:
        days = [r for r in rows if r['trip'] == key]
        total = sum(r['miles'] or 0 for r in days)
        o.append(f'<text x="{x}" y="16" fill="{INK}" font-size="15">{esc(name)}</text>')
        o.append(f'<text x="{x}" y="33" class="it">{year}, {total:.0f} miles recorded</text>')
        for r in days:
            label = f'{r["date"]:%b} {r["date"].day}'
            if r['miles'] is None:
                o.append(f'<rect x="{x}" y="{base - 60 * scale:.1f}" width="{bar}" height="{60 * scale:.1f}" fill="none" stroke="{FAINT}" stroke-width="1" stroke-dasharray="3 3"/>')
                o.append(f'<text x="{x + bar / 2}" y="{base - 60 * scale - 6:.1f}" text-anchor="middle" class="it">?</text>')
            else:
                h = r['miles'] * scale
                fill = BLAZE if r is slowest else GREY
                o.append(f'<rect x="{x}" y="{base - h:.1f}" width="{bar}" height="{h:.1f}" fill="{fill}"><title>{label}, {r["date"].year}: {r["miles"]:.1f} miles, {hm(r["moving_time_s"])} moving, {r["climb_ft"]:,} ft of climbing</title></rect>')
                o.append(f'<text x="{x + bar / 2}" y="{base - h - 6:.1f}" text-anchor="middle" fill="{BLAZE if r is slowest else INK}">{r["miles"]:.0f}</text>')
            o.append(f'<text x="{x + bar / 2}" y="{base + 17}" text-anchor="middle">{label}</text>')
            x += slot
        x += gap
    o.append(f'<line x1="34" y1="{base}" x2="{W}" y2="{base}" stroke="{INK}" stroke-width="1"/>')
    o.append('</svg>')
    return ''.join(o)


def table(rows, key):
    days = [r for r in rows if r['trip'] == key]
    o = ['<table class="plain">',
         '<thead><tr><th>Day</th><th>Started in</th><th>Miles</th><th>Moving</th><th>Climbing, ft</th></tr></thead>', '<tbody>']
    for r in days:
        d = f'{r["date"]:%a}, {r["date"]:%b} {r["date"].day}'
        if r['miles'] is None:
            o.append(f'<tr><td>{d}</td><td><em>not recorded</em></td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td></tr>')
        else:
            o.append(f'<tr><td>{d}</td><td>{esc(r["start_place"])}</td><td>{r["miles"]:.1f}</td><td>{hm(r["moving_time_s"])}</td><td>{r["climb_ft"]:,}</td></tr>')
    rec = [r for r in days if r['miles']]
    o.append(f'<tr><td>Recorded</td><td></td><td>{sum(r["miles"] for r in rec):.1f}</td><td>{hm(sum(r["moving_time_s"] for r in rec))}</td><td>{sum(r["climb_ft"] for r in rec):,}</td></tr>')
    o.append('</tbody></table>')
    return '\n          '.join(o)


def main():
    rows = load()
    rec = [r for r in rows if r['miles']]
    html = open(os.path.join(HERE, 'bikepacking_template.html'), encoding='utf-8').read()
    subs = {'{{CHART}}': chart(rows),
            '{{TOTAL_MILES}}': f'{sum(r["miles"] for r in rec):.0f}',
            '{{TOTAL_DAYS}}': str(len(rec))}
    for key, _, _ in TRIPS:
        subs['{{TABLE_%s}}' % key.upper()] = table(rows, key)
    for k, v in subs.items():
        assert k in html, k
        html = html.replace(k, v)
    assert '{{' not in html
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'{len(rec)} recorded days, {sum(r["miles"] for r in rec):.1f} miles ->', os.path.normpath(OUT))


if __name__ == '__main__':
    main()
