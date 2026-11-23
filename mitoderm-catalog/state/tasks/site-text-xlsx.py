#!/usr/bin/env python3
"""Builds the owner's Excel file with every text of the site.

Input: the JSON written by site-text-export.cjs (the rendered pages, block by block) and site-text-extra.json
(texts that appear only after the visitor does something). Output: one workbook, Hebrew throughout, right to left:
  "סיכום"            what the file holds, how to fill it in, and totals per page (formulas over the second sheet)
  "כל הטקסטים"       one row per text: page, address, part of the page, kind, the text, words, characters, a yellow
                     column for the team's remarks, and where the text comes from (for whoever applies the remarks)
  "לא מוצג באתר"     texts of the verified content file (codex-site/mitoderm/content.json) that no page shows now
What repeats on every page (header, contact form, footer) is listed once; decorations (arrows, bare numbers) and the
anti-spam field are left out; a picture description that only repeats the visible name next to it is left out.

Usage: site-text-xlsx.py <site-texts.json> <out.xlsx>     (needs openpyxl; then run the xlsx skill's recalc.py)
The script stops if a text of site-text-extra.json no longer stands in the code, or if the workbook would carry a
Cyrillic letter; it reports Hebrew texts of the code that are neither on a page nor in site-text-extra.json.
"""
import collections
import datetime
import json
import os
import re
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

src, out = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
APP = os.path.join(ROOT, 'codex-site')
data = json.load(open(src, encoding='utf-8'))
extra = json.load(open(os.path.join(HERE, 'site-text-extra.json'), encoding='utf-8'))
content = json.load(open(os.path.join(APP, 'mitoderm', 'content.json'), encoding='utf-8'))

HEB = re.compile(r'[֐-׿]')
LETTER = re.compile(r'[A-Za-z֐-׿]')
INVISIBLE = re.compile(r'[​‎‏⁠﻿]')
EDGE = '←→↗↘↙↖↓↑›‹×▷Ⅱ✓☰'


def norm(text):
    """One line, plain spaces, no invisible marks."""
    return re.sub(r'\s+', ' ', INVISIBLE.sub('', (text or '').replace(' ', ' '))).strip()


def tidy(text):
    """The text as it goes into the file: one line, without the arrows and marks that only decorate its ends."""
    t = norm(text)
    t = re.sub('^[\\s' + EDGE + ']+', '', t)
    t = re.sub('[\\s' + EDGE + ']+$', '', t)
    if t.endswith(' +') or t.endswith(' ·'):
        t = t[:-2].rstrip()
    return t


def compact(text):
    return re.sub(r'\s+', '', tidy(text))


