# Builds the Hebrew V-TECH SYSTEM live page (vtech-live.html) from vtech-live-template.html: the scroll story on
# pre-rendered Blender frames and the blocks of the approved Figma design (page 142:3) with the owner's edits of 17/10.
# Text comes only from reviewed sources: vtech-he-figma.json (the approved Figma copy and the owner's edits),
# product-pages.he.json (the full formula), the mitoderm.com form and contacts, exocell-he-ui.json (UI strings shared
# with the EXOCELL MASK page). The build fails if any placeholder is left unfilled or any text is never placed.
# `python3 build-vtech.py` writes the page; `... --files <dir> --keys <dir of transparent key frames>` also writes its
# images (img/) into <dir>, the folder published with the page. Specialists: a monogram and the city only (public repo).
# `--product <slug>` (default v-tech-system) builds another product's page on the same template: its texts come from
# story_content.py (the product's reviewed 3D story and catalogue page, in this schema), the page is written into
# <dir> as <slug>-live.html. A home-care product's buttons go to WhatsApp («איפה לקנות»), not to the price form; the
# blocks it has no text for (protocol note, step paragraphs, kit callouts) are left out.
# Frames: <dir>/seq/<tier>/<A>_<B>_NNN.webp, one folder per tier (the full 16:10 frame's width in px: 1600, 1920,
# 2400 …); each frame holds only its run's crop box, from <dir>/seq/runs.json ({"runs": [{"a", "b", "n", "box":
# [x0, y0, x1, y1] in fractions of the frame]}]}, else 40 frames and the whole frame). Only complete tiers are offered.
# Exosome cells: site/design/vtech-3d/cells/cNN-{0,1,2}.webp (sharp, soft, bokeh; glassy), fNN-… (the owner's folded
# exosome, design/exosomes/make_folded.py) and plate.webp are copied into <dir>/img/cells/ and <dir>/img/plate.webp when
# they exist; otherwise whatever <dir>/img/cells/ holds is used.
# PDRN molecules mNN-{0,1,2}.webp join the same field; helix.webp (the DNA loop) goes to <dir>/img/ for S3.
# The frame engine is engine/story.js (an ES module, also what a React app mounts); the build inlines it into the page.
# `--scene` (another product): no frames; the page draws scenes/<slug>.js live with three.js (the engine's `scene`),
# every run in the same box SCENE_BOX, its textures from img/<slug>-3d/; without WebGL the first key frame stands still.
import glob, html, json, os, re, shutil, sys, urllib.parse
from PIL import Image

ARGS = sys.argv[1:]
opt = lambda name: ARGS[ARGS.index(name) + 1] if name in ARGS else None
FILES, KEYS, PRODUCT = opt('--files'), opt('--keys'), opt('--product') or 'v-tech-system'
SCENE = '--scene' in ARGS
H = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(H, '..'))
REPO = os.path.normpath(os.path.join(SITE, '..'))
load = lambda *p: json.load(open(os.path.join(*p), encoding='utf-8'))

if PRODUCT == 'v-tech-system':
    v = load(H, 'vtech-he-figma.json')
else:
    assert FILES, '--files <dir> is needed: the page is written there, next to its img/ and seq/'
    sys.path.insert(0, H); from story_content import content; v = content(PRODUCT)
cat = {s['slug']: h for s, h in zip(load(SITE, 'product-pages.json'), load(SITE, 'product-pages.he.json'))}[PRODUCT]
ui = load(H, 'exocell-he-ui.json')
form = load(SITE, 'sources/mitoderm-com/form-he.json'); ff = form['form']
site = load(SITE, 'sources/mitoderm-com/contacts.json')
home = {i['key']: i['he'] for p in load(SITE, 'storyboard.he.json')['pages'] if p['slug'] == 'home' for i in p['items']}
assert site['phone'] == ui['phone'] and site['email'] == ui['email'] and site['whatsapp_link'].endswith(ui['wa_number'])

esc = lambda s: html.escape(s, quote=True)
wa = lambda text: 'https://wa.me/' + ui['wa_number'] + '?text=' + urllib.parse.quote(text)


