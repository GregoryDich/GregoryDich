#!/usr/bin/env python3
"""Puts the REAL pack (a cut-out photo or render with a transparent background) into a generated frame.

Why: an image model redraws a pack with small mistakes (a wrong letter on the side, a made-up symbol), and the
customer's rule is that a real pack is never redesigned. So the scene is generated WITHOUT the pack and the
real one is placed here: sharp (the plate behind it softened, as when the focus is on the pack) or softly out
of focus (when the focus is on the people). The pack is the same pixel for pixel in every frame of a page, so
a focus pull or a dissolve between two such frames keeps it perfectly still.

usage: place-pack.py <plate.png> <pack cut-out.png> <out.png> key=value ...
  at=X,Y          where the top-left corner of the pack's visible part goes in the frame      (required)
  height=H        height of the pack's visible part in the frame, px                          (required)
  plate_blur=S    soften the whole plate first (focus on the pack), sigma in px               default 0
  pack_blur=S     soften the pack and its mirror image (focus elsewhere), sigma in px         default 0
  gain=r,g,b      colour gains for the pack, to match the light of the scene                  default 1,1,1
  mirror=A,R      mirror image under the pack on a polished top: strength and reach in px     default 0.40,150 (0,0 = none)
  contact=K       strength of the thin dark line where the pack meets the table               default 0.22
Needs ImageMagick (convert). Prints the place of the pack so the next frame can repeat it exactly.
"""
import os
import subprocess
import sys
import tempfile


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def read_rgba(path):
    width, height = map(int, subprocess.run(["identify", "-format", "%w %h", path], capture_output=True,
                                            text=True, check=True).stdout.split())
    data = subprocess.run(["convert", path, "-depth", "8", "rgba:-"], capture_output=True, check=True).stdout
    return width, height, bytearray(data)


def main(argv):
    if len(argv) < 5:
        sys.exit(__doc__)
    plate, cutout, out = argv[:3]
    options = dict(item.split("=", 1) for item in argv[3:])
    left, top = (int(v) for v in options["at"].split(","))
    target = int(options["height"])
    plate_blur = float(options.get("plate_blur", 0))
    pack_blur = float(options.get("pack_blur", 0))
    gains = [float(v) for v in options.get("gain", "1,1,1").split(",")]
    strength, reach = (float(v) for v in options.get("mirror", "0.40,150").split(","))
    contact = float(options.get("contact", 0.22))
    work = tempfile.mkdtemp(prefix="pack-")
    path = lambda name: os.path.join(work, name)

    # 1. the visible part of the cut-out, scaled to the wanted height, in the light of the scene
    width, height, data = read_rgba(cutout)
    rows = [y for y in range(height) if any(data[(y * width + x) * 4 + 3] > 128 for x in range(0, width, 2))]
    columns = [x for x in range(width) if any(data[(y * width + x) * 4 + 3] > 128 for y in range(0, height, 2))]
    box = (columns[-1] - columns[0] + 1, rows[-1] - rows[0] + 1, columns[0], rows[0])
    run("convert", cutout, "-crop", "%dx%d+%d+%d" % box, "+repage", "-resize", "x%d" % target,
        "-channel", "R", "-evaluate", "multiply", gains[0], "-channel", "G", "-evaluate", "multiply", gains[1],
        "-channel", "B", "-evaluate", "multiply", gains[2], "+channel", path("pack.png"))
    width, height, data = read_rgba(path("pack.png"))

    # 2. the layer: the pack, and under it its mirror image fading with distance plus a contact line
    extra = int(reach) if strength > 0 else 6
    layer = bytearray(width * (height + extra) * 4)
    layer[:width * height * 4] = data
    for x in range(width):
        opaque = [y for y in range(height - 1, -1, -1) if data[(y * width + x) * 4 + 3] > 128][:1]
        if not opaque:
            continue
        base = opaque[0]                                   # the lowest point of the pack in this column
        for y in range(base + 1, height + extra):
            distance = y - base
            source = base - distance + 1
            alpha, colour = 0.0, (0, 0, 0)
            if strength > 0 and distance < reach and source >= 0:
                at = (source * width + x) * 4
                alpha = strength * (1 - distance / reach) ** 1.4 * data[at + 3] / 255
                colour = data[at:at + 3]
            line = contact * (1 - (distance - 1) / 4) if distance <= 4 else 0.0
            total = alpha + line * (1 - alpha)
            if total <= 0:
                continue
            at = (y * width + x) * 4
            if y < height and data[at + 3] > 128:
                continue                                   # never draw over the pack itself
            for channel in range(3):
                layer[at + channel] = int(round(colour[channel] * alpha * (1 - line) / total))
            layer[at + 3] = int(round(255 * total))
    with open(path("layer.rgba"), "wb") as raw:
        raw.write(bytes(layer))
    run("convert", "-size", "%dx%d" % (width, height + extra), "-depth", "8", "rgba:" + path("layer.rgba"),
        path("layer.png"))

    # 3. soften what is not in focus and put the layer onto the plate
    margin = int(pack_blur * 3) + 2 if pack_blur > 0 else 0
    if pack_blur > 0:
        run("convert", path("layer.png"), "-background", "none", "-gravity", "center",
            "-extent", "%dx%d" % (width + 2 * margin, height + extra + 2 * margin),
            "-channel", "RGBA", "-blur", "0x%g" % pack_blur, path("layer.png"))
    command = ["convert", plate]
    if plate_blur > 0:
        command += ["-gaussian-blur", "0x%g" % plate_blur]
    command += [path("layer.png"), "-gravity", "northwest", "-geometry", "%+d%+d" % (left - margin, top - margin),
                "-compose", "Over", "-composite", out]
    run(*command)
    for name in os.listdir(work):
        os.remove(path(name))
    os.rmdir(work)
    print("pack placed: at=%d,%d height=%d (visible part %dx%d px), base at y=%d" %
          (left, top, target, width, height, top + height))


if __name__ == "__main__":
    main(sys.argv[1:])
