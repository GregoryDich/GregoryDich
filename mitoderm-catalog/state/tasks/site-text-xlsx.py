#!/usr/bin/env python3
"""Builds the owner's Excel file with every text of the site, laid out for editing.

Input: the JSON written by site-text-export.cjs (the rendered pages, block by block) and site-text-extra.json
(texts that appear only after the visitor does something). Output: one workbook, Hebrew throughout, right to left:
  "הוראות ותוכן"         how to edit, the colours, and every sheet with its counters and a status for the team
  one sheet per page      home, catalog, the 13 products in catalog order, privacy, not found: the texts in page
                          order, in bands (parts of the page); a grey column with today's text (locked), a yellow one
                          for the new wording and one for a remark; length counters; a link to the page's recording
  "קבוע בעמודי המוצרים"   texts that the standard product pages repeat word for word, listed once with their pages
  "משותף לכל האתר"        header, contact form, footer and the messages that appear after an action
  "לא מוצג באתר"          texts of the verified content file (codex-site/mitoderm/content.json) that no page shows
Left out, and counted: a row that is only a product's name (names are not edited), a text repeated in one part of a
page (one row, "repeated N times"). Texts no one sees on the screen (screen-reader labels, picture descriptions) stand
at the end of every sheet. Hidden columns keep a row id and where the text comes from, for applying the edits.

Usage: site-text-xlsx.py <site-texts.json> <out.xlsx>     (needs openpyxl; then run the xlsx skill's recalc.py)
The script stops if a text of site-text-extra.json no longer stands in the code, if a row of the site is not
accounted for, or if the workbook would carry a Cyrillic letter; it reports Hebrew texts of the code that are
neither on a page nor in site-text-extra.json.
"""
import collections
import datetime
import json
import os
import re
import sys

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.hyperlink import Hyperlink

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
    'vtech-kit-alt': 'עמוד V-TECH – תיאור התמונה כשמגיעים לסצנה של ערכת המוצר',
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