def keep(s):
    """As in build-exocell.py: escape a Hebrew line and keep each Latin name whole and in order ('V-TECH' never breaks,
    'BIOSPICULE™' keeps its ™ after the word, a one-letter prefix stays with its name)."""
    out, pos = [], 0
    for m in re.finditer(r'(?<![א-ת])([א-ת]-)?([A-Za-z][A-Za-z0-9™®%\-‑]*(?:[ /]+[A-Za-z0-9][A-Za-z0-9™®%\-‑]*)*)', s):
        run = f'<bdi>{esc(m.group(2))}</bdi>'
        out += [esc(s[pos:m.start()]), f'<span class="nw">{esc(m.group(1))}{run}</span>' if m.group(1) else run.replace('<bdi>', '<bdi class="nw">', 1)]
        pos = m.end()
    return ''.join(out) + esc(s[pos:])


def brand(s):  # Latin product and brand names in capitals, as everywhere in the edition (build-exocell.py)
    for a, b in (('Mitoderm', 'MITODERM'), ('V-Tech', 'V-TECH'), ('Exo-NAD', 'EXO-NAD'), ('Exocell', 'EXOCELL')):
        s = s.replace(a, b)
    return s


lis = lambda items, f=esc: ''.join(f'<li>{f(t)}</li>' for t in items)
txt = lambda s: keep(s) if re.search('[™®]', s) else esc(s)   # a mark sign stays after its word in an RTL line
nav = v['nav']
PIN = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s7-6.2 7-11.5a7 7 0 0 0-14 0C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>'
CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.7 2.7L16 9.8"/></svg>'
s1, s2, s3, s4, s5, s6, s7, s8, s9 = (v[f's{i}'] for i in range(1, 10))
tel = '+972' + re.sub(r'\D', '', ui['phone'])[1:]
NAME, HOME = s1['h1'], v.get('use') == 'home'
EXO, PDRN = v.get('exo', True), v.get('pdrn', True)   # synthetic exosomes, PDRN: the cells' field, the molecules, the DNA helix
LINE = v.get('line', 'V-TECH FACE')   # the line's smoke: V-TECH FACE and HAIR are black and gold (design-rules), the others
SMOKE = (f'{SITE}/design/vtech-3d/layers/vt-bg-wide.jpg' if LINE in ('V-TECH FACE', 'HAIR')   # recoloured by tools/line_smoke.py
         else f'{SITE}/design/lines/{LINE.lower()}-smoke.jpg')
assert os.path.exists(SMOKE), f'no smoke for the {LINE} line: run tools/line_smoke.py'
# the main button: the price form (WhatsApp without JS) for a professional product, WhatsApp for a home-care one
WA_MAIN = wa(ui['wa_text_product'].format(name=NAME)) if HOME else wa(ui['wa_text_price'].replace('EXOCELL MASK', NAME))
LEAD = '' if HOME else ' data-lead aria-haspopup="dialog"'

T = {
    'cta_price': v['cta_price'], 'use_pro': s1['use_pro'],
    'eyebrow': s1['eyebrow'], 'h1': s1['h1'], 'tag': s1['tag'], 's1_lead': s1['lead'], 's1_more': s1['more'],
    **{f'nav{i}': nav[i] for i in range(1, 6)},
    's2_h2': s2['h2'], 's2_p': s2['p'], 's2_kicker': s2['kicker'],
    's3_h2': s3['h2'], 's3_kicker': s3['kicker'],
    's4_h2': s4['h2'], 's4_p': s4['p'], 's5_h2': s5['h2'], 's5_p': s5['p'],
    's7_p': s7['p'], 's7_card_title': s7['card_title'],
    'kit_alt': s1['h1'] + ': ' + re.split(r'\.\s+(?=[^\sa-z])', s6['p'], 1)[0],   # the S6 line's first sentence (not «1.5%»): what is in the box
    'phone_href': 'tel:' + tel, 'phone_label': ui['phone_label'], 'phone': ui['phone'],
    'email_href': 'mailto:' + ui['email'] + '?subject=' + urllib.parse.quote(NAME), 'email_label': ui['email_label'], 'email': ui['email'],
    's8_kicker': s8['kicker'], 's8_filter': s8['filter'], 'spec_empty': ui['spec.empty'], 's8_list': s8['list'],
    's8_join': s8['join'], 's8_join_cta': s8['join_cta'],
    'footer': home['home.footer-2'], 'foot_access': site['footer_he']['accessibility'], 'foot_privacy': site['footer_he']['privacy'],
    'nav_label': ui['nav_label'], 'bar_name': v['bar'][0], 'bar_note': v['bar'][1], 'close_label': ui['ui.close'],
    'form_p1': ff['titleP1'], 'form_p2': ff['titleP2'].strip(), 'form_p3': ff['titleP3'], 'form_sub': ff['subtitle'],
    'f_name': ff['placeholderInputName'], 'f_prof': ff['placeholderProfession'], 'f_email': ff['placeholderEmailName'],
    'f_phone': ff['placeholderPhoneName'], 'f_consent': ff['checkboxLabel'], 'f_submit': form['buttons']['requestCallback'],
    'f_privacy': ff['sharing'], 'f_sent': ff['sent']['text'], 'f_sent_gold': ff['sent']['textColored'],
    'f_sent_mob': ff['sent']['mobTitle'], 'f_more': form['buttons']['learnMore'],
}


