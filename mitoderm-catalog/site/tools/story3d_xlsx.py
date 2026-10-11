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

# The 'who performs the treatment' block (owner 11/10): screen 8 on every page, right after the price screen.
# Texts come from the owner's Make site (sources/make-dictionary-spec.json) and from mitoderm.com (sources/mitoderm-com).
MAKE = load('sources/make-dictionary-spec.json')
FORM = load('sources/mitoderm-com/form-he.json')
FORM_EN = {  # English site form, from the owner's screenshots of mitoderm.com (11/10)
    'form.titleP1': 'Get Personalized', 'form.titleP2': 'Solutions', 'form.titleP3': 'for Your Practice',
    'form.subtitle': 'Our Specialist Will Reach Out Within 30 Minutes', 'form.placeholderInputName': 'Name',
    'form.placeholderEmailName': 'E-mail', 'form.placeholderPhoneName': 'Phone Number', 'form.placeholderProfession': 'Profession',
    'form.checkboxLabel': 'I agree with rules of Mitoderm *', 'form.sharing': 'Your information will never be shared with third parties *',
    'buttons.requestCallback': 'Request A Callback', 'form.sent.mobTitle': 'Congratulations!', 'form.sent.text': 'Your form has been submitted',
    'form.sent.textColored': 'successfully', 'buttons.contactForPrice': 'Contact for price', 'specialists.title': 'Certified cosmetologists and clinics',
    'buttons.learnMore': 'More info', 'form.eventTitle': 'Reserve your spot for the Event', 'form.placeholderInputID': 'ID Card Number',
    'form.numberTickets': 'Tickets', 'form.total': 'TOTAL', 'form.promo': 'Promo Code', 'form.apply': 'Apply', 'buttons.reserveSeat': 'Reserve a Seat'}
TAGS = {'face': ('פנים', 'Face', 'заказчик'), 'scalp': ('קרקפת', 'Scalp', 'заказчик'),
        'trich': (MAKE['prof.trichologist']['he'], MAKE['prof.trichologist']['en'], 'Make')}
SPEC_LINE = {'v-tech-system': 'tech.face.1.body', 'exo-nad': 'tech.face.1.body', 'exocell-mask': 'tech.face.1.body',
             'exosignal-hair': 'tech.hair.1.body', 'mitopen': 'tech.devices.3.body', 'mitoscan': 'tech.devices.3.body',
             'micro-boost-10': 'tech.biospicules.1.body'}
SPEC_TAGS = {'exosignal-hair': ['scalp', 'trich'], 'exosignal-spray': ['scalp', 'trich'], 'mitopen': ['face', 'scalp'],
             'home': ['face', 'scalp', 'trich'], 'catalog': ['face', 'scalp', 'trich']}
# owner's photos in the Figma collage (site/photo-catalog.md), by page
PHOTOS = {'exocell-mask': '11–24 (саше, двойная маска, нанесение)', 'v-tech-system': '40, 42, 44–50, 53, 54, 60',
          'exo-nad': '26–32, 35, 39, 51, 63, 64', 'exosignal-hair': '36, 47, 55, 58', 'exosignal-spray': '2, 3, 21, 33, 34, 41, 43, 59, 65',
          'exotech-gel': '37, 38, 52', 'mitopen': '56, 57', 'derma-recovery-cream': '1, 5, 73', 'micro-boost-10': '6, 67–69, 72, 74, 77',
          'cell-renew-1-5': '10, 70, 75, 67–69', 'cellular-age-defense-2-5': '7, 9, 67–69', 'mitoscan': '— (нужно фото прибора)',
          'home': '66, 71, 76', 'catalog': 'пакшоты всех средств'}


def form_value(path):
    obj = FORM
    for part in path.split('.'):
        obj = obj[part]
    return obj


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
        if key.startswith('make.'):
            e = MAKE[key[5:]]
            return e['he'], e['en']
        if key.startswith('site.'):
            path = key[5:]
            return form_value(path), FORM_EN.get(path, '')
        if key.startswith('tag.'):
            t = TAGS[key[4:]]
            return t[0], t[1]
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
                       ('Экран с оттенком серии', 12), ('Герой-объект', 30), ('Сюжет одной строкой', 60), ('Метки специалистов', 18),
                       ('Фото заказчика (№ в коллаже)', 24), ('Новых строк', 10), ('Вопросов', 10)],
      [[s['name'], s['slug'], s['line'], s['use'], s['colour_env'], s['series_tint_screen'], s['hero_object'], s['story_one_line'],
        ' · '.join(TAGS[t][0] for t in SPEC_TAGS.get(s['slug'], ['face'])), PHOTOS.get(s['slug'], ''),
        len(s.get('new_strings', [])), len(s.get('questions_ru', []))] for s in stories])
rows = []
for s in stories:
    for sc in s['screens']:
        k, t, l, c = (resolve(s['slug'], sc[x]) for x in ('kicker_key', 'title_key', 'line_key', 'cta_key'))
        labs = [resolve(s['slug'], x) for x in sc['label_keys']]
        rows.append([s['name'], sc['n'], sc['block'], sc['screen_name_ru'], sc['action_3d_ru'], sc['transition_ru'],
                     k[0], t[0], l[0], ' · '.join(x[0] for x in labs), c[0], t[1], l[1], ' · '.join(x[1] for x in labs), c[1], sc['mobile_ru'],
                     ' | '.join([sc['kicker_key'], sc['title_key'], sc['line_key'], ','.join(sc['label_keys']), sc['cta_key']])])
