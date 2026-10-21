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
S1 meet         s1.line_mark, line_name        the product's line (LINES, design-rules.md «палитра по линейкам»): its Latin
                                               name; the Hebrew one only where a source has it (V-TECH FACE: ui.line_name,
                                               DEVICES: home.sl-2 «מכשור»); the line's name also heads the related cards
                s1.use_pro                     ui.use_home when the catalogue tags it HOME CARE (the badge, outlined)
                s1.eyebrow                     product-pages eyebrow
                s1.h1 · tag · lead · chips     name · b0.title · b0.line · b0.label1–4
S2 why          s2.h2 · p · chips              b1.title · b1.line · b1.label1–4;  s2.kicker  product-pages s05[0]
S3 inside       s3.h2 · p · chips              b2.title · b2.line · b2.label1–4;  s3.kicker  product-pages s03[0]
                exo, pdrn                      the catalogue's eyebrow and formula name synthetic exosomes / PDRN: the
                                               exosome legend, cells, PDRN molecules and DNA helix only then
S4 feel         s4.h2 · p · pins               b3.title · b3.line · b3.label1–4
S5 protocol     s5.h2 · p                      b4.title · b4.line
                s5.steps                       b4.label1–3, «1 · » dropped (the template numbers them), no paragraph
                s5.chip                        b4.label4
S6 kit (card)   s7.card_lines                  b5.line split at its quantity («1×» + the rest), none without one
                s7.card_facts                  b5.title (one line)
                s7.card_chips                  b5.label3–4
S7 offer        s7.h2 · p                      b6.title · b6.line;  s7.training  b6.cta's second button
S8 specialists  s8.tag                         «קרקפת» (ui.spec_tag_scalp) for a scalp product (catalogue eyebrow, tagline)
S9 related      s9.line, s9.more               the rest of the line, then the products b4.line names (RELATED overrides);
                                               name, tagline and tag from product-pages; a product whose packshot (in
                                               protocols/assets or protocols/print) is too small for an HD card is left out