def card(name, line, use, img, i):
    return (f'<a class="card rv" style="--d:{i * .08:.2f}s" href="{esc(wa(ui["wa_text_product"].format(name=name)))}" target="_blank" rel="noopener">'
            f'<div class="pic"><img src="img/{img}" alt="{esc(name)}" loading="lazy"></div>'
            f'<div class="body"><span class="badge{" pro" if use == "pro" else " home"}">{esc(s9[use])}</span>'
            f'<h3><bdi>{esc(name)}</bdi></h3><p>{keep(line)}</p><span class="go">{esc(s9["go"])}</span></div></a>')


book = f'<a class="book" href="{esc(WA_MAIN)}"{LEAD}>{esc(s8["book"])} <span aria-hidden="true">↗</span></a>'
calls = len(s7['card_lines']) == 2   # the two kinds in the box named over and under its picture (V-TECH: sachets, ampoules)
call = lambda pos, k: (f'<p class="kc-call {pos}" aria-hidden="true"><b><bdi dir="ltr">{esc(s7["card_lines"][k][0])}</bdi></b>'
                       f'{esc(s7["card_lines"][k][1].split(" — ")[0])}</p>') if calls else ''
RAW = {
    's1_chips': lis(s1['chips'], keep), 's2_chips': lis(s2['chips']), 's3_p': keep(s3['p']), 's3_chips': lis(s3['chips'], keep),
    's3_formula': (f'<details class="rv" style="--d:.3s"><summary>{esc(s3["formula"])}</summary><ul>{lis(cat["ingredients"], keep)}</ul></details>'
                   if s3['formula'] else ''),   # a device has features, not a formula
    's4_pins': lis(s4['pins']), 's5_chip': keep(s5['chip']),
    's5_steps': ''.join(f'<li class="step rv" style="--d:{i * .08:.2f}s"><span class="n">0{i + 1}</span><h3>{keep(t)}</h3>{f"<p>{keep(p)}</p>" if p else ""}</li>'
                        for i, (t, p) in enumerate(s5['steps'])),
    's5_note': f'<p class="note rv" style="--d:.24s">{esc(s5["note"])}</p>' if s5['note'] else '',
    'lead': LEAD, 'use_cls': '' if HOME else ' pro',
    # the offer's second button does what its label says: a price quote opens the price form (a home-care page too),
    # «WhatsApp» opens WhatsApp, a home-care page otherwise sends to the specialists, a professional one to the form
    'offer_more': '' if not s7['training'] else (
        f'<a class="btn ghost" href="{esc(wa(ui["wa_text_price"].replace("EXOCELL MASK", NAME)))}" target="_blank" rel="noopener" data-lead aria-haspopup="dialog">{esc(s7["training"])}</a>'
        if HOME and 'מחיר' in s7['training'] else
        f'<a class="btn ghost" href="{esc(wa(ui["wa_text_product"].format(name=NAME)))}" target="_blank" rel="noopener">{esc(s7["training"])}</a>'
        if 'WhatsApp' in s7['training'] else
        f'<a class="btn ghost" href="#specialists">{esc(s7["training"])}</a>' if HOME else
        f'<a class="btn ghost" href="__WA_PRICE__" target="_blank" rel="noopener"{LEAD}>{esc(s7["training"])}</a>'),
    's7_h2': keep(s7['h2']),
    'kit_call_top': call('top', 1), 'kit_call_bot': call('bot', 0),   # «מסכת ג׳ל» over the sachets, «סרום» under the ampoules
    's7_card_lines': ''.join(f'<p class="kc-qty"><b><bdi dir="ltr">{esc(q)}</bdi></b><span>{keep(t)}</span></p>' for q, t in s7['card_lines']),
    # one thin line from the approved S6 facts: «4–6 טיפולים בסדרה · 14 יום בין טיפול לטיפול» (or the product's own line)
    's7_card_facts': f'<p class="kc-facts"><span>{keep(s7["card_facts"])}</span></p>' if 'card_facts' in s7 else '<p class="kc-facts">' + '<i aria-hidden="true">·</i>'.join(
        f'<span><b><bdi dir="ltr">{esc(n)}</bdi></b> {esc(l)}</span>' for n, l in s6['facts'][2:4]) + '</p>',
    's7_card_chips': lis(s7['card_chips'], keep), 's8_h2': keep(brand(s8['h2'])), 's8_p': keep(brand(s8['p'])),
    's8_chips': ''.join(f'<button type="button" class="fchip" data-tag="{esc(tag)}" aria-pressed="{str(tag == s8["tag"]).lower()}">{esc(label)}</button>'
                        for label, tag in zip(s8['chips'], ['*'] + s8['chips'][1:])),
    's8_cards': ''.join(f'<article class="spec rv" style="--d:{i * .08:.2f}s" data-tags="{esc(s8["tag"])}"><div class="av" aria-hidden="true">{esc(city[0])}</div>'
                        f'<div class="sb"><h3>{PIN}<span>{esc(city)}</span></h3><div class="tags"><span>{esc(s8["tag"])}</span><span>{CHECK}{esc(s8["certified"])}</span></div>'
                        f'{book}</div></article>' for i, city in enumerate(s8['cities'])),
    # the line's badge (its Latin name, its Hebrew name where there is one) on S1 and the offer card
    'line_badges': (f'<span class="mark-line"><bdi>{esc(s1["line_mark"])}</bdi></span>' if s1['line_mark'] else '')
                   + (f'<span class="badge">{esc(s1["line_name"])}</span>' if s1['line_name'] else ''),
    'kit_line': f'<span class="badge"><bdi>{esc(s1["line_mark"] or s1["line_name"])}</bdi></span>' if s1['line_mark'] or s1['line_name'] else '',
    # the exosome legend only on a product with synthetic exosomes; a related row only when it has cards
    's3_legend': f'<p class="legend rv" style="--d:.15s"><span class="dot" aria-hidden="true"></span><span>{esc(s3["legend"])}</span></p>' if s3['legend'] else '',
    's9': ('<section class="related" data-st="7"><div class="wrap">\n    ' + '\n    '.join(
        f'<h2 class="rv">{txt(s9[k + "_h"])}</h2>\n    <div class="cards">' + ''.join(card(*c, i) for i, c in enumerate(s9[k])) + '</div>' if s9[k] else ''
        for k in ('line', 'more')) + '\n  </div></section>') if s9['line'] or s9['more'] else '',
    'dock': ''.join(f'<a href="#{h}" data-i="{i}">{esc(n)}</a>' for i, (h, n) in enumerate(zip(
        ('meet', 'why', 'inside', 'feel', 'protocol', 'offer', 'specialists'), nav))),
    'form_fail': keep(ui['form.error']),
    'form_errors': json.dumps(dict(ff['errors'], consent_required=ui['form.consent_required']), ensure_ascii=False).replace('<', '\\u003c'),
}
PAIRS = [('v1-meet', 'v2-why'), ('v2-why', 'v3-inside'), ('v3-inside', 'v4-feel'), ('v4-feel', 'v5-protocol'), ('v5-protocol', 'v6-kit')]
RUNS = [{'a': a, 'b': b, 'n': 40, 'box': [0, 0, 1, 1]} for a, b in PAIRS]
SCENE_BOX = [0.07, 0.19, 0.52, 0.81]   # a live scene: the left of the 16:10 frame that the objects move in (all screens)
SCENE_JS = os.path.join(H, 'scenes', f'{PRODUCT}.js')
if SCENE:
    assert PRODUCT != 'v-tech-system' and os.path.exists(SCENE_JS) and FILES and KEYS, '--scene needs --product with scenes/<slug>.js, --files, --keys'
    RUNS = [{'a': a, 'b': b, 'n': 60, 'box': SCENE_BOX} for a, b in PAIRS]
