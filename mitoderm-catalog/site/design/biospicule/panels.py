#!/usr/bin/env python3
"""Extract BIOSPICULE box panels (and bottle labels) from the printer's dieline PDFs.

    python3 panels.py SLUG PDF [--page N] [--label-pdf PDF] [--out DIR] [--geometry FILE] [--dpi 600]

The PDFs themselves are not in the repository (23-29 MB each); only the PNG panels
written to panels/<slug>/ and geometry.json are.  The script

  1. renders the page at 300 dpi (pdftoppm) and finds the thin black fold/cut lines
     of the dieline (long runs of dark pixels, at most 8 px thick, so filled bands and
     text are ignored);
  2. takes the two longest horizontal lines as the top/bottom of the main panel row and
     the vertical lines spanning that row as the fold lines; the cells between them are
     named by LAYOUTS[slug]["cells"] (checked by eye against the drawing);
  3. finds the top flap (and, where the drawing has one, the bottom flap) above/below
     the front panel: the horizontal line at a distance ~D from the panel row;
  4. crops every panel at --dpi with pdftocairo, inset 0.3 mm inside the fold lines so
     no dieline strokes are included, and trims any residual dark border pixels;
  5. writes/merges geometry.json (mm, ratios, scale method, texts per face).

Scale: all drawings are 1:1 (1 mm = 2.8346 pt), verified against the dimension labels
on the 30 ml and 50 ml drawings; the A4 3 ml drawing carries no labels and is assumed
1:1 (see LAYOUTS["micro-boost-10"]["scale_note"]).
"""
import argparse, json, math, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image

PT_PER_MM = 72 / 25.4
DETECT_DPI = 300
INSET_MM = 0.3
HERE = os.path.dirname(os.path.abspath(__file__))

SERUM_CONTENT = {
    'left':  'BIOSPICULE (vertical, reads top-to-bottom) + small text "Micro Spicule Serum formulated with marine spicules ..."',
    'front': 'M monogram; MITODERM / BIOSPICULE SYSTEM; dark-green band {name}; BIOSPICULE SERUM; spicule circle; frame ADVANCED BIOSPICULE TECHNOLOGY; 30ml e 1.0 fl.oz.',
    'right': 'MICRO SPICULE TECHNOLOGY / MADE IN KOREA (vertical, reads bottom-to-top) + 6M PAO icon',
    'back':  'BIOSPICULE {name}: description, Ingredients, How to use, Cautions, Manufactured by: Republic of Korea, Batch No.',
    'top':   'BIOSPICULE / by MITODERM (upright, same orientation as the front; PNG bottom edge is hinged to the front top edge)',
    'bottom': 'blank 35 mm flap (unprinted cream)',
}