# ---------------------------------------------------------------- the editing layout: what goes on which sheet
# Every Hebrew word a reader of the file sees, apart from the site's own texts, stands in UI below.
UI = {
    'title': 'טקסטי האתר של MITODERM – קובץ לעריכה',
    'updated': 'עודכן: {date} · {texts} טקסטים לעריכה',
    'how': 'איך עורכים',
    'how_steps': [
        'כל לשונית היא עמוד באתר. השורות מסודרות לפי הסדר שבו הגולש רואה אותן ומחולקות לחלקי העמוד (הפסים הירוקים).',
        'בראש כל לשונית יש קישור לסרטון של העמוד. כדאי לצפות בו לפני שמתחילים.',
        'כדי לשנות טקסט, כתבו את הנוסח החדש המלא בעמודה הצהובה "הנוסח החדש". אפשר להעתיק את הטקסט מהעמודה "הטקסט באתר היום" ולתקן אותו.',
        'אם לא כתבתם דבר בשורה, הטקסט שלה נשאר באתר כמו שהוא.',
        'כדי למחוק טקסט, כתבו "למחוק" בעמודה "הערה". הטקסט יסומן בקו חוצה.',
        'כדי להוסיף טקסט חדש, כתבו אותו בעמודה "הערה" של השורה שאחריה הוא צריך להופיע.',
        'גם שאלות ובקשות אחרות כתבו בעמודה "הערה".',
        'בסיום שמרו את הקובץ ושלחו אותו אלינו. כמה אנשים יכולים לעבוד במקביל, כל אחד על לשוניות אחרות; בטבלה שלמטה אפשר לסמן את מצב העבודה בכל לשונית.',
    ],
    'know': 'כדאי לדעת',
    'know_lines': [
        'טקסטים שחוזרים בכל עמודי המוצרים (למשל "לקבלת פרטים" או "שאלות נפוצות") מופיעים פעם אחת, בלשונית "{template}". שינוי שתכתבו שם יחול על כל העמודים שרשומים באותה שורה. כדי לשנות טקסט כזה בעמוד אחד בלבד, כתבו זאת בעמודה "הערה".',
        'התפריט העליון, טופס יצירת הקשר, תחתית העמוד והודעות הטופס מופיעים פעם אחת, בלשונית "{shared}".',
        '{mark} מסמן מקום שבו האתר מציב את שם המוצר של כל עמוד. {num} מסמן מספר שהאתר מחשב בעצמו.',
        'שמות המוצרים באנגלית אינם רשומים בקובץ: הם אינם מתורגמים ואינם משתנים.',
        'בסוף כל לשונית יש טקסטים שאינם נראים על המסך: קוראי מסך מקריאים אותם לגולשים עם לקות ראייה, וגם גוגל קורא אותם. אפשר לדלג עליהם.',
        'העמוד של V-TECH SYSTEM בנוי אחרת משאר עמודי המוצרים, ולכן כל הטקסטים שלו נמצאים בלשונית שלו.',
        'בלשונית "{notshown}" יש טקסטים מקובץ התוכן המאושר שהאתר אינו מציג כרגע. אין צורך לערוך אותם; אם משהו מהם חסר באתר, כתבו זאת בעמודה "הערה".',
    ],
    'legend': 'מקרא הצבעים',
    'legend_rows': [
        ('current', 'הטקסט שמופיע באתר היום (לקריאה בלבד)'),
        ('new', 'כאן כותבים את הנוסח החדש'),
        ('done', 'נכתב נוסח חדש'),
        ('long', 'הנוסח החדש ארוך בהרבה מהטקסט באתר היום ואולי לא ייכנס בעיצוב; נבדוק ונחזור אליכם. בגוגל: כותרת עד 60 תווים, תיאור עד 160.'),
        ('strike', 'בעמודה "הערה" נכתב "למחוק"'),
    ],
    'toc': 'הלשוניות בקובץ',
    'toc_head': ['לשונית', 'מה יש בה', 'טקסטים', 'נכתב נוסח חדש', 'מצב העבודה', 'הערות הצוות'],
    'toc_total': 'סה״כ',
    'status': ['טרם התחיל', 'בעבודה', 'הסתיים'],
    'what': {
        'home': 'דף הבית', 'catalog': 'הקטלוג וכרטיסי המוצרים', 'product': 'עמוד המוצר',
        'template': 'טקסטים שחוזרים בכל עמודי המוצרים', 'shared': 'תפריט עליון, טופס יצירת קשר, תחתית העמוד והודעות',
        'privacy': 'עמוד הפרטיות', 'notfound': 'העמוד שמופיע כשהכתובת אינה קיימת', 'notshown': 'לעיון בלבד',
    },
    'sheet': {'index': 'הוראות ותוכן', 'home': 'דף הבית', 'catalog': 'קטלוג', 'template': 'קבוע בעמודי המוצרים',
              'shared': 'משותף לכל האתר', 'privacy': 'פרטיות', 'notfound': 'עמוד שגיאה', 'notshown': 'לא מוצג באתר'},
    'back': '→ חזרה להוראות ולתוכן',
    'address': 'כתובת העמוד:',
    'watch_desktop': '▶ צפייה בעמוד במחשב (וידאו)',
    'watch_phone': '▶ צפייה בעמוד בטלפון (וידאו)',
    'count_line': '="טקסטים בלשונית: {n} · נכתב נוסח חדש: "&{formula}',
    'head': ['מס׳', 'סוג הטקסט', 'הטקסט באתר היום', 'הנוסח החדש ✎', 'הערה', 'תווים בטקסט היום', 'תווים בנוסח החדש'],
    'head_pages': 'מופיע בעמודים',
    'head_hidden': ['אורך מרבי מומלץ', 'מזהה השורה', 'מקור הטקסט (לצוות הפיתוח)'],
    'band_seo': 'בגוגל ובשיתוף קישור (לא מופיע בתוך העמוד)',
    'band_hidden': 'לא נראים על המסך: טקסטים לקוראי מסך ותיאורי תמונות',
    'band_cards': 'כרטיסי המוצרים',
    'band_after': {'form-errors': 'אחרי לחיצה על "שליחה": הודעות שגיאה בטופס',
                   'form-sent': 'אחרי לחיצה על "שליחה": בזמן השליחה ולאחריה',
                   'whatsapp-message': 'ההודעה שנפתחת מוכנה מראש ב-WhatsApp',
                   'inquiry-panel': 'חלון הפנייה (נפתח בלחיצה על כפתורי ההצעה וההדרכה)',
                   'inquiry-comment': 'חלון הפנייה: השאלה שכבר כתובה בשדה',
                   'vtech-entry': 'המעבר מדף הבית לעמוד (מופיע לשנייה, בזמן המעבר)'},
    'scene_of': 'סצנה {i} מתוך {n}',
    'more_in_template': 'עוד {n} טקסטים בחלק הזה משותפים גם לעמודי מוצרים אחרים ונמצאים בלשונית "{template}"',
    'more_in_template_one': 'עוד טקסט אחד בחלק הזה משותף גם לעמודי מוצרים אחרים ונמצא בלשונית "{template}"',
    'shown_products': 'מוצגים כאן: {names}',
    'names_here': 'בחלק הזה מופיעים גם שמות המוצרים ({n}). שמות המוצרים אינם משתנים, ולכן אינם רשומים כאן.',
    'repeated': '{kind} ({n} פעמים)',
    'with_name': '{kind} · {name}',
    'first_scene': '{kind} · בסצנה הראשונה',
    'last_scene': '{kind} · בסצנה האחרונה',
    'all_products': 'בכל {n} עמודי המוצרים',
    'all_but': 'בכל עמודי המוצרים, למעט: {names}',
    'clinic_pages': 'בעמודי המוצרים לקליניקה, {n} עמודים: {names}',
    'home_pages': 'בעמודי המוצרים לטיפוח בבית, {n} עמודים: {names}',
    'seo_kind': {'seo-title': 'כותרת בגוגל ובלשונית הדפדפן', 'seo-desc': 'תיאור בתוצאות החיפוש',
                 'og-title': 'כותרת בשיתוף קישור (WhatsApp, פייסבוק)', 'og-desc': 'תיאור בשיתוף קישור'},
    'notshown_note': 'טקסטים מקובץ התוכן המאושר ({file}) שהאתר אינו מציג כרגע. אין צורך לערוך אותם. אם משהו מהם צריך להופיע באתר, כתבו זאת בעמודה "הערה".',
    'notshown_head': ['מס׳', 'שיוך', 'הטקסט בקובץ התוכן', 'הערה'],
    'footer': '&A · עמוד &P מתוך &N',
    'delete_word': 'למחוק',
    'strike_sample': 'טקסט לדוגמה',
}

PRODUCTS = [(p['slug'], p['name']) for p in content['products']]
NAME_OF = dict(PRODUCTS)
NAMES = sorted(NAME_OF.values(), key=len, reverse=True)
MARK, NUM = '[שם המוצר]', '[מספר]'
STANDARD = [slug for slug, _ in PRODUCTS if slug != 'v-tech-system']
HIDDEN_KINDS = {'aria', 'alt', 'title'}
SEO_KINDS = {'seo-title', 'seo-desc', 'og-title', 'og-desc'}
AREA_ORDER = {'seo': 0, 'film-frame': 1, 'film': 2, 'film-hud': 3, 'evidence': 4, 'offer': 5, 'training': 6, 'faq': 7,
              'related': 8, 'contact': 9}
