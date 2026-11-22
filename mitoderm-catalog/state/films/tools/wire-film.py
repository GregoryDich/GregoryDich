#!/usr/bin/env python3
"""Wires a finished film into a product page: the film addresses, the chapters, the captions and the page shots.

usage: wire-film.py <wire.json> [--replace]

wire.json (kept next to the storyboard, state/films/<slug>/wire.json):
{
  "slug": "cell-renew-1-5",
  "frames": 1022,
  "desktop_url": "https://.../film.mp4",
  "mobile_url": "https://.../film-mobile.mp4",
  "comment": ["A connected film: ...", "second comment line"],
  "anchor": "left",        (optional: keep the left edge of the desktop film in a window narrower than 16:9)
  "chapters": [
    {"start": 0, "end": 110, "note": "01 the pack at home", "shot": "Упаковка дома у зеркала", "type": "pack", "section": 1},
    {"start": 110, "end": 250, "note": "02 at the mirror", "shot": "...", "type": "patient", "section": 2,
     "body": "optional: a part of the section body, word for word, when the whole body is too long"}
  ]
}
Captions are taken from codex-site/mitoderm/content.json word for word: section 1 is the intro (title = the product
name, body = intro.title, tag = intro.eyebrow), section N is the section whose "index" is N (title, body, eyebrow).
An optional "body" must be an exact part of that section's body - the tool refuses anything else. Spaces inside
Latin product names and between a number and its unit become non-breaking, so a name is never split across lines.
An optional "quiet": [from, to] (parts of the chapter, 0..1) names the stretch where the camera brings a face under
the caption: on a wide screen the caption fades for that stretch (on a phone it stands under the film and stays).

It edits three files of codex-site: mitoderm/media-urls.json, mitoderm/pilot/product-films.ts and
production/page-bible/REGISTRY.json. With --replace an existing entry of the slug is replaced.
"""
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'codex-site'))
CONTENT = os.path.join(ROOT, 'mitoderm', 'content.json')
MEDIA = os.path.join(ROOT, 'mitoderm', 'media-urls.json')
FILMS = os.path.join(ROOT, 'mitoderm', 'pilot', 'product-films.ts')
REGISTRY = os.path.join(ROOT, 'production', 'page-bible', 'REGISTRY.json')
NAMES = ['MICRO BOOST 10%', 'CELL RENEW 1.5%', 'CELLULAR AGE DEFENSE 2.5%', 'DERMA RECOVERY CREAM', 'MITOTECH CELL BOOSTER',
         'EXOSIGNAL HAIR', 'EXOSIGNAL SPRAY', 'EXOCELL MASK', 'EXOTECH GEL', 'V-TECH SYSTEM', 'Longevity Serum',
         'LONGEVITY SERUM', 'Galactomyces ferment', 'Sodium DNA', 'Hydrolyzed Sponge', 'Advanced Biospicule Technology']


def typography(text, names=True):
    """Non-breaking spaces inside product names and between a number and its unit; the words stay the same.
    A heading keeps ordinary spaces inside a product name: a long name must be able to wrap on a phone."""
    for name in NAMES if names else []:
        text = text.replace(name, name.replace(' ', '\u00a0'))
    text = re.sub(r'(\d) (מ״ל|מ״מ|ml|fl\.)', '\\1\u00a0\\2', text)
    text = text.replace('fl.\u00a0oz', 'fl.\u00a0oz').replace('fl. oz', 'fl.\u00a0oz')
    return text


def ts_string(text):
    out = text.replace('\\', '\\\\').replace("'", "\\'")
    return "'" + out.replace('\u00a0', '\\u00a0').replace('\u2060', '\\u2060') + "'"


def captions(wire):
    products = json.load(open(CONTENT, encoding='utf-8'))['products']
    product = next(p for p in products if p['slug'] == wire['slug'])
    result = []
    for chapter in wire['chapters']:
        number = chapter['section']
        if number == 1:
            title, body, tag = product['name'], product['intro']['title'], product['intro']['eyebrow']
            source = product['intro']['title'] + ' ' + product['intro'].get('body', '')
        else:
            section = next(s for s in product['sections'] if s['index'] == number)
            title, body, tag = section['title'], section['body'], section['eyebrow']
            source = section['body']
        if 'body' in chapter:
            if chapter['body'] not in source:
                sys.exit('chapter %s: the given body is not word for word from section %d' % (chapter['note'], number))
            body = chapter['body']
        if 'tag' in chapter:
            if chapter['tag'] not in tag:
                sys.exit('chapter %s: the given tag is not a part of the eyebrow of section %d' % (chapter['note'], number))
            tag = chapter['tag']
        result.append({'title': typography(title, names=False), 'body': typography(body), 'tag': tag})
    return result


