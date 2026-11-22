#!/usr/bin/env python3
"""Opens every link that the owner's pages give out and says which do not answer.

Reads the data files of the readiness page and of the video library (state/progress/samples.json, videos.json; other
JSON files can be named as arguments), takes every http(s) address found anywhere in them and asks the server for the
first kilobyte of each. A link is good when the answer is 200 or 206 and the content is what the extension promises
(a video for .mp4, a picture for .png/.jpg/.webp). For a video the whole size is printed in the JSON report, so a
truncated upload shows.

Usage:  check-links.py [file.json ...] [--json <report>]
Exit code 1 when a link fails. Hosts the session's network does not allow (the proxy answers 000 or 403 for the
whole host) are listed apart: they are not checked, which is not the same as broken.
"""
import concurrent.futures
import json
import os
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = [os.path.join(HERE, '..', 'progress', name) for name in ('samples.json', 'videos.json')]
KIND = {'mp4': 'video/', 'webm': 'video/', 'png': 'image/', 'jpg': 'image/', 'jpeg': 'image/', 'webp': 'image/'}


def addresses(node, found):
    if isinstance(node, dict):
        for value in node.values():
            addresses(value, found)
    elif isinstance(node, list):
        for value in node:
            addresses(value, found)
    elif isinstance(node, str) and node.startswith(('http://', 'https://')) and ' ' not in node:
        found.add(node)


def probe(url):
    done = subprocess.run(
        ['curl', '-s', '-o', '/dev/null', '-r', '0-1023', '--max-time', '60', '-D', '-',
         '-w', 'CODE=%{http_code} TYPE=%{content_type}', url], capture_output=True, text=True).stdout
    code = done.rsplit('CODE=', 1)[1].split(' ')[0] if 'CODE=' in done else '000'
    kind = done.rsplit('TYPE=', 1)[1].strip() if 'TYPE=' in done else ''
    size = None
    for line in done.split('\n'):
        if line.lower().startswith('content-range:') and '/' in line:
            tail = line.strip().rsplit('/', 1)[1]
            size = int(tail) if tail.isdigit() else None
    extension = urllib.parse.urlparse(url).path.rsplit('.', 1)[-1].lower()
    wanted = KIND.get(extension)
    good = code in ('200', '206') and (wanted is None or kind.startswith(wanted))
    return {'url': url, 'code': code, 'type': kind, 'size': size, 'good': good}


def main(argv):
    report = argv[argv.index('--json') + 1] if '--json' in argv else None
    files = [a for i, a in enumerate(argv) if not a.startswith('--') and (i == 0 or argv[i - 1] != '--json')] or DEFAULT
    found = set()
    for path in files:
        if os.path.exists(path):
            addresses(json.load(open(path, encoding='utf-8')), found)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(probe, sorted(found)))
    by_host = {}
    for row in results:
        by_host.setdefault(urllib.parse.urlparse(row['url']).netloc, []).append(row)
    closed = [host for host, rows in by_host.items() if all(r['code'] in ('000', '403') for r in rows) and len(rows) > 1]
    bad = [r for r in results if not r['good'] and urllib.parse.urlparse(r['url']).netloc not in closed]
    videos = [r for r in results if r['good'] and r['type'].startswith('video/')]
    print('links: %d; answer: %d (videos %d, %.0f MB together); fail: %d'
          % (len(results), sum(1 for r in results if r['good']), len(videos), sum(r['size'] or 0 for r in videos) / 1e6, len(bad)))
    for host, rows in sorted(by_host.items()):
        print('  %-48s %3d links%s' % (host, len(rows), '   NOT CHECKED: this session may not reach the host' if host in closed else ''))
    for row in bad:
        print('  FAIL %s %s %s' % (row['code'], row['type'] or '-', row['url']))
    if report:
        json.dump(results, open(report, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
