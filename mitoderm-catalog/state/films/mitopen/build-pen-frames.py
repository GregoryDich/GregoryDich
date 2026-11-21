#!/usr/bin/env python3
"""MITOPEN: frames with the REAL pen, built without drawing the device by a model.

The clinic plate is generated WITHOUT any device (a folded white towel lies on the table). The real cut-out photo of
the pen (codex-site/public/assets/products/mitopen.webp, 466x1521) is turned to lie on the towel in a side view -
77.44 degrees clockwise, which also makes the word MITOPEN read left to right - and placed over the plate. The pen
sinks a few pixels into the towel: the towel's own bright pixels are put back in front of its lowest sliver.

  K0  the pen sharp on the towel, the room and the people softly out of focus
  K1  the people sharp, the pen and the near table softly out of focus (the same pen in the same place)
  K2  the camera close to the pen: the plate enlarged around it, the pen taken from the full-size photo, so it
      stays crisp (zoom=2); a sequence of zooms is a free camera move

usage: build-pen-frames.py <plate.png> <pen cut-out> <out dir> [zoom=Z] [sequence=Z0,Z1,COUNT] [size=WxH]
  no option            K0.png and K1.png
  zoom=2               K2.png (any other zoom: zoom-<Z>.png)
  sequence=1,2,54      a camera move as frames z000.png ... z053.png: the zoom goes from Z0 to Z1, eased at both ends
  size=1912x1080       the size of the frames (default 2688x1520, the size of the plate)
needs ImageMagick
"""
import os
import subprocess
import sys
import tempfile

PLATE = (2688, 1520)       # the plate; every measure below is in its pixels
TURN = 77.44               # degrees clockwise: the pen's axis becomes horizontal (measured on the cut-out)
LENGTH = 470               # the pen's length in the wide frame (about three quarters of the towel)
LEFT, REST = 222, 1353     # the pen's left end and its lowest line: 6 px below the towel's top
TOWEL = (140, 1330, 640, 130)   # the towel (left, top, width, height): its bright pixels hide the pen's lowest sliver
FOCUS_LINE = (1296, 1334)  # above the first row the plate is far (soft when the focus is on the pen), below the second near


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def size_of(path):
    return tuple(map(int, subprocess.run(["identify", "-format", "%w %h", path], capture_output=True, text=True,
                                         check=True).stdout.split()))


def soften(source, sigma, target, geometry):
    """a gaussian blur; a strong one is made on a smaller copy (same look, much faster)"""
    if sigma < 0.05:
        run("convert", source, target)
    elif sigma < 6:
        run("convert", source, "-blur", "0x%.2f" % sigma, target)
    else:
        run("convert", source, "-resize", "25%", "-blur", "0x%.2f" % (sigma / 4), "-resize", geometry + "!", target)


def prepare(plate, cutout, work):
    """what does not depend on the zoom: the pen lying, the towel as a mask"""
    path = lambda name: os.path.join(work, name)
    run("convert", cutout, "-background", "none", "-rotate", TURN, "-trim", "+repage", path("pen.png"))
    left, top, t_w, t_h = TOWEL
    run("convert", "-size", "%dx%d" % PLATE, "xc:black",
        "(", plate, "-crop", "%dx%d+%d+%d" % (t_w, t_h, left, top), "+repage", "-colorspace", "Gray",
        "-threshold", "89%", ")", "-geometry", "+%d+%d" % (left, top), "-composite", path("towel-plate.png"))


