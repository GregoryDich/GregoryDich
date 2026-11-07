# Checks on the built v3 pair. Usage: python3 -I verify.py file.docx file.pdf pages.json file.docx.manifest.json
#  1. Cyrillic = 0 in the docx XML and in the PDF text
#  2. page count; TOC numbers on page 2 == start pages from the mark pass (in TOC order)
#  3. for EVERY printed source file: each word token of the .md is present on that chapter's page range (missing = 0)
#  4. no word outside the printable area (40 pt left/right, 20 pt top/bottom)
# Exit code 1 if any check fails.
import sys, zipfile, re, subprocess, json, collections, os
import xml.etree.ElementTree as ET
docx, pdf, pj, mf = sys.argv[1:5]
run = lambda *a: subprocess.run(a, capture_output=True, text=True).stdout
ok = True
z = zipfile.ZipFile(docx)
cx = sum(sum(1 for ch in z.read(n).decode('utf-8', 'replace') if 'Ѐ' <= ch <= 'ӿ') for n in z.namelist() if n.endswith(('.xml', '.rels')))
txt = run('pdftotext', pdf, '-'); cp = sum(1 for ch in txt if 'Ѐ' <= ch <= 'ӿ')
n = int(re.search(r'Pages:\s+(\d+)', run('pdfinfo', pdf)).group(1))
print('cyrillic docx-xml', cx, 'pdf-text', cp, '| pages', n)
ok &= cx == 0 and cp == 0
pages = json.load(open(pj)); man = json.load(open(mf))
toc = run('pdftotext', '-f', '2', '-l', '2', '-layout', pdf, '-')
nums = [int(m) for m in re.findall(r'^\s*(\d+)\.{5,}', toc, flags=re.M)]
starts = [pages.get(e['bm'], 0) for e in man['toc']]
print('toc numbers', nums, '== starts' if nums == starts else '!= starts %s' % starts)
ok &= nums == starts
if man['missing']: print('not printed (source missing):', ', '.join(man['missing']))
# tokens split at script changes (Hebrew | Latin/digits): pdftotext reorders mixed runs like «ד8» around bidi marks
tok = lambda s: re.findall(r'[\u05D0-\u05EA\uFB1D-\uFB4F׳״]+|[^\W\u05D0-\u05EA\uFB1D-\uFB4F]+', s)
ents = man['toc']; total_miss = 0
for i, e in enumerate(ents):
    if not e['slug']: continue
    first = pages[e['bm']]
    last = (pages[ents[i + 1]['bm']] - 1) if i + 1 < len(ents) else n
    md = open(os.path.join(man['src'], e['slug'] + '.md'), encoding='utf-8').read().replace('**', '').replace('`', '')
    exp = collections.Counter(tok(md))
    got = collections.Counter(tok(run('pdftotext', '-f', str(first), '-l', str(last), pdf, '-')))
    miss = {w: (c, got.get(w, 0)) for w, c in exp.items() if got.get(w, 0) < c}
    total_miss += len(miss)
    print('%-26s pages %3d-%3d: source tokens %5d, missing %d %s' % (e['slug'], first, last, sum(exp.values()), len(miss), list(miss.items())[:8]))
ok &= total_miss == 0
x = re.sub(r'<!DOCTYPE[^>]*>', '', run('pdftotext', '-bbox', pdf, '-')).replace('xmlns="http://www.w3.org/1999/xhtml"', '')
bad = []
for pi, page in enumerate(ET.fromstring(x).iter('page'), 1):
    W_, H_ = float(page.get('width')), float(page.get('height'))
    for w in page.iter('word'):
        x0, y0, x1, y1 = (float(w.get(k)) for k in ('xMin', 'yMin', 'xMax', 'yMax'))
        if x0 < 40 or x1 > W_ - 40 or y0 < 20 or y1 > H_ - 20: bad.append((pi, round(x0), round(x1), w.text))
print('words outside the printable area', len(bad), bad[:20])
ok &= not bad
print('VERIFY', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
