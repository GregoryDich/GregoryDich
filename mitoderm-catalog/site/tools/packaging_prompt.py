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
