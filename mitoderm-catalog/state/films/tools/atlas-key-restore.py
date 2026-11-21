#!/usr/bin/env python3
"""Puts the Atlas Cloud key back into ~/.atlas_key after a container restart.

The customer gave the key in the chat of the cloud session, so the session log on this machine holds it.
This tool finds it there and writes it to ~/.atlas_key (readable by the owner only). The key is never
printed and never written anywhere else. Nothing here contains the key: only its public format.

usage: atlas-key-restore.py            -> prints what it did, never the key
"""
import glob
import os
import re
import sys

TARGET = os.path.expanduser("~/.atlas_key")
FORMAT = re.compile(rb"(?<![0-9A-Za-z-])apikey-[0-9a-f]{32}(?![0-9A-Za-z])")  # the public shape of an Atlas key


def main():
    if os.path.exists(TARGET) and open(TARGET).read().strip():
        print("the key is already in place")
        return 0
    logs = sorted(glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")), key=os.path.getmtime)
    last, distinct = None, set()
    for path in logs:
        with open(path, "rb") as source:
            for line in source:
                for match in FORMAT.findall(line):
                    distinct.add(match)
                    last = match
    if not last:
        print("no key found in the session logs: ask the customer for it (Atlas console, API keys)")
        return 1
    handle = os.open(TARGET, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "wb") as target:
        target.write(last + b"\n")
    print("the key is restored (the most recent of %d found); check it with atlas.py balance" % len(distinct))
    return 0


if __name__ == "__main__":
    sys.exit(main())
