# Builds the Hebrew EXOCELL MASK "Story Scroll" page: one HTML file with logos and packshots inlined; scene stills
# and transition frames are loaded from scenes/ and transitions/ next to the page when present.
# Text comes only from reviewed sources: storyboard.he.json (board version of EXOCELL), product-pages.he.json
# (catalogue details) and exocell-he-ui.json (UI strings). The build fails if any placeholder is left unfilled.
import base64, html, io, json, os, re, sys, urllib.parse
from PIL import Image, ImageFilter

# `python3 build-exocell.py` builds the still version (exocell-mask.html); `python3 build-exocell.py 3d` builds the
# 3D scroll version (exocell-mask-3d.html) from exocell-3d-template.html with the same texts.
# `... 3d --private <figma-texts.json> [--out <page.html>]` builds the review copy with the specialists' photos, names
# and phones. That data must never reach this public repository, so the private page is written next to the JSON
# (or to --out) and the build refuses any path inside the git checkout. Without --private the specialists block shows
# a monogram and the city only.
ARGS = sys.argv[1:]
MODE = '3d' if '3d' in ARGS else 'still'
opt = lambda name: ARGS[ARGS.index(name) + 1] if name in ARGS else None
PRIVATE, OUT = opt('--private'), opt('--out')
assert not PRIVATE or MODE == '3d', '--private applies to the 3D page only'
H = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(H, '..'))
REPO = os.path.normpath(os.path.join(SITE, '..'))


def load(*p):
    with open(os.path.join(*p), encoding='utf-8') as f:
        return json.load(f)


