#!/bin/bash
# Two-pass build of MITODERM-video-scenarios-HE-v3.docx/.pdf from ../src/*.md, then verify.py.
# Pass 1 (--mark) puts QQMARKpgNN on every part page / chapter title; the PDF is scanned for start pages;
# pass 2 prints those numbers in the TOC. Missing source files are skipped with a note.
# Usage: build.sh [--publish]    (--publish copies the pair to site/xlsx-he/scenarios/ if verify passes)
# Env:   W=<work dir> (default: the session scratchpad scenarios-v3-build)
set -e
B=$(cd "$(dirname "$0")" && pwd)
SRC=$(cd "$B/../src" && pwd)
REPO=$(cd "$B/../../../.." && pwd)
W=${W:-/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/scenarios-v3-build}
N=MITODERM-video-scenarios-HE-v3
O=$W/out; rm -rf "$O"; mkdir -p "$O/mark" "$O/final"
export NODE_PATH=$(npm root -g)
LO="-env:UserInstallation=file://$W/lo-profile"
node "$B/build-docx.cjs" "$O/mark/$N.docx" --src "$SRC" --mark
python3 -I "$B/post-docx.py" "$O/mark/$N.docx"
soffice $LO --headless --convert-to pdf --outdir "$O/mark" "$O/mark/$N.docx" >/dev/null 2>&1
python3 -I - "$O/mark/$N.pdf" "$O/pages.json" <<'PY'
import subprocess, sys, json, re
pdf, out = sys.argv[1], sys.argv[2]
n = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout).group(1))
pages = {}
for p in range(1, n + 1):
    t = subprocess.run(['pdftotext', '-f', str(p), '-l', str(p), pdf, '-'], capture_output=True, text=True).stdout
    for m in re.findall(r'QQMARK(pg\d\d)', t): pages.setdefault(m, p)
json.dump(pages, open(out, 'w')); print('mark pass pages', n, pages)
PY
node "$B/build-docx.cjs" "$O/final/$N.docx" --src "$SRC" --pages "$O/pages.json"
python3 -I "$B/post-docx.py" "$O/final/$N.docx"
soffice $LO --headless --convert-to pdf --outdir "$O/final" "$O/final/$N.docx" >/dev/null 2>&1
pdfinfo "$O/final/$N.pdf" | grep -E "Pages|Page size"
python3 -I "$B/verify.py" "$O/final/$N.docx" "$O/final/$N.pdf" "$O/pages.json" "$O/final/$N.docx.manifest.json"
if [ "$1" = "--publish" ]; then
  D="$REPO/mitoderm-catalog/site/xlsx-he/scenarios"; mkdir -p "$D"
  cp "$O/final/$N.docx" "$O/final/$N.pdf" "$D/"; ls -la "$D/$N".*
fi