elif FILES and os.path.exists(f'{FILES}/seq/runs.json'):   # crop boxes and frame counts from the render
    RUNS = json.load(open(f'{FILES}/seq/runs.json'))['runs']
    assert [(r['a'], r['b']) for r in RUNS] == PAIRS, 'runs.json must list the five runs in story order'
for r in RUNS:
    x0, y0, x1, y1 = r['box']; assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1 and r['n'] >= 2, r
frame = lambda r, i, t: f'seq/{t}/{r["a"]}_{r["b"]}_{i:03d}.webp'
TIERS = []
if FILES and not SCENE:   # a tier is offered only when every frame of every run is there
    for d in sorted(glob.glob(f'{FILES}/seq/[0-9]*/'), key=lambda d: int(os.path.basename(d.rstrip('/')))):
        t = int(os.path.basename(d.rstrip('/'))); lack = sum(not os.path.exists(f'{FILES}/{frame(r, i, t)}') for r in RUNS for i in range(r['n']))
        print(f'tier {t}: ' + ('complete' if not lack else f'{lack} frames missing, not offered'))
        if not lack: TIERS.append(t)
elif not SCENE:
    print('no --files: the page is built without frames (no 3D)')
STILL = ''
if TIERS:   # no JS: the first key frame, in its box of the cover-fitted frame
    t = min([x for x in TIERS if x >= 1920] or [max(TIERS)]); x0, y0, x1, y1 = RUNS[0]['box']
    STILL = (f'<div class="still" aria-hidden="true"><div class="still-f"><img src="{frame(RUNS[0], 0, t)}" alt="" loading="lazy" '
             f'style="left:{x0 * 100:.3f}%;top:{y0 * 100:.3f}%;width:{(x1 - x0) * 100:.3f}%;height:{(y1 - y0) * 100:.3f}%"></div></div>')