bar             bar                            name · ui.use_home / ui.use_pro"""
import json, os, re

H = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(H, '..'))
load = lambda *p: json.load(open(os.path.join(*p), encoding='utf-8'))
REPO = os.path.normpath(os.path.join(SITE, '..'))
# the lines (design-rules.md, owner 10/10), each in its agreed order (spicules 10% → 2.5% → 1.5%)
LINES = {'V-TECH FACE': ['v-tech-system', 'exocell-mask', 'exotech-gel'], 'HAIR': ['exosignal-hair', 'exosignal-spray'],
         'PEELING': ['exo-nad'], 'BIOSPICULE': ['micro-boost-10', 'cellular-age-defense-2-5', 'cell-renew-1-5', 'derma-recovery-cream'],
         'DEVICES': ['mitoscan', 'mitopen']}
MARK = {'BIOSPICULE': 'BIOSPICULE™', 'DEVICES': ''}   # the badge's Latin name (as the catalogue writes it; none for devices)
# the related cards, where they were chosen by hand (the gel: its line, then the protocols it joins)
RELATED = {'exotech-gel': (['v-tech-system', 'exocell-mask'], ['exo-nad', 'micro-boost-10'])}
IMG = {'v-tech-system': 'vtech-system.webp', 'derma-recovery-cream': 'derma-recovery.webp',   # protocols/assets/img names
       'cell-renew-1-5': 'cell-renew-15.webp', 'cellular-age-defense-2-5': 'cellular-age-25.webp'}   # protocols/print/img
PACKSHOTS = [os.path.join(REPO, 'protocols', d, 'img') for d in ('assets', 'print')]


def packshot(slug):   # the card's picture: its file name, or None when it is too small for an HD card: the picture is
    from PIL import Image   # drawn in a box of about 280×204 css px on a 390 px phone, at DPR 3 (as qa/verify-hd.cjs)
    f = IMG.get(slug, slug + '.webp')
    for d in PACKSHOTS:
        if os.path.exists(os.path.join(d, f)):
            w, h = Image.open(os.path.join(d, f)).size
            return f if min(840 / w, 612 / h) <= 1 / 0.94 else None
    return None


def content(slug):
    vt, ui = load(H, 'vtech-he-figma.json'), load(H, 'exocell-he-ui.json')
    home = {i['key']: i['he'] for p in load(SITE, 'storyboard.he.json')['pages'] if p['slug'] == 'home' for i in p['items']}
    pages = {p['slug']: (p, h) for p, h in zip(load(SITE, 'product-pages.json'), load(SITE, 'product-pages.he.json'))}
    sb = {i['key']: i['he'] for p in load(SITE, 'storyboard.he.json')['pages'] if p['slug'] == slug for i in p['items']}
    assert sb, f'no storyboard for {slug}'
    en, c = pages[slug]; name = c['name']
    use = 'home' if en['tag'] == 'HOME CARE' else 'pro'
    two = lambda k: [t.strip() for t in sb[k].split(' · ')]
    labels = lambda b, ks=(1, 2, 3, 4): [sb[f'{b}.label{i}'] for i in ks]
    buy, more = two('b0.cta')[:2]; ask = (two('b6.cta') + [''])[1]   # b6.cta: the price button, then the offer's second one
    qty = sb['b5.line'].split(' ', 1)[0]; qty = qty if re.fullmatch(r'\d+×', qty) else ''
    line_id = next(k for k, v in LINES.items() if slug in v)
    mark = MARK.get(line_id, line_id) if line_id != 'V-TECH FACE' else ui['line_mark']
    lname = {'V-TECH FACE': ui['line_name'], 'DEVICES': home['home.sl-2']}.get(line_id, '')
    about = c['eyebrow'] + ' ' + ' '.join(c['ingredients'])
    exo, pdrn = 'אקסוזומים סינתטיים' in about or 'אקסוזומליים סינתטיים' in about, 'PDRN' in about
    scalp = 'קרקפת' in c['eyebrow'] + c['tagline']
    products = [p['slug'] for p, _ in pages.values() if p['tag'] in ('PRO', 'HOME CARE', 'DEVICE')]
    if slug in RELATED: line, also = RELATED[slug]
    else:   # the rest of the line, then what the protocol names (b4.line), in the order it names them
        line = [s for s in LINES[line_id] if s != slug]
        at = lambda s: sb['b4.line'].find(pages[s][1]['name']) if pages[s][1]['name'] in sb['b4.line'] else (
            m.start() if s == 'v-tech-system' and (m := re.search(r'V-TECH(?! FACE)', sb['b4.line'])) else -1)
        also = sorted((s for s in products if s != slug and s not in line and at(s) >= 0), key=at)
    left = [s for s in line + also if not packshot(s)]
    if left: print('related: no packshot of HD size, left out:', ' '.join(left))
    card = lambda s: [pages[s][1]['name'], pages[s][1]['tagline'], 'home' if pages[s][0]['tag'] == 'HOME CARE' else 'pro', packshot(s)]
    line, also = [s for s in line if packshot(s)][:4], [s for s in also if packshot(s)][:4]
    return {
        'use': use, 'nav': vt['nav'], 'cta_price': buy, 'line': line_id, 'exo': exo, 'pdrn': pdrn,
        's1': {'line_mark': mark, 'line_name': lname, 'use_pro': ui['use_' + use], 'eyebrow': c['eyebrow'],
               'h1': name, 'tag': sb['b0.title'], 'lead': sb['b0.line'], 'chips': labels('b0'), 'more': more},
        's2': {'h2': sb['b1.title'], 'p': sb['b1.line'], 'kicker': c['s05'][0], 'chips': labels('b1')},
        's3': {'h2': sb['b2.title'], 'legend': vt['s3']['legend'] if exo else '', 'p': sb['b2.line'], 'kicker': c['s03'][0],
               'chips': labels('b2'), 'formula': vt['s3']['formula'] if line_id != 'DEVICES' else ''},   # a device: no «formula»
        's4': {'h2': sb['b3.title'], 'p': sb['b3.line'], 'pins': labels('b3')},
        's5': {'h2': sb['b4.title'], 'p': sb['b4.line'], 'chip': sb['b4.label4'], 'note': '',
               'steps': [[re.sub(r'^\d+\s*·\s*', '', t), ''] for t in labels('b4', (1, 2, 3))]},
        's6': {'p': sb['b5.line']},
        's7': {'h2': sb['b6.title'], 'p': sb['b6.line'], 'training': ask, 'card_title': vt['s7']['card_title'],
               'card_lines': [[qty, sb['b5.line'][len(qty):].strip()]] if qty else [], 'card_facts': sb['b5.title'], 'card_chips': labels('b5', (3, 4))},
        's8': {**vt['s8'], 'tag': ui['spec_tag_scalp'] if scalp else vt['s8']['tag']},
        's9': {**{k: vt['s9'][k] for k in ('more_h', 'go', 'pro', 'home')}, 'line_h': vt['s9']['line_h'].replace(ui['line_mark'], mark or 'ה' + lname),   # «עוד מקו המכשור»: a common noun takes the article
               'line': [card(s) for s in line], 'more': [card(s) for s in also]},
        'bar': [name, ui['use_' + use]],
    }
