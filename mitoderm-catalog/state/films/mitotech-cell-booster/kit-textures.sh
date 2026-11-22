#!/bin/bash
# kit-textures.sh <out dir> <clinic plate.png>
# Builds the textures that kit3d.py reads, so the kit can be rendered again after a container restart.
#   box-front.png, box-metal.png   the lid's face, the owner's print R15 (site/proto/img/mitotech-cell-booster-3d)
#   guide.png                      the owner's user guide R7, 300 dpi - the sheet inside the lid
#   plate-soft.jpg                 the film's clinic plate without the pack, soft - the room behind the table
#   label-card-powder.png, label-card-ampoule.png
#                                  the vial labels as on the owner's card of 22/11 ("this is how our ampoules look"):
#                                  the clear vial has a frosted white label with black text, the amber vial white
#                                  text straight on the glass. There is no print file of this label, so the six lines
#                                  are set here word for word from the card, in the same order and weights (Inter).
set -euo pipefail
OUT=${1:?out dir}; PLATE=${2:?the clinic plate of the film, without the pack}
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../../.." && pwd)
P3D="$ROOT/site/proto/img/mitotech-cell-booster-3d"
F=/usr/share/fonts/opentype/inter
mkdir -p "$OUT"
convert "$P3D/box-front.webp" "$OUT/box-front.png"
cp "$P3D/box-metal.png" "$OUT/box-metal.png"
pdftoppm -r 300 -png -singlefile "$ROOT/site/design/mitotech/print/USER_GUIDE_PRINT_R7.pdf" "$OUT/guide"
convert "$PLATE" -resize 1344x -blur 0x7 -quality 92 "$OUT/plate-soft.jpg"

W=1024; H=1135; LEFT=84
width() { convert -font "$1" -pointsize "$2" label:"$3" -format '%w' info:; }
label() {   # <out file> <ink> <ground> <third line> <fourth line> <fifth line>
  local out=$1 ink=$2 ground=$3 third=$4 fourth=$5 fifth=$6 base brand big small mark reg
  # the third line of the powder label ("Concentrated") sets the scale: 86 % of the label's width, as on the card
  base=$(awk -v w="$(width $F/Inter-Regular.otf 200 Concentrated)" -v t=$((W*86/100)) 'BEGIN{printf "%d", 200*t/w}')
  brand=$((base*22/40)); big=$((base*58/40)); small=$((base*35/40)); mark=$((base*24/40)); reg=$((brand*55/100))
  convert -size ${W}x${H} "xc:$ground" -fill "$ink" \
    -font $F/Inter-Bold.otf -pointsize $brand -annotate +${LEFT}+$((H*160/1000)) 'MITOTECH' \
    -pointsize $reg -annotate +$((LEFT + $(width $F/Inter-Bold.otf $brand MITOTECH) + brand/12))+$((H*160/1000 - brand*40/100)) '®' \
    -pointsize $brand -annotate +${LEFT}+$((H*250/1000)) 'CELL BOOSTER' \
    -font $F/Inter-Regular.otf -pointsize $base -annotate +${LEFT}+$((H*437/1000)) "$third" \
    -font $F/Inter-ExtraBold.otf -pointsize $big -annotate +${LEFT}+$((H*620/1000)) "$fourth" \
    -font $F/Inter-Medium.otf -pointsize $small -annotate +${LEFT}+$((H*800/1000)) "$fifth" \
    -font $F/Inter-SemiBold.otf -pointsize $mark -kerning 2 -annotate +${LEFT}+$((H*955/1000)) 'MITODERM' \
    "png32:$out"
}
label "$OUT/label-card-powder.png" '#111111' 'rgba(255,255,255,0.52)' 'Concentrated' 'Powder' '154 mg'
label "$OUT/label-card-ampoule.png" '#ffffff' 'rgba(255,255,255,0)' 'Boosting' 'Ampoule' '15 ml'
ls -la "$OUT"