# ---------------------------------------------------------------- Hebrew labels of the file
PAGE_LABEL = {'home': 'דף הבית', 'catalog': 'קטלוג', 'privacy': 'פרטיות ופניות', 'notfound': 'עמוד שגיאה (העמוד לא נמצא)'}
SHARED, AFTER = 'חלקים משותפים לכל העמודים', 'מופיע רק אחרי פעולה של המבקר'
AREA = {
    'seo': 'כותרת ותיאור לדפדפן ולמנועי חיפוש',
    'skip': 'קישור דילוג לתוכן (נגישות)', 'header': 'תפריט עליון', 'footer': 'תחתית העמוד', 'contact': 'טופס יצירת קשר',
    'home-hero': 'מסך הפתיחה – הקולקציה', 'home-collection': 'הקולקציה – כל המוצרים', 'home-support': 'ליווי ותמיכה',
    'film': 'סרט המוצר – סצנה {n}', 'film-frame': 'סרט המוצר', 'film-hud': 'סרט המוצר – מעבר בין השלבים',
    'evidence': 'תיעוד מקצועי', 'offer': 'הצעה מקצועית', 'training': 'הדרכה וליווי', 'faq': 'שאלות נפוצות',
    'related': 'מוצרים משלימים',
    'vt-nav': 'ניווט בתוך העמוד', 'vt-chapters': 'סרט המוצר – מעבר בין השלבים', 'vt-floating': 'כפתור צף',
    'catalog': 'קטלוג – כותרת וסינון', 'catalog-card': 'קטלוג – כרטיס מוצר: {name}',
    'privacy': 'תוכן העמוד', 'notfound': 'תוכן העמוד', 'main': 'תוכן העמוד', 'body': 'תוכן העמוד', 'dialog': 'חלון קופץ',
    'form-errors': 'טופס יצירת קשר – הודעות שגיאה',
    'form-sent': 'טופס יצירת קשר – בזמן השליחה ולאחריה',
    'whatsapp-message': 'הודעת WhatsApp שנפתחת מוכנה מראש',
    'inquiry-panel': 'חלון פנייה (נפתח בלחיצה על כפתור)',
    'inquiry-comment': 'חלון פנייה – טקסט שמופיע מראש בשדה השאלה',
    'vtech-entry': 'כניסה לעמוד V-TECH מדף הבית',
    'vtech-kit-alt': 'עמוד V-TECH – תיאור התמונה כשמגיעים לסצנת הערכה',
}
KIND = {
    'seo-title': 'כותרת הלשונית בדפדפן', 'seo-desc': 'תיאור העמוד במנועי חיפוש',
    'og-title': 'כותרת בשיתוף קישור', 'og-desc': 'תיאור בשיתוף קישור',
    'h1': 'כותרת ראשית', 'heading': 'כותרת', 'paragraph': 'פסקה', 'short': 'טקסט קצר', 'link': 'קישור',
    'button': 'כפתור', 'label': 'שם שדה בטופס', 'option': 'אפשרות בחירה', 'placeholder': 'רמז בתוך שדה',
    'summary': 'שאלה', 'item': 'פריט ברשימה', 'caption': 'כיתוב לתמונה', 'term': 'מונח', 'value': 'ערך',
    'aria': 'תווית לקוראי מסך', 'alt': 'תיאור תמונה (לקוראי מסך)', 'title': 'רמז בריחוף העכבר', 'message': 'הודעה',
}
CALM = ' (במצב "הפחתת תנועה")'
CHROME = {'skip', 'header', 'footer', 'contact'}


def area_label(area):
    label = AREA.get(area['key'], AREA['body'])
    return label.replace('{n}', str(area.get('scene') or '')).replace('{name}', area.get('name') or '').strip(' :–')


# ---------------------------------------------------------------- where a text comes from
content_index = {}


def index_content(node, path):
    if isinstance(node, dict):
        for k, v in node.items():
            index_content(v, path + [k])
    elif isinstance(node, list):
        for i, v in enumerate(node):
            index_content(v, path + [v['slug'] if isinstance(v, dict) and 'slug' in v else str(i)])
    elif isinstance(node, str) and norm(node):
        key = '.'.join(path)
        for part in [node] + node.split(' · '):
            if compact(part) and key not in content_index.setdefault(compact(part), []):
                content_index[compact(part)].append(key)


index_content(content, [])


def decode(source):
    return re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), source)


code = collections.OrderedDict()
for top in ('mitoderm', 'app'):
    for folder, _, names in sorted(os.walk(os.path.join(APP, top))):
        for name in sorted(names):
            if name.endswith(('.ts', '.tsx')):
                path = os.path.join(folder, name)
                rel = os.path.relpath(path, APP)
                code[rel] = decode(open(path, encoding='utf-8').read())
code_compact = {rel: re.sub(r'\s+', '', INVISIBLE.sub('', text.replace(' ', ' '))) for rel, text in code.items()}
# the film file first: it holds the captions of the product films, which other files only repeat in part
ORDER = sorted(code_compact, key=lambda rel: (0 if rel.endswith('product-films.ts') else 1, rel))


# which files and which part of the content file a page is built from: a short word ("הדרכה") stands in many
# places, and the place that belongs to the page is the one to name
PREFER = {
    'home': (['pilot/CollectionHero', 'pilot/HomeSections', 'mitoderm/Home'], 'home.'),
    'catalog': (['app/catalog', 'mitoderm/shared'], 'ui.'),
    'privacy': (['app/privacy'], ''),
    'notfound': (['app/not-found'], ''),
    'shared': (['mitoderm/shared', 'pilot/LeadForm', 'pilot/Experience', 'app/layout'], 'ui.'),
    'v-tech-system': (['pilot/VTech', 'pilot/vtech'], 'products.v-tech-system.'),
}