def build(plate, work, out_dir, out_size, zoom, frames):
    """frames: [(file name, far blur, near blur, pen blur)] - blurs in plate pixels at zoom 1"""
    path = lambda name: os.path.join(work, name)
    width, height = out_size
    geometry = "%dx%d" % out_size
    g = width / PLATE[0]
    pen_w, pen_h = size_of(path("pen.png"))
    scale = LENGTH / pen_w

    # the window of the plate that the camera sees at this zoom: it keeps the pen where a closer camera would see it
    view_w, view_h = PLATE[0] / zoom, PLATE[1] / zoom
    centre_x, centre_y = LEFT + LENGTH / 2, REST - pen_h * scale / 2
    x0 = min(max(centre_x - view_w / 2, 0), PLATE[0] - view_w)
    y0 = min(max(centre_y - view_h * 0.58, 0), PLATE[1] - view_h)
    crop = "%dx%d+%d+%d" % (round(view_w), round(view_h), round(x0), round(y0))
    sharpen = ["-unsharp", "0x%.1f+0.6+0" % (1.2 * zoom * g)] if zoom > 1.01 else []   # an enlarged plate is soft
    run("convert", plate, "-crop", crop, "+repage", "-resize", geometry + "!", *sharpen, path("plate.png"))
    run("convert", path("towel-plate.png"), "-crop", crop, "+repage", "-resize", geometry + "!", path("towel.png"))

    k = zoom * scale * g
    pen_x, pen_bottom = (LEFT - x0) * zoom * g, (REST - y0) * zoom * g
    pen_y = pen_bottom - pen_h * k
    far, near = ((v - y0) * zoom * g for v in FOCUS_LINE)
    run("convert", "-size", "%dx%d" % (width, max(1, round(near - far))), "gradient:white-black", path("ramp.png"))
    run("convert", "-size", geometry, "xc:black",
        "(", "-size", "%dx%d" % (width, max(1, round(far))), "xc:white", ")", "-geometry", "+0+0", "-composite",
        path("ramp.png"), "-geometry", "+0+%d" % round(far), "-composite", path("far.png"))   # white = far from the pen
    run("convert", path("pen.png"), "-resize", "%dx%d!" % (round(pen_w * k), round(pen_h * k)), path("pen-k.png"))

    for name, far_blur, near_blur, pen_blur in frames:
        far_blur, near_blur, pen_blur = far_blur * zoom * g, near_blur * zoom * g, pen_blur * zoom * g
        soften(path("plate.png"), far_blur, path("a.png"), geometry)
        soften(path("plate.png"), near_blur, path("b.png"), geometry)
        run("convert", path("b.png"), path("a.png"), path("far.png"), "-composite", path("base.png"))
        # a soft darkening where the pen lies on the towel (only on the towel itself; under the pen's thin parts
        # there is air, and a shadow there would hang in it)
        run("convert", path("pen-k.png"), "-alpha", "extract", "-blur", "0x%.1f" % (4 * zoom * g + pen_blur), path("sh.png"))
        run("convert", "-size", geometry, "xc:black", path("sh.png"), "-geometry",
            "+%d+%d" % (round(pen_x), round(pen_y + 9 * zoom * g)), "-composite", path("towel.png"),
            "-compose", "Multiply", "-composite", "-evaluate", "multiply", "0.30", path("shm.png"))
        run("convert", path("base.png"), "(", "-size", geometry, "xc:#4a3a2c", path("shm.png"), "-alpha", "off",
            "-compose", "CopyOpacity", "-composite", ")", "-compose", "Over", "-composite", path("shadowed.png"))
        pen = path("pen-k.png")
        if pen_blur:
            run("convert", pen, "-channel", "RGBA", "-blur", "0x%.1f" % pen_blur, path("pen-soft.png"))
            pen = path("pen-soft.png")
        run("convert", path("shadowed.png"), pen, "-geometry", "+%d+%d" % (round(pen_x), round(pen_y)),
            "-compose", "Over", "-composite", path("with-pen.png"))
        # the towel in front of the pen's lowest sliver
        run("convert", path("towel.png"), "-blur", "0x%.1f" % (0.8 * zoom * g + pen_blur / 2), path("towel-soft.png"))
        run("convert", path("with-pen.png"), path("shadowed.png"), path("towel-soft.png"), "-composite",
            os.path.join(out_dir, name))
    return round(pen_x), round(pen_y), round(pen_w * k), round(pen_h * k)


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    plate, cutout, out_dir = argv[:3]
    options = dict(item.split("=", 1) for item in argv[3:])
    out_size = tuple(int(v) for v in options["size"].split("x")) if "size" in options else PLATE
    os.makedirs(out_dir, exist_ok=True)
    work = tempfile.mkdtemp(prefix="pen-")
    prepare(plate, cutout, work)
    if "sequence" in options:
        first, last, count = options["sequence"].split(",")
        first, last, count = float(first), float(last), int(count)
        for index in range(count):
            step = index / (count - 1)
            eased = step * step * (3 - 2 * step)
            build(plate, work, out_dir, out_size, first * (last / first) ** eased, [("z%03d.png" % index, 9, 0, 0)])
        print("built %d frames: zoom %.2f -> %.2f" % (count, first, last))
    else:
        zoom = float(options.get("zoom", 1))
        if zoom > 1.01:
            name = "K2.png" if abs(zoom - 2) < 0.01 else "zoom-%.2f.png" % zoom
            print("built", name, "pen at %d,%d size %dx%d" % build(plate, work, out_dir, out_size, zoom, [(name, 9, 0, 0)]))
        else:
            place = build(plate, work, out_dir, out_size, 1.0, [("K0.png", 9, 0, 0), ("K1.png", 0, 4, 6)])
            print("built K0.png, K1.png: pen at %d,%d size %dx%d" % place)
    for name in os.listdir(work):
        os.remove(os.path.join(work, name))
    os.rmdir(work)


if __name__ == "__main__":
    main(sys.argv[1:])
