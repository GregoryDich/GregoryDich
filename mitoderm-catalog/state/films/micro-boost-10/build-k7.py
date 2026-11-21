#!/usr/bin/env python3
"""MICRO BOOST 10%: the two frames with the focus on the box, built without paid generation.

K7 (the last still). Two generated attempts made the box bigger than in K6 (by 17 % and 31 %) and one garbled
the print on its side, so the frame is assembled from two approved stills: K6 (the mask on the face), softened
as if the focus had moved to the box, and the sharp box of K0 (checked against the real pack photo), put exactly
where the blurred box of K6 stands. The polished table mirrors the box, as it does in K0.

K0p (the opening frame of the film). The same way from K1 (the skin examination): the people go soft and the
sharp box of K0 stands where the blurred box of K1 stands (found by matching: 1 px to the left of its place in
K0). K0p and K1 differ only in focus, so the opening focus pull is a dissolve at assembly, not a paid clip.

usage: build-k7.py <K0.png> <people-sharp still> <out.png> [scale=S] [at=X,Y] [region=L,T,W,H]
  K7:   build-k7.py K0.png K6.png K7.png
  K0p:  build-k7.py K0.png K1.png K0p.png scale=1 at=281,252 region=262,1170,400,350
needs ImageMagick (convert); stills are 2688x1520
"""
import os
import subprocess
import sys
import tempfile

BOX = (362, 1116, 282, 252)          # the box in K0: width, height, left, top
SCALE, OX, OY = 0.78, 204, 548       # its size and place in K6, found by matching against the blurred box (scale=, at=)
OUTLINE = [(5, 8), (272, 0), (352, 16), (352, 1082), (272, 1114), (9, 1110)]   # the box outline inside that crop
FRAME = (2688, 1520)
REGION = (190, 1240, 320, 280)       # where the mirror image is drawn: left, top, width, height (region=)
MIRROR, REACH, FALL = 0.40, 150.0, 1.4   # strength at the base, how far it reaches (px), how fast it fades


def run(*args):
    subprocess.run(list(args), check=True)


def main(k0, k6, out, SCALE=SCALE, OX=OX, OY=OY, REGION=REGION):
    work = tempfile.mkdtemp(prefix="k7-")
    path = lambda name: os.path.join(work, name)
    size = "%dx%d" % FRAME
    points = " ".join("%.1f,%.1f" % (OX + x * SCALE, OY + y * SCALE) for x, y in OUTLINE)

    # 1. the outline of the box as a mask, and a wider one that takes the blurred box out of K6
    run("convert", "-size", size, "xc:black", "-fill", "white", "-draw", "polygon " + points, path("mask.png"))
    run("convert", path("mask.png"), "-morphology", "Dilate", "Disk:24", "-blur", "0x3", path("wide.png"))
    run("convert", k6, "(", path("wide.png"), "-negate", ")", "-alpha", "off", "-compose", "CopyOpacity",
        "-composite", path("holed.png"))
    run("convert", path("holed.png"),
        "(", "+clone", "-channel", "RGBA", "-blur", "0x25", ")", "-compose", "DstOver", "-composite",
        "(", "+clone", "-channel", "RGBA", "-blur", "0x60", ")", "-compose", "DstOver", "-composite",
        "(", "+clone", "-channel", "RGBA", "-blur", "0x140", ")", "-compose", "DstOver", "-composite",
        "-background", "#d9c7b4", "-alpha", "remove", "-alpha", "off", path("filled.png"))
    # 2. the focus moves to the box: everything behind it goes soft
    run("convert", path("filled.png"), "-gaussian-blur", "0x5", path("soft.png"))
    # 3. the sharp box from K0, scaled, cut by its outline
    run("convert", k0, "-crop", "%dx%d+%d+%d" % BOX, "+repage", "-resize", "%d%%" % round(SCALE * 100), path("box.png"))
    run("convert", "-size", size, "xc:none", path("box.png"), "-geometry", "+%d+%d" % (OX, OY), "-composite",
        path("layer.png"))
    run("convert", path("layer.png"), "(", path("mask.png"), "-blur", "0x1.2", ")", "-alpha", "off",
        "-compose", "CopyOpacity", "-composite", path("cut.png"))
    run("convert", path("soft.png"), path("cut.png"), "-compose", "Over", "-composite", path("flat.png"))

    # 4. the table mirrors the box: each column is mirrored about the base line, fading with distance
    left, top, width, height = REGION
    crop = "%dx%d+%d+%d" % (width, height, left, top)
    read = lambda name, kind: bytearray(subprocess.run(
        ["convert", path(name), "-crop", crop, "+repage", "-depth", "8", kind + ":-"],
        capture_output=True, check=True).stdout)
    image, mask = read("flat.png", "rgb"), read("mask.png", "gray")
    at = lambda x, y: (y * width + x) * 3
    p_left = (OX + 9 * SCALE, OY + 1110 * SCALE)      # the base line: the front face, then the side face
    p_corner = (OX + 272 * SCALE, OY + 1114 * SCALE)
    p_right = (OX + 352 * SCALE, OY + 1082 * SCALE)

    def base(x):
        a, b = (p_left, p_corner) if x <= p_corner[0] else (p_corner, p_right)
        return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])

    result = bytearray(image)
    for x in range(int(p_left[0]) + 1, int(p_right[0]) + 1):
        line, column = base(x), x - left
        for y in range(int(line) + 1, top + height):
            distance = y - line
            if distance >= REACH:
                break
            source = int(round(2 * line - y)) - top
            if source < 0 or mask[source * width + column] < 200:
                continue                                  # the mirror takes only what belongs to the box
            strength = MIRROR * (1 - distance / REACH) ** FALL
            if x > p_corner[0]:
                strength *= 0.85                          # the side face is turned away: a weaker mirror
            target, origin = at(column, y - top), at(column, source)
            for channel in range(3):
                result[target + channel] = int(round(
                    image[target + channel] * (1 - strength) + image[origin + channel] * strength))
        for step in range(4):                             # a thin contact line right under the base
            row = int(line) + 1 + step - top
            if row >= height:
                break
            target, factor = at(column, row), 1 - 0.22 * (1 - step / 4)
            for channel in range(3):
                result[target + channel] = int(result[target + channel] * factor)
    with open(path("mirror.rgb"), "wb") as raw:
        raw.write(bytes(result))
    run("convert", "-size", "%dx%d" % (width, height), "-depth", "8", "rgb:" + path("mirror.rgb"), path("mirror.png"))
    run("convert", path("flat.png"), "(", path("mirror.png"), "-blur", "0x0.7", ")", "-geometry",
        "+%d+%d" % (left, top), "-composite", path("cut.png"), "-compose", "Over", "-composite", out)
    for name in os.listdir(work):
        os.remove(path(name))
    os.rmdir(work)
    print("built", out)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    options = dict(item.split("=", 1) for item in sys.argv[4:])
    place = {}
    if "scale" in options:
        place["SCALE"] = float(options["scale"])
    if "at" in options:
        place["OX"], place["OY"] = (int(v) for v in options["at"].split(","))
    if "region" in options:
        place["REGION"] = tuple(int(v) for v in options["region"].split(","))
    main(*sys.argv[1:4], **place)
