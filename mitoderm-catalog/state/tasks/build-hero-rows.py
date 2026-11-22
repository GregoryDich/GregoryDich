#!/usr/bin/env python3
"""The home banner for large screens: 13 products in two even rows on an empty stage.

Why: the owner (22/11) - on Full HD and larger screens the banner must not have V-TECH in the centre with the
other products around it; the products stand in two even rows, as evenly as on small screens. The old picture is
1672 px wide and is shown as a box with visible edges on screens wider than 1800 px.

How: the stage (plate) is generated WITHOUT any product. Every product is the customer's real cut-out - a model
never draws a pack. V-TECH SYSTEM is not baked in: on the page its box is drawn from the first frame of its film
(the "canonical pack" in codex-site/mitoderm/pilot/CollectionHero.tsx), so here it only gets its slot, its
shadow and its place in the map. The edges of the picture fall into the page colour, so it has no visible box on
any screen.

usage: build-hero-rows.py <plate.png> <out dir> [window=0.156,0.75] [row1=0.50] [row2=0.80] [base1=520] [base2=540]
                          [span=0.86] [vtech_preview=<box.png>]
  window       the part of the plate that becomes the picture: its top and its height as fractions of the plate's
               height (the width is cut around the middle to keep 16:9). A smaller window brings the camera closer:
               the steps move apart and the products can be larger.
  row1, row2   the lines the products stand on, as fractions of the picture height (the stage of 22/11 has its step
               surfaces at 51.0-54.4 % and 72.8-77.5 % of the plate's height; with the default window the products
               stand at 50 % and 80 % of the picture)
  base1, base2 the height of a tall product in each row, px in the 3840x2160 master
  span         the part of the width a row takes
  vtech_preview  a cut-out of the V-TECH box to bake into preview.jpg only (never into the site pictures)
writes: collection-rows-desktop-{3840,2560,1920}.webp, pack-<slug>.webp, hero-rows-map.json, preview.jpg
needs ImageMagick
"""
import json
import os
import subprocess
import sys
import tempfile

W, H = 3840, 2160
PAGE = "#0b0b0b"
HERE = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.normpath(os.path.join(HERE, "..", ".."))
ASSETS = os.path.join(CAT, "codex-site", "public", "assets")
PRINT = os.path.join(CAT, "protocols", "print", "img")
SOURCE = {
    "exo-nad": os.path.join(PRINT, "exo-nad.webp"),
    "exocell-mask": os.path.join(PRINT, "exocell-mask.webp"),
    "exotech-gel": os.path.join(ASSETS, "products", "exotech-gel.webp"),
    "exosignal-hair": os.path.join(ASSETS, "products", "exosignal-hair.webp"),
    "exosignal-spray": os.path.join(CAT, "sources", "exosignal-spray-cutout-upscaled.png"),
    "mitotech-cell-booster": os.path.join(ASSETS, "products", "mitotech-cell-booster.webp"),
    "cell-renew-1-5": os.path.join(ASSETS, "products", "cell-renew-1-5.webp"),
    "cellular-age-defense-2-5": os.path.join(ASSETS, "products", "cellular-age-defense-2-5.webp"),
    "micro-boost-10": os.path.join(ASSETS, "products", "micro-boost-10.webp"),
    "derma-recovery-cream": os.path.join(ASSETS, "products", "derma-recovery-cream.webp"),
    "mitoscan": os.path.join(PRINT, "mitoscan.webp"),
    "mitopen": os.path.join(ASSETS, "products", "mitopen.webp"),
}
VTECH_ASPECT = 466 / 1014      # the box in the first frame of the V-TECH film (pilot/vtech-entry.ts)
PEN_TURN = 30                  # the pen leans: the clear end down on a small disc, the cap up to the right
# Left to right. In a right-to-left page the first product of a row is the right one: the order of the site list.
# The number is the product's height as a part of the row's base height: wide boxes are lower than tall ones.
ROW1 = [("exosignal-spray", 0.96), ("exosignal-hair", 0.70), ("exotech-gel", 0.86), ("exocell-mask", 0.80),
        ("exo-nad", 0.70), ("v-tech-system", 1.00)]
ROW2 = [("mitoscan", 0.74), ("mitopen", 0.92), ("mitotech-cell-booster", 0.72), ("derma-recovery-cream", 0.86),
        ("cellular-age-defense-2-5", 1.00), ("cell-renew-1-5", 1.00), ("micro-boost-10", 1.00)]


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def size_of(path):
    out = subprocess.run(["identify", "-format", "%w %h", path], capture_output=True, text=True, check=True).stdout
    return tuple(int(v) for v in out.split())


def prepare(slug, work):
    """the trimmed cut-out of a product (the pen is turned first)"""
    out = os.path.join(work, slug + "-src.png")
    turn = ["-rotate", PEN_TURN] if slug == "mitopen" else []
    run("convert", SOURCE[slug], "-background", "none", *turn, "-trim", "+repage", out)
    return out


