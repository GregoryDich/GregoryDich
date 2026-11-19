#!/usr/bin/env python3
"""PUT local files to Higgsfield upload slots without ever printing the presigned links.

`media_upload` returns a presigned link per file; it must not be copied into commands, logs or the repo.
This script finds the link for each media id in the session log and uploads the file to it.

Usage:  put-upload.py <media_id>=<file> [<media_id>=<file> ...]
Then call `media_confirm` for the ids that report put=200.
"""
import glob
import json
import mimetypes
import os
import subprocess
import sys

LOG_DIR = '/root/.claude/projects/-home-user-GregoryDich'


def strings(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings(value)
    elif isinstance(node, str):
        yield node


def find_links(wanted):
    links = {}
    logs = sorted(glob.glob(os.path.join(LOG_DIR, '*.jsonl')), key=os.path.getmtime, reverse=True)
    for log in logs[:2]:
        with open(log, errors='replace') as handle:
            for line in handle:
                if not any(media_id in line for media_id in wanted):
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                for text in strings(entry):
                    if not text.startswith('{"uploads"'):
                        continue
                    try:
                        for upload in json.loads(text)['uploads']:
                            links[upload['media_id']] = upload['upload_url']
                    except (ValueError, KeyError):
                        pass
        if all(media_id in links for media_id in wanted):
            break
    return links


def main():
    pairs = dict(arg.split('=', 1) for arg in sys.argv[1:] if '=' in arg)
    if not pairs:
        sys.exit(__doc__)
    links = find_links(pairs)
    failed = False
    for media_id, path in pairs.items():
        link = links.get(media_id)
        if not link:
            print(media_id[:8], 'upload link not found in the session log')
            failed = True
            continue
        kind = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        result = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '600', '-X', 'PUT',
             '-H', 'Content-Type: ' + kind, '--data-binary', '@' + path, link],
            capture_output=True, text=True)
        code = result.stdout.strip()
        print(media_id[:8], os.path.basename(path), 'put=' + code)
        failed = failed or code != '200'
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