def source_of(text, where=None, product=None):
    """Where the words stand: the content file's key, or the file of the code - as a whole text, not as a
    piece of another one (a long text may also be found broken by markup)."""
    c = compact(text)
    if not c or not HEB.search(text):
        return ''
    files, prefix = PREFER.get(where, (['pilot/product-films', 'pilot/ProductCinema', 'pilot/product-proof'],
                                       'products.%s.' % where if where else ''))
    keys = content_index.get(c)
    if keys:
        own = [k for k in keys if prefix and k.startswith(prefix)]
        if own or where not in ('v-tech-system', 'privacy', 'notfound'):
            return 'content.json › ' + (own or keys)[0]
    order = sorted(ORDER, key=lambda rel: (0 if any(f in rel for f in files) else 1))
    whole = ("'%s'" % c, '"%s"' % c, '`%s`' % c, '>%s<' % c)
    for rel in order:
        if any(w in code_compact[rel] for w in whole):
            return rel
    if keys:
        return 'content.json › ' + keys[0]
    if len(c) >= 22:
        for rel in order:
            if c in code_compact[rel]:
                return rel
    if product and product in text:                       # a sentence built around the product's name
        pieces = [compact(p) for p in tidy(text).split(product) if HEB.search(p)]
        for rel in order:
            if pieces and all(p in code_compact[rel] for p in pieces):
                return rel + ' (תבנית עם שם המוצר)'
    return ''


# ---------------------------------------------------------------- rows of every page
def page_rows(page):
    """The rows of one page in page order: the computer view, plus what only the phone or the reduced-motion view
    shows, each put after the row it follows there."""
    views = page['views']
    merged = [dict(r, calm=False) for r in views['desktop']['rows']]
    for view in ('phone', 'calm'):
        if view not in views:
            continue
        by_area = collections.defaultdict(str)
        for r in merged:
            by_area[r['area']['key']] += compact(r['text'])
        whole = ''.join(by_area.values())
        pos = -1
        for r in views[view]['rows']:
            key = (r['kind'], compact(r['text']))
            hit = next((i for i in range(pos + 1, len(merged)) if (merged[i]['kind'], compact(merged[i]['text'])) == key), None)
            if hit is None:
                hit = next((i for i in range(len(merged)) if (merged[i]['kind'], compact(merged[i]['text'])) == key), None)
                if hit is not None:
                    continue                                # the same text stands elsewhere on the page
            if hit is not None:
                pos = hit
                continue
            c = compact(r['text'])
            if not c or c in by_area[r['area']['key']] or c in whole:
                continue                                    # the same words, only cut into pieces differently
            pos += 1
            merged.insert(pos, dict(r, calm=(view == 'calm')))
            by_area[r['area']['key']] += c
            whole += c
    rows = []
    for r in merged:
        if 'honeypot' in r.get('cls', ''):
            continue                                        # the anti-spam field: a visitor never sees it
        text = tidy(r['text'])
        if not LETTER.search(text):
            continue                                        # arrows, bare numbers, counters
        rows.append({'area_key': r['area']['key'], 'area': area_label(r['area']) + (CALM if r['calm'] else ''),
                     'kind': r['kind'], 'text': text})
    # a picture description or a screen-reader label that only repeats words visible right there adds nothing
    visible = collections.defaultdict(set)
    for r in rows:
        if r['kind'] not in ('alt', 'aria', 'title'):
            visible[r['area']].add(compact(r['text']))
    rows = [r for r in rows if not (r['kind'] in ('alt', 'aria', 'title') and compact(r['text']) in visible[r['area']])]
    seen, unique = set(), []
    for r in rows:
        key = (r['area'], r['kind'], compact(r['text']))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


pages = []
for page in data['pages']:
    view = page['views']['desktop']
    if page['kind'] == 'product':
        h1 = next((r['text'] for r in view['rows'] if r['kind'] == 'h1'), page['slug'])
        label = tidy(h1)
    else:
        label = PAGE_LABEL[page['kind']]
    seo = [('seo-title', view['title']), ('seo-desc', view['description'])]
    if view.get('ogTitle') and norm(view['ogTitle']) != norm(view['title']):
        seo.append(('og-title', view['ogTitle']))
    if view.get('ogDescription') and norm(view['ogDescription']) != norm(view['description']):
        seo.append(('og-desc', view['ogDescription']))
    rows = [{'area_key': 'seo', 'area': AREA['seo'], 'kind': k, 'text': tidy(t)} for k, t in seo if tidy(t)]
    pages.append({'label': label, 'route': page['route'] if page['kind'] != 'notfound' else '(כל כתובת שאינה קיימת)',
                  'kind': page['kind'], 'where': page.get('slug') or page['kind'], 'rows': rows + page_rows(page)})

