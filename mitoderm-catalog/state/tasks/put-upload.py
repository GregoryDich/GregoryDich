#!/usr/bin/env python3
"""PUT local files to Higgsfield upload slots without ever printing the presigned links.

`media_upload` returns a presigned link per file; it must not be copied into commands, logs or the repo.
This script finds the link for each media id in the session log and uploads the file to it.

Usage:  put-upload.py <media_id>=<file> [<media_id>=<file> ...]
        put-upload.py --slots <saved result.json> <name in the request>=<file> [...]
Then call `media_confirm` for the ids that report put=200.

--slots: a large answer of `media_upload` is not put into the session log but saved to a file (the tool names it).
Give that file here and name each upload by the filename it was requested under; the media ids are printed in full,
ready for `media_confirm`. Never print that file: besides the link itself, its "instructions" field repeats the link.
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


def slots(path, pairs):
    """The upload links of a saved `media_upload` answer, keyed by media id; `pairs` is re-keyed from the requested
    filename to the media id."""
    links, by_name = {}, {}
    for upload in json.load(open(path))['uploads']:
        links[upload['media_id']] = upload['upload_url']
        for name in pairs:
            if '@' + name + ' ' in upload.get('instructions', ''):
                by_name[name] = upload['media_id']
    missing = [name for name in pairs if name not in by_name]
    if missing:
        sys.exit('no upload slot for: ' + ', '.join(missing))
    return links, {by_name[name]: path_ for name, path_ in pairs.items()}


def main():
    args = sys.argv[1:]
    saved = None
    if '--slots' in args:
        at = args.index('--slots')
        saved = args[at + 1]
        del args[at:at + 2]
    pairs = dict(arg.split('=', 1) for arg in args if '=' in arg)
    if not pairs:
        sys.exit(__doc__)
    if saved:
        links, pairs = slots(saved, pairs)
    else:
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
        print(media_id if saved else media_id[:8], os.path.basename(path), 'put=' + code)
        failed = failed or code != '200'
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
