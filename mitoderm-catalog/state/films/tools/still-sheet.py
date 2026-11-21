#!/usr/bin/env python3
"""One labelled sheet of all the stills of a page - what goes to the owner for his ok BEFORE any clip is paid
for (the money rule of 21/11: frames first, clips after).

usage: still-sheet.py <stills dir> <out.jpg> "NAME=label text" ...
Each NAME is a file <stills dir>/NAME.png; cells go three in a row, in the order given. Needs ImageMagick.
"""
import os
import subprocess
import sys
import tempfile

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    stills, out, cells = argv[0], argv[1], [item.split("=", 1) for item in argv[2:]]
    work = tempfile.mkdtemp(prefix="sheet-")
    names = []
    for index, (name, text) in enumerate(cells):
        cell = os.path.join(work, "cell%02d.png" % index)
        names.append(cell)
        subprocess.run(["convert", os.path.join(stills, name + ".png"), "-resize", "1000x566!", "-background", "#f4efe8",
                        "-gravity", "south", "-splice", "0x64", "-font", FONT, "-pointsize", "27", "-fill", "#2b2b2b",
                        "-gravity", "southwest", "-annotate", "+18+18", "%s   %s" % (name, text), cell], check=True)
    sheet = os.path.join(work, "sheet.png")
    subprocess.run(["montage"] + names + ["-tile", "3x", "-geometry", "+14+14", "-background", "#f4efe8", sheet], check=True)
    subprocess.run(["convert", sheet, "-quality", "88", out], check=True)
    for path in names + [sheet]:
        os.remove(path)
    os.rmdir(work)
    print("sheet written:", out)


if __name__ == "__main__":
    main(sys.argv[1:])