LAYOUTS = {
    'cell-renew-1-5': dict(
        pdf='spicule-serum-30ml-boxes-labels.pdf', page=1,
        cells=['left', 'front', 'right', 'back', 'glue'],
        nominal_mm=dict(W=35, D=35, H=110), bottom=True, label='page',
        content={k: v.replace('{name}', 'CELL RENEW 1.5%') for k, v in SERUM_CONTENT.items()},
        scale_note='dimension labels 35 mm x4 / 110 mm / 35 mm on the drawing match the fold-line distances at 1:1 (pt/2.8346)'),
    'cellular-age-defense-2-5': dict(
        pdf='spicule-serum-30ml-boxes-labels.pdf', page=2,
        cells=['left', 'front', 'right', 'back', 'glue'],
        nominal_mm=dict(W=35, D=35, H=110), bottom=True, label='page',
        content={k: v.replace('{name}', 'CELLULAR AGE DEFENSE 2.5%') for k, v in SERUM_CONTENT.items()},
        scale_note='dimension labels 35 mm x4 / 110 mm / 35 mm on the drawing match the fold-line distances at 1:1 (pt/2.8346)'),
    'derma-recovery-cream': dict(
        pdf='derma-recovery-cream-box-50ml.pdf', page=1,
        cells=['glue', 'back', 'left', 'front', 'right'],
        nominal_mm=dict(W=62, D=62, H=85), bottom=False, label='page',
        content={
            'back':  'BIOSPICULE Derma Recovery Cream: description, Ingredients, Cautions, How to use, Manufactured by: Republic of Korea',
            'left':  'BIOSPICULE (vertical, reads top-to-bottom) + "Formulated to help support skin comfort after professional treatments"',
            'front': 'M monogram; MITODERM / BIOSPICULE SYSTEM; olive band DERMA RECOVERY CREAM (gold); SNAIL COLLAGEN; cream swirl; frame "Daily nourishing collagen cream for healthy-looking glow"; 50 ml e 1.69 fl.oz.',
            'right': 'MADE IN KOREA (vertical, reads bottom-to-top) + 6M PAO icon',
            'top':   'BIOSPICULE / by MITODERM (62 mm top face; the rounded tuck above it is not extracted)',
            'bottom': 'crash-lock bottom, unprinted cream (no panel file; use fill_rgb)',
        },
        scale_note='dimension labels 62 mm x4 / 85 mm / 62 mm on the drawing match the fold-line distances at 1:1 (pt/2.8346)'),
    'micro-boost-10': dict(
        pdf='micro-boost-10-box-3ml.pdf', page=1,
        cells=['flap', 'glue', 'back', 'left', 'front', 'right'],
        nominal_mm=None, bottom=True, bottom_extra_inset_mm=1.0, label='separate', label_thr=240,
        content={
            'back':  'MICRO BOOST 10% SPICULE SERUM: Professional cosmetic serum ..., Ingredients, How to use, Cautions, Manufactured by: Republic of Korea, Expiry Date & Batch No.',
            'left':  'MICRO BOOST 10% SPICULE SERUM (vertical, reads top-to-bottom) + "Formulated with marine spicule, helps enhance skin elasticity and radiance."',
            'front': 'M monogram; MITODERM / BIOSPICULE PROFESSIONAL; black band MICRO BOOST 10% (gold); SPICULE SERUM; spicule circle with gold ring; frame Concentrated Spicule System; PROFESSIONAL TREATMENT; 3 ml e 0.10 fl.oz.',
            'right': 'PROFESSIONAL TREATMENT / MADE IN KOREA (vertical, reads bottom-to-top)',
            'top':   'MICRO SPICULE SERUM / BIOSPICULE by MITODERM (top face; a short tuck above it is not extracted)',
            'bottom': 'blank flap (unprinted cream)',
        },
        scale_note=('A4 drawing without dimension labels, assumed 1:1 (pt/2.8346). Evidence: the designer\'s other '
                    'files are exactly 1:1; type sizes match the 30 ml drawings ("3 ml e 0.10 fl.oz." 4.6 pt vs '
                    '"30ml e 1.0 fl.oz." 4.8 pt, side text 7.5 pt, MITODERM wordmark 80 vs 77 pt), at 2:1 the body '
                    'text would print at ~3.5 pt; the 63x34 mm label drawing is 1:1 too. Confidence: medium-high. '
                    'Only W:H and D:H matter for the 3D scene and they do not depend on the scale.')),
}


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def render(pdf, page, dpi, out_base):
    run(['pdftoppm', '-png', '-r', str(dpi), '-f', str(page), '-l', str(page), '-singlefile', pdf, out_base])
    return out_base + '.png'


def thin_lines(mask, axis, min_len, max_thick=8):
    """Thin straight lines in a boolean mask. axis=0: vertical lines (one per column cluster),
    axis=1: horizontal. Returns dicts with pos (px, line centre), start/end (px, along the line)."""
    m = mask if axis == 0 else mask.T
    runs = []
    for i in range(m.shape[1]):
        col = m[:, i]
        if col.sum() < min_len:
            runs.append((0, 0)); continue
        d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
        s = np.where(d == 1)[0]; e = np.where(d == -1)[0]
        k = int(np.argmax(e - s)); runs.append((int(e[k] - s[k]), int(s[k])))
    clusters, cur = [], None
    for i, (L, s) in enumerate(runs):
        if L < min_len:
            continue
        if cur and i - cur['i1'] <= 2:
            cur['i1'] = i; cur['items'].append((L, s))
        else:
            if cur: clusters.append(cur)
            cur = dict(i0=i, i1=i, items=[(L, s)])
    if cur: clusters.append(cur)
    out = []
    for c in clusters:
        if c['i1'] - c['i0'] + 1 > max_thick:
            continue  # a filled band, not a line
        L, s = max(c['items'])
        out.append(dict(pos=(c['i0'] + c['i1']) / 2.0, start=s, end=s + L, length=L))
    return out


