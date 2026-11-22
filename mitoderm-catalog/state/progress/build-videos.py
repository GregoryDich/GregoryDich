#!/usr/bin/env python3
"""Builds the owner's video library from videos.json in this folder:
  videos.html                    the page published as an artifact (one card per site page)
  ../../VIDEOS.md                the same list for the repository on GitHub
For every page of the site: its film as the page plays it (desktop and phone), a recording of the whole page being
scrolled, and every clip the film is cut from. Each link opens the file itself, so it can be saved from the browser.

videos.json: "pages" in the order of the scale; each has "record" and "film" ({"desktop", "phone"} or null) and
"clips" ([{"code", "what", "wide"?, "tall"?}]: the 16:9 and the 9:16 file of one clip); "sizes" maps an address to
megabytes. "site" is the address of the published test site (null until there is one): with it every card gets a link
to the page itself. After changing the data run this script, then state/tasks/check-links.py, then republish the artifact.
"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, 'videos.json'), encoding='utf-8'))
meta = {m['label']: m['value'] for m in data['meta']}
pages, sizes = data['pages'], data['sizes']
REPO = data['repo']
SITE = (data.get('site') or '').rstrip('/')
VIDEOS_MD = REPO.rsplit('/codex-site', 1)[0].replace('/tree/', '/blob/') + '/VIDEOS.md'


def esc(value):
    return html.escape(str(value), quote=True)


def mb(url):
    size = sizes.get(url)
    return ('%.1f' % size).replace('.', ',').replace(',0', '') + ' МБ' if size else ''


def link(url, label):
    size = mb(url)
    return (f'<a class="file" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}'
            + (f'<span>{esc(size)}</span>' if size else '') + '</a>')


def pair(row, wide_label='компьютер, 16:9', tall_label='телефон, 9:16'):
    return ''.join(link(row[key], label) for key, label in (('desktop', wide_label), ('phone', tall_label)) if row.get(key))


def card(page):
    rows = ''
    if SITE:
        path = '/' if page['slug'] == 'home' else '/products/' + page['slug']
        rows += (f'<div class="row"><h3>Сама страница</h3><div class="files">'
                 f'<a class="file" href="{esc(SITE + path)}" target="_blank" rel="noopener">открыть на тестовом сайте</a></div></div>')
    if page.get('film'):
        rows += f'<div class="row"><h3>Фильм страницы</h3><div class="files">{pair(page["film"])}</div></div>'
    rows += (f'<div class="row"><h3>Страница целиком <small>запись прокрутки</small></h3>'
             f'<div class="files">{pair(page["record"], "компьютер", "телефон")}</div></div>')
    if page['clips']:
        clips = ''.join(
            f'<li><b>{esc(c["code"])}</b><p>{esc(c["what"])}</p><div class="files">'
            + (link(c['wide'], '16:9') if c.get('wide') else '') + (link(c['tall'], '9:16') if c.get('tall') else '')
            + '</div></li>' for c in page['clips'])
        rows += (f'<div class="row clips"><h3>Ролики внутри фильма <small>{len(page["clips"])}</small></h3>'
                 f'<ol>{clips}</ol></div>')
    if page.get('extra'):
        rows += ('<div class="row"><h3>Снимки</h3><div class="files">'
                 + ''.join(link(e['url'], e['label']) for e in page['extra']) + '</div></div>')
    note = f'<p class="note">{esc(page["note"])}</p>' if page.get('note') else ''
    where = f'<span class="where" data-where="{esc(page["where"])}">{esc(page["where"])}</span>' if page.get('where') else ''
    return (f'<section class="page" id="{esc(page["slug"])}"><header><h2>{esc(page["name"])}</h2>{where}</header>'
            f'{rows}{note}</section>')


files = set()
for page in pages:
    for group in (page.get('film') or {}, page['record']):
        files.update(group.values())
    for clip in page['clips']:
        files.update(clip[k] for k in ('wide', 'tall') if clip.get(k))
total = sum(sizes.get(u, 0) for u in files)
films = sum(len(p['film']) for p in pages if p.get('film'))
clip_files = sum(1 for p in pages for c in p['clips'] for k in ('wide', 'tall') if c.get(k))
nav = ''.join(f'<a href="#{esc(p["slug"])}">{esc(p["name"])}</a>' for p in pages)

page_html = f'''<title>Видео MITODERM</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Manrope:wght@600;700&display=swap">
<style>
/* Layout: one calm column, the same hand as the readiness page. A short "how to save" note, a strip of page names,
   then one card per site page: film, whole-page recording, clips. Every link is a file, labelled with its size. */
:root {{
  --bg: #f6f4ef; --surface: #ffffff; --ink: #1d1a15; --muted: #6b655a; --line: #e2ddd2;
  --accent: #8a5f17; --accent-soft: #ead9b8; --good-soft: #cfe6dc; --home-soft: #dde3f2;
  --display: "Manrope", "Inter", system-ui, sans-serif; --text: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #15130f; --surface: #1e1b16; --ink: #f1ece2; --muted: #a39c8d; --line: #332e26;
  --accent: #d7b579; --accent-soft: #4a3d24; --good-soft: #23443a; --home-soft: #2b3350; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #15130f; --surface: #1e1b16; --ink: #f1ece2; --muted: #a39c8d; --line: #332e26;
  --accent: #d7b579; --accent-soft: #4a3d24; --good-soft: #23443a; --home-soft: #2b3350; color-scheme: dark }}
body {{ background: var(--bg); color: var(--ink); font: 400 15px/1.55 var(--text); }}
.wrap {{ max-width: 860px; margin: 0 auto; padding-block: 28px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 24px; }}
h1, h2, h3 {{ font-family: var(--display); margin: 0; text-wrap: balance; }}
h1 {{ font-size: 28px; line-height: 1.15; }}
h2 {{ font-size: 19px; }}
h3 {{ font: 600 13px/1.4 var(--text); color: var(--muted); }}
h3 small {{ font-weight: 400; margin-left: 6px; }}
p {{ margin: 0; }}
.top {{ display: flex; flex-direction: column; gap: 8px; }}
.muted {{ color: var(--muted); font-size: 13px; }}
.how {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; display: flex; flex-direction: column; gap: 4px; }}
.how b {{ font-weight: 600; }}
.nav {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.nav a {{ font-size: 13px; padding: 4px 10px; border: 1px solid var(--line); border-radius: 999px; background: var(--surface);
  color: var(--ink); text-decoration: none; }}
.nav a:hover {{ border-color: var(--accent); }}
.page {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px;
  display: flex; flex-direction: column; gap: 14px; scroll-margin-top: 12px; min-width: 0; }}
.page > header {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 10px; }}
.where {{ font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 999px; background: var(--good-soft); }}
.where[data-where="дом"] {{ background: var(--home-soft); }}
.row {{ display: flex; flex-direction: column; gap: 6px; min-width: 0; }}
.files {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.file {{ display: inline-flex; align-items: baseline; gap: 8px; padding: 6px 10px; border: 1px solid var(--line); border-radius: 8px;
  color: var(--accent); font-weight: 500; text-decoration: none; background: var(--bg); }}
.file:hover {{ border-color: var(--accent); }}
.file span {{ color: var(--muted); font-weight: 400; font-size: 12px; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.clips ol {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }}
.clips li {{ display: grid; grid-template-columns: minmax(2.4em, max-content) minmax(0, 1fr) auto; align-items: baseline; gap: 4px 12px;
  padding: 8px 0; border-top: 1px solid var(--line); }}
.clips li b {{ font-weight: 600; font-variant-numeric: tabular-nums; }}
.clips .file {{ padding: 3px 8px; font-size: 13px; }}
.note {{ color: var(--muted); font-size: 13px; }}
a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 6px; }}
footer {{ color: var(--muted); font-size: 13px; display: flex; flex-direction: column; gap: 4px; }}
footer a {{ color: var(--accent); text-underline-offset: 3px; overflow-wrap: anywhere; }}
@media (max-width: 560px) {{
  .clips li {{ display: flex; flex-direction: column; gap: 4px; }}
}}
</style>
<div class="wrap">
 <div class="top">
  <h1>Видео страниц MITODERM</h1>
  <p class="muted">Обновлено {esc(meta["Обновлено"])}. {len(pages)} страниц, {films} фильмов, {clip_files} файлов роликов, {round(total)} МБ. Каждая ссылка проверена: файл открывается.</p>
 </div>
 <div class="how">
  <p><b>Как скачать.</b> Ссылка открывает сам файл в новой вкладке. На компьютере: меню «⋮» в углу плеера → «Скачать» (или правой кнопкой по видео → «Сохранить видео как»). На телефоне: долгое нажатие на видео → «Сохранить» или «Скачать видео».</p>
  <p class="muted">Фильм — то, что играет на странице при прокрутке. Ролики — куски, из которых он собран; файлы по 5 секунд, 1080p, без звука.</p>
  {'' if SITE else '<p class="muted">Ссылки на сами страницы появятся в каждой карточке, как только тестовый сайт будет выложен; пока страницу целиком показывает запись прокрутки.</p>'}
 </div>
 <nav class="nav" aria-label="Страницы">{nav}</nav>
 {''.join(card(p) for p in pages)}
 <footer>
  <p>Код страниц (репозиторий): <a href="{esc(REPO)}" target="_blank" rel="noopener">{esc(REPO.split("github.com/")[1])}</a></p>
  <p>Этот же список файлом в репозитории: <a href="{esc(VIDEOS_MD)}" target="_blank" rel="noopener">VIDEOS.md</a></p>
 </footer>
</div>
'''
with open(os.path.join(HERE, 'videos.html'), 'w', encoding='utf-8') as f:
    f.write(page_html)


def md_link(url, label):
    size = mb(url)
    return '[%s](%s)%s' % (label, url, ' — ' + size if size else '')


lines = ['# Видео страниц MITODERM', '',
         'Обновлено %s. %d страниц, %d фильмов, %d файлов роликов, %d МБ. Каждая ссылка проверена: файл открывается.'
         % (meta['Обновлено'], len(pages), films, clip_files, round(total)), '',
         '**Как скачать.** Ссылка открывает сам файл. На компьютере: меню «⋮» в углу плеера → «Скачать» (или правой '
         'кнопкой по видео → «Сохранить видео как»). На телефоне: долгое нажатие на видео → «Сохранить» или «Скачать видео».', '',
         'Фильм — то, что играет на странице при прокрутке. Ролики — куски, из которых он собран: по 5 секунд, 1080p, без звука.', '',
         'Этот файл собирает `state/progress/build-videos.py` из `state/progress/videos.json`; ссылки проверяет '
         '`state/tasks/check-links.py`. Код страниц — в [`codex-site`](codex-site).', '']
for page in pages:
    lines += ['## %s%s' % (page['name'], ' — ' + page['where'] if page.get('where') else ''), '']
    if SITE:
        lines += ['- **Сама страница:** ' + SITE + ('/' if page['slug'] == 'home' else '/products/' + page['slug'])]
    if page.get('film'):
        lines += ['- **Фильм страницы:** ' + ' · '.join(md_link(page['film'][k], t) for k, t in (('desktop', 'компьютер, 16:9'), ('phone', 'телефон, 9:16')))]
    lines += ['- **Страница целиком (запись прокрутки):** ' + ' · '.join(md_link(page['record'][k], t) for k, t in (('desktop', 'компьютер'), ('phone', 'телефон')))]
    for extra in page.get('extra', []):
        lines += ['- ' + md_link(extra['url'], extra['label'])]
    if page.get('note'):
        lines += ['- ' + page['note']]
    if page['clips']:
        lines += ['', '| Ролик | Что в кадре | Файлы |', '|---|---|---|']
        for clip in page['clips']:
            files_md = ' · '.join(md_link(clip[k], t) for k, t in (('wide', '16:9'), ('tall', '9:16')) if clip.get(k))
            lines += ['| %s | %s | %s |' % (clip['code'], clip['what'], files_md)]
    lines += ['']
with open(os.path.join(HERE, '..', '..', 'VIDEOS.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('videos.html: %d chars; VIDEOS.md: %d lines; pages %d, films %d, clip files %d, %d MB'
      % (len(page_html), len(lines), len(pages), films, clip_files, round(total)))
