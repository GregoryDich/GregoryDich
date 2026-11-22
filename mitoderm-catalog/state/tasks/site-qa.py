#!/usr/bin/env python3
"""Static checks of every page of the test site: what a browser would not complain about but a visitor or a search
engine would. Reads the rendered HTML from the running site; changes nothing and sends no form.

Usage (site running on 8787):  site-qa.py [base url=http://127.0.0.1:8787] [--json <file>]

Per page: HTTP status, <title>, meta description, <html lang/dir>, number of <h1>, Open Graph title and picture,
pictures without an alt attribute, ids used twice, links inside the page (#id) that point nowhere.
For the whole site: every internal link and every picture, script and stylesheet address is requested once and
must answer 200 (films are checked by their first bytes); titles and descriptions used on more than one page.
The pages are the same list the static copy is made of: home, catalogue, privacy and every product of
codex-site/production/page-bible/REGISTRY.json.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, '..', '..', 'codex-site', 'production', 'page-bible', 'REGISTRY.json')


def slugs():
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
    walk(json.load(open(REGISTRY, encoding='utf-8')))
    return found


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.in_title = '', False
        self.meta, self.html = {}, {}
        self.h1, self.ids, self.links, self.assets, self.no_alt = 0, [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html':
            self.html = a
        elif tag == 'title':
            self.in_title = True
        elif tag == 'meta':
            key = a.get('name') or a.get('property')
            if key:
                self.meta[key] = a.get('content', '')
        elif tag == 'h1':
            self.h1 += 1
        elif tag == 'a' and a.get('href'):
            self.links.append(a['href'])
        elif tag == 'img':
            if 'alt' not in a:
                self.no_alt.append((a.get('src') or '')[:80])
            if a.get('src'):
                self.assets.append(a['src'])
            for part in (a.get('srcset') or '').split(','):
                if part.strip():
                    self.assets.append(part.strip().split()[0])
        elif tag == 'source':
            for part in (a.get('srcset') or a.get('src') or '').split(','):
                if part.strip():
                    self.assets.append(part.strip().split()[0])
        elif tag == 'script' and a.get('src'):
            self.assets.append(a['src'])
        elif tag == 'link' and a.get('href') and a.get('rel') in ('stylesheet', 'icon', 'manifest', 'preload', 'modulepreload'):
            self.assets.append(a['href'])
        elif tag == 'video' and a.get('src'):
            self.assets.append(a['src'])
        if a.get('id'):
            self.ids.append(a['id'])

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def fetch(url, head_bytes=None):
    request = urllib.request.Request(url, headers={'User-Agent': 'site-qa'})
    if head_bytes:
        request.add_header('Range', 'bytes=0-%d' % (head_bytes - 1))
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read() if not head_bytes else response.read(head_bytes)
    except urllib.error.HTTPError as error:
        return error.code, b''
    except Exception as error:                      # noqa: BLE001 - a refused connection is a finding, not a crash
        return 0, str(error).encode()


def main(argv):
    base = next((a for a in argv if a.startswith('http')), 'http://127.0.0.1:8787').rstrip('/')
    out = argv[argv.index('--json') + 1] if '--json' in argv else None
    paths = ['/', '/catalog', '/privacy'] + ['/products/' + s for s in slugs()]
    pages, targets, problems = {}, {}, []
    for path in paths:
        status, body = fetch(base + path)
        page = Page()
        page.feed(body.decode('utf-8', 'replace'))
        pages[path] = page
        twice = sorted({i for i in page.ids if page.ids.count(i) > 1})
        row = {'status': status, 'title': page.title.strip(), 'description': page.meta.get('description', ''),
               'lang': page.html.get('lang'), 'dir': page.html.get('dir'), 'h1': page.h1,
               'og': bool(page.meta.get('og:title')) and bool(page.meta.get('og:image')),
               'robots': page.meta.get('robots', ''), 'no_alt': page.no_alt, 'ids_twice': twice}
        dead = []
        for href in page.links:
            if href.startswith('#'):
                if len(href) > 1 and href[1:] not in page.ids:
                    dead.append(href)
            elif href.startswith('/') and not href.startswith('//'):
                targets.setdefault(href.split('#')[0], set()).add(path)
        for src in page.assets:
            if src.startswith('data:'):
                continue
            full = urllib.parse.urljoin(base + path, src)
            targets.setdefault(full if not full.startswith(base) else full[len(base):], set()).add(path)
        row['dead_anchors'] = sorted(set(dead))
        pages[path] = row
        if status != 200: problems.append('%s answers %s' % (path, status))
        if not row['title']: problems.append('%s has no <title>' % path)
        if not row['description']: problems.append('%s has no meta description' % path)
        if row['h1'] != 1: problems.append('%s has %d <h1>' % (path, row['h1']))
        if row['lang'] != 'he' or row['dir'] != 'rtl': problems.append('%s: <html lang=%s dir=%s>' % (path, row['lang'], row['dir']))
        if row['no_alt']: problems.append('%s: %d pictures without alt: %s' % (path, len(row['no_alt']), row['no_alt'][:3]))
        if twice: problems.append('%s: ids used twice: %s' % (path, twice[:6]))
        if row['dead_anchors']: problems.append('%s: links to missing ids: %s' % (path, row['dead_anchors'][:6]))
    broken = []
    for target in sorted(targets):
        url = target if target.startswith('http') else base + target
        film = url.split('?')[0].endswith(('.mp4', '.webm'))
        status, _ = fetch(url, 2048 if film else None)
        if status not in (200, 206):
            broken.append({'target': target, 'status': status, 'on': sorted(targets[target])[:4]})
    for item in broken:
        problems.append('%s answers %s (linked from %s)' % (item['target'], item['status'], ', '.join(item['on'])))
    for field in ('title', 'description'):
        used = {}
        for path, row in pages.items():
            if row[field]:
                used.setdefault(row[field], []).append(path)
        for text, where in used.items():
            if len(where) > 1:
                problems.append('the same %s on %s: "%s"' % (field, ', '.join(where), text[:60]))
    for path, row in pages.items():
        print('%-36s %s  h1=%d  og=%s  robots=%-18s title=%s' % (path, row['status'], row['h1'], 'yes' if row['og'] else 'NO ',
                                                                 row['robots'] or '-', row['title'][:58]))
    print('addresses requested: %d, not answering: %d' % (len(targets), len(broken)))
    print('PROBLEMS: %d' % len(problems))
    for line in problems:
        print('  -', line)
    if out:
        json.dump({'pages': pages, 'broken': broken, 'problems': problems}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1:])
