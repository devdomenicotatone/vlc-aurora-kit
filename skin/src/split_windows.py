"""Ritaglia le zone non grigie (finestre) da uno screenshot composito di shot.ps1."""
import sys
from PIL import Image, ImageChops

src = sys.argv[1]
im = Image.open(src).convert("RGB")
gray = (70, 74, 84)
mask = ImageChops.difference(im, Image.new("RGB", im.size, gray)).convert("L").point(lambda v: 255 if v > 0 else 0)
W, H = im.size
# proiezione sulle colonne
cols = [x for x in range(W) if mask.crop((x, 0, x + 1, H)).getbbox()]
groups = []
for x in cols:
    if groups and x - groups[-1][1] <= 12:
        groups[-1][1] = x
    else:
        groups.append([x, x])
n = 0
for a, b in groups:
    sub = mask.crop((a, 0, b + 1, H))
    bb = sub.getbbox()
    if not bb:
        continue
    crop = im.crop((a, bb[1], b + 1, bb[3]))
    if crop.width < 40 or crop.height < 40:
        continue
    out = src[:-4] + f"_w{n}.png"
    crop.save(out)
    print(out, crop.size, "at", a, bb[1])
    n += 1