def nearest(lines, y, tol):
    c = [l for l in lines if abs(l['pos'] - y) <= tol]
    return min(c, key=lambda l: abs(l['pos'] - y)) if c else None


def crop(pdf, page, dpi, box_pt, out_png):
    """box_pt = (x0, y0, x1, y1) in pt from the page's top-left; crops INSET_MM inside it."""
    k = dpi / 72.0; ins = INSET_MM * PT_PER_MM
    X0 = math.ceil((box_pt[0] + ins) * k); Y0 = math.ceil((box_pt[1] + ins) * k)
    X1 = math.floor((box_pt[2] - ins) * k); Y1 = math.floor((box_pt[3] - ins) * k)
    base = out_png[:-4]
    run(['pdftocairo', '-png', '-r', str(dpi), '-f', str(page), '-l', str(page), '-x', str(X0), '-y', str(Y0),
         '-W', str(X1 - X0), '-H', str(Y1 - Y0), '-singlefile', pdf, base])
    im = Image.open(out_png).convert('RGB')
    a = np.asarray(im)
    # trim residual dieline pixels on the border (never more than 6 px)
    lum = a.min(axis=2)
    l = t = 0; r, b = a.shape[1], a.shape[0]
    def residue(edge, inner):   # a thin stroke: much darker than the print 8 px further in
        fe = (edge < 100).mean(); fi = (inner < 100).mean()
        return fe > 0.1 and fe > 2 * fi + 0.05
    for _ in range(6):
        if residue(lum[t:b, l], lum[t:b, l + 8]): l += 1
        if residue(lum[t:b, r - 1], lum[t:b, r - 9]): r -= 1
        if residue(lum[t, l:r], lum[t + 8, l:r]): t += 1
        if residue(lum[b - 1, l:r], lum[b - 9, l:r]): b -= 1
    if (l, t, r, b) != (0, 0, a.shape[1], a.shape[0]):
        im = im.crop((l, t, r, b))
    im.save(out_png, optimize=True)
    border = np.concatenate([np.asarray(im)[0], np.asarray(im)[-1], np.asarray(im)[:, 0], np.asarray(im)[:, -1]])
    fill = [int(v) for v in np.median(border, axis=0)]
    return im.size, fill


def find_rect(mask, min_len):
    v = thin_lines(mask, 0, min_len); h = thin_lines(mask, 1, min_len)
    if len(v) < 2 or len(h) < 2:
        return None
    return (min(l['pos'] for l in v), min(l['pos'] for l in h), max(l['pos'] for l in v), max(l['pos'] for l in h))


