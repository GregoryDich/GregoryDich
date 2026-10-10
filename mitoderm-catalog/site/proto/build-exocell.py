# Builds the Hebrew EXOCELL MASK "Story Scroll" page: one HTML file with logos and packshots inlined; scene stills
# and transition frames are loaded from scenes/ and transitions/ next to the page when present.
# Text comes only from reviewed sources: storyboard.he.json (board version of EXOCELL), product-pages.he.json
# (catalogue details) and exocell-he-ui.json (UI strings). The build fails if any placeholder is left unfilled.
import base64, html, io, json, os, re, urllib.parse
from PIL import Image

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
    'hero_eyebrow': d['eyebrow'], 'hero_h1': 'EXOCELL MASK', 'hero_tag': x['b0.title'].split(' – ', 1)[1],
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
RAW = {
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


def card(slug, img, use, i):
    c = cat[slug]
    return (f'<a class="card rv" style="--d:{i * .08:.2f}s" href="{esc(wa(ui["wa_text_product"].format(name=c["name"])))}" target="_blank" rel="noopener">'
            f'<div class="pic"><img src="{data_uri(os.path.join(REPO, "protocols/assets/img", img), 360, "WEBP")}" alt="{esc(c["name"])}" loading="lazy"></div>'
            f'<div class="body"><span class="badge{" pro" if use == "pro" else " home"}">{esc(ui["use_pro" if use == "pro" else "use_home"])}</span>'
            f'<h3><bdi>{esc(c["name"])}</bdi></h3><p>{esc(c["tagline"])}</p><span class="go">{esc(ui["card_cta"])} ←</span></div></a>')


RAW['related_line'] = ''.join(card(s, f, u, i) for i, (s, f, u) in enumerate([
    ('v-tech-system', 'vtech-system.webp', 'pro'), ('exotech-gel', 'exotech-gel.webp', 'home')]))
RAW['related_more'] = ''.join(card(s, f, u, i) for i, (s, f, u) in enumerate([
    ('exo-nad', 'exo-nad.webp', 'pro'), ('micro-boost-10', 'micro-boost-10.webp', 'pro'), ('derma-recovery-cream', 'derma-recovery.webp', 'home')]))

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
SCENES = {
    'S1': ('scenes/01-meet.jpg', ph('01', '#1f6b70')), 'S2': ('scenes/02-inside.jpg', ph('02', '#2a8a8e')),
    'S3': ('scenes/03-mirror.jpg', ph('03', '#357f86')), 'S4': ('scenes/04-protocol.jpg', ph('04', '#1d5a62')),
}
for k, (src, fb) in SCENES.items():
    ASSETS[f'__{k}_SRC__'], ASSETS[f'__{k}_FALLBACK__'] = src, fb

page = open(os.path.join(H, 'exocell-template.html'), encoding='utf-8').read()
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
out = os.path.join(H, 'exocell-mask.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(page)
print(out, len(page), 'bytes;', len(T), 'texts,', len(RAW), 'blocks')