def save(im, path, width, **kw):  # downscale to width (never up) and write WebP/PNG
    if im.width > width: im = im.resize((width, round(width * im.height / im.width)), Image.LANCZOS)
    im.save(path, **kw); return im.size


KIT = (f'{KEYS}/v6-kit.png' if KEYS and os.path.exists(f'{KEYS}/v6-kit.png') else   # the kit of the story's last frame
       f'{SITE}/design/vtech-3d/hd/kit-hd.webp' if PRODUCT == 'v-tech-system' else f'{REPO}/protocols/print/img/{PRODUCT}.webp')
k = Image.open(KIT).convert('RGBA'); k = k.crop(k.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox())
KIT_W = 1200   # the offer card's picture: up to ~320 css px tall on a phone at DPR 3, ~500 on a desktop at 2
kit_size = (min(KIT_W, k.width), round(min(KIT_W, k.width) * k.height / k.width))
if FILES:   # the page's images: smoke, logos, kit card, related products, phone stills cut from the key frames
    os.makedirs(f'{FILES}/img', exist_ok=True)
    save(Image.open(SMOKE).convert('RGB'), f'{FILES}/img/bg.webp', 3456, quality=80, method=6)   # the whole source
    save(Image.open(f'{SITE}/img/mitoderm-logo-white-mark.png').convert('RGBA'), f'{FILES}/img/logo-mark.png', 600, optimize=True)
    save(Image.open(f'{SITE}/img/mitoderm-logo-white.png').convert('RGBA'), f'{FILES}/img/logo.png', 420, optimize=True)
    save(k, f'{FILES}/img/kit.webp', KIT_W, quality=86, method=6)
    for c in s9['line'] + s9['more']:   # a card's packshot at its full size (≤ 1000 px): 204 css px tall × 3 on a phone
        src = next(f'{REPO}/protocols/{d}/img/{c[3]}' for d in ('assets', 'print') if os.path.exists(f'{REPO}/protocols/{d}/img/{c[3]}'))
        save(Image.open(src).convert('RGBA'), f'{FILES}/img/{c[3]}', 1000, quality=84, method=6)
    assert KEYS, '--keys <dir with the transparent key frames (render_series.py output)> is needed for the phone stills'
    for n, shot in enumerate(('v1-meet', 'v2-why', 'v3-inside', 'v4-feel', 'v5-protocol'), 1):   # the key frames of the story of 17/10
        im = Image.open(f'{KEYS}/{shot}.png').convert('RGBA'); x0, y0, x1, y1 = im.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox()
        p = round(0.03 * max(x1 - x0, y1 - y0))   # a little air around the objects
        save(im.crop((max(0, x0 - p), max(0, y0 - p), min(im.width, x1 + p), min(im.height, y1 + p))), f'{FILES}/img/m{n}.webp', 900, quality=84, method=6)
    src = f'{SITE}/design/vtech-3d/cells'   # exosome sprites and the deep plate (render), when they exist
    kinds = ('cf' if EXO else '') + ('m' if EXO and PDRN else '')   # glassy (c) and folded (f) cells, PDRN molecules (m)
    real = sorted(f for k in kinds for f in glob.glob(f'{src}/{k}[0-9][0-9]-[012].webp'))
    if real:
        for f in glob.glob(f'{FILES}/img/cells/[cfm][0-9][0-9]-[012].webp'): os.remove(f)
        os.makedirs(f'{FILES}/img/cells', exist_ok=True)
        for f in real:   # sharp ≤ 1024 px, soft ≤ 640, bokeh ≤ 512: what a cell is ever drawn at
            im = Image.open(f); cap = (1024, 640, 512)[int(f[-6])]
            if im.width > cap: save(im.convert('RGBA'), f'{FILES}/img/cells/{os.path.basename(f)}', cap, quality=88, alpha_quality=92, method=6)
            else: shutil.copyfile(f, f'{FILES}/img/cells/{os.path.basename(f)}')
    if EXO and os.path.exists(f'{src}/plate.webp'):
        save(Image.open(f'{src}/plate.webp').convert('RGB'), f'{FILES}/img/plate.webp', 2592, quality=82, method=6)
    if EXO and PDRN and os.path.exists(f'{src}/helix.webp'):   # the DNA helix loop (animated, over black: the page screens it)
        shutil.copyfile(f'{src}/helix.webp', f'{FILES}/img/helix.webp')
    if SCENE:   # the scene's textures; the first key frame as the still (no JS, no WebGL)
        shutil.copytree(os.path.join(H, 'img', f'{PRODUCT}-3d'), f'{FILES}/img/{PRODUCT}-3d', dirs_exist_ok=True)
        save(Image.open(f'{KEYS}/v1-meet.png').convert('RGBA'), f'{FILES}/img/still.webp', 3840, quality=86, alpha_quality=92, method=6)
        STILL = ('<div class="still" aria-hidden="true"><div class="still-f"><img src="img/still.webp" alt="" loading="lazy" '
                 'style="left:0;top:0;width:100%;height:100%"></div></div>')