def extract(slug, pdf, page, label_pdf, out_dir, dpi, geometry_file):
    lay = LAYOUTS[slug]
    page = page or lay['page']
    os.makedirs(out_dir, exist_ok=True)
    mm = DETECT_DPI / 25.4          # px per mm at detection resolution
    px2pt = 72.0 / DETECT_DPI
    with tempfile.TemporaryDirectory() as td:
        img = Image.open(render(pdf, page, DETECT_DPI, os.path.join(td, 'p'))).convert('RGB')
        a = np.asarray(img)
        dark = a.max(axis=2) < 120   # black strokes/text; the red dimension lines are excluded (r > 150)
        H, W = dark.shape

        hl = thin_lines(dark, 1, int(25 * mm))
        y_top, y_bot = sorted(l['pos'] for l in sorted(hl, key=lambda l: -l['length'])[:2])
        row_h = y_bot - y_top
        vl = [l for l in thin_lines(dark, 0, int(25 * mm))
              if min(l['end'], y_bot) - max(l['start'], y_top) >= 0.7 * row_h]
        vl.sort(key=lambda l: l['pos'])
        xs = [l['pos'] for l in vl]
        if len(xs) - 1 != len(lay['cells']):
            sys.exit(f'{slug}: expected {len(lay["cells"])} cells, found {len(xs) - 1} fold lines at '
                     f'{[round(x * px2pt, 1) for x in xs]} pt')
        cells = {}
        for name, x0, x1 in zip(lay['cells'], xs[:-1], xs[1:]):
            sub = dark[:, int(x0 + 0.1 * (x1 - x0)):int(x1 - 0.1 * (x1 - x0))]
            hls = thin_lines(sub, 1, int(0.6 * sub.shape[1]))
            t = nearest(hls, y_top, 3 * mm) or dict(pos=y_top)
            b = nearest(hls, y_bot, 3 * mm) or dict(pos=y_bot)
            cells[name] = dict(x0=x0, x1=x1, y0=t['pos'], y1=b['pos'], hlines=hls)
        D_px = np.mean([cells['left']['x1'] - cells['left']['x0'], cells['right']['x1'] - cells['right']['x0']])
        W_px = np.mean([cells['front']['x1'] - cells['front']['x0'], cells['back']['x1'] - cells['back']['x0']])
        f = cells['front']
        H_px = f['y1'] - f['y0']
        boxes = {n: (c['x0'], c['y0'], c['x1'], c['y1']) for n, c in cells.items() if n in ('left', 'front', 'right', 'back')}
        cand = [l for l in f['hlines'] if l['pos'] < f['y0'] and abs((f['y0'] - l['pos']) - D_px) < 0.15 * D_px]
        if not cand:
            sys.exit(f'{slug}: no top-flap fold line ~{D_px * px2pt / PT_PER_MM:.1f} mm above the front panel')
        top = min(cand, key=lambda l: abs((f['y0'] - l['pos']) - D_px))
        boxes['top'] = (f['x0'], top['pos'], f['x1'], f['y0'])
        if lay['bottom']:
            cand = [l for l in f['hlines'] if l['pos'] > f['y1'] and abs((l['pos'] - f['y1']) - D_px) < 0.15 * D_px]
            if not cand:
                sys.exit(f'{slug}: no bottom-flap fold line below the front panel')
            bot = min(cand, key=lambda l: abs((l['pos'] - f['y1']) - D_px))
            # the fold line to the tuck may be notched at the corners: optional extra inset
            boxes['bottom'] = (f['x0'], f['y1'], f['x1'], bot['pos'] - lay.get('bottom_extra_inset_mm', 0) * mm)

        # bottle label
        label = None
        if lay['label'] == 'page':
            xr = int(xs[-1] + 15 * mm); yr = max(0, int(y_top - 10 * mm))
            sub = dark[yr:int(y_bot + 10 * mm), xr:]     # beside the panel row (skips the printer's logo)
            r = find_rect(sub, int(20 * mm))
            if r: label = (pdf, page, (r[0] + xr, r[1] + yr, r[2] + xr, r[3] + yr))
        elif lay['label'] == 'separate' and label_pdf:
            limg = Image.open(render(label_pdf, 1, DETECT_DPI, os.path.join(td, 'l'))).convert('RGB')
            lm = np.asarray(limg).max(axis=2) < lay.get('label_thr', 120)
            r = find_rect(lm, int(20 * mm))
            if r: label = (label_pdf, 1, r)

    def pt(box): return tuple(v * px2pt for v in box)
    def mmv(px): return px * px2pt / PT_PER_MM

    panels = {}
    for name, box in boxes.items():
        out = os.path.join(out_dir, name + '.png')
        size, fill = crop(pdf, page, dpi, pt(box), out)
        panels[name] = dict(file=os.path.relpath(out, HERE), px=list(size),
                            box_pt=[round(v, 2) for v in pt(box)],
                            size_mm=[round(mmv(box[2] - box[0]), 2), round(mmv(box[3] - box[1]), 2)],
                            content=lay['content'].get(name, ''))
        if name == 'front': fill_rgb = fill
    if lay['content'].get('bottom') and 'bottom' not in panels:
        panels['bottom'] = dict(file=None, content=lay['content']['bottom'])
    label_info = None
    if label:
        lpdf, lpage, r = label
        out = os.path.join(out_dir, 'label.png')
        size, _ = crop(lpdf, lpage, dpi, pt(r), out)
        label_info = dict(file=os.path.relpath(out, HERE), px=list(size), pdf=os.path.basename(lpdf), page=lpage,
                          size_mm=[round(mmv(r[2] - r[0]), 2), round(mmv(r[3] - r[1]), 2)])

    meas = dict(W=round(mmv(W_px), 2), D=round(mmv(D_px), 2), H=round(mmv(H_px), 2),
                W_pt=round(W_px * px2pt, 2), D_pt=round(D_px * px2pt, 2), H_pt=round(H_px * px2pt, 2),
                left_mm=round(mmv(cells['left']['x1'] - cells['left']['x0']), 2),
                right_mm=round(mmv(cells['right']['x1'] - cells['right']['x0']), 2),
                side_H_mm=round(mmv(cells['left']['y1'] - cells['left']['y0']), 2),
                glue_flap_mm=round(mmv(cells['glue']['x1'] - cells['glue']['x0']), 2) if 'glue' in cells else None)
    nom = lay['nominal_mm']
    if nom:
        for k in 'WDH':
            if abs(meas[k] - nom[k]) > 0.5:
                sys.exit(f'{slug}: measured {k}={meas[k]} mm differs from the drawing label {nom[k]} mm')
        dims = dict(nom); method = 'dimension-labels'
    else:
        dims = {k: round(meas[k] * 2) / 2 for k in 'WDH'}; method = 'assumed-1:1'
    entry = dict(
        W_mm=dims['W'], D_mm=dims['D'], H_mm=dims['H'],
        W_over_H=round(dims['W'] / dims['H'], 4), D_over_H=round(dims['D'] / dims['H'], 4),
        source=dict(pdf=os.path.basename(pdf), page=page, page_size_pt=None),
        scale=dict(pt_per_mm=round(PT_PER_MM, 4), method=method, note=lay['scale_note'],
                   measured_mm=meas),
        dieline_cells_left_to_right=lay['cells'],
        face_mapping='print side up: the cell left of "front" is the LEFT face (-W/2), right of it the RIGHT face (+W/2); '
                     'top/bottom flaps are hinged to the front panel',
        fill_rgb=fill_rgb, panels=panels, label=label_info)
    try:
        info = subprocess.run(['pdfinfo', '-f', str(page), '-l', str(page), pdf], capture_output=True, text=True).stdout
        entry['source']['page_size_pt'] = [l.split(':', 1)[1].strip() for l in info.splitlines() if 'Page' in l and 'size' in l][0]
    except Exception:
        pass
    geo = {}
    if os.path.exists(geometry_file):
        with open(geometry_file) as fh: geo = json.load(fh)
    geo.setdefault('units', 'mm; ratios are W/H and D/H as used by mkBox(front, side, hidden, W, D, ...)')
    geo.setdefault('generated_by', 'site/design/biospicule/panels.py')
    geo.setdefault('boxes', {})[slug] = entry
    with open(geometry_file, 'w') as fh:
        json.dump(geo, fh, indent=1, ensure_ascii=False)
    print(json.dumps({slug: dict(W=dims['W'], D=dims['D'], H=dims['H'], measured=meas,
                                 panels={k: v.get('px') for k, v in panels.items()}, label=label_info)}, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('slug', choices=sorted(LAYOUTS))
    ap.add_argument('pdf')
    ap.add_argument('--page', type=int)
    ap.add_argument('--label-pdf', help='separate label drawing (micro-boost-10)')
    ap.add_argument('--out', help='output directory (default panels/<slug> next to this script)')
    ap.add_argument('--geometry', default=os.path.join(HERE, 'geometry.json'))
    ap.add_argument('--dpi', type=int, default=600)
    a = ap.parse_args()
    extract(a.slug, a.pdf, a.page, a.label_pdf, a.out or os.path.join(HERE, 'panels', a.slug), a.dpi, a.geometry)
