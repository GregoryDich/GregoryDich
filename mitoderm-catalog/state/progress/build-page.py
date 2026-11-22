#!/usr/bin/env python3
"""Builds progress.html (the owner's readiness scale) from pages.json, compliance.json, improvements.json,
needs.json and samples.json in this folder. Run it after changing any of them, then republish the artifact."""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name), encoding='utf-8') as f:
        return json.load(f)


def esc(value):
    return html.escape(str(value), quote=True)


pages = load('pages.json')
improvements = load('improvements.json')['rows']
needs = load('needs.json')['rows']
samples = load('samples.json')['rows'] if os.path.exists(os.path.join(HERE, 'samples.json')) else []
compliance = load('compliance.json')['rows'] if os.path.exists(os.path.join(HERE, 'compliance.json')) else []
rows = pages['rows']
meta = {m['label']: m['value'] for m in pages['meta']}
steps = [part.split(' — ')[0].split('. ', 1)[1] for part in meta['Шаги и веса'].split('; ')]
overall = round(sum(r['percent'] for r in rows) / len(rows))
review = sum(1 for r in rows if r['percent'] >= 90)
working = len(rows) - review


def page_row(r):
    state = 'ready' if r['percent'] >= 90 else 'work'
    pips = ''.join(
        f'<span class="pip{" on" if r[f"s{i + 1}"] else ""}" title="{esc(steps[i])}"></span>' for i in range(9))
    return f'''<li class="page" data-state="{state}">
  <div class="page-head"><h3>{esc(r["page"])}</h3><span class="pct">{r["percent"]}%</span></div>
  <div class="bar" role="img" aria-label="Готово {r["percent"]} процентов"><span style="width:{r["percent"]}%"></span></div>
  <div class="page-foot"><span class="pips" aria-label="Сделано шагов: {r["steps_done"]} из 9">{pips}</span>
   <span class="stage">{esc(r["stage"])}</span><span class="who">пациент: {esc(r["patient"])}</span></div>
</li>'''


def sample_block(group):
    links = ''.join(f'<li><a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["label"])}</a></li>'
                    for s in group['links'])
    return f'<section class="samples"><h3>{esc(group["page"])}</h3><ul>{links}</ul></section>'


legend = ''.join(f'<li><span class="num">{i + 1}</span>{esc(s)}</li>' for i, s in enumerate(steps))
imp_rows = ''.join(
    f'<tr><td class="t-page">{esc(i["page"])}</td><td>{esc(i["what"])}<small>{esc(i["why"])}</small></td>'
    f'<td class="t-eff">{esc(i["effort"])}</td><td class="t-st">{esc(i["status"])}</td></tr>' for i in improvements)
VERDICT = {'совпадает': 'ok', 'частично': 'part', 'не совпадает': 'no'}
comp_rows = ''.join(
    f'<tr><td class="t-page">{esc(c["page"])}</td><td class="t-where">{esc(c["where"])}</td><td>{esc(c["film"])}</td>'
    f'<td><span class="verdict" data-v="{VERDICT.get(c["verdict"], "part")}">{esc(c["verdict"])}</span></td>'
    f'<td>{esc(c["todo"])}</td></tr>' for c in compliance)
comp_html = (f'''<section>
  <h2>Клиника или дом — по вашему списку 21/11</h2>
  <p class="muted">Где применяется средство по вашему слову и что сейчас показывает фильм страницы. Готовые фильмы
  меняются только после вашего «да» на названную цену.</p>
  <div class="table"><table><thead><tr><th>Страница</th><th>По списку</th><th>В фильме сейчас</th><th>Итог</th><th>Что сделать</th></tr></thead><tbody>{comp_rows}</tbody></table></div>
 </section>''' if compliance else '')
need_rows = ''.join(f'<li><b>{esc(n["topic"])}.</b> {esc(n["need"])} <small>{esc(n["why"])}</small></li>' for n in needs)
sample_html = ''.join(sample_block(g) for g in samples) or '<p class="muted">Ссылки появятся здесь по мере работы над страницей.</p>'