def layout(row, base, line, span, work):
    """[(slug, source or None, x, y, w, h)] - equal gaps between the products, all standing on one line"""
    items = []
    for slug, factor in row:
        h = round(base * factor)
        if slug == "v-tech-system":
            items.append([slug, None, round(h * VTECH_ASPECT), h])
        else:
            src = prepare(slug, work)
            sw, sh = size_of(src)
            items.append([slug, src, round(h * sw / sh), h])
    total = sum(item[2] for item in items)
    gap = (W * span - total) / (len(items) - 1)
    x = W * (1 - span) / 2
    placed = []
    for slug, src, w, h in items:
        placed.append((slug, src, round(x), round(H * line) - h, w, h))
        x += w + gap
    return placed, gap


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    plate, out_dir = argv[:2]
    options = dict(item.split("=", 1) for item in argv[2:])
    row1, row2 = float(options.get("row1", 0.50)), float(options.get("row2", 0.80))
    base1, base2 = float(options.get("base1", 520)), float(options.get("base2", 540))
    span = float(options.get("span", 0.86))
    window_top, window_height = (float(v) for v in options.get("window", "0.156,0.75").split(","))
    os.makedirs(out_dir, exist_ok=True)
    work = tempfile.mkdtemp(prefix="hero-")
    path = lambda name: os.path.join(work, name)

    top, gap1 = layout(ROW1, base1, row1, span, work)
    bottom, gap2 = layout(ROW2, base2, row2, span, work)
    placed = top + bottom

    # the stage, the soft shadows where the products stand, then the products
    plate_w, plate_h = size_of(plate)
    keep_h = round(plate_h * window_height)
    keep_w = min(plate_w, round(keep_h * W / H))
    run("convert", plate, "-crop", "%dx%d+%d+%d" % (keep_w, keep_h, (plate_w - keep_w) // 2, round(plate_h * window_top)),
        "+repage", "-filter", "Lanczos", "-resize", "%dx%d!" % (W, H), path("stage.png"))
    shadow = ["convert", "-size", "%dx%d" % (W, H), "xc:none", "-fill", "black"]
    for slug, src, x, y, w, h in placed:
        cx, base = x + w / 2, y + h
        shadow += ["-draw", "ellipse %.0f,%.0f %.0f,%.0f 0,360" % (cx, base + 4, w * 0.54, 20)]
    run(*shadow, "-channel", "A", "-blur", "0x16", "-evaluate", "multiply", "0.62", "+channel", path("shadow.png"))
    command = ["convert", path("stage.png"), path("shadow.png"), "-composite"]
    pen = next(item for item in placed if item[0] == "mitopen")
    # a small bronze disc under the clear end of the pen (the pen's lower left)
    disc_x, disc_y = pen[2] + pen[4] * 0.16, pen[3] + pen[5] + 2
    command += ["(", "-size", "%dx%d" % (W, H), "xc:none", "-fill", "#5d4526", "-draw",
                "ellipse %.0f,%.0f 86,17 0,360" % (disc_x, disc_y), "-fill", "#a07a41", "-draw",
                "ellipse %.0f,%.0f 86,13 0,360" % (disc_x, disc_y - 5), "-blur", "0x1.2", ")", "-composite"]
    for slug, src, x, y, w, h in placed:
        if src:
            command += ["(", src, "-resize", "%dx%d!" % (w, h), ")", "-geometry", "+%d+%d" % (x, y), "-composite"]
    run(*command, path("with-products.png"))

    # the edges fall into the page colour: no visible box on any screen
    side, head, foot = round(W * 0.06), round(H * 0.07), round(H * 0.035)
    run("convert", "-size", "%dx%d" % (H, side), "gradient:white-black", "-rotate", "-90", path("left.png"))
    run("convert", "-size", "%dx%d" % (W, head), "gradient:white-black", path("top.png"))
    run("convert", "-size", "%dx%d" % (W, H), "xc:black",
        path("left.png"), "-geometry", "+0+0", "-compose", "Lighten", "-composite",
        "(", path("left.png"), "-flop", ")", "-geometry", "+%d+0" % (W - side), "-compose", "Lighten", "-composite",
        path("top.png"), "-geometry", "+0+0", "-compose", "Lighten", "-composite",
        "(", path("top.png"), "-flip", "-resize", "%dx%d!" % (W, foot), ")", "-geometry", "+0+%d" % (H - foot),
        "-compose", "Lighten", "-composite", path("edge-mask.png"))
    run("convert", path("with-products.png"), "(", "-size", "%dx%d" % (W, H), "xc:" + PAGE, path("edge-mask.png"),
        "-alpha", "off", "-compose", "CopyOpacity", "-composite", ")", "-compose", "Over", "-composite", path("master.png"))

    for width in (3840, 2560, 1920):
        run("convert", path("master.png"), "-resize", "%dx" % width, "-quality", "82", "-define", "webp:method=6",
            os.path.join(out_dir, "collection-rows-desktop-%d.webp" % width))

    # the separate packs: the picture that lifts off the banner when a product is chosen
    spots = {}
    for slug, src, x, y, w, h in placed:
        spots[slug] = {"x": x, "y": y, "width": w, "height": h}
        if src:
            sw, sh = size_of(src)
            big = min(sh, round(h * 1.8))
            run("convert", src, "-resize", "x%d" % big, "-quality", "90", "-define", "webp:alpha-quality=95",
                os.path.join(out_dir, "pack-%s.webp" % slug))
    json.dump({"size": {"width": W, "height": H}, "rows": {"first": row1, "second": row2},
               "order": [item[0] for item in placed], "spots": spots},
              open(os.path.join(out_dir, "hero-rows-map.json"), "w"), indent=1)

    preview = [path("master.png")]
    if "vtech_preview" in options:
        slug, src, x, y, w, h = next(item for item in placed if item[0] == "v-tech-system")
        preview = [path("master.png"), "(", options["vtech_preview"], "-resize", "%dx%d!" % (w, h), ")", "-geometry",
                   "+%d+%d" % (x, y), "-composite"]
    run("convert", *preview, "-resize", "1920x", "-quality", "88", os.path.join(out_dir, "preview.jpg"))
    print("rows: gaps %.0f and %.0f px; products %d; wrote %s" % (gap1, gap2, len(placed), out_dir))
    for name in os.listdir(work):
        os.remove(os.path.join(work, name))
    os.rmdir(work)


if __name__ == "__main__":
    main(sys.argv[1:])