RAW['kit_size'] = f'width="{kit_size[0]}" height="{kit_size[1]}"'
cdir, plate = (f'{FILES}/img/cells', f'{FILES}/img/plate.webp') if FILES else (f'{SITE}/design/vtech-3d/cells',) * 2
def sprites(k): return sorted(c for c in {os.path.basename(f)[:3] for f in glob.glob(f'{cdir}/{k}[0-9][0-9]-0.webp')}
                              if all(os.path.exists(f'{cdir}/{c}-{v}.webp') for v in '012'))
CELLS, MOLS = (sprites('c') if EXO else []), (sprites('m') if PDRN else [])
FOLDED = sprites('f') if CELLS else []   # owner 22/10: his folded exosomes among the glassy ones, at these places of the
if FOLDED:                               # list the engine's field draws from (a near one, far ones, one on the phone)
    glass, folded, at = iter(CELLS), iter(FOLDED), (1, 3, 5, 8)[:len(FOLDED)]
    CELLS = [next(folded) if i in at else next(glass) for i in range(len(CELLS))]
    if FILES:   # the glassy ones they replaced are not drawn: not shipped either
        for f in glob.glob(f'{cdir}/[cf][0-9][0-9]-[012].webp'):
            if os.path.basename(f)[:3] not in CELLS: os.remove(f)
if CELLS and not os.path.exists(plate if FILES else f'{plate}/plate.webp'):
    print('cells without plate.webp: no cells'); CELLS = []