def remove_entry(text, slug, opener, closer):
    """Removes ' 'slug':<opener> ... <closer>' with a preceding comma or a following comma, and its comment lines."""
    start = text.find("\n '%s':%s" % (slug, opener))
    if start < 0:
        return text, False
    end = text.index('\n ' + closer, start) + len('\n ' + closer)
    comment_start = start
    while True:                                       # comment lines right above the entry go with it
        previous = text.rfind('\n', 0, comment_start)
        if previous >= 0 and text[previous + 1:comment_start].lstrip().startswith('//'):
            comment_start = previous
        else:
            break
    before, after = text[:comment_start], text[end:]
    if after.startswith(','):
        after = after[1:]
    elif before.rstrip().endswith(','):
        before = before.rstrip()[:-1]
    return before + after, True


def main(argv):
    if not argv:
        sys.exit(__doc__)
    wire = json.load(open(argv[0], encoding='utf-8'))
    replace = '--replace' in argv
    slug, chapters = wire['slug'], wire['chapters']
    if chapters[0]['start'] != 0 or chapters[-1]['end'] != wire['frames']:
        sys.exit('the chapters must run from 0 to the last frame (%d)' % wire['frames'])
    for a, b in zip(chapters, chapters[1:]):
        if a['end'] != b['start']:
            sys.exit('chapters %s and %s do not meet' % (a['note'], b['note']))
    caps = captions(wire)

    media = json.load(open(MEDIA, encoding='utf-8'))
    desktop, mobile = '/assets/world/%s-film.mp4' % slug, '/assets/world/%s-film-mobile.mp4' % slug
    media[desktop], media[mobile] = wire['desktop_url'], wire['mobile_url']
    json.dump(media, open(MEDIA, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    open(MEDIA, 'a').write('\n')

    text = open(FILMS, encoding='utf-8').read()
    for opener, closer in (('{', ']}'), ('[', ']')):
        text, found = remove_entry(text, slug, opener, closer)
        if found and not replace:
            sys.exit('the slug is already wired; use --replace')
    def span(c):
        quiet = ',quiet:[%g,%g]' % tuple(c['quiet']) if c.get('quiet') else ''
        return '{start:%d,end:%d%s}' % (c['start'], c['end'], quiet)
    width = max(len(span(c) + ',') for c in chapters)
    lines = [' // ' + line for line in wire.get('comment', [])]
    anchor = "anchor:'left'," if wire.get('anchor') == 'left' else ''
    lines.append(" '%s':{desktop:'%s',mobile:'%s',fps:24,frames:%d,%schapters:[" % (slug, desktop, mobile, wire['frames'], anchor))
    for index, chapter in enumerate(chapters):
        item = span(chapter) + (',' if index < len(chapters) - 1 else '')
        lines.append('  %s // %s' % (item.ljust(width), chapter['note']))
    lines.append(' ]}')
    marker = '\n};\n// Chapter captions'
    if marker not in text:
        sys.exit('product-films.ts: the end of productFilms was not found')
    text = text.replace(marker, ',\n' + '\n'.join(lines) + marker, 1)
    block = [" '%s':[" % slug]
    for index, cap in enumerate(caps):
        block.append('  {title:%s,body:%s,tag:%s}%s' % (ts_string(cap['title']), ts_string(cap['body']), ts_string(cap['tag']),
                                                        ',' if index < len(caps) - 1 else ''))
    block.append(' ]')
    tail = text.rstrip()
    if not tail.endswith('};'):
        sys.exit('product-films.ts: the end of productCaptions was not found')
    text = tail[:-2].rstrip() + ',\n' + '\n'.join(block) + '\n};\n'
    open(FILMS, 'w', encoding='utf-8').write(text)

    registry = json.load(open(REGISTRY, encoding='utf-8'))

    def find(node):
        if isinstance(node, dict):
            if node.get('slug') == slug and 'shots' in node:
                return node
            for value in node.values():
                hit = find(value)
                if hit:
                    return hit
        elif isinstance(node, list):
            for value in node:
                hit = find(value)
                if hit:
                    return hit
        return None

    page = find(registry)
    if not page:
        sys.exit('REGISTRY.json: the page %s was not found' % slug)
    shots = []
    for index, chapter in enumerate(chapters):
        seconds = round((chapter['end'] - chapter['start']) / 24, 2)
        shots.append({'title': chapter['shot'], 'seconds': seconds, 'vh': max(1.1, round(seconds * 0.285 / 0.05) * 0.05),
                      'type': chapter['type'], 'index': index + 1})
    for shot in shots:
        shot['vh'] = round(shot['vh'], 2)
    page['shots'] = shots
    json.dump(registry, open(REGISTRY, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    open(REGISTRY, 'a').write('\n')
    print('wired %s: %d frames, %d chapters; captions word for word from content.json' % (slug, wire['frames'], len(chapters)))
    for cap in caps:
        print('  ', cap['tag'], '|', cap['title'], '|', cap['body'][:60])


if __name__ == '__main__':
    main(sys.argv[1:])
