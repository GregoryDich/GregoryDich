#!/bin/bash
# Static copy of the cinematic site for a test link (no server, no lead form, no database).
# Usage: static-snapshot.sh [out dir=mitoderm-catalog/preview-site/site] [base url=http://127.0.0.1:8787]
# Needs the built site running locally (codex-site: pnpm build && pnpm start).
# Writes into <out dir>:
#   index.html, catalog/index.html, privacy/index.html, products/<slug>/index.html   the rendered pages
#   404.html                                                                         the not-found page
#   _next/                                                                           the built scripts and styles
#   robots.txt                                                                       closes the test copy to search robots
# The images and fonts are NOT copied: they are codex-site/public, which the deploy step lays under the same root.
# Films are loaded from their own addresses (mitoderm/media-urls.json), so they work from any host.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)            # mitoderm-catalog
OUT=${1:-$ROOT/preview-site/site}
BASE=${2:-http://127.0.0.1:8787}
APP=$ROOT/codex-site
[ -d "$APP/dist/client/_next" ] || { echo "no build: run pnpm build in codex-site"; exit 1; }
SLUGS=$(python3 - "$APP/production/page-bible/REGISTRY.json" <<'EOF'
import json, sys
seen = []
def walk(o):
    if isinstance(o, dict):
        s = o.get('slug')
        if isinstance(s, str) and s not in seen: seen.append(s)
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(json.load(open(sys.argv[1])))
print(' '.join(seen))
EOF
)
rm -rf "$OUT"; mkdir -p "$OUT"
cp -r "$APP/dist/client/_next" "$OUT/_next"
fetch() {  # <route> <file> <expected status>
  mkdir -p "$(dirname "$2")"
  code=$(curl -s --max-time 60 -o "$2" -w '%{http_code}' "$BASE$1")
  [ "$code" = "$3" ] || { echo "FAIL $1 -> $code (expected $3)"; exit 1; }
  echo "$1 $code $(wc -c < "$2") bytes"
}
fetch / "$OUT/index.html" 200
fetch /catalog "$OUT/catalog/index.html" 200
fetch /privacy "$OUT/privacy/index.html" 200
for s in $SLUGS; do fetch "/products/$s" "$OUT/products/$s/index.html" 200; done
fetch /no-such-page "$OUT/404.html" 404
# A test copy must stay out of search results: its pages name the live site as their canonical address, and this keeps
# robots out altogether. The live site serves its own robots.txt and sitemap.xml (codex-site/app/robots.ts, sitemap.ts).
printf 'User-agent: *\nDisallow: /\n' > "$OUT/robots.txt"
echo "pages: $(find "$OUT" -name '*.html' | wc -l); size: $(du -sh "$OUT" | cut -f1)"