if not CELLS: MOLS = []   # the molecules float in the cells' field
HELIX = PDRN and os.path.exists(f'{FILES}/img/helix.webp' if FILES else f'{cdir}/helix.webp') and bool(CELLS)
print('cells:', ' '.join(CELLS) or 'none', '| molecules:', ' '.join(MOLS) or 'none', '| helix:', HELIX)

page = open(os.path.join(H, 'vtech-live-template.html'), encoding='utf-8').read()
used = set(re.findall(r'\{\{\{?(\w+)\}?\}\}', page))
missing, unused = used - set(T) - set(RAW), (set(T) | set(RAW)) - used
assert not missing, f'no text for {sorted(missing)}'
assert not unused, f'texts never placed: {sorted(unused)}'
page = re.sub(r'\{\{\{(\w+)\}\}\}', lambda m: RAW[m.group(1)], page)
KEEP = {'eyebrow', 'tag', 's1_lead', 's2_h2', 's2_p', 's2_kicker', 's3_h2', 's3_kicker', 's4_h2', 's4_p', 's5_h2', 's5_p', 's7_p'}   # text, not attributes
page = re.sub(r'\{\{(\w+)\}\}', lambda m: txt(T[m.group(1)]) if m.group(1) in KEEP else esc(T[m.group(1)]), page)
# the live scene: three.js from jsDelivr (as the MASK page), imported so that a failed load (or no WebGL) leaves the
# page whole, without 3D: no-gl, the still; then the scene module inlined
SRC = open(SCENE_JS, encoding='utf-8').read() if SCENE else ''
assert not SCENE or (SRC.count('export function createScene(') == 1 and '</script' not in SRC)
SCENE_INIT = ("(() => { try { if (!THREE) throw 0; return createScene(THREE, { canvas: $('seq'), base: document.baseURI, onLoad: () => story.measure() }); }\n"
              "  catch (e) { document.documentElement.classList.add('no-gl'); return null; } })()")
ASSETS = {'__WA_PRICE__': esc(WA_MAIN), '__STILL__': STILL,
          '__SCENE_JS__': ("// three.js 0.160 from jsDelivr: failed or stalled (8 s), the page goes on without 3D (no-gl: the still)\n"
                           "const THREE = await Promise.race([import('https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.min.js').catch(() => null),\n"
                           "  new Promise(r => setTimeout(r, 8000, null))]);\n"
                           f'// scenes/{PRODUCT}.js, inlined by build-vtech.py\n' + SRC.replace('export function createScene(', 'function createScene(', 1)) if SCENE else '',
          '__SCENE__': SCENE_INIT if SCENE else 'null',
          '__SEQ__': json.dumps({'runs': RUNS, 'tiers': TIERS, 'cells': CELLS, 'mols': MOLS, 'helix': HELIX}, separators=(',', ':')),
          # phone: three still cells around the S3 ampoules (soft and bokeh sprites, small)
          '__PH_CELLS__': ('<span class="ph-cells" aria-hidden="true">' + ''.join(
              f'<img src="img/cells/{CELLS[j % len(CELLS)]}-{s}.webp" alt="" loading="lazy" decoding="async">' for j, s in ((0, 2), (3, 1), (6, 1)))
              + '</span>') if CELLS else ''}
for k, val in ASSETS.items(): page = page.replace(k, val)
left = re.findall(r'__[A-Z0-9_]+__|\{\{', page)
assert not left, f'unfilled placeholders: {sorted(set(left))}'
# the frame engine (engine/story.js, the module a React app imports) goes into the page: one file to publish or open
ENGINE, IMPORT = open(os.path.join(H, 'engine', 'story.js'), encoding='utf-8').read(), "import { createFrameStory } from './engine/story.js';"
assert page.count(IMPORT) == 1 and ENGINE.count('export function createFrameStory(') == 1 and '</script' not in ENGINE
page = page.replace(IMPORT, '// engine/story.js, inlined by build-vtech.py\n' + ENGINE.replace('export function createFrameStory(', 'function createFrameStory(', 1))
out = os.path.join(H, 'vtech-live.html') if PRODUCT == 'v-tech-system' else os.path.join(FILES, f'{PRODUCT}-live.html')
open(out, 'w', encoding='utf-8').write(page)
print(out, len(page), 'bytes;', len(T), 'texts,', len(RAW), 'blocks')