# what repeats on every page is listed once
count = collections.Counter()
for p in pages:
    for key in {(r['area_key'], r['kind'], compact(r['text'])) for r in p['rows'] if r['area_key'] in CHROME}:
        count[key] += 1
shared, shared_seen = [], set()
for p in pages:
    kept = []
    for r in p['rows']:
        key = (r['area_key'], r['kind'], compact(r['text']))
        if r['area_key'] in CHROME and count[key] >= 2:
            if key not in shared_seen:
                shared_seen.add(key)
                shared.append(r)
            continue
        kept.append(r)
    p['rows'] = kept
order = {'skip': 0, 'header': 1, 'contact': 2, 'footer': 3}
shared.sort(key=lambda r: order[r['area_key']])             # stable: keeps page order inside each part

# texts that appear only after an action: word for word from the code, and still standing there
after = []
for e in extra['after_action']:
    text = code.get(e['file'])
    if text is None:
        sys.exit('site-text-extra.json names a file that is gone: ' + e['file'])
    flat = re.sub(r'\s+', ' ', INVISIBLE.sub('', text.replace(' ', ' ')))
    for fragment in e.get('fragments') or [e['text']]:
        if fragment not in flat:
            sys.exit('a text of site-text-extra.json no longer stands in %s: %s' % (e['file'], fragment))
    after.append({'area_key': e['area'], 'area': AREA[e['area']], 'kind': e['kind'], 'text': e['text'], 'source': e['file']})

for r in shared:
    r['source'] = source_of(r['text'], 'shared')
for p in pages:
    for r in p['rows']:
        r['source'] = source_of(r['text'], p['where'], p['label'] if p['kind'] == 'product' else None)
groups = [(p['label'], p['route'], p['rows']) for p in pages]
groups.append((SHARED, '(בכל העמודים)', shared))
groups.append((AFTER, '(בכל העמודים)', after))

# ---------------------------------------------------------------- the content file's texts that no page shows
shown = set()
for _, _, rows in groups:
    for r in rows:
        shown.add(compact(r['text']))
blob = ''.join(sorted(shown))
all_page_text = ''.join(compact(r['text']) for p in data['pages'] for v in p['views'].values() for r in v['rows'])
unused = []


def walk_unused(node, path, owner):
    if isinstance(node, dict):
        for k, v in node.items():
            walk_unused(v, path + [k], owner)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_unused(v, path + [str(i)], owner)
    elif isinstance(node, str) and HEB.search(node):
        for part in node.split(' · '):
            t = tidy(part)
            c = compact(part)
            if not c or not HEB.search(t):
                continue
            if c in shown or c in all_page_text:
                continue
            unused.append((owner, '.'.join(path), t))


for i, block in enumerate(content['home']):
    walk_unused(block, ['home', str(i)], PAGE_LABEL['home'])
for product in content['products']:
    walk_unused({k: v for k, v in product.items() if k not in ('slug', 'name', 'source_note')}, ['products', product['slug']], product['name'])
for key, owner in (('ui', 'כפתורים וכיתובים כלליים'), ('form', 'טופס'), ('contact', 'פרטי יצירת קשר')):
    walk_unused(content[key], [key], owner)
seen_unused, unique_unused = set(), []
for owner, key, text in unused:
    if (owner, compact(text)) not in seen_unused:
        seen_unused.add((owner, compact(text)))
        unique_unused.append((owner, key, text))
unused = unique_unused

# ---------------------------------------------------------------- report: Hebrew of the code that is nowhere in the file
listed = shown | {compact(e['text']) for e in extra['after_action']}
ignore = set(extra['not_on_site']['files'])
literal = re.compile(r'''(['"`])((?:\\.|(?!\1).)*?)\1''', re.S)
jsx = re.compile(r'>([^<>{}]*[֐-׿][^<>{}]*)<')
left = collections.OrderedDict()
for rel, text in code.items():
    if rel in ignore:
        continue
    found = set(m.group(2) for m in literal.finditer(text) if HEB.search(m.group(2)) and len(m.group(2)) < 400)
    found |= set(m.group(1) for m in jsx.finditer(text))
    for s in sorted(found):
        pieces = [compact(p) for p in re.split(r'\$\{[^}]*\}', s.replace('\\n', ' ').replace("\\'", "'")) if HEB.search(p)]
        if not pieces or any(ch in s for ch in ('=>', 'className', 'const ', '={', '/>', '//')):
            continue
        if all(p in listed or p in all_page_text or p in blob for p in pieces):
            continue
        if any(compact(f) in ''.join(pieces) or ''.join(pieces) in compact(f)
               for e in extra['after_action'] for f in (e.get('fragments') or [e['text']])):
            continue
        left.setdefault(rel, []).append(norm(s))
