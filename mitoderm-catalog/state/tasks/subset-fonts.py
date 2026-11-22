#!/usr/bin/env python3
"""Makes the fonts the site serves (codex-site/public/fonts/Rubik-<weight>.woff2) from the full Rubik files kept in
codex-site/production/fonts/Rubik-<weight>.ttf.

The full files carry Cyrillic, Arabic and extended Latin, which the Hebrew site never shows; without them and packed as
WOFF2 a weight is about 25 KB instead of 175 KB (about 65 KB as the server compresses a TTF). Kept: Latin and Latin-1,
Hebrew with its points and presentation forms, punctuation, super- and subscripts, currency, letter-like signs, number
forms, mathematical signs and box drawing. Outlines, metrics, kerning and all layout features of the kept characters
are unchanged, so text takes exactly the same space as before.

Usage:  subset-fonts.py                       rebuild the five WOFF2 files
        subset-fonts.py --check <base url>    also read every page of the running site and name each character of the
                                              page text that the full font has and the served one lacks (must be none)
Needs:  pip install fonttools brotli
If the site starts showing another alphabet, add its range to KEEP and run this again.
"""
import html
import json
import os
import re
import sys
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, '..', '..', 'codex-site')
SRC = os.path.join(APP, 'production', 'fonts')
OUT = os.path.join(APP, 'public', 'fonts')
WEIGHTS = (300, 400, 500, 600, 700)
KEEP = [(0x20, 0x7E), (0xA0, 0xFF), (0x2B0, 0x36F), (0x591, 0x5F4), (0x2000, 0x206F), (0x2070, 0x209F),
        (0x20A0, 0x20CF), (0x2100, 0x218F), (0x2200, 0x22FF), (0x2500, 0x25FF), (0xFB1D, 0xFB4F), (0xFEFF, 0xFEFF)]


def kept(code):
    return any(lo <= code <= hi for lo, hi in KEEP)


def build():
    os.makedirs(OUT, exist_ok=True)
    for weight in WEIGHTS:
        path = os.path.join(SRC, 'Rubik-%d.ttf' % weight)
        full = TTFont(path).getBestCmap()
        options = subset.Options()
        options.flavor = 'woff2'
        options.layout_features = ['*']
        options.name_IDs = ['*']
        options.notdef_outline = True
        options.glyph_names = False
        options.hinting = True
        font = subset.load_font(path, options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(unicodes=sorted(code for code in full if kept(code)))
        subsetter.subset(font)
        target = os.path.join(OUT, 'Rubik-%d.woff2' % weight)
        subset.save_font(font, target, options)
        print('Rubik-%d: %d characters of %d kept, %d bytes (the full ttf is %d)'
              % (weight, sum(1 for code in full if kept(code)), len(full), os.path.getsize(target), os.path.getsize(path)))


def page_paths():
    found = []

    def walk(node):
        if isinstance(node, dict):
            slug = node.get('slug')
            if isinstance(slug, str) and 'shots' in node and slug not in found:
                found.append(slug)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(json.load(open(os.path.join(APP, 'production', 'page-bible', 'REGISTRY.json'), encoding='utf-8')))
    return ['/', '/catalog', '/privacy'] + ['/products/' + slug for slug in found]


def check(base):
    full = set(TTFont(os.path.join(SRC, 'Rubik-400.ttf')).getBestCmap())
    served = set(TTFont(os.path.join(OUT, 'Rubik-400.woff2')).getBestCmap())
    lost = {}
    for path in page_paths():
        with urllib.request.urlopen(base.rstrip('/') + path, timeout=60) as response:
            page = response.read().decode('utf-8', 'replace')
        page = re.sub(r'(?s)<(script|style)\b.*?</\1>', ' ', page)
        text = html.unescape(re.sub(r'<[^>]+>', ' ', page))
        for char in set(text):
            if ord(char) in full and ord(char) not in served:
                lost.setdefault(char, []).append(path)
    print('pages read: %d; characters of the page text the served font lost: %d' % (len(page_paths()), len(lost)))
    for char, where in sorted(lost.items()):
        print('  U+%04X %s on %s' % (ord(char), char, ', '.join(where[:4])))
    return not lost


if __name__ == '__main__':
    build()
    if '--check' in sys.argv:
        sys.exit(0 if check(sys.argv[sys.argv.index('--check') + 1]) else 1)
