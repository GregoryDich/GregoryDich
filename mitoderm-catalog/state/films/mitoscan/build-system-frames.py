#!/usr/bin/env python3
"""MITOSCAN: the camera comes close to the REAL system - a free camera move, no generation.

The scene is generated WITHOUT the device (plate P1) and the real photo of the system
(protocols/print/img/mitoscan.webp, 1145x777, transparent) is placed on it - the stills K0r, K1r and Sr are made
that way by tools/place-pack.py (at=36,985 height=470 mirror=0.10,50 contact=0.25). This script repeats that
placement for a camera that moves toward the system: the plate is enlarged around the system and softened, and the
system is taken from the full-size photo every time, so it stays crisp up to zoom 2.25 (there the photo is shown
pixel for pixel on a 1912 px frame). A model never draws the device.

usage: build-system-frames.py <plate.png> <system cut-out> <out dir> sequence=Z0,Z1,COUNT [blur=B0,B1] [size=WxH] [prefix=z]
       build-system-frames.py <plate.png> <system cut-out> <out dir> zoom=Z [blur=B] [size=WxH] [name=<file.png>]
  sequence=1,2,72      a camera move as frames z000.png ... z071.png: the zoom goes from Z0 to Z1, eased at both ends
  blur=0,9             how soft the room behind the system is at the start and at the end of the move: sigma in plate
                       pixels at zoom 1 (9 is the softness of K0r; 0 keeps the people sharp, as in Sr)
  zoom=1 blur=9        one frame (zoom 1 with blur 9 repeats K0r; with the scan fitted into the display it is "K0s")
  size=1912x1080       the size of the frames (default 2688x1520, the size of the plate)
The system cut-out is the real photo, or the same photo with a picture fitted into its display.
needs ImageMagick and tools/place-pack.py
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLACE = os.path.join(HERE, "..", "tools", "place-pack.py")
PLATE = (2688, 1520)        # the plate; every measure below is in its pixels
AT = (36, 985)              # the top-left corner of the system on the plate (as in K0r, K1r, Sr)
HEIGHT = 470                # the height of the system on the plate
MIRROR = (0.10, 50)         # the faint mirror image on the table top: strength, reach in plate pixels
CONTACT = 0.25              # the thin dark line where the system meets the table
AIM = (0.32, 0.55)          # where in the frame the middle of the system is kept when the plate allows it
PAD = 24                    # an empty margin around the system in its layer


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def read(*args):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, check=True).stdout


def prepare(cutout, work):
    """the system as a layer in the full size of the photo: itself, its mirror image and its contact line"""
    box = read("convert", cutout, "-alpha", "extract", "-threshold", "50%", "-format", "%@", "info:")
    size, left, top = box.replace("+", " ").split()
    width, height = (int(v) for v in size.split("x"))
    k = height / HEIGHT                                     # photo pixels in one plate pixel
    reach = round(MIRROR[1] * k)
    canvas = os.path.join(work, "canvas.png")
    layer = os.path.join(work, "layer.png")
    run("convert", "-size", "%dx%d" % (width + 2 * PAD, height + reach + 2 * PAD), "xc:none", "PNG32:" + canvas)
    run(sys.executable, PLACE, canvas, cutout, "PNG32:" + layer, "at=%d,%d" % (PAD, PAD), "height=%d" % height,
        "mirror=%g,%d" % (MIRROR[0], reach), "contact=%g" % CONTACT)
    return layer, k, width / k


def frame(plate, layer, k, system_width, out, out_size, zoom, blur):
    width, height = out_size
    g = width / PLATE[0]
    view_w, view_h = PLATE[0] / zoom, PLATE[1] / zoom
    centre_x, centre_y = AT[0] + system_width / 2, AT[1] + HEIGHT / 2
    x0 = min(max(centre_x - view_w * AIM[0], 0), PLATE[0] - view_w)
    y0 = min(max(centre_y - view_h * AIM[1], 0), PLATE[1] - view_h)
    geometry = "%dx%d!" % out_size
    command = ["convert", plate, "-crop", "%dx%d+%d+%d" % (round(view_w), round(view_h), round(x0), round(y0)),
               "+repage"]
    sigma = blur * zoom * g                                 # the softness grows with the picture
    if sigma >= 6:                                          # a strong blur is made on a smaller copy: same look, faster
        command += ["-resize", "%dx%d!" % (width // 4, height // 4), "-gaussian-blur", "0x%.2f" % (sigma / 4),
                    "-resize", geometry]
    else:
        command += ["-resize", geometry]
        if sigma >= 0.05:
            command += ["-gaussian-blur", "0x%.2f" % sigma]
        elif zoom > 1.01:
            command += ["-unsharp", "0x%.1f+0.6+0" % (1.2 * zoom * g)]      # an enlarged plate is soft
    scale = zoom * g / k                                    # layer pixels -> frame pixels
    left = (AT[0] - x0) * zoom * g - PAD * scale
    top = (AT[1] - y0) * zoom * g - PAD * scale
    # the layer is put at its exact place, to a fraction of a pixel: in a slow move a system that snaps to whole
    # pixels would tremble against the room
    command += ["(", layer, "-alpha", "set", "-virtual-pixel", "transparent", "-background", "none",
                "-define", "distort:viewport=%dx%d+0+0" % out_size, "-filter", "RobidouxSharp",
                "-distort", "SRT", "0,0 %.6f 0 %.3f,%.3f" % (scale, left, top), ")",
                "-compose", "Over", "-composite", out]
    run(*command)
    return round(left + PAD * scale), round(top + PAD * scale), round(system_width * zoom * g), round(HEIGHT * zoom * g)


def main(argv):
    if len(argv) < 4:
        sys.exit(__doc__)
    plate, cutout, out_dir = argv[:3]
    options = dict(item.split("=", 1) for item in argv[3:])
    out_size = tuple(int(v) for v in options["size"].split("x")) if "size" in options else PLATE
    os.makedirs(out_dir, exist_ok=True)
    work = tempfile.mkdtemp(prefix="system-")
    layer, k, system_width = prepare(cutout, work)
    if "sequence" in options:
        first, last, count = options["sequence"].split(",")
        first, last, count = float(first), float(last), int(count)
        blur_first, blur_last = (float(v) for v in options.get("blur", "9,9").split(","))
        prefix = options.get("prefix", "z")
        for index in range(count):
            step = index / (count - 1)
            eased = step * step * (3 - 2 * step)
            place = frame(plate, layer, k, system_width, os.path.join(out_dir, "%s%03d.png" % (prefix, index)),
                          out_size, first * (last / first) ** eased, blur_first + (blur_last - blur_first) * eased)
        print("built %d frames: zoom %.2f -> %.2f, blur %g -> %g; the system ends at %d,%d size %dx%d" %
              ((count, first, last, blur_first, blur_last) + place))
    else:
        zoom = float(options.get("zoom", 1))
        name = options.get("name", "zoom-%.2f.png" % zoom)
        place = frame(plate, layer, k, system_width, os.path.join(out_dir, name), out_size, zoom,
                      float(options.get("blur", 9)))
        print("built %s: the system at %d,%d size %dx%d" % ((name,) + place))
    for name in os.listdir(work):
        os.remove(os.path.join(work, name))
    os.rmdir(work)


if __name__ == "__main__":
    main(sys.argv[1:])