if left:
    print('Hebrew texts of the code that are neither on a page nor in site-text-extra.json:', file=sys.stderr)
    for rel, items in left.items():
        for s in items:
            print('   %s: %s' % (rel, s[:110]), file=sys.stderr)

# ---------------------------------------------------------------- the workbook
ARIAL = 'Arial'
GREEN, PALE, YELLOW, LINE = '1F4D3A', 'EEF4F0', 'FFF6CC', 'B7C4BC'
head_font = Font(name=ARIAL, size=11, bold=True, color='FFFFFF')
base_font = Font(name=ARIAL, size=11)
small_font = Font(name=ARIAL, size=9, color='5A6660')
thin = Side(style='thin', color=LINE)
RTL = dict(horizontal='right', vertical='top', wrap_text=True, readingOrder=2)
LTR = dict(horizontal='left', vertical='top', wrap_text=True, readingOrder=1)
PATH = dict(horizontal='right', vertical='top', wrap_text=True, readingOrder=1)

wb = Workbook()
summary = wb.active
summary.title = 'סיכום'
texts = wb.create_sheet('כל הטקסטים')
hidden = wb.create_sheet('לא מוצג באתר')
for ws in (summary, texts, hidden):
    ws.sheet_view.rightToLeft = True
    ws.sheet_view.showGridLines = False if ws is summary else True


def put(ws, ref, value, font=base_font, align=RTL, fill=None, fmt=None):
    cell = ws[ref]
    cell.value = value
    if isinstance(value, str) and value.startswith('=') and not fmt == 'formula':
        cell.data_type = 's'                                # a text that starts with "=" stays a text
    cell.font = font
    cell.alignment = Alignment(**align)
    if fill:
        cell.fill = PatternFill('solid', start_color=fill)
    return cell


# ---- sheet 2: every text
HEAD = ['מס׳', 'עמוד', 'כתובת העמוד', 'אזור בעמוד', 'סוג הטקסט', 'הטקסט באתר', 'מילים', 'תווים', 'הערות ותיקונים',
        'מקור הטקסט (לצוות הפיתוח)']
WIDTH = [6, 27, 34, 38, 24, 78, 8, 8, 44, 46]
for i, (title, width) in enumerate(zip(HEAD, WIDTH), 1):
    col = get_column_letter(i)
    texts.column_dimensions[col].width = width
    cell = put(texts, col + '1', title, head_font, dict(horizontal='center', vertical='center', wrap_text=True, readingOrder=2), GREEN)
    cell.border = Border(bottom=thin)
texts.row_dimensions[1].height = 32
row = 1
group_rows = []
for label, route, rows in groups:
    first = row + 1
    for r in rows:
        row += 1
        n = str(row)
        put(texts, 'A' + n, row - 1, align=dict(horizontal='center', vertical='top'))
        put(texts, 'B' + n, label)
        put(texts, 'C' + n, route, align=PATH if route.startswith('/') else RTL)
        put(texts, 'D' + n, r['area'])
        put(texts, 'E' + n, KIND[r['kind']])
        put(texts, 'F' + n, r['text'])
        put(texts, 'G' + n, '=IF(TRIM(F%s)="",0,LEN(TRIM(F%s))-LEN(SUBSTITUTE(TRIM(F%s)," ",""))+1)' % (n, n, n),
            align=dict(horizontal='center', vertical='top'), fmt='formula')
        put(texts, 'H' + n, '=LEN(F%s)' % n, align=dict(horizontal='center', vertical='top'), fmt='formula')
        put(texts, 'I' + n, None, fill=YELLOW)
        put(texts, 'J' + n, r.get('source', ''), font=small_font, align=LTR)
        if row == first:
            for i in range(1, len(HEAD) + 1):
                texts.cell(row=row, column=i).border = Border(top=thin)
    group_rows.append((label, route, first, row))
