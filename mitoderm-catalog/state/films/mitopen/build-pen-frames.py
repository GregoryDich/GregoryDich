#!/usr/bin/env python3
"""MITOPEN: frames with the REAL pen, built without drawing the device by a model.

The clinic plate is generated WITHOUT any device (a folded white towel lies on the table). The real cut-out photo of
the pen (codex-site/public/assets/products/mitopen.webp, 466x1521) is turned to lie on the towel in a side view -
77.44 degrees clockwise, which also makes the word MITOPEN read left to right - and placed over the plate:

  K0  the pen sharp on the towel, the room and the people softly out of focus
  K1  the people sharp, the pen and the near table softly out of focus (the same pen in the same place)
  K2  the camera close to the pen: the plate enlarged around it, the pen taken from the full-size photo, so it
      stays crisp (pass zoom=2); any zoom between 1 and 2 gives a frame of a free camera move

usage: build-pen-frames.py <plate.png> <pen cut-out> <out dir> [zoom=Z]     needs ImageMagick; frames are 2688x1520
"""
import os
import subprocess
import sys
import tempfile

FRAME = (2688, 1520)
TURN = 77.44               # degrees clockwise: the pen's axis becomes horizontal (measured on the cut-out)
LENGTH = 470               # the pen's length in the wide frame, px (about three quarters of the towel)
LEFT, REST = 222, 1353     # the pen's left end and its lowest line, px in the wide frame: 6 px below the towel's top
TOWEL = (140, 1330, 640, 130)   # the towel in the plate (left, top, width, height): its bright pixels hide the pen's lowest sliver
FOCUS_LINE = (1296, 1334)  # above the first row the plate is far (soft when the focus is on the pen), below the second it is near


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def size(path):
    return tuple(map(int, subprocess.run(["identify", "-format", "%w %h", path], capture_output=True, text=True,
                                         check=True).stdout.split()))


def main(plate, cutout, out_dir, zoom=1.0):
    work = tempfile.mkdtemp(prefix="pen-")
    path = lambda name: os.path.join(work, name)
    width, height = FRAME
    geometry = "%dx%d" % FRAME

    # the pen lying: turned, trimmed
    run("convert", cutout, "-background", "none", "-rotate", TURN, "-trim", "+repage", path("pen.png"))
    pen_w, pen_h = size(path("pen.png"))
    scale = LENGTH / pen_w

    # the window of the plate that the camera sees at this zoom: it keeps the pen where a closer camera would see it
    view_w, view_h = width / zoom, height / zoom
    centre_x, centre_y = LEFT + LENGTH / 2, REST - pen_h * scale / 2
    x0 = min(max(centre_x - view_w / 2, 0), width - view_w)
    y0 = min(max(centre_y - view_h * 0.58, 0), height - view_h)
    crop = "%dx%d+%d+%d" % (round(view_w), round(view_h), round(x0), round(y0))
    run("convert", plate, "-crop", crop, "+repage", "-resize", geometry + "!", path("plate.png"))
    if zoom > 1.01:                      # an enlarged plate is soft; bring back the edge of the towel and the table
        run("convert", path("plate.png"), "-unsharp", "0x%.1f+0.6+0" % (1.2 * zoom), path("plate.png"))

    # where the pen and the focus line are in this view
    k = zoom * scale
    pen_x, pen_bottom = (LEFT - x0) * zoom, (REST - y0) * zoom
    pen_y = pen_bottom - pen_h * k
    far, near = ((v - y0) * zoom for v in FOCUS_LINE)
    run("convert", "-size", "%dx%d" % (width, max(1, round(near - far))), "gradient:white-black", path("ramp.png"))
    run("convert", "-size", geometry, "xc:black",
        "(", "-size", "%dx%d" % (width, max(1, round(far))), "xc:white", ")", "-geometry", "+0+0", "-composite",
        path("ramp.png"), "-geometry", "+0+%d" % round(far), "-composite", path("far.png"))   # white = far from the pen
    run("convert", path("pen.png"), "-resize", "%dx%d!" % (round(pen_w * k), round(pen_h * k)), path("pen-k.png"))
    # the towel as a mask (its bright pixels), in this view: the pen sinks a little into it, so the towel is in front
    left, top, t_w, t_h = TOWEL
    run("convert", "-size", geometry, "xc:black",
        "(", plate, "-crop", "%dx%d+%d+%d" % (t_w, t_h, left, top), "+repage", "-colorspace", "Gray",
        "-threshold", "89%", ")", "-geometry", "+%d+%d" % (left, top), "-composite",
        "-crop", crop, "+repage", "-resize", geometry + "!", path("towel.png"))

    def frame(name, far_blur, near_blur, pen_blur):
        """the plate with its far part and near part softened separately, a thin shadow under the pen, the pen"""
        run("convert", path("plate.png"), "-blur", "0x%.1f" % far_blur if far_blur else "0x0.01", path("a.png"))
        run("convert", path("plate.png"), "-blur", "0x%.1f" % near_blur if near_blur else "0x0.01", path("b.png"))
        run("convert", path("b.png"), path("a.png"), path("far.png"), "-composite", path("base.png"))
        # a soft darkening where the pen lies on the towel (only on the towel itself; under the pen's thin parts
        # there is air, and a shadow there would hang in it)
        run("convert", path("pen-k.png"), "-alpha", "extract", "-blur", "0x%.1f" % (4 * zoom + pen_blur), path("sh.png"))
        run("convert", "-size", geometry, "xc:black", path("sh.png"), "-geometry",
            "+%d+%d" % (round(pen_x), round(pen_y + 9 * zoom)), "-composite", path("towel.png"),
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
        run("convert", path("towel.png"), "-blur", "0x%.1f" % (0.8 * zoom + pen_blur / 2), path("towel-soft.png"))
        run("convert", path("with-pen.png"), path("shadowed.png"), path("towel-soft.png"), "-composite",
            os.path.join(out_dir, name))
        print("built", name, "pen at %d,%d size %dx%d" % (round(pen_x), round(pen_y), round(pen_w * k), round(pen_h * k)))

    os.makedirs(out_dir, exist_ok=True)
    if zoom > 1.01:
        frame("K2.png" if abs(zoom - 2) < 0.01 else "zoom-%.2f.png" % zoom, 9 * zoom, 0, 0)
    else:
        frame("K0.png", 9, 0, 0)
        frame("K1.png", 0, 4, 6)
    for name in os.listdir(work):
        os.remove(path(name))
    os.rmdir(work)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    options = dict(item.split("=", 1) for item in sys.argv[4:])
    main(sys.argv[1], sys.argv[2], sys.argv[3], float(options.get("zoom", 1)))
