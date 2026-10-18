"""The texts of a product page on the V-TECH template (build-vtech.py --product <slug>), in the schema of
vtech-he-figma.json (nav, cta_price, s1…s9, bar, plus use), from reviewed sources only, with no new wording:
  storyboard.he.json     the product's 3D story, blocks b0–b6, written for these screens (key.he);
  product-pages.he.json  the catalogue page: eyebrow, kickers, formula, taglines of the related products;
  exocell-he-ui.json     the line, «טיפוח ביתי», the WhatsApp text;
  vtech-he-figma.json    the strings every product page shares with V-TECH: menu, S3 legend and formula label, the kit
                         card's title, the specialists block, the related headings.
A text the sources lack is left out (its block is not drawn), never written here.

screen          schema key                     source
header, S1, S7  cta_price · s1.more            b0.cta  «איפה לקנות · פתחו את הצנצנת» (the two buttons)
S1 meet         s1.line_mark, line_name        ui.line_mark, ui.line_name (the line's mark)
                s1.use_pro                     ui.use_home when the catalogue tags it HOME CARE (the badge, outlined)
                s1.eyebrow                     product-pages eyebrow
                s1.h1 · tag · lead · chips     name · b0.title · b0.line · b0.label1–4
S2 why          s2.h2 · p · chips              b1.title · b1.line · b1.label1–4;  s2.kicker  product-pages s05[0]
S3 inside       s3.h2 · p · chips              b2.title · b2.line · b2.label1–4;  s3.kicker  product-pages s03[0]
S4 feel         s4.h2 · p · pins               b3.title · b3.line · b3.label1–4
S5 protocol     s5.h2 · p                      b4.title · b4.line
                s5.steps                       b4.label1–3, «1 · » dropped (the template numbers them), no paragraph
                s5.chip                        b4.label4
S6 kit (card)   s7.card_lines                  b5.line split at its quantity («1×» + the rest)
                s7.card_facts                  b5.title (one line)
                s7.card_chips                  b5.label3–4
S7 offer        s7.h2 · p                      b6.title · b6.line;  s7.training  b6.cta's second button
S9 related      s9.line, s9.more               RELATED below: name, tagline and tag from product-pages
bar             bar                            name · ui.use_home / ui.use_pro"""
import json, os, re

H = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(H, '..'))
load = lambda *p: json.load(open(os.path.join(*p), encoding='utf-8'))
# the related cards: the rest of the product's line, then what its protocol names (b4.line)
RELATED = {'exotech-gel': (['v-tech-system', 'exocell-mask'], ['exo-nad', 'micro-boost-10'])}
IMG = {'v-tech-system': 'vtech-system.webp', 'derma-recovery-cream': 'derma-recovery.webp'}   # protocols/assets/img names


def content(slug):
    vt, ui = load(H, 'vtech-he-figma.json'), load(H, 'exocell-he-ui.json')
    pages = {p['slug']: (p, h) for p, h in zip(load(SITE, 'product-pages.json'), load(SITE, 'product-pages.he.json'))}
    sb = {i['key']: i['he'] for p in load(SITE, 'storyboard.he.json')['pages'] if p['slug'] == slug for i in p['items']}
    assert sb, f'no storyboard for {slug}'
    en, c = pages[slug]; name = c['name']
    use = 'home' if en['tag'] == 'HOME CARE' else 'pro'
    two = lambda k: [t.strip() for t in sb[k].split(' · ')]
    labels = lambda b, ks=(1, 2, 3, 4): [sb[f'{b}.label{i}'] for i in ks]
    buy, more = two('b0.cta'); _, ask = two('b6.cta')
    qty = sb['b5.line'].split(' ', 1)[0]; assert re.fullmatch(r'\d+×', qty), sb['b5.line']
    card = lambda s: [pages[s][1]['name'], pages[s][1]['tagline'], 'home' if pages[s][0]['tag'] == 'HOME CARE' else 'pro', IMG.get(s, s + '.webp')]
    line, also = RELATED[slug]
    return {
        'use': use, 'nav': vt['nav'], 'cta_price': buy,
        's1': {'line_mark': ui['line_mark'], 'line_name': ui['line_name'], 'use_pro': ui['use_' + use], 'eyebrow': c['eyebrow'],
               'h1': name, 'tag': sb['b0.title'], 'lead': sb['b0.line'], 'chips': labels('b0'), 'more': more},
        's2': {'h2': sb['b1.title'], 'p': sb['b1.line'], 'kicker': c['s05'][0], 'chips': labels('b1')},
        's3': {'h2': sb['b2.title'], 'legend': vt['s3']['legend'], 'p': sb['b2.line'], 'kicker': c['s03'][0],
               'chips': labels('b2'), 'formula': vt['s3']['formula']},
        's4': {'h2': sb['b3.title'], 'p': sb['b3.line'], 'pins': labels('b3')},
        's5': {'h2': sb['b4.title'], 'p': sb['b4.line'], 'chip': sb['b4.label4'], 'note': '',
               'steps': [[re.sub(r'^\d+\s*·\s*', '', t), ''] for t in labels('b4', (1, 2, 3))]},
        's6': {'p': sb['b5.line']},
        's7': {'h2': sb['b6.title'], 'p': sb['b6.line'], 'training': ask, 'card_title': vt['s7']['card_title'],
               'card_lines': [[qty, sb['b5.line'][len(qty):].strip()]], 'card_facts': sb['b5.title'], 'card_chips': labels('b5', (3, 4))},
        's8': vt['s8'],
        's9': {**{k: vt['s9'][k] for k in ('line_h', 'more_h', 'go', 'pro', 'home')}, 'line': [card(s) for s in line], 'more': [card(s) for s in also]},
        'bar': [name, ui['use_' + use]],
    }
