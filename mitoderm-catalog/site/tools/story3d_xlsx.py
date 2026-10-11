#!/usr/bin/env python3
"""Build site/MITODERM-3D-story.xlsx from site/story3d.json (the 3D scroll story of every page, 11/10/2026).

story3d.json holds, per page, the story written by the workflow (writer -> marketing and fact critics -> fixer):
screens with the 3D action and text KEYS, the purchase screen, 3D assets, new strings and questions. Texts are never
typed here: each key is resolved against the reviewed sources (storyboard.he.json, product-pages*.json) or the
reviewed new strings, so the workbook shows exactly the Hebrew and English that passed review. An unknown key is
marked, not guessed.

Usage: python3 site/tools/story3d_xlsx.py
"""
import json, os, re
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

SITE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
load = lambda name: json.load(open(os.path.join(SITE, name), encoding='utf-8'))

data = load('story3d.json')
he_pages = {p['slug']: {i['key']: i for i in p['items']} for p in load('storyboard.he.json')['pages']}
cat_en = {s['slug']: s for s in load('product-pages.json')}
cat_he = {s['slug']: h for s, h in zip(load('product-pages.json'), load('product-pages.he.json'))}
nav = he_pages['home']['nav.blocks']
nav_he, nav_en = nav['he'].split(' · '), nav['en'].split(' · ')
new = {(n['slug'], n['key']): n for n in data.get('new_strings', [])}
for h in data.get('hebrew', []):
    new.setdefault((h['slug'], h['key']), {}).update(he=h['he'])

MISSING = '⚠ нет ключа: '


def walk(obj, path):
    """cat path like 'steps[0][0]' or 'ingredients' -> value"""
    for part in re.findall(r'[A-Za-z_0-9]+|\[\d+\]', path):
        obj = obj[int(part[1:-1])] if part.startswith('[') else obj[part]
    return obj


def flat(v):
    if isinstance(v, list):
        return ' · '.join(flat(x) for x in v)
    return str(v)


def resolve(slug, key):
    """-> (he, en) for a text key, or a marked miss"""
    if not key:
        return '', ''
    key = key.strip()
    try:
        m = re.fullmatch(r'nav\[(\d)\]', key)
        if m:
            return nav_he[int(m.group(1))], nav_en[int(m.group(1))]
        if key.startswith('cat.'):
            path = key[4:]
            return flat(walk(cat_he[slug], path)), flat(walk(cat_en[slug], path))
        page = he_pages['home'] if key.startswith('home.') else he_pages.get(slug, {})
        if key in page:
            return page[key]['he'], page[key]['en']
        if (slug, key) in new:
            n = new[(slug, key)]
            return n.get('he', MISSING + key + ' (иврит не готов)'), n.get('en', '')
    except (KeyError, IndexError, TypeError):
        pass
    return MISSING + key, MISSING + key


HEAD = PatternFill('solid', fgColor='1A1817')
HFONT = Font(bold=True, color='FFFFFF')
WRAP = Alignment(wrap_text=True, vertical='top')
RTL = Alignment(wrap_text=True, vertical='top', horizontal='right', readingOrder=2)


def sheet(wb, title, cols, rows, he_cols=()):
    ws = wb.create_sheet(title)
    ws.append([c for c, _ in cols])
    for c in ws[1]:
        c.fill, c.font, c.alignment = HEAD, HFONT, WRAP
    for r in rows:
        ws.append(r)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = RTL if ws.cell(1, c.column).value in he_cols else WRAP
    for i, (_, w) in enumerate(cols, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w
    ws.freeze_panes = 'C2'
    return ws


stories = data['stories']
wb = Workbook(); wb.remove(wb.active)
sheet(wb, 'Overview', [('Страница', 22), ('Slug', 20), ('Линейка', 16), ('Назначение', 14), ('Цветовое окружение', 40),
                       ('Экран с оттенком серии', 12), ('Герой-объект', 30), ('Сюжет одной строкой', 60), ('Новых строк', 10), ('Вопросов', 10)],
      [[s['name'], s['slug'], s['line'], s['use'], s['colour_env'], s['series_tint_screen'], s['hero_object'], s['story_one_line'],
        len(s.get('new_strings', [])), len(s.get('questions_ru', []))] for s in stories])
rows = []
for s in stories:
    for sc in s['screens']:
        k, t, l, c = (resolve(s['slug'], sc[x]) for x in ('kicker_key', 'title_key', 'line_key', 'cta_key'))
        labs = [resolve(s['slug'], x) for x in sc['label_keys']]
        rows.append([s['name'], sc['n'], sc['block'], sc['screen_name_ru'], sc['action_3d_ru'], sc['transition_ru'],
                     k[0], t[0], l[0], ' · '.join(x[0] for x in labs), c[0], t[1], l[1], ' · '.join(x[1] for x in labs), c[1], sc['mobile_ru'],
                     ' | '.join([sc['kicker_key'], sc['title_key'], sc['line_key'], ','.join(sc['label_keys']), sc['cta_key']])])
sheet(wb, 'Screens', [('Страница', 20), ('#', 4), ('Блок', 12), ('Экран', 24), ('Что делает 3D', 50), ('Переход на скролле', 40),
                      ('Кикер HE', 18), ('Заголовок HE', 34), ('Фраза HE', 50), ('Метки HE', 40), ('Кнопка HE', 30),
                      ('Title EN', 30), ('Line EN', 46), ('Labels EN', 36), ('CTA EN', 28), ('Телефон', 36), ('Ключи', 40)],
      rows, he_cols=('Кикер HE', 'Заголовок HE', 'Фраза HE', 'Метки HE', 'Кнопка HE'))
rows = []
for s in stories:
    ins = s['inside']
    act, btn = resolve(s['slug'], ins['actives_key']), resolve(s['slug'], ins['button_key'])
    for i, c in enumerate(ins['components']):
        rows.append([s['name'], c['what'], c['qty'], c['volume_dose'], c['source'],
                     act[0] if i == 0 else '', btn[0] if i == 0 else '', 'да' if ins['pro_only'] and i == 0 else ''])
sheet(wb, "What's inside", [('Страница', 20), ('Компонент', 34), ('Кол-во', 10), ('Объём / доза', 26), ('Источник', 30),
                            ('Активы HE', 50), ('Кнопка HE', 28), ('Только для специалистов', 12)], rows, he_cols=('Активы HE', 'Кнопка HE'))
sheet(wb, '3D assets', [('Страница', 20), ('Объект', 34), ('Как строим', 30), ('Текстура / источник', 44), ('Статус', 16)],
      [[s['name'], a['object'], a['build'], a['texture_source'], a['status']] for s in stories for a in s['assets']])
sheet(wb, 'New strings', [('Страница', 20), ('Ключ', 20), ('EN', 50), ('HE', 50), ('Где', 40)],
      [[s['name'], n['key'], n['en'], resolve(s['slug'], n['key'])[0], n['where']] for s in stories for n in s.get('new_strings', [])], he_cols=('HE',))
sheet(wb, 'Questions', [('Страница', 20), ('Вопрос заказчику', 100)], [[s['name'], q] for s in stories for q in s.get('questions_ru', [])])
out = os.path.join(SITE, 'MITODERM-3D-story.xlsx')
wb.save(out)
misses = sum(str(c.value).startswith(MISSING) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value)
print(out, {ws.title: ws.max_row - 1 for ws in wb.worksheets}, 'unresolved keys:', misses)