for s in stories:
    tags = SPEC_TAGS.get(s['slug'], ['face'])
    sc = {'n': len(s['screens']) + 1, 'block': '7 Specialists', 'screen_name_ru': 'Кто делает процедуру (после экрана с ценой)',
          'action_3d_ru': 'Объекты уходят, дым линейки успокаивается под тёмной вуалью. Три карточки специалистов: фото сверху плавно '
                          'переходит в текст (ничего не накладывается), имя, город, телефон, метка и «מוסמך», ссылка «קביעת ייעוץ». '
                          'Фильтр «מקצוע» открыт на метке этой страницы; ниже кнопка полного списка и строка для косметологов.',
          'transition_ru': 'Смена экрана без движения объектов; карточки появляются по очереди (0,08 с), как в Make.',
          'kicker_key': 'make.spec.kicker', 'title_key': 'make.spec.title', 'line_key': 'make.' + SPEC_LINE.get(s['slug'], 'spec.intro'),
          'label_keys': ['make.spec.filter.all'] + ['tag.' + t for t in tags] + ['make.spec.certified', 'make.spec.book', 'make.spec.join.title', 'make.spec.join.cta'],
          'cta_key': 'site.specialists.title',
          'mobile_ru': 'Карточки столбиком, фото 228 px с переходом в текст, фильтр-чипы переносятся; липкая панель с ценой внизу.'}
    k, t, l, c = (resolve(s['slug'], sc[x]) for x in ('kicker_key', 'title_key', 'line_key', 'cta_key'))
    labs = [resolve(s['slug'], x) for x in sc['label_keys']]
    rows.append([s['name'], sc['n'], sc['block'], sc['screen_name_ru'], sc['action_3d_ru'], sc['transition_ru'],
                 k[0], t[0], l[0], ' · '.join(x[0] for x in labs), c[0], t[1], l[1], ' · '.join(x[1] for x in labs), c[1], sc['mobile_ru'],
                 ' | '.join([sc['kicker_key'], sc['title_key'], sc['line_key'], ','.join(sc['label_keys']), sc['cta_key']])])
order = {s['name']: i for i, s in enumerate(stories)}
rows.sort(key=lambda r: (order[r[0]], r[1]))
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
FORM_ROWS = [
    ('Заявка на средство', 'Заголовок, часть 1', 'site.form.titleP1'), ('Заявка на средство', 'Заголовок, часть 2 (золото)', 'site.form.titleP2'),
    ('Заявка на средство', 'Заголовок, часть 3', 'site.form.titleP3'), ('Заявка на средство', 'Подзаголовок', 'site.form.subtitle'),
    ('Заявка на средство', 'Поле', 'site.form.placeholderInputName'), ('Заявка на средство', 'Поле', 'site.form.placeholderProfession'),
    ('Заявка на средство', 'Поле', 'site.form.placeholderEmailName'), ('Заявка на средство', 'Поле', 'site.form.placeholderPhoneName'),
    ('Заявка на средство', 'Согласие', 'site.form.checkboxLabel'), ('Заявка на средство', 'Кнопка', 'site.buttons.requestCallback'),
    ('Заявка на средство', 'Примечание', 'site.form.sharing'), ('Заявка на средство', 'Загрузка', ''),
    ('Заявка на средство', 'Успех (телефон)', 'site.form.sent.mobTitle'), ('Заявка на средство', 'Успех', 'site.form.sent.text'),
    ('Заявка на средство', 'Успех (золото)', 'site.form.sent.textColored'), ('Заявка на средство', 'Кнопка после успеха', 'site.buttons.learnMore'),
    ('Мероприятие (в конце работ)', 'Заголовок', 'site.form.eventTitle'), ('Мероприятие (в конце работ)', 'Поле', 'site.form.placeholderInputName'),
    ('Мероприятие (в конце работ)', 'Поле', 'site.form.placeholderInputID'), ('Мероприятие (в конце работ)', 'Билеты −/+', 'site.form.numberTickets'),
    ('Мероприятие (в конце работ)', 'Поле', 'site.form.placeholderEmailName'), ('Мероприятие (в конце работ)', 'Поле', 'site.form.placeholderPhoneName'),
    ('Мероприятие (в конце работ)', 'Итого ₪', 'site.form.total'), ('Мероприятие (в конце работ)', 'Промокод', 'site.form.promo'),
    ('Мероприятие (в конце работ)', 'Применить', 'site.form.apply'), ('Мероприятие (в конце работ)', 'Промокод принят', 'site.form.success'),
    ('Мероприятие (в конце работ)', 'Промокод неверный', 'site.form.wrongPromo'), ('Мероприятие (в конце работ)', 'Согласие', 'site.form.checkboxLabel'),
    ('Мероприятие (в конце работ)', 'Кнопка', 'site.buttons.reserveSeat'), ('Мероприятие (в конце работ)', 'Примечание', 'site.form.sharing'),
]
frows = []
for kind, what, key in FORM_ROWS:
    he, en = resolve('', key) if key else ('', '')
    note = 'Индикатор загрузки, поля затемнены (как на сайте)' if what == 'Загрузка' else ''
    frows.append([kind, what, he, en, key or '—', note])
sheet(wb, 'Form', [('Форма', 22), ('Элемент', 24), ('HE', 50), ('EN', 40), ('Ключ', 34), ('Примечание', 40)], frows, he_cols=('HE',))
sheet(wb, 'Questions', [('Страница', 20), ('Вопрос заказчику', 100)], [[s['name'], q] for s in stories for q in s.get('questions_ru', [])])
out = os.path.join(SITE, 'MITODERM-3D-story.xlsx')
wb.save(out)
misses = sum(str(c.value).startswith(MISSING) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value)
print(out, {ws.title: ws.max_row - 1 for ws in wb.worksheets}, 'unresolved keys:', misses)
