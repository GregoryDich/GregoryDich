# Post-processing of the Chromium PDFs (called by build-print.mjs; needs PyMuPDF: pip install pymupdf).
# 1. Chromium rounds the page up to 595.92 x 420.96 pt, leaving a white hairline on the right and bottom
#    edges. The page box is cut back to the layout, 794 x 561 px = 595.5 x 420.75 pt.
# 2. A press copy gets 3 mm bleed: the page stays vector inside the trim, and every edge is extended
#    outward by its own outermost pixels (a 1 px strip of a 600 dpi render, stretched over the bleed).
#    TrimBox/BleedBox are set for the printer.
#    Stretching the vector page itself instead makes renderers scale every image on the page 17x;
#    MuPDF refuses that ("overly large image"), so a RIP could too.
import io
import sys
import numpy as np
import pymupdf
from PIL import Image

W, H = 595.5, 420.75          # 794 x 561 px
B = 3 / 25.4 * 72             # 3 mm bleed in pt
DPI = 600


def trim(path):
    doc = pymupdf.open(path)
    for page in doc:
        mb = page.mediabox  # PDF coordinates, origin bottom-left; the layout hangs from the top-left corner
        page.set_mediabox(pymupdf.Rect(0, mb.y1 - H, W, mb.y1))
    doc.save(path, incremental=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    doc.close()


def png(arr):
    buf = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(arr)).save(buf, 'PNG')
    return buf.getvalue()


def press(src_path, out_path):
    src = pymupdf.open(src_path)
    out = pymupdf.open()
    for pno, sp in enumerate(src):
        pix = sp.get_pixmap(dpi=DPI, alpha=False)
        px = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
        page = out.new_page(width=W + 2 * B, height=H + 2 * B)
        page.show_pdf_page(pymupdf.Rect(B, B, B + W, B + H), src, pno)
        # second pixel from each edge: the outermost one can carry anti-aliasing against the paper
        L, R, T, Bo = px[:, 1:2], px[:, -2:-1], px[1:2, :], px[-2:-1, :]
        strips = [
            ((0, B, B, B + H), L), ((B + W, B, W + 2 * B, B + H), R),
            ((B, 0, B + W, B), T), ((B, B + H, B + W, H + 2 * B), Bo),
            ((0, 0, B, B), px[1:2, 1:2]), ((B + W, 0, W + 2 * B, B), px[1:2, -2:-1]),
            ((0, B + H, B, H + 2 * B), px[-2:-1, 1:2]), ((B + W, B + H, W + 2 * B, H + 2 * B), px[-2:-1, -2:-1]),
        ]
        for rect, arr in strips:
            page.insert_image(pymupdf.Rect(rect), stream=png(arr), keep_proportion=False)
        page.set_trimbox(pymupdf.Rect(B, B, B + W, B + H))
        page.set_bleedbox(page.mediabox)
    out.set_metadata(src.metadata)
    out.save(out_path, garbage=3, deflate=True)


if __name__ == '__main__':
    for path in sys.argv[1:]:
        trim(path)
        press(path, path[:-4] + '-press.pdf')