def data_uri(path, width, fmt='PNG'):
    im = Image.open(path).convert('RGBA')
    if im.width > width:
        im = im.resize((width, round(width * im.height / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, fmt, **({'quality': 82, 'method': 6} if fmt == 'WEBP' else {'optimize': True}))
    return f'data:image/{fmt.lower()};base64,' + base64.b64encode(buf.getvalue()).decode()


def ph(label, hue):
    """Placeholder still, shown only if a scene file is missing."""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900"><defs><radialGradient id="g" cx="50%" cy="45%" r="70%"><stop offset="0" stop-color="{hue}" stop-opacity=".55"/><stop offset="1" stop-color="#0a0a0b" stop-opacity="1"/></radialGradient></defs><rect width="1600" height="900" fill="url(#g)"/><text x="800" y="450" fill="#dfe9ea" font-family="Arial" font-size="34" text-anchor="middle" opacity=".7">{label}</text></svg>'''
    return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()


he = load(SITE, 'storyboard.he.json')
pages = {p['slug']: {i['key']: i['he'] for i in p['items']} for p in he['pages']}
x, home = pages['exocell-mask'], pages['home']
spec_en, spec_he = load(SITE, 'product-pages.json'), load(SITE, 'product-pages.he.json')
cat = {s['slug']: h for s, h in zip(spec_en, spec_he)}
d = cat['exocell-mask']
ui = load(H, 'exocell-he-ui.json')

nav = home['nav.blocks'].split(' · ')           # meet, why, inside, feel, protocol, kit, offer
cta0 = x['b0.cta'].split(' · ')                  # price, see what's inside
cta6 = x['b6.cta'].split(' · ')                  # price, bundle, phone, email
esc = lambda s: html.escape(s, quote=True)
wa = lambda text: 'https://wa.me/' + ui['wa_number'] + '?text=' + urllib.parse.quote(text)
chips = lambda items, cls='': ''.join(f'<span class="chip{(" " + cls) if cls else ""}">{esc(t)}</span>' for t in items)
labels = lambda b: [x[k] for k in sorted((k for k in x if k.startswith(f'b{b}.label')), key=lambda k: int(k.split('label')[1]))]

T = {
    'page_title': ui['page_title'], 'nav_label': ui['nav_label'],
    'nav_why': nav[1], 'nav_inside': nav[2], 'nav_feel': nav[3], 'nav_protocol': nav[4], 'nav_kit': nav[5], 'nav_offer': nav[6],
    'cta_price': cta0[0], 'hero_more': cta0[1],
    'line_mark': ui['line_mark'], 'line_name': ui['line_name'], 'use_pro': ui['use_pro'],
    'hero_h1': 'EXOCELL MASK', 'hero_tag': x['b0.title'].split(' – ', 1)[1],
    'hero_lead': x['b0.line'], 'scroll_hint': ui['scroll_hint'],
    'why_h2': x['b1.title'], 'why_p': x['b1.line'], 'why_kicker': labels(1)[0],
    'inside_h2': x['b2.title'], 'inside_p': x['b2.line'], 'inside_head': ui['inside_head'], 'inside_formula': x['b2.cta'],
    'feel_h2': x['b3.title'], 'feel_p': x['b3.line'], 'feel_link': x['b3.cta'],
    'protocol_h2': x['b4.title'], 'protocol_p': x['b4.line'], 'protocol_finish': labels(4)[3],
    'kit_h2': x['b5.title'], 'kit_p': x['b5.line'], 'kitshot_alt': ui['kitshot_alt'],
    # a button may wrap, but never inside a product name: hyphens between Latin letters become non-breaking
    'offer_bundle': re.sub(r'(?<=[A-Z])-(?=[A-Z])', '\u2011', cta6[1]),
    'offer_h2': x['b6.title'], 'offer_p': x['b6.line'],
    'phone_label': ui['phone_label'], 'phone': ui['phone'], 'email_label': ui['email_label'], 'email': ui['email'],
    'related_line_h': ui['related_line_h'], 'related_more_h': ui['related_more_h'],
    'footer': home['home.footer-2'], 'bar_note': ui['bar'].split(' · ')[0], 'bar_name': ui['bar'].split(' · ')[1],
}
if MODE == '3d':
    T['nav_meet'] = nav[0]  # the 3D version has a section dock with all seven blocks
    T['page_title'] = ui['page_title'].replace('EXOCELL MASK', 'EXOCELL MASK 3D', 1)  # tells the two samples apart
RAW = {
    'hero_eyebrow': '<span class="sep"> · </span>'.join(f'<span class="nw">{esc(t)}</span>' for t in d['eyebrow'].split(' · ')),
    'hero_chips': chips(labels(0), 'drop'),
    'why_chips': chips(labels(1)[1:], 'gold'),
    'inside_chips': chips(labels(2), 'drop'),
    'inside_formula_list': ''.join(f'<li><bdi>{esc(t)}</bdi></li>' for t in d['ingredients']),
    # pins on the face in the treatment frame (forehead, cheek, jaw, chin), clear of the caption (upper left) and the box
    'feel_marks': ''.join(f'<span class="mark" data-at="{at}" style="{pos}">{esc(t)}</span>' for t, (pos, at) in zip(
        labels(3), [('left:42%;top:38%', .15), ('left:47%;top:46%', .3), ('left:50%;top:62%', .45), ('left:33%;top:76%', .6)])),
    'protocol_steps': ''.join(f'<div class="step rv" style="--d:{i * .08:.2f}s"><span class="n">0{i + 1}</span><h3>{esc(t)}</h3><p>{esc(s)}</p></div>'
                              for i, (t, s) in enumerate(d['steps'])),
    'kit_facts': ''.join(f'<div class="fact rv" style="--d:{i * .08:.2f}s"><b>{esc(n)}</b><span>{esc(l)}</span></div>' for i, (n, l) in enumerate(d['stats'])),
    'feel_chips': chips(labels(3), 'drop'),
    'kit_chips': chips(labels(5)),
    'offer_chips': chips(labels(6), 'gold'),
}


def card(slug, img, use, i, txt=esc):
    c = cat[slug]
    return (f'<a class="card rv" style="--d:{i * .08:.2f}s" href="{esc(wa(ui["wa_text_product"].format(name=c["name"])))}" target="_blank" rel="noopener">'
            f'<div class="pic"><img src="{data_uri(os.path.join(REPO, "protocols/assets/img", img), 360, "WEBP")}" alt="{esc(c["name"])}" loading="lazy"></div>'
            f'<div class="body"><span class="badge{" pro" if use == "pro" else " home"}">{esc(ui["use_pro" if use == "pro" else "use_home"])}</span>'
            f'<h3><bdi>{txt(c["name"])}</bdi></h3><p>{txt(c["tagline"])}</p><span class="go">{esc(ui["card_cta"])} ←</span></div></a>')


RELATED = {'related_line': [('v-tech-system', 'vtech-system.webp', 'pro'), ('exotech-gel', 'exotech-gel.webp', 'home')],
           'related_more': [('exo-nad', 'exo-nad.webp', 'pro'), ('micro-boost-10', 'micro-boost-10.webp', 'pro'),
                            ('derma-recovery-cream', 'derma-recovery.webp', 'home')]}
for key, row in RELATED.items():
    RAW[key] = ''.join(card(s, f, u, i) for i, (s, f, u) in enumerate(row))

ASSETS = {
    '__LOGO_MARK__': data_uri(os.path.join(SITE, 'img/mitoderm-logo-white-mark.png'), 300),
    '__LOGO_FULL__': data_uri(os.path.join(SITE, 'img/mitoderm-logo-white.png'), 420),
    '__WA_PRICE__': esc(wa(ui['wa_text_price'])), '__WA_BUNDLE__': esc(wa(ui['wa_text_bundle'])),
}
# A stage gets its clip only once its frames (or the clip) exist next to the page, so a missing transition never
# turns into failed requests; until then the stage crossfades the two stills.
for k, clip in (('__T1__', 'transitions/01-settle.mp4'), ('__T2__', 'transitions/02-kit.mp4')):
    ready = os.path.exists(os.path.join(H, clip[:-4], '0001.webp')) or os.path.exists(os.path.join(H, clip))
    ASSETS[k] = clip if ready else ''
def jpeg_uri(path):
    with open(path, 'rb') as f:
        return 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode()


if MODE == '3d':  # carton faces cut and straightened from the packshot (site/img/exocell-box-*.jpg)
    ASSETS['__BOX_FRONT__'] = jpeg_uri(os.path.join(SITE, 'img/exocell-box-front.jpg'))
    _f = Image.open(os.path.join(SITE, 'img/exocell-box-front.jpg')).convert('RGB').resize((370, 500), Image.LANCZOS)
    _f = _f.filter(ImageFilter.UnsharpMask(radius=1.2, percent=90, threshold=2))
    _b = io.BytesIO(); _f.save(_b, 'JPEG', quality=90)
    ASSETS['__BOX_FRONT_SM__'] = 'data:image/jpeg;base64,' + base64.b64encode(_b.getvalue()).decode()
    ASSETS['__BOX_SIDE__'] = jpeg_uri(os.path.join(SITE, 'img/exocell-box-side.jpg'))
SCENES = {
    'S1': ('scenes/01-meet.jpg', ph('01', '#1f6b70')), 'S2': ('scenes/02-inside.jpg', ph('02', '#2a8a8e')),
    'S3': ('scenes/03-mirror.jpg', ph('03', '#357f86')), 'S4': ('scenes/04-protocol.jpg', ph('04', '#1d5a62')),
}
for k, (src, fb) in SCENES.items():
    ASSETS[f'__{k}_SRC__'], ASSETS[f'__{k}_FALLBACK__'] = src, fb


# ---- 3D page: screen order of the approved Figma design (page 98:2): meet, why, inside, feel, kit, protocol, offer,
# specialists; the lead form of mitoderm.com in this design. New strings come only from the reviewed sources below.
def ltr_runs(s):
    """Escape a Hebrew line and isolate its Latin runs, so 'Ubiquinone – קו־אנזים Q10' keeps its order in RTL."""
    out, pos = [], 0
    for m in re.finditer(r'[A-Za-z][A-Za-z0-9.\-]*(?: [A-Za-z0-9][A-Za-z0-9.\-]*)*', s):
        out += [esc(s[pos:m.start()]), f'<bdi dir="ltr">{esc(m.group(0))}</bdi>']
        pos = m.end()
    return ''.join(out) + esc(s[pos:])


def brand(s):
    """Latin product and brand names in capitals, as everywhere in the edition; the Hebrew words are not touched."""
    for a, b in (('Mitoderm', 'MITODERM'), ('V-Tech', 'V-TECH'), ('Exo-NAD', 'EXO-NAD'), ('Exocell', 'EXOCELL')):
        s = s.replace(a, b)
    return s


def keep(s):
    """Escape a Hebrew line and keep each Latin name whole and in order: 'EXOCELL MASK' never breaks across lines,
    'BIOSPICULE™' keeps its ™ after the word, and a one-letter prefix stays with its name ('ו-Q10')."""
    out, pos = [], 0
    for m in re.finditer(r'(?<![\u05d0-\u05ea])([\u05d0-\u05ea]-)?([A-Za-z][A-Za-z0-9™®%\-]*(?:[ /]+[A-Za-z0-9][A-Za-z0-9™®%\-]*)*)', s):
        run = f'<bdi>{esc(m.group(2))}</bdi>'
        out += [esc(s[pos:m.start()]), f'<span class="nw">{esc(m.group(1))}{run}</span>' if m.group(1) else run.replace('<bdi>', '<bdi class="nw">', 1)]
        pos = m.end()
    return ''.join(out) + esc(s[pos:])


def fallback_still():
    """The still shown before the first 3D frame and without WebGL: the bright kit render with the two layers of the
    mask (white and blue) in front, from the layer renders in site/design/exocell-3d."""
    d3 = os.path.join(SITE, 'design/exocell-3d')
    still = os.path.join(d3, 'still-hd.png')  # rendered from this page's own scene (true colours), see window.__renderStill
    if os.path.exists(still):
        c = Image.open(still).convert('RGBA')
        c = c.resize((720, round(720 * c.height / c.width)), Image.LANCZOS)
        buf = io.BytesIO()
        c.save(buf, 'WEBP', quality=84, method=6)
        return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()
    kit = Image.open(os.path.join(d3, 'kit-hd.png')).convert('RGBA')
    kit = kit.crop(kit.getbbox())
    masks = Image.open(os.path.join(d3, 'layers/d5-burst-mask.png')).convert('RGBA')
    masks = masks.crop(masks.getbbox())
    mw = round(kit.width * 0.62)
    masks = masks.resize((mw, round(masks.height * mw / masks.width)), Image.LANCZOS)
    W, H_ = kit.width + round(mw * 0.28), kit.height + round(masks.height * 0.42)
    c = Image.new('RGBA', (W, H_), (0, 0, 0, 0))
    c.alpha_composite(kit, (0, 0))
    c.alpha_composite(masks, (W - mw, H_ - masks.height))
    c = c.crop(c.getbbox())
    c = c.resize((720, round(720 * c.height / c.width)), Image.LANCZOS)
    buf = io.BytesIO()
    c.save(buf, 'WEBP', quality=82, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()


def git_root(path):
    p = os.path.dirname(os.path.abspath(path))
    while p != os.path.dirname(p):
        if os.path.exists(os.path.join(p, '.git')):
            return p
        p = os.path.dirname(p)
    return None


def head_shot(path, width=520, aspect=4 / 3):
    """Head-and-shoulders crop of a portrait: the subject is what differs from each row's background (its left edge);
    the first rows of the subject are the head, and the crop is about three and a half head widths wide."""
    import numpy as np
    im = Image.open(path).convert('RGB')
    a = np.asarray(im.resize((160, round(160 * im.height / im.width))), dtype=float)
    h, w, _ = a.shape
    m = np.sqrt(((a - np.median(a[:, :max(4, w // 10)], axis=1, keepdims=True)) ** 2).sum(2)) > 38
    top = np.where(m.sum(1) > w * 0.04)[0][0]
    ys, xs = np.nonzero(m[top:top + max(3, h // 8)])
    cx, hw = xs.mean() / w, (np.percentile(xs, 95) - np.percentile(xs, 5)) / w
    W = min(im.width, hw * 3.6 * im.width)
    H_ = min(im.height, W / aspect)
    W = H_ * aspect
    x0 = min(max(cx * im.width - W / 2, 0), im.width - W)
    y0 = min(max(top * im.width / w - H_ * 0.08, 0), im.height - H_)
    im = im.crop((round(x0), round(y0), round(x0 + W), round(y0 + H_)))
    im = im.resize((width, round(width / aspect)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=80, optimize=True, progressive=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


PIN = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s7-6.2 7-11.5a7 7 0 0 0-14 0C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>'
CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.7 2.7L16 9.8"/></svg>'

if MODE == '3d':
    mk = load(SITE, 'sources/make-dictionary-spec.json')        # Make site dictionary: the specialists block
    mkh = lambda k: mk[k]['he']
    form = load(SITE, 'sources/mitoderm-com/form-he.json')        # the lead form of mitoderm.com
    ff = form['form']
    dz = load(H, 'exocell-he-design.json')                        # lines added for this design (two-layer mask)
    carton_front = load(SITE, 'packaging-text.json')['exocell-mask']['objects'][0]['front']
    net = next(m.group(1) for line in carton_front for m in [re.search(r"'(Net [^'℮]+?) ℮", line)] if m)
    tel = '+972' + re.sub(r'\D', '', ui['phone'])[1:]
    site = load(SITE, 'sources/mitoderm-com/contacts.json')       # contacts as on mitoderm.com (owner 11/10)
    assert site['phone'] == ui['phone'] and site['email'] == ui['email'] and site['whatsapp_link'].endswith(ui['wa_number'])
    hrs = site['hours_he']
    for k in ('feel_link', 'protocol_finish'):                    # not on the Figma screens / now protocol_chip
        T.pop(k)
    for k in ('offer_h2', 'inside_p', 'protocol_p'):              # copy with Latin names in it
        RAW[k] = keep(T.pop(k))
    for key, row in RELATED.items():
        RAW[key] = ''.join(card(s, f, u, i, keep) for i, (s, f, u) in enumerate(row))
    # Reviewed strings (he-strings-2026-10-11.json → exocell-he-ui.json, same keys); each hook keeps its approved default
    # (or stays empty) if its key is missing. Nothing here is invented.
    hook = lambda k, default='': ui.get(k, default)
    for k in ('feel_chips', 'feel_marks', 'kit_chips', 'offer_chips'):
        RAW.pop(k)
    T.update({
        'nav_spec': mkh('nav.specialists'), 'kit_double': dz['s5.double']['he'],
        # the two layers named on the kit screen, from the approved line «מסכה כפולה: שכבה לבנה ושכבה כחולה, …»
        'layer_white': dz['s5.double']['he'].split(':')[1].split(',')[0].strip().split(' ו')[0], 'layer_blue': dz['s5.double']['he'].split(':')[1].split(',')[0].strip().split(' ו')[1],
        'wa_display': site['whatsapp'], 'foot_access': site['footer_he']['accessibility'], 'foot_privacy': site['footer_he']['privacy'],
        'spec_empty': hook('spec.empty'),
        'phone_href': 'tel:' + tel, 'email_href': 'mailto:' + ui['email'] + '?subject=' + urllib.parse.quote('EXOCELL MASK'),
        'card_title': d['s04'][1], 'card_qty': d['kit'][0][0], 'card_line': d['kit'][0][2],  # '5×' + the reviewed line (the noun alone before it repeated «מסכות — מסכות»)
        'card_net': net, 'card_actives_h': d['s03'][0], 'card_chip': hook('mask.use', x['b6.line']),
        'spec_kicker': mkh('spec.kicker'), 'spec_h2': brand(mkh('spec.title')),
        'spec_filter': mkh('spec.filter.profession'), 'spec_list': form['specialists']['title'],
        'spec_join_h': mkh('spec.join.title'), 'spec_join_cta': mkh('spec.join.cta'),
        'form_p1': ff['titleP1'], 'form_p2': ff['titleP2'].strip(), 'form_p3': ff['titleP3'], 'form_sub': ff['subtitle'],
        'f_name': ff['placeholderInputName'], 'f_prof': ff['placeholderProfession'], 'f_email': ff['placeholderEmailName'],
        'f_phone': ff['placeholderPhoneName'], 'f_consent': ff['checkboxLabel'], 'f_submit': form['buttons']['requestCallback'],
        'f_privacy': ff['sharing'], 'f_sent': ff['sent']['text'], 'f_sent_gold': ff['sent']['textColored'],
        'f_sent_mob': ff['sent']['mobTitle'], 'f_more': form['buttons']['learnMore'], 'close_label': ui['ui.close'],
    })
    T['offer_p'] = hook('mask.use', T['offer_p'])
    chip_parts = labels(4)[3].split(' · ')                        # '+ DERMA RECOVERY CREAM' · 'הגנה מהשמש'
    RAW.update({
        'spec_p': keep(brand(mkh('tech.face.1.body'))),
        'form_fail': keep(hook('form.error')),
        'hours': ''.join(f'<span>{esc(t)}</span>' for t in (f"{hrs['title']}: {hrs['workWeek']}", f"{hrs['friday']}: {hrs['fridayText']}",
                                                               f"{hrs['saturday']}: {hrs['closed']}")),
        'protocol_chip': '<span class="sep"> · </span>'.join(f'<span class="nw">{keep(t)}</span>' for t in chip_parts),
        'inside_formula_list': ''.join(f'<li>{ltr_runs(t)}</li>' for t in d['ingredients']),
        'card_actives': ''.join(f'<li>{ltr_runs(t)}</li>' for t in d['ingredients']),
        'feel_pins': ''.join(f'<li class="mark">{esc(t)}</li>' for t in labels(3)),
        # step 02 «ספיגה» carries the time from the owner's protocol («עד 30 דקות»)
        'protocol_steps': ''.join(f'<li class="step rv" style="--d:{i * .08:.2f}s"><span class="n">0{i + 1}</span><h3>{esc(t)}</h3><p>{esc(s)}</p>'
                                  + (f'<span class="chip drop sm">{esc(hook("mask.step2.time"))}</span>' if i == 1 and hook('mask.step2.time') else '') + '</li>'
                                  for i, (t, s) in enumerate(d['steps'])),
        # the form's validation messages, as on mitoderm.com (read by the page script)
        'form_errors': json.dumps(dict(ff['errors'], consent_required=hook('form.consent_required')), ensure_ascii=False).replace('<', '\\u003c'),
        'spec_chips': ''.join(f'<button type="button" class="fchip" data-tag="{esc(tag)}" aria-pressed="{"true" if tag == ui["spec_tag_face"] else "false"}">{esc(label)}</button>'
                              for label, tag in [(mkh('spec.filter.all'), '*'), (ui['spec_tag_face'],) * 2, (ui['spec_tag_scalp'],) * 2,
                                                 (mkh('prof.trichologist'),) * 2]),
    })
    tags = (f'<div class="tags"><span class="tag">{esc(ui["spec_tag_face"])}</span>'
            f'<span class="ok">{CHECK}{esc(hook("spec.certified", mkh("spec.certified")))}</span></div>')
    book = lambda href, extra='': f'<a class="book" href="{esc(href)}"{extra}>{esc(mkh("spec.book"))} <span aria-hidden="true">↗</span></a>'
    if PRIVATE:  # review copy: photos, names and phones of the three specialists in the design
        s8 = json.load(open(PRIVATE, encoding='utf-8'))['S8_specialists']
        RAW['spec_cards'] = ''.join(
            f'<article class="spec rv" style="--d:{i * .08:.2f}s" data-tags="{esc(ui["spec_tag_face"])}">'
            f'<div class="pic"><img src="{head_shot(os.path.join(s8["photos_dir"], c["photo"]))}" alt="{esc(c["name"])}" loading="lazy"></div>'
            f'<div class="sb"><h3>{esc(c["name"])}</h3><p class="city">{PIN}<span>{esc(c["city"])}</span></p>'
            f'<p class="tel">{esc(s8["phone_label"])} <a href="tel:{esc(c["phone"])}"><bdi dir="ltr">{esc(c["phone"])}</bdi></a></p>'
            f'{tags}{book("tel:" + c["phone"])}</div></article>' for i, c in enumerate(s8['cards']))
    else:  # public build: a monogram and the city only, no names, addresses, phones or photos
        RAW['spec_cards'] = ''.join(
            f'<article class="spec mono rv" style="--d:{i * .08:.2f}s" data-tags="{esc(ui["spec_tag_face"])}">'
            f'<div class="av" aria-hidden="true">{esc(city[0])}</div>'
            f'<div class="sb"><h3 class="city">{PIN}<span>{esc(city)}</span></h3>'
            f'{tags}{book(wa(ui["wa_text_price"]), " data-lead")}</div></article>' for i, city in enumerate(ui['spec_demo_cities']))
    ASSETS['__SACHET__'] = jpeg_uri(os.path.join(SITE, 'img/exocell-sachet-front.jpg'))    # print of the single sachet
    ASSETS['__MIRROR__'] = jpeg_uri(os.path.join(H, 'scenes/03-mirror.jpg'))              # the approved treatment frame
    ASSETS['__FALLBACK__'] = fallback_still()
    ASSETS['__KIT__'] = data_uri(os.path.join(SITE, 'design/exocell-3d/kit-hd.png'), 760, 'WEBP')  # bright kit render

page = open(os.path.join(H, 'exocell-3d-template.html' if MODE == '3d' else 'exocell-template.html'), encoding='utf-8').read()
used = set(re.findall(r'\{\{\{?(\w+)\}?\}\}', page))
missing = used - set(T) - set(RAW)
unused = (set(T) | set(RAW)) - used
assert not missing, f'no text for {sorted(missing)}'
assert not unused, f'texts never placed: {sorted(unused)}'
page = re.sub(r'\{\{\{(\w+)\}\}\}', lambda m: RAW[m.group(1)], page)
page = re.sub(r'\{\{(\w+)\}\}', lambda m: esc(T[m.group(1)]), page)
for k, v in ASSETS.items():
    page = page.replace(k, v)
left = re.findall(r'__[A-Z0-9_]+__|\{\{', page)
assert not left, f'unfilled placeholders: {sorted(set(left))}'
out = os.path.abspath(OUT or (os.path.join(os.path.dirname(os.path.abspath(PRIVATE)), 'exocell-mask-3d.html') if PRIVATE else
                              os.path.join(H, 'exocell-mask-3d.html' if MODE == '3d' else 'exocell-mask.html')))
assert not (PRIVATE and git_root(out)), f'refusing to write the private build inside the git checkout: {out}'
with open(out, 'w', encoding='utf-8') as f:
    f.write(page)
print(out, len(page), 'bytes;', len(T), 'texts,', len(RAW), 'blocks')
