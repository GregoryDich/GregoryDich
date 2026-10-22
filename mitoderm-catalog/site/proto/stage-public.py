#!/usr/bin/env python3
"""Stages the built prototype pages as one static site, site/public/, for any static host (Vercel, GitHub Pages):
each page becomes <slug>/index.html with the document shell the artifact host and serve-local.py add (doctype, UTF-8,
viewport), next to its own img/ and seq/ (only the frame tiers the page offers, and runs.json); index.html lists the
pages and links the developer handoff and the Hebrew workbook of all page texts on GitHub.
usage: python3 stage-public.py <slug>=<page.html>[:<files dir>] …
  e.g. v-tech-system=<dir>/vtech-live.html:<dir>  exotech-gel=<dir>/exotech-gel-live.html:<dir>  exocell-mask=exocell-mask-3d.html"""
import html, json, os, re, shutil, sys

H = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(H, '..', 'public'))
HEAD = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>'
GH = 'https://github.com/GregoryDich/GregoryDich/blob/claude/mitoderm-figma-catalog-74tbuw/mitoderm-catalog/site/'
# the hub's lines: the page's name and what it shows (Hebrew; product names stay Latin)
ABOUT = {'v-tech-system': ('V-TECH SYSTEM', 'סיפור 3D בגלילה: פריימים ב-HD שרונדרו ב-Blender'),
         'exocell-mask': ('EXOCELL MASK', 'סיפור 3D חי ב-three.js'),
         'exotech-gel': ('EXOTECH GEL', 'סיפור 3D חי ב-three.js'),
         'exosignal-hair': ('EXOSIGNAL HAIR', 'סיפור 3D חי ב-three.js'),
         'exosignal-spray': ('EXOSIGNAL SPRAY', 'סיפור 3D חי ב-three.js'),
         'exo-nad': ('EXO-NAD', 'סיפור 3D חי ב-three.js'),
         'micro-boost-10': ('MICRO BOOST 10%', 'סיפור 3D חי ב-three.js'),
         'cellular-age-defense-2-5': ('CELLULAR AGE DEFENSE 2.5%', 'סיפור 3D חי ב-three.js'),
         'mitopen': ('MITOPEN', 'סיפור 3D חי ב-three.js'),
         'cell-renew-1-5': ('CELL RENEW 1.5%', 'סיפור 3D חי ב-three.js')}

pages = []
for arg in sys.argv[1:]:
    slug, rest = arg.split('=', 1)
    page, files = (rest.split(':', 1) + [None])[:2]
    body = open(page, encoding='utf-8').read()
    assert not body.lstrip()[:9].lower().startswith('<!doctype'), f'{page}: expected a <body> fragment'
    dst = os.path.join(OUT, slug)
    if os.path.exists(dst): shutil.rmtree(dst)
    os.makedirs(dst)
    open(os.path.join(dst, 'index.html'), 'w', encoding='utf-8').write(HEAD + body + '</body></html>')
    if files:
        if os.path.isdir(os.path.join(files, 'img')):   # the page's images; another product's 3D textures are not its own
            shutil.copytree(os.path.join(files, 'img'), os.path.join(dst, 'img'),
                            ignore=lambda d, names: [n for n in names if n.endswith('-3d') and n != f'{slug}-3d'])
        m = re.search(r'"tiers":\[([0-9,]*)\]', body)
        tiers = [t for t in (m.group(1).split(',') if m else []) if t]
        for t in tiers:
            shutil.copytree(os.path.join(files, 'seq', t), os.path.join(dst, 'seq', t))
        if tiers and os.path.exists(os.path.join(files, 'seq', 'runs.json')):
            shutil.copyfile(os.path.join(files, 'seq', 'runs.json'), os.path.join(dst, 'seq', 'runs.json'))
    size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(dst) for f in fs)
    print(f'{slug}: {sum(len(fs) for _, _, fs in os.walk(dst))} files, {size / 1e6:.1f} MB')
    pages.append(slug)

items = ''.join(f'<li><a href="{s}/"><b>{html.escape(ABOUT[s][0])}</b><span>{html.escape(ABOUT[s][1])}</span></a></li>'
                for s in ABOUT if s in pages)
hub = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>MITODERM — אב־טיפוס</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500&display=swap">
<style>
:root {{ --bg: #0a0a0b; --card: #141417; --cream: #f6f3ec; --text: rgba(246,243,236,.72); --gold: #c9a24b; --line: rgba(201,162,75,.28); color-scheme: dark; }}
body {{ margin: 0; background: var(--bg); color: var(--cream); font: 400 17px/1.6 Rubik, system-ui, sans-serif; }}
main {{ width: min(760px, 100% - 32px); margin: 0 auto; padding-block: 56px 72px; }}
h1 {{ margin: 0 0 6px; font-weight: 400; font-size: clamp(28px, 5vw, 40px); }}
p {{ margin: 0 0 32px; color: var(--text); }}
h2 {{ margin: 40px 0 12px; font: 500 13px/1.3 Rubik, sans-serif; letter-spacing: .04em; color: var(--gold); }}
ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }}
a {{ color: inherit; text-decoration: none; }}
li a {{ display: flex; flex-direction: column; gap: 2px; padding: 18px 20px; background: var(--card); border: 1px solid var(--line); border-radius: 14px; }}
li a:hover, li a:focus-visible {{ border-color: var(--gold); outline: none; }}
li b {{ font-weight: 500; letter-spacing: .02em; }}
li span {{ color: var(--text); font-size: 15px; }}
</style></head><body><main>
<h1>MITODERM — אב־טיפוס האתר</h1>
<p>העמודים החיים של האתר החדש, בעברית, לטלפון ולמחשב.</p>
<h2>עמודים</h2>
<ul>{items}</ul>
<h2>לפיתוח</h2>
<ul>
<li><a href="{GH}HANDOFF-dev.he.md"><b>מסמך מסירה לפיתוח</b><span>המבנה, המנוע, הבדיקות והכללים</span></a></li>
<li><a href="{GH}MITODERM-3D-story.xlsx"><b>הטקסטים של כל העמודים — Excel</b><span>כל המסכים של כל המוצרים, דף הבית, הקטלוג, המדע ואודות</span></a></li>
<li><a href="https://github.com/GregoryDich/GregoryDich/tree/claude/mitoderm-figma-catalog-74tbuw/mitoderm-catalog/site"><b>הקוד</b><span>GitHub</span></a></li>
</ul>
</main></body></html>
'''
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(hub)
print(os.path.join(OUT, 'index.html'))