last = row
texts.freeze_panes = 'C2'
texts.auto_filter.ref = 'A1:%s%d' % (get_column_letter(len(HEAD)), last)
texts.page_setup.orientation = 'landscape'
texts.page_setup.fitToWidth = 1
texts.page_setup.fitToHeight = 0
texts.sheet_properties.pageSetUpPr.fitToPage = True
texts.print_title_rows = '1:1'

# ---- sheet 3: the content file's texts that the site does not show
HEAD3 = ['מס׳', 'שייך ל', 'הטקסט בקובץ התוכן', 'הערות', 'מפתח בקובץ התוכן (לצוות הפיתוח)']
for i, (title, width) in enumerate(zip(HEAD3, [6, 30, 90, 44, 50]), 1):
    col = get_column_letter(i)
    hidden.column_dimensions[col].width = width
    put(hidden, col + '3', title, head_font, dict(horizontal='center', vertical='center', wrap_text=True, readingOrder=2), GREEN)
put(hidden, 'A1', 'טקסטים מקובץ התוכן המאומת (%s) שהאתר אינו מציג בגרסתו הנוכחית. אין צורך לתקן אותם; הגיליון נועד לבדיקה אם משהו חסר באתר.'
    % content['source']['filename'], Font(name=ARIAL, size=11, bold=True), dict(horizontal='right', vertical='center', wrap_text=False, readingOrder=2))
for i, (owner, key, text) in enumerate(unused, 1):
    n = str(i + 3)
    put(hidden, 'A' + n, i, align=dict(horizontal='center', vertical='top'))
    put(hidden, 'B' + n, owner)
    put(hidden, 'C' + n, text)
    put(hidden, 'D' + n, None, fill=YELLOW)
    put(hidden, 'E' + n, key, font=small_font, align=LTR)
hidden.freeze_panes = 'A4'
hidden.auto_filter.ref = 'A3:E%d' % (len(unused) + 3)

# ---- sheet 1: what the file is and totals per page
summary.column_dimensions['A'].width = 46
summary.column_dimensions['B'].width = 40
for col in 'CDE':
    summary.column_dimensions[col].width = 14