page = f'''<title>Шкала страниц MITODERM</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Manrope:wght@600;700&display=swap">
<style>
/* Layout: one calm column. A summary strip, then one row per page (name, percent, bar, nine step marks),
   then what to improve and what is needed from the owner. */
:root {{
  --bg: #f6f4ef; --surface: #ffffff; --ink: #1d1a15; --muted: #6b655a; --line: #e2ddd2;
  --accent: #a9792b; --accent-soft: #ead9b8; --good: #2f7d62; --good-soft: #cfe6dc; --track: #e9e5db; --warn-soft: #f1cfc6;
  --display: "Manrope", "Inter", system-ui, sans-serif; --text: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #15130f; --surface: #1e1b16; --ink: #f1ece2; --muted: #a39c8d; --line: #332e26;
  --accent: #d7b579; --accent-soft: #4a3d24; --good: #6cc3a3; --good-soft: #23443a; --track: #2b2721; --warn-soft: #5a2f27; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #15130f; --surface: #1e1b16; --ink: #f1ece2; --muted: #a39c8d; --line: #332e26;
  --accent: #d7b579; --accent-soft: #4a3d24; --good: #6cc3a3; --good-soft: #23443a; --track: #2b2721; --warn-soft: #5a2f27; color-scheme: dark }}
body {{ background: var(--bg); color: var(--ink); font: 400 15px/1.55 var(--text); }}
.wrap {{ max-width: 860px; margin: 0 auto; padding-block: 28px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 32px; }}
h1, h2, h3 {{ font-family: var(--display); margin: 0; text-wrap: balance; }}
h1 {{ font-size: 28px; line-height: 1.15; }}
h2 {{ font-size: 19px; }}
h3 {{ font-size: 15px; font-weight: 600; }}
p {{ margin: 0; }}
small {{ display: block; color: var(--muted); font-size: 13px; margin-top: 2px; }}
.muted, .updated {{ color: var(--muted); font-size: 13px; }}
header {{ display: flex; flex-direction: column; gap: 6px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }}
.summary div {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; min-width: 0; }}
.summary b {{ display: block; font: 700 26px/1.1 var(--display); font-variant-numeric: tabular-nums; }}
.summary span {{ color: var(--muted); font-size: 13px; }}
section {{ display: flex; flex-direction: column; gap: 14px; min-width: 0; }}
.pages {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }}
.page {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px;
  display: flex; flex-direction: column; gap: 8px; }}
.page-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }}
.pct {{ font: 700 17px/1 var(--display); font-variant-numeric: tabular-nums; color: var(--accent); }}
.page[data-state="ready"] .pct {{ color: var(--good); }}
.bar {{ height: 8px; border-radius: 6px; background: var(--track); overflow: hidden; }}
.bar span {{ display: block; height: 100%; border-radius: 6px; background: var(--accent); }}
.page[data-state="ready"] .bar span {{ background: var(--good); }}
.page-foot {{ display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; color: var(--muted); font-size: 13px; }}
.pips {{ display: inline-flex; gap: 3px; }}
.pip {{ width: 12px; height: 12px; border-radius: 3px; background: var(--track); }}
.pip.on {{ background: var(--accent); }}
.page[data-state="ready"] .pip.on {{ background: var(--good); }}
.stage {{ color: var(--ink); }}
.legend {{ list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 4px 16px; color: var(--muted); font-size: 13px; }}
.legend .num {{ display: inline-block; min-width: 1.5em; font-variant-numeric: tabular-nums; color: var(--ink); font-weight: 600; }}
.table {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); }}
table {{ border-collapse: collapse; width: 100%; min-width: 560px; font-size: 14px; }}
th, td {{ text-align: left; vertical-align: top; padding: 10px 12px; border-bottom: 1px solid var(--line); }}
th {{ color: var(--muted); font-weight: 500; font-size: 12px; letter-spacing: .03em; text-transform: uppercase; }}
tr:last-child td {{ border-bottom: 0; }}
.t-page {{ white-space: nowrap; font-weight: 600; }} .t-eff, .t-st {{ color: var(--muted); white-space: nowrap; }}
.t-where {{ white-space: nowrap; }}
.verdict {{ display: inline-block; white-space: nowrap; padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 600;
  background: var(--accent-soft); color: var(--ink); }}
.verdict[data-v="ok"] {{ background: var(--good-soft); }}
.verdict[data-v="no"] {{ background: var(--warn-soft); }}
.needs {{ margin: 0; padding-left: 1.1em; display: flex; flex-direction: column; gap: 8px; }}
.samples ul {{ margin: 0; padding-left: 1.1em; display: flex; flex-direction: column; gap: 4px; }}
a {{ color: var(--accent); text-underline-offset: 3px; }}
a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 3px; }}
</style>
<div class="wrap">
 <header>
  <h1>Шкала страниц MITODERM</h1>
  <p class="updated">Обновлено {esc(meta["Обновлено"])}. Страницы средств делаются по одной, сверху вниз.</p>
 </header>
 <div class="summary">
  <div><b>{overall}%</b><span>готовность 13 страниц средств в среднем</span></div>
  <div><b>{review}</b><span>ждут вашего просмотра</span></div>
  <div><b>{working}</b><span>в работе и в очереди</span></div>
 </div>
 <section>
  <h2>Страницы средств</h2>
  <ol class="pages">{''.join(page_row(r) for r in rows)}</ol>
  <ul class="legend" aria-label="Девять шагов страницы">{legend}</ul>
 </section>
 {comp_html}
 <section>
  <h2>Пробники: ссылки на промежуточные материалы</h2>
  {sample_html}
 </section>
 <section>
  <h2>Что можно улучшить в готовых страницах</h2>
  <div class="table"><table><thead><tr><th>Страница</th><th>Что и почему</th><th>Объём</th><th>Состояние</th></tr></thead><tbody>{imp_rows}</tbody></table></div>
 </section>
 <section>
  <h2>Что нужно от вас</h2>
  <ul class="needs">{need_rows}</ul>
 </section>
</div>
'''

with open(os.path.join(HERE, 'progress.html'), 'w', encoding='utf-8') as f:
    f.write(page)
print('progress.html written:', len(page), 'chars;', len(rows), 'pages; overall', overall, '%')
