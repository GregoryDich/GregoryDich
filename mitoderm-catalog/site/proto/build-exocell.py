# Builds the EXOCELL MASK "Story Scroll" prototype: one HTML file, packshot and logo inlined,
# scene stills and transition clips loaded from scenes/ and transitions/ next to the page when present.
import base64, os, re
H = os.path.dirname(os.path.abspath(__file__))
IMG = '/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/site-img/compact/'
pack = base64.b64encode(open(IMG + 'exocell-mask.png', 'rb').read()).decode()
# The repo logo is black on transparent; the page is dark, so recolour every opaque pixel white, alpha untouched.
from PIL import Image
import io
_im = Image.open(IMG + 'mitoderm-logo.png').convert('RGBA')
_px = _im.get_flattened_data()
_im.putdata([(255, 255, 255, a) for (r, g, b, a) in _px])
_buf = io.BytesIO(); _im.save(_buf, 'PNG', optimize=True)
logo = base64.b64encode(_buf.getvalue()).decode()

def ph(label, hue):
    """Placeholder still: an inline SVG with the scene label, so the page reads before the generated images arrive."""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900"><defs><radialGradient id="g" cx="50%" cy="45%" r="70%"><stop offset="0" stop-color="{hue}" stop-opacity=".55"/><stop offset="1" stop-color="#070b0c" stop-opacity="1"/></radialGradient></defs><rect width="1600" height="900" fill="url(#g)"/><text x="800" y="450" fill="#dfe9ea" font-family="Rubik,Arial" font-size="34" text-anchor="middle" opacity=".7">{label}</text></svg>'''
    return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()

SCENES = {
    's1': ('scenes/01-meet.jpg', ph('Scene 01 · the box on a teal studio surface', '#1f6b70')),
    's2': ('scenes/02-inside.jpg', ph('Scene 02 · the mask unfolded, serum catching the light', '#2a8a8e')),
    's3': ('scenes/03-mirror.jpg', ph('Scene 03 · the mirror — she lays the mask on her face', '#357f86')),
    's4': ('scenes/04-protocol.jpg', ph('Scene 04 · the clinic — mask after the procedure', '#1d5a62')),
}
CLIPS = {'t1': 'transitions/01-open.mp4', 't2': 'transitions/02-unfold.mp4', 't3': 'transitions/03-mirror.mp4'}

html = open(os.path.join(H, 'exocell-template.html'), encoding='utf-8').read()
html = html.replace('__PACK__', pack).replace('__LOGO__', logo)
for k, (src, fallback) in SCENES.items():
    html = html.replace(f'__{k.upper()}_SRC__', src).replace(f'__{k.upper()}_FALLBACK__', fallback)
for k, src in CLIPS.items():
    html = html.replace(f'__{k.upper()}__', src)
out = os.path.join(H, 'exocell-mask.html')
open(out, 'w', encoding='utf-8').write(html)
print(out, len(html))