made = datetime.datetime.fromisoformat(data['made'].replace('Z', '+00:00')).astimezone(datetime.timezone(datetime.timedelta(hours=2)))
put(summary, 'A1', 'כל הטקסטים באתר MITODERM', Font(name=ARIAL, size=18, bold=True, color=GREEN), dict(horizontal='right', vertical='center', readingOrder=2))
summary.row_dimensions[1].height = 34
put(summary, 'A2', 'עודכן: %s · לפי גרסת הבדיקה של האתר' % made.strftime('%d.%m.%Y'), small_font, dict(horizontal='right', vertical='center', readingOrder=2))
NOTES = [
    ('מה יש בקובץ', True),
    ('בגיליון "כל הטקסטים" רשום כל טקסט שמופיע באתר – עמוד אחר עמוד, לפי סדר ההופעה בעמוד.', False),
    ('כל שורה היא קטע טקסט אחד: כותרת, פסקה, כפתור, קישור, שם שדה בטופס וכדומה.', False),
    ('חלקים שחוזרים בכל העמודים (תפריט עליון, טופס יצירת קשר, תחתית העמוד) רשומים פעם אחת, תחת "%s".' % SHARED, False),
    ('טקסטים שמופיעים רק אחרי פעולה – הודעות הטופס וחלון הפנייה – רשומים בסוף הגיליון, תחת "%s".' % AFTER, False),
    ('תוויות לקוראי מסך ותיאורי תמונות אינם נראים על המסך: הם מוקראים למשתמשים בקורא מסך ונקראים גם על ידי מנועי החיפוש.', False),
    ('בגיליון "לא מוצג באתר" רשומים טקסטים מקובץ התוכן המאומת שהאתר אינו מציג כרגע.', False),
    ('איך ממלאים', True),
    ('הערות ותיקונים כותבים בגיליון "כל הטקסטים", בעמודה הצהובה "הערות ותיקונים", בשורה של הטקסט המתאים. את עמודת הטקסט אין צורך לשנות.', False),
    ('דוגמה להערה: להחליף את המילה "קליניקה" במילה "מרפאה".', False),
]
r = 4
for text, bold in NOTES:
    cell = put(summary, 'A%d' % r, text, Font(name=ARIAL, size=12 if bold else 11, bold=bold, color=GREEN if bold else '000000'),
               dict(horizontal='right', vertical='center', wrap_text=True, readingOrder=2))
    summary.merge_cells('A%d:E%d' % (r, r))
    summary.row_dimensions[r].height = 18 * (1 + len(text) // 118) + (4 if bold else 0)
    if text.startswith('דוגמה'):
        cell.fill = PatternFill('solid', start_color=YELLOW)
    r += 2 if text.startswith('בגיליון "לא מוצג') else 1
top = r + 1
for i, title in enumerate(['עמוד', 'כתובת באתר', 'קטעי טקסט', 'מילים', 'תווים']):
    put(summary, '%s%d' % ('ABCDE'[i], top), title, head_font, dict(horizontal='center', vertical='center', readingOrder=2), GREEN)
T = "'%s'" % texts.title
r = top
for label, route, first, final in group_rows:
    r += 1
    put(summary, 'A%d' % r, label)
    put(summary, 'B%d' % r, route, align=PATH if route.startswith('/') else RTL)
    put(summary, 'C%d' % r, '=COUNTIF(%s!$B$2:$B$%d,A%d)' % (T, last, r), align=dict(horizontal='center', vertical='top'), fmt='formula')
    put(summary, 'D%d' % r, '=SUMIF(%s!$B$2:$B$%d,A%d,%s!$G$2:$G$%d)' % (T, last, r, T, last), align=dict(horizontal='center', vertical='top'), fmt='formula')
    put(summary, 'E%d' % r, '=SUMIF(%s!$B$2:$B$%d,A%d,%s!$H$2:$H$%d)' % (T, last, r, T, last), align=dict(horizontal='center', vertical='top'), fmt='formula')
    for col in 'ABCDE':
        summary['%s%d' % (col, r)].border = Border(bottom=Side(style='hair', color=LINE))
        if (r - top) % 2 == 0:
            summary['%s%d' % (col, r)].fill = PatternFill('solid', start_color=PALE)
    for col in 'CDE':
        summary['%s%d' % (col, r)].number_format = '#,##0'
r += 1
bold = Font(name=ARIAL, size=11, bold=True)
put(summary, 'A%d' % r, 'סה״כ', bold)
for col in 'CDE':
    cell = put(summary, '%s%d' % (col, r), '=SUM(%s%d:%s%d)' % (col, top + 1, col, r - 1), bold, dict(horizontal='center', vertical='top'), fmt='formula')
    cell.number_format = '#,##0'
for col in 'ABCDE':
    summary['%s%d' % (col, r)].border = Border(top=thin)
put(summary, 'A%d' % (r + 2), 'בגיליון "לא מוצג באתר": %d קטעי טקסט.' % len(unused), small_font, dict(horizontal='right', vertical='center', readingOrder=2))
summary.freeze_panes = 'A%d' % (top + 1)
summary.page_setup.orientation = 'landscape'
summary.page_setup.fitToWidth = 1
summary.page_setup.fitToHeight = 0
summary.sheet_properties.pageSetUpPr.fitToPage = True
hidden.page_setup.orientation = 'landscape'
hidden.page_setup.fitToWidth = 1
hidden.page_setup.fitToHeight = 0
hidden.sheet_properties.pageSetUpPr.fitToPage = True

# no Cyrillic may reach the owner's file
for ws in wb:
    for line in ws.iter_rows():
        for cell in line:
            if isinstance(cell.value, str) and re.search(r'[Ѐ-ӿ]', cell.value):
                sys.exit('Cyrillic in %s!%s: %s' % (ws.title, cell.coordinate, cell.value[:60]))
wb.save(out)
total = sum(final - first + 1 for _, _, first, final in group_rows)
print(json.dumps({'out': out, 'rows': total, 'groups': len(group_rows), 'shared': len(shared), 'after_action': len(after),
                  'not_shown': len(unused), 'without_source': sum(1 for _, _, rows in groups for x in rows if not x.get('source')),
                  'per_group': [[label, final - first + 1] for label, _, first, final in group_rows]}, ensure_ascii=False))