disposition = collections.Counter()                       # what became of every row of the flat list


def marked(text):
    """The text with every product name and the film's step counter replaced by their marks."""
    t = text
    for name in NAMES:
        t = t.replace(name, MARK)
    return re.sub(r'^\d+ / \d+ · ', NUM + ' / ' + NUM + ' · ', t)


def name_only(text):
    return marked(norm(text)) == MARK


def strings_of(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from strings_of(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings_of(value)
    elif isinstance(node, str):
        yield node


def flat_code(text):
    return re.sub(r'\s+', '', INVISIBLE.sub('', text.replace(' ', ' ')))


# ---- what belongs to one product: its part of the content file, of the film file and of the template's tables
own_text = collections.defaultdict(str)
for product in content['products']:
    own_text[product['slug']] += ''.join(compact(s) for s in strings_of(product))
PER_SLUG = re.compile(r"^ '([a-z0-9-]+)':")
current = None
for line in code['mitoderm/pilot/product-films.ts'].split('\n'):
    if line.startswith(('export', '};')):
        current = None
    match = PER_SLUG.match(line)
    if match:
        current = match.group(1)
    if current:
        own_text[current] += flat_code(line)
# the template's own split of the product pages: home care, and the clinic products
HOME_CARE = re.findall(r"'([a-z0-9-]+)'", re.search(r'const homeCare=\[([^\]]*)\]', code['mitoderm/pilot/ProductCinema.tsx']).group(1))
CLINIC = [slug for slug in STANDARD if slug not in HOME_CARE]
template_lines = []
for line in code['mitoderm/pilot/ProductCinema.tsx'].split('\n'):
    match = PER_SLUG.match(line)
    if match:
        own_text[match.group(1)] += flat_code(line)        # one line per product: its titles, its related products
    else:
        template_lines.append(line)
TEMPLATE_CODE = flat_code('\n'.join(template_lines))
for ch in EDGE:
    TEMPLATE_CODE = TEMPLATE_CODE.replace(ch, '')
storyboard = os.path.join(APP, 'production', 'page-bible', 'pages', 'exo-nad', 'STORYBOARD.json')
own_text['exo-nad'] += ''.join(compact(s) for s in strings_of(json.load(open(storyboard, encoding='utf-8'))))


def template_literal(text):
    """The words stand in the product page template itself, as a whole literal (around the product's name)."""
    pieces = [compact(p) for p in re.split('|'.join(map(re.escape, (MARK, NUM))), marked(text))]
    pieces = [p for p in pieces if HEB.search(p)]
    return bool(pieces) and all(re.search(r"[\'\"`>}]" + re.escape(p) + r"[\'\"`<{]", TEMPLATE_CODE) for p in pieces)


def scene_of(row):
    match = re.search(r'סצנה (\d+)', row['area'])
    return int(match.group(1)) if match else None


def readable(text):
    """Two inline pieces of the page that touch without a space ("V-TECHלקבלת מחיר") get one; the marks of
    site-text-extra.json (‹שם המוצר›) become square brackets, which stay the right way round in a Hebrew cell."""
    return re.sub(r'([A-Za-z0-9%™])([א-ת])', r'\1 \2', text).replace('‹', '[').replace('›', ']')


def prepare(rows, own_name=None, cards=False):
    """Rows of one page for editing: a row that is only a product's name is left out (names are not edited); in a
    list of cards the name goes with the text that follows it in every card ("פסקה · EXO-NAD"); rows repeated in one
    part of the page (one text in every card) become one row, with the product's name as a mark."""
    rows = [dict(r) for r in rows]
    for r in rows:
        if cards and r['area_key'] == 'catalog-card':
            r['area'] = UI['band_cards']
    name_count, after_name = collections.Counter(), collections.defaultdict(collections.Counter)
    previous = None
    for r in rows:
        if r['kind'] not in SEO_KINDS and name_only(r['text']):
            name_count[r['area']] += 1
            previous = r['area']
            continue
        if previous == r['area']:
            after_name[r['area']][r['kind']] += 1
        previous = None

    def card_slot(r):
        n = name_count[r['area']]
        return n >= 3 and after_name[r['area']][r['kind']] * 2 >= n

    out, seen, names = [], {}, collections.defaultdict(list)
    context = None
    for r in rows:
        if r['kind'] not in SEO_KINDS and name_only(r['text']):
            disposition['product name'] += 1
            names[r['area']].append(norm(r['text']))
            context = (r['area'], norm(r['text']))
            continue
        r['context'] = context[1] if context and context[0] == r['area'] and context[1] != own_name and card_slot(r) else None
        context = None
        key = (r['area_key'], r['kind'], marked(r['text']))
        if key in seen:
            seen[key]['times'] += 1
            disposition['repeated on the page'] += 1
            continue
        r['times'] = 1
        r['shown'] = readable(r['text'])
        seen[key] = r
        out.append(r)
    for r in out:
        if r['times'] > 1:
            r['context'] = None
            r['shown'] = readable(marked(r['text']))
    return out, names


# ---- the pages, prepared
sheets_pages = []
for p in pages:
    slug = p['where'] if p['kind'] == 'product' else None
    rows, names = prepare(p['rows'], own_name=p['label'] if slug else None, cards=(p['kind'] == 'catalog'))
    scenes = max([scene_of(r) or 0 for r in rows] + [0])
    sheets_pages.append({'page': p, 'slug': slug, 'rows': rows, 'names': names, 'scenes': scenes})

# ---- texts that every standard product page repeats: one row each, on the template sheet
key_rows = collections.defaultdict(list)
for sp in sheets_pages:
    if sp['slug'] in STANDARD:
        for i, r in enumerate(sp['rows']):
            if r['kind'] not in SEO_KINDS:
                key_rows[(r['area_key'], r['kind'], marked(r['text']))].append((sp, i, r))
template_keys = set()
for key, found in key_rows.items():
    slugs = {sp['slug'] for sp, _, _ in found}
    if len(slugs) < 2:
        continue
    if template_literal(key[2]) or not any(compact(re.sub(r'^(שלב \d+: |\d+\. )', '', r['text'])) in own_text[sp['slug']]
                                           for sp, _, r in found):
        template_keys.add(key)


def first_pos(key):
    sp, i, r = key_rows[key][0]
    return (AREA_ORDER.get(key[0], 50), min(i / max(1, len(s['rows'])) for s, i, _ in key_rows[key]))


template_rows = []
for key in sorted(template_keys, key=first_pos):
    found = key_rows[key]
    sp0, _, r0 = found[0]
    slugs = [s for s in STANDARD if any(sp['slug'] == s for sp, _, _ in found)]
    scenes = [(scene_of(r), sp['scenes']) for sp, _, r in found]
    kind = KIND[key[1]]
    if key[0] == 'film' and all(s == 1 for s, _ in scenes):
        kind = UI['first_scene'].format(kind=kind)
    elif key[0] == 'film' and all(s == n for s, n in scenes):
        kind = UI['last_scene'].format(kind=kind)
    if len(slugs) == len(STANDARD):
        where = UI['all_products'].format(n=len(STANDARD))
    elif set(slugs) == set(CLINIC):
        where = UI['clinic_pages'].format(n=len(slugs), names=', '.join(NAME_OF[s] for s in slugs))
    elif set(slugs) == set(HOME_CARE):
        where = UI['home_pages'].format(n=len(slugs), names=', '.join(NAME_OF[s] for s in slugs))
    elif len(slugs) >= len(STANDARD) - 4:
        where = UI['all_but'].format(names=', '.join(NAME_OF[s] for s in STANDARD if s not in slugs))
    else:
        where = ', '.join(NAME_OF[s] for s in slugs)
    area = AREA['film-frame'] if key[0] == 'film' else AREA.get(key[0], AREA['body'])
    template_rows.append({'area_key': key[0], 'area': area, 'kind': key[1], 'kind_label': kind, 'text': r0['text'],
                          'shown': key[2], 'where': where, 'source': r0.get('source', ''), 'times': 1, 'context': None})
    disposition['shared by the product pages'] += len(found)
    disposition['template row'] += 1
    for sp, i, r in found:
        r['template'] = True


# ---------------------------------------------------------------- the workbook
ARIAL = 'Arial'
GREEN, PALE, LINE = '1F4D3A', 'EEF4F0', 'B7C4BC'
FILL = {'current': 'F1F3F2', 'new': 'FFF2B3', 'note': 'FFF9DD', 'done': 'D5F0DC', 'long': 'FFD39A', 'band': GREEN,
        'band_hidden': '6B7C73', 'info': 'F7F9F8'}
head_font = Font(name=ARIAL, size=11, bold=True, color='FFFFFF')
base_font = Font(name=ARIAL, size=11)
info_font = Font(name=ARIAL, size=10, italic=True, color='4F5D56')
small_font = Font(name=ARIAL, size=9, color='5A6660')
link_font = Font(name=ARIAL, size=11, color='0B57D0', underline='single')
thin = Side(style='thin', color=LINE)
hair = Side(style='hair', color=LINE)
RTL = dict(horizontal='right', vertical='top', wrap_text=True, readingOrder=2)
CENTER = dict(horizontal='center', vertical='top', wrap_text=True)
LTR = dict(horizontal='left', vertical='top', wrap_text=True, readingOrder=1)
PATH = dict(horizontal='right', vertical='center', wrap_text=False, readingOrder=1)
UNLOCKED = Protection(locked=False)
WIDTH = {'A': 6, 'B': 24, 'C': 54, 'D': 54, 'E': 30, 'F': 8, 'G': 10, 'H': 34}
HEAD_ROW = 5
made = datetime.datetime.fromisoformat(data['made'].replace('Z', '+00:00')).astimezone(datetime.timezone(datetime.timedelta(hours=2)))
today = datetime.date.today()

wb = Workbook()
index = wb.active
index.title = UI['sheet']['index']


def put(ws, ref, value, font=base_font, align=RTL, fill=None, formula=False):
    cell = ws[ref]
    cell.value = value
    if isinstance(value, str) and value.startswith('=') and not formula:
        cell.data_type = 's'                                # a text that starts with "=" stays a text
    cell.font = font
    cell.alignment = Alignment(**align)
    if fill:
        cell.fill = PatternFill('solid', start_color=fill)
    return cell


def lines(text, width):
    """How many lines a wrapped cell needs (Arial 11, about one character per unit of column width)."""
    per = max(4, int(width * 0.95))
    return sum(max(1, -(-len(part) // per)) for part in str(text).split('\n')) if text else 1


def link_to(ws, ref, sheet_title):
    ws[ref].hyperlink = Hyperlink(ref=ref, location="'%s'!A1" % sheet_title, display=ws[ref].value)


def setup(ws, tab, landscape=True):
    ws.sheet_view.rightToLeft = True
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = tab
    ws.page_setup.orientation = 'landscape' if landscape else 'portrait'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.5
    ws.oddFooter.center.text = UI['footer']
    ws.oddFooter.center.font = 'Arial'


def limit_of(kind, text):
    if kind == 'seo-title' or kind == 'og-title':
        return 60
    if kind == 'seo-desc':
        return 160
    if kind == 'og-desc':
        return 200
    return max(len(text) + 8, -(-len(text) * 13 // 10))


counts = {}                                                 # sheet title -> (first row, last row, texts)


def write_edit_sheet(ws, code_name, title, route, videos, items, pages_col=False, tab=GREEN):
    """One sheet to edit: the heading lines, then bands (parts of the page), rows of text and info lines."""
    setup(ws, tab)
    last_col = 'H' if pages_col else 'G'
    for col, width in WIDTH.items():
        if col <= last_col:
            ws.column_dimensions[col].width = width
    hidden = ['I', 'J', 'K'] if pages_col else ['H', 'I', 'J']
    for col, width in zip(hidden, (10, 14, 40)):
        ws.column_dimensions[col].width = width
        ws.column_dimensions[col].hidden = True
    limit_col, id_col, source_col = hidden
    put(ws, 'A1', title, Font(name=ARIAL, size=18, bold=True, color=GREEN), dict(horizontal='right', vertical='center', readingOrder=2))
    ws.merge_cells('A1:D1')
    ws.row_dimensions[1].height = 32
    put(ws, 'E1', UI['back'], link_font, dict(horizontal='left', vertical='center', readingOrder=2))
    ws.merge_cells('E1:%s1' % last_col)
    link_to(ws, 'E1', index.title)
    if route:
        put(ws, 'A2', UI['address'], small_font, dict(horizontal='right', vertical='center', readingOrder=2))
        ws.merge_cells('A2:B2')
        put(ws, 'C2', route, small_font, dict(horizontal='right', vertical='center', readingOrder=1 if route.startswith('/') else 2))
    if videos:
        put(ws, 'D2', UI['watch_desktop'], link_font, dict(horizontal='right', vertical='center', readingOrder=2))
        ws['D2'].hyperlink = videos['desktop']
        put(ws, 'E2', UI['watch_phone'], link_font, dict(horizontal='right', vertical='center', readingOrder=2))
        ws.merge_cells('E2:%s2' % last_col)
        ws['E2'].hyperlink = videos['phone']
    ws.row_dimensions[2].height = 20
    heads = UI['head'] + ([UI['head_pages']] if pages_col else [])
    for i, text in enumerate(heads):
        col = get_column_letter(i + 1)
        put(ws, '%s%d' % (col, HEAD_ROW), text, head_font, dict(horizontal='center', vertical='center', wrap_text=True, readingOrder=2), GREEN)
    for col, text in zip(hidden, UI['head_hidden']):
        put(ws, '%s%d' % (col, HEAD_ROW), text, small_font, CENTER)
    ws.row_dimensions[HEAD_ROW].height = 34
    row, n = HEAD_ROW, 0
    first = HEAD_ROW + 1
    for item in items:
        row += 1
        if item[0] == 'band':
            style = item[2] if len(item) > 2 else 'band'
            put(ws, 'A%d' % row, item[1], Font(name=ARIAL, size=11, bold=True, color='FFFFFF'),
                dict(horizontal='right', vertical='center', readingOrder=2, indent=1), FILL[style])
            ws.merge_cells('A%d:%s%d' % (row, last_col, row))
            ws.row_dimensions[row].height = 22
            continue
        if item[0] == 'info':
            put(ws, 'A%d' % row, None, fill=FILL['info'])
            put(ws, 'B%d' % row, item[1], info_font, dict(horizontal='right', vertical='center', wrap_text=True, readingOrder=2), FILL['info'])
            ws.merge_cells('B%d:D%d' % (row, row))
            if len(item) > 2 and item[2]:
                ws['B%d' % row].hyperlink = Hyperlink(ref='B%d' % row, location="'%s'!A1" % item[2], display=item[1])
                ws['B%d' % row].font = Font(name=ARIAL, size=10, italic=True, color='0B57D0', underline='single')
            put(ws, 'E%d' % row, None, fill=FILL['note']).protection = UNLOCKED
            for col in 'FG' + ('H' if pages_col else ''):
                put(ws, '%s%d' % (col, row), None, fill=FILL['info'])
            ws.row_dimensions[row].height = 15 * lines(item[1], WIDTH['B'] + WIDTH['C'] + WIDTH['D']) + 6
            continue
        r = item[1]
        n += 1
        nn = str(row)
        put(ws, 'A' + nn, n, align=CENTER)
        put(ws, 'B' + nn, r['kind_label'], Font(name=ARIAL, size=10, color='3D4A44'))
        put(ws, 'C' + nn, r['shown'], fill=FILL['current'])
        put(ws, 'D' + nn, None, fill=FILL['new']).protection = UNLOCKED
        put(ws, 'E' + nn, None, fill=FILL['note']).protection = UNLOCKED
        put(ws, 'F' + nn, '=LEN(C%s)' % nn, Font(name=ARIAL, size=10, color='5A6660'), CENTER, formula=True)
        put(ws, 'G' + nn, '=IF(LEN(TRIM(D%s))=0,"",LEN(TRIM(D%s)))' % (nn, nn), Font(name=ARIAL, size=10, color='5A6660'), CENTER, formula=True)
        if pages_col:
            put(ws, 'H' + nn, r['where'], Font(name=ARIAL, size=10, color='3D4A44'))
        put(ws, limit_col + nn, limit_of(r['kind'], r['shown']), small_font, CENTER)
        put(ws, id_col + nn, '%s-%03d' % (code_name, n), small_font, LTR)
        put(ws, source_col + nn, r.get('source', ''), small_font, LTR)
        for col in 'ABCDEFG' + ('H' if pages_col else ''):
            ws['%s%s' % (col, nn)].border = Border(bottom=hair)
        need = max(lines(r['shown'], WIDTH['C']), lines(r['kind_label'], WIDTH['B']),
                   lines(r['where'], WIDTH['H']) if pages_col else 1)
        ws.row_dimensions[row].height = 15 * need + 6
    last = row
    counts[ws.title] = (first, last, n, id_col)
    put(ws, 'A3', UI['count_line'].format(n=n, formula='SUMPRODUCT(--(LEN(TRIM(D%d:D%d))>0))' % (first, last)),
        Font(name=ARIAL, size=10, color='3D4A44'), dict(horizontal='right', vertical='center', readingOrder=2), formula=True)
    ws.merge_cells('A3:D3')
    rng = 'D%d:D%d' % (first, last)
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=['AND(LEN(TRIM(D%d))>0,LEN(TRIM(D%d))>$%s%d)' % (first, first, limit_col, first)],
        fill=PatternFill('solid', start_color=FILL['long'], end_color=FILL['long']), stopIfTrue=True))
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=['LEN(TRIM(D%d))>0' % first], fill=PatternFill('solid', start_color=FILL['done'], end_color=FILL['done'])))
    ws.conditional_formatting.add('C%d:C%d' % (first, last), FormulaRule(
        formula=['TRIM($E%d)="%s"' % (first, UI['delete_word'])], font=Font(strike=True, color='8A8F8C')))
    ws.freeze_panes = 'A%d' % (HEAD_ROW + 1)
    ws.print_title_rows = '%d:%d' % (HEAD_ROW, HEAD_ROW)
    ws.protection.sheet = True
    ws.protection.formatColumns = False
    ws.protection.formatRows = False
    return ws


def kind_label(r):
    if r['kind'] in SEO_KINDS:
        return UI['seo_kind'][r['kind']]
    label = KIND[r['kind']]
    if r.get('times', 1) > 1:
        return UI['repeated'].format(kind=label, n=r['times'])
    if r.get('context'):
        return UI['with_name'].format(kind=label, name=r['context'])
    return label


def items_of(rows, scenes=0, names=None, template_counts=None, hidden_area=True, order_rows=None):
    """Bands and rows in page order: the search texts first, the texts no one sees on the screen last."""
    seo = [r for r in rows if r['kind'] in SEO_KINDS]
    seen_rows = [r for r in rows if r['kind'] not in SEO_KINDS and r['kind'] not in HIDDEN_KINDS]
    unseen = [r for r in rows if r['kind'] in HIDDEN_KINDS]
    items = []
    if seo:
        items.append(('band', UI['band_seo']))
        items += [('row', dict(r, kind_label=r.get('kind_label') or kind_label(r))) for r in seo]

    def band_title(area):
        if scenes and re.search(r'סצנה \d+', area):
            return re.sub(r'סצנה (\d+)', lambda m: UI['scene_of'].format(i=m.group(1), n=scenes), area)
        return area

    order, by_area = [], collections.OrderedDict()
    for r in seen_rows:
        by_area.setdefault(r['area'], []).append(r)
    areas_in_order = list(by_area)
    for area in (template_counts or {}):
        if area not in by_area:
            areas_in_order.append(area)                    # a part of the page with nothing of its own
    order_rows = order_rows or rows
    areas_in_order.sort(key=lambda a: min([i for i, r in enumerate(order_rows) if r['area'] == a] or [10 ** 6]))
    for area in areas_in_order:
        items.append(('band', band_title(area)))
        items += [('row', dict(r, kind_label=r.get('kind_label') or kind_label(r))) for r in by_area.get(area, [])]
        if names and names.get(area) and area == AREA['related']:
            items.append(('info', UI['shown_products'].format(names=' · '.join(names[area]))))
        elif names and len(names.get(area, [])) >= 3:
            items.append(('info', UI['names_here'].format(n=len(set(names[area])))))
        if template_counts and template_counts.get(area):
            n = template_counts[area]
            line = UI['more_in_template_one'] if n == 1 else UI['more_in_template']
            items.append(('info', line.format(n=n, template=UI['sheet']['template']), UI['sheet']['template']))
    if unseen:
        items.append(('band', UI['band_hidden'], 'band_hidden'))
        for r in unseen:
            label = r.get('kind_label') or kind_label(r)
            if hidden_area:
                label = label + ' · ' + band_title(r['area'])
            items.append(('row', dict(r, kind_label=label)))
    return items


# ---- recordings of the pages (the owner's acceptance list), so the editor can watch the page while editing
videos = {}
samples_path = os.path.join(ROOT, 'state', 'progress', 'samples.json')
if os.path.exists(samples_path):
    for pair in json.load(open(samples_path, encoding='utf-8'))['rows'][0]['pairs']:
        key = 'home' if not re.search('[A-Z]', pair['name']) else pair['name']
        videos[key] = {'desktop': pair['desktop'], 'phone': pair['phone']}

# ---- the sheets, in the order a visitor meets the pages
toc = []
by_kind = {sp['page']['kind']: sp for sp in sheets_pages if sp['page']['kind'] != 'product'}
by_slug = {sp['slug']: sp for sp in sheets_pages if sp['slug']}
vtech_extra = [dict(area_key=e['area_key'], area=UI['band_after'].get(e['area_key'], e['area']), kind=e['kind'],
                    text=e['text'], shown=readable(e['text']), source=e['source'], times=1, context=None)
               for e in after if e['area_key'] in ('vtech-entry', 'vtech-kit-alt')]


def page_sheet(sp, code_name, title, what, extra=()):
    rows = [r for r in sp['rows'] if not r.get('template')] + list(extra)
    tcounts = collections.Counter(r['area'] for r in sp['rows'] if r.get('template') and r['kind'] not in HIDDEN_KINDS)
    disposition['own row'] += sum(1 for r in sp['rows'] if not r.get('template'))
    route = sp['page']['route']
    ws = wb.create_sheet(title)
    write_edit_sheet(ws, code_name, title, route, videos.get('home' if sp['page']['kind'] == 'home' else title),
                     items_of(rows, sp['scenes'], sp['names'], tcounts, order_rows=sp['rows'] + list(extra)))
    toc.append((title, what))


page_sheet(by_kind['home'], 'home', UI['sheet']['home'], UI['what']['home'])
page_sheet(by_kind['catalog'], 'catalog', UI['sheet']['catalog'], UI['what']['catalog'])
for slug, name in PRODUCTS:
    page_sheet(by_slug[slug], slug, name, UI['what']['product'], vtech_extra if slug == 'v-tech-system' else ())
disposition['own row'] += len(vtech_extra)

ws = wb.create_sheet(UI['sheet']['template'])
write_edit_sheet(ws, 'template', UI['sheet']['template'], None, None, items_of(template_rows, hidden_area=True),
                 pages_col=True, tab='B8860B')
toc.append((ws.title, UI['what']['template']))

shared_rows, shared_names = prepare(shared)
shared_rows += [dict(area_key=e['area_key'], area=UI['band_after'].get(e['area_key'], e['area']), kind=e['kind'],
                     text=e['text'], shown=readable(e['text']), source=e['source'], times=1, context=None)
                for e in after if e['area_key'] not in ('vtech-entry', 'vtech-kit-alt')]
disposition['own row'] += len(shared_rows)
ws = wb.create_sheet(UI['sheet']['shared'])
write_edit_sheet(ws, 'shared', UI['sheet']['shared'], None, None, items_of(shared_rows, names=shared_names), tab='B8860B')
toc.append((ws.title, UI['what']['shared']))

page_sheet(by_kind['privacy'], 'privacy', UI['sheet']['privacy'], UI['what']['privacy'])
page_sheet(by_kind['notfound'], 'notfound', UI['sheet']['notfound'], UI['what']['notfound'])

# ---- the content file's texts that no page shows: for reference
ns = wb.create_sheet(UI['sheet']['notshown'])
setup(ns, '8A9690')
for col, width in zip('ABCDE', (6, 30, 90, 40, 46)):
    ns.column_dimensions[col].width = width
ns.column_dimensions['E'].hidden = True
put(ns, 'A1', UI['sheet']['notshown'], Font(name=ARIAL, size=18, bold=True, color=GREEN), dict(horizontal='right', vertical='center', readingOrder=2))
ns.merge_cells('A1:C1')
ns.row_dimensions[1].height = 32
put(ns, 'D1', UI['back'], link_font, dict(horizontal='left', vertical='center', readingOrder=2))
link_to(ns, 'D1', index.title)
put(ns, 'A2', UI['notshown_note'].format(file=content['source']['filename']), Font(name=ARIAL, size=11),
    dict(horizontal='right', vertical='center', wrap_text=True, readingOrder=2))
ns.merge_cells('A2:D2')
ns.row_dimensions[2].height = 36
for i, text in enumerate(UI['notshown_head']):
    put(ns, '%s%d' % ('ABCD'[i], HEAD_ROW - 1), text, head_font, dict(horizontal='center', vertical='center', readingOrder=2), GREEN)
put(ns, 'E%d' % (HEAD_ROW - 1), UI['head_hidden'][2], small_font, CENTER)
for i, (owner, key, text) in enumerate(unused, 1):
    rr = HEAD_ROW - 1 + i
    put(ns, 'A%d' % rr, i, align=CENTER)
    put(ns, 'B%d' % rr, owner, Font(name=ARIAL, size=10, color='3D4A44'))
    put(ns, 'C%d' % rr, text, fill=FILL['current'])
    put(ns, 'D%d' % rr, None, fill=FILL['note']).protection = UNLOCKED
    put(ns, 'E%d' % rr, key, small_font, LTR)
    for col in 'ABCD':
        ns['%s%d' % (col, rr)].border = Border(bottom=hair)
    ns.row_dimensions[rr].height = 15 * max(lines(text, 90), lines(owner, 30)) + 6
ns.freeze_panes = 'A%d' % HEAD_ROW
ns.print_title_rows = '%d:%d' % (HEAD_ROW - 1, HEAD_ROW - 1)
ns.protection.sheet = True
ns.protection.formatColumns = False
ns.protection.formatRows = False
toc.append((ns.title, UI['what']['notshown']))

# ---- the first sheet: how to edit, the colours, the sheets with their counters
setup(index, GREEN, landscape=False)
for col, width in zip('ABCDEF', (36, 44, 11, 14, 15, 34)):
    index.column_dimensions[col].width = width
total_texts = sum(c[2] for c in counts.values())
put(index, 'A1', UI['title'], Font(name=ARIAL, size=20, bold=True, color=GREEN), dict(horizontal='right', vertical='center', readingOrder=2))
index.merge_cells('A1:F1')
index.row_dimensions[1].height = 38
put(index, 'A2', UI['updated'].format(date=today.strftime('%d.%m.%Y'), texts=total_texts), small_font,
    dict(horizontal='right', vertical='center', readingOrder=2))
index.merge_cells('A2:F2')
r = 4


def note_line(text, bold=False, number=None, fill=None):
    global r
    font = Font(name=ARIAL, size=13 if bold else 11, bold=bold, color=GREEN if bold else '1E2622')
    put(index, 'A%d' % r, ('%d.  ' % number if number else ('•  ' if not bold else '')) + text, font,
        dict(horizontal='right', vertical='center', wrap_text=True, readingOrder=2), fill)
    index.merge_cells('A%d:F%d' % (r, r))
    index.row_dimensions[r].height = (17 * lines(text, 140) + 6) if not bold else 24
    r += 1


note_line(UI['how'], bold=True)
for i, text in enumerate(UI['how_steps'], 1):
    note_line(text, number=i)
r += 1
note_line(UI['know'], bold=True)
for text in UI['know_lines']:
    note_line(text.format(template=UI['sheet']['template'], shared=UI['sheet']['shared'], notshown=UI['sheet']['notshown'],
                          mark=MARK, num=NUM))
r += 1
note_line(UI['legend'], bold=True)
for key, text in UI['legend_rows']:
    sample = index['A%d' % r]
    put(index, 'A%d' % r, UI['delete_word'] if key == 'strike' else '', base_font, CENTER,
        {'current': FILL['current'], 'new': FILL['new'], 'done': FILL['done'], 'long': FILL['long'], 'strike': FILL['current']}[key])
    if key == 'strike':
        sample.value = UI['strike_sample']
        sample.font = Font(name=ARIAL, size=11, strike=True, color='8A8F8C')
    sample.border = Border(top=thin, bottom=thin, left=thin, right=thin)
    put(index, 'B%d' % r, text, base_font, dict(horizontal='right', vertical='center', wrap_text=True, readingOrder=2))
    index.merge_cells('B%d:F%d' % (r, r))
    index.row_dimensions[r].height = 17 * lines(text, 110) + 6
    r += 1
r += 1
note_line(UI['toc'], bold=True)
top = r
for i, text in enumerate(UI['toc_head']):
    put(index, '%s%d' % ('ABCDEF'[i], top), text, head_font, dict(horizontal='center', vertical='center', wrap_text=True, readingOrder=2), GREEN)
index.row_dimensions[top].height = 30
status = DataValidation(type='list', formula1='"%s"' % ','.join(UI['status']), allow_blank=True)
index.add_data_validation(status)
for title, what in toc:
    r += 1
    put(index, 'A%d' % r, title, link_font, dict(horizontal='right', vertical='center', readingOrder=2))
    link_to(index, 'A%d' % r, title)
    put(index, 'B%d' % r, what, base_font, dict(horizontal='right', vertical='center', wrap_text=True, readingOrder=2))
    q = "'%s'" % title
    if title in counts:
        first, last, n, id_col = counts[title]
        put(index, 'C%d' % r, '=COUNTA(%s!%s%d:%s%d)' % (q, id_col, first, id_col, last), base_font, CENTER, formula=True)
        put(index, 'D%d' % r, '=SUMPRODUCT(--(LEN(TRIM(%s!D%d:D%d))>0))' % (q, first, last), base_font, CENTER, formula=True)
        put(index, 'E%d' % r, None, base_font, CENTER, FILL['note']).protection = UNLOCKED
        status.add('E%d' % r)
    else:
        put(index, 'C%d' % r, '=COUNTA(%s!C%d:C%d)' % (q, HEAD_ROW, HEAD_ROW + len(unused) - 1), base_font, CENTER, formula=True)
    put(index, 'F%d' % r, None, base_font, RTL, FILL['note']).protection = UNLOCKED
    for col in 'ABCDEF':
        index['%s%d' % (col, r)].border = Border(bottom=hair)
        if col in 'CDE':
            index['%s%d' % (col, r)].alignment = Alignment(horizontal='center', vertical='center')
    index.row_dimensions[r].height = 20
r += 1
put(index, 'A%d' % r, UI['toc_total'], Font(name=ARIAL, size=11, bold=True))
for col in 'CD':
    cell = put(index, '%s%d' % (col, r), '=SUM(%s%d:%s%d)' % (col, top + 1, col, r - 2), Font(name=ARIAL, size=11, bold=True), CENTER, formula=True)
    cell.number_format = '#,##0'
for col in 'ABCDEF':
    index['%s%d' % (col, r)].border = Border(top=thin)
index.protection.sheet = True
index.protection.formatColumns = False
index.protection.formatRows = False

# ---- checks before the file is written
for ws in wb:
    for line in ws.iter_rows():
        for cell in line:
            if isinstance(cell.value, str) and re.search(r'[Ѐ-ӿ]', cell.value):
                sys.exit('Cyrillic in %s!%s: %s' % (ws.title, cell.coordinate, cell.value[:60]))
flat_rows = sum(len(p['rows']) for p in pages) + len(shared) + len(after)
accounted = disposition['product name'] + disposition['repeated on the page'] + disposition['own row'] + disposition['shared by the product pages']
if accounted != flat_rows:
    sys.exit('rows not accounted for: %d of %d (%s)' % (accounted, flat_rows, dict(disposition)))
wb.save(out)

# rows keep their height but grow again when someone types a longer text: no row height is a manual one
import zipfile
tmp = out + '.tmp'
with zipfile.ZipFile(out) as src_zip, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as dst_zip:
    for info in src_zip.infolist():
        blob = src_zip.read(info.filename)
        if info.filename.startswith('xl/worksheets/sheet'):
            blob = blob.replace(b' customHeight="1"', b'')
        dst_zip.writestr(info, blob)
os.replace(tmp, out)
print(json.dumps({'out': out, 'sheets': [ws.title for ws in wb], 'texts_to_edit': total_texts,
                  'per_sheet': {t: c[2] for t, c in counts.items()}, 'not_shown': len(unused),
                  'flat_rows': flat_rows, 'disposition': dict(disposition)}, ensure_ascii=False))
