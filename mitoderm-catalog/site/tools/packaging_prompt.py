"""Build the PACKAGING TEXT clause for image prompts from site/packaging-text.json (one source of truth)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, '..', 'packaging-text.json'), encoding='utf-8'))

def clause(slug, objects=None):
    v = DATA[slug]; parts = []
    for o in v['objects']:
        if objects and not any(k in o['what'] for k in objects): continue
        lines = o.get('front', []) + o.get('side', [])
        txt = f"{o['what'].upper()} — {o['look']}" + (': ' + '; '.join(lines) if lines else '')
        parts.append(txt)
    return ("PACKAGING TEXT — reproduce exactly as listed, every word spelled exactly as written here, crisp and legible, nothing added or translated "
            "(lines marked [unreadable] are tiny grey lines, not words): " + ' || '.join(parts) + '.')


def render_md(data=DATA):
    """packaging-text.md is rendered from the JSON, never edited by hand."""
    out = ['# Текст на упаковке — для промптов', '', data['_note'], '']
    for slug, v in data.items():
        if slug.startswith('_'):
            continue
        warn = f" — ⚠ {v['_warning']}" if v.get('_warning') else ''
        out += [f'## {slug}', '', f"Пакшот: `{v['packshot']}`{warn}", '']
        for o in v['objects']:
            out.append(f"- **{o['what']}** — {o['look']}")
            out += [f'  - {line}' for line in o.get('front', []) + o.get('side', [])]
        out.append('')
    return '\n'.join(out)


if __name__ == '__main__':
    with open(os.path.join(HERE, '..', 'packaging-text.md'), 'w', encoding='utf-8') as f:
        f.write(render_md())
