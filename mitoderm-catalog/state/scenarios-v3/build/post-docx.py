"""Patch a docx-js output: RTL (w:bidi) as the document default and in Heading 1-3 / TOC 1 (styles.xml);
unique bookmark ids and schema order of paragraph borders (document.xml).
Usage: python3 post-docx.py file.docx   (in place)"""
import re
import shutil
import sys
import zipfile

path = sys.argv[1]
tmp = path + '.tmp'


def add_bidi(ppr_xml):
    if '<w:bidi/>' in ppr_xml:
        return ppr_xml
    for tag in ('<w:spacing', '<w:ind', '<w:jc', '<w:outlineLvl'):
        i = ppr_xml.find(tag)
        if i >= 0:
            return ppr_xml[:i] + '<w:bidi/>' + ppr_xml[i:]
    return ppr_xml.replace('</w:pPr>', '<w:bidi/></w:pPr>')


def patch_styles(xml):
    xml = re.sub(r'(<w:pPrDefault><w:pPr>.*?</w:pPr>)', lambda m: add_bidi(m.group(1)), xml, count=1, flags=re.S)
    for sid in ('Heading1', 'Heading2', 'Heading3', 'TOC1'):
        pat = r'(<w:style [^>]*w:styleId="%s".*?)(<w:pPr>.*?</w:pPr>)' % sid
        xml, n = re.subn(pat, lambda m: m.group(1) + add_bidi(m.group(2)), xml, count=1, flags=re.S)
        if n == 0:
            raise SystemExit('style %s has no pPr' % sid)
    return xml


BDR_ORDER = ['top', 'left', 'bottom', 'right', 'between', 'bar']


def patch_document(xml):
    def reorder(m):
        kids = re.findall(r'<w:(\w+) [^>]*/>', m.group(1))
        parts = dict(zip(kids, re.findall(r'<w:\w+ [^>]*/>', m.group(1))))
        return '<w:pBdr>' + ''.join(parts[k] for k in BDR_ORDER if k in parts) + '</w:pBdr>'
    xml = re.sub(r'<w:pBdr>(.*?)</w:pBdr>', reorder, xml)
    counter = [0]

    def bm(m):
        if m.group(1) == 'Start':
            counter[0] += 1
        return '<w:bookmark%s%s w:id="%d"%s/>' % (m.group(1), m.group(2), counter[0], m.group(3))
    return re.sub(r'<w:bookmark(Start|End)([^>]*?) w:id="\d+"([^>]*)/>', bm, xml)


with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == 'word/styles.xml':
            data = patch_styles(data.decode('utf-8')).encode('utf-8')
        elif item.filename == 'word/document.xml':
            data = patch_document(data.decode('utf-8')).encode('utf-8')
        zout.writestr(item, data)
shutil.move(tmp, path)
print('patched', path)
