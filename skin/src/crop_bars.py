# ritaglia barra titolo e barra comandi della finestra principale (la piu' grande) da una cattura shot2
import re, sys
from PIL import Image
name = sys.argv[1]
txt = open(name + ".txt", encoding="utf-8", errors="ignore").read()
wins = [(int(a), int(b), int(c), int(d)) for a, b, c, d in re.findall(r"WIN (-?\d+),(-?\d+) (\d+)x(\d+)", txt)]
ox, oy = map(int, re.search(r"origin=(-?\d+),(-?\d+)", txt).groups())
L, T, W, H = max(wins, key=lambda w: w[2] * w[3])
im = Image.open(name + ".png")
x0, y0 = L - ox, T - oy
top = im.crop((x0, y0, x0 + W, y0 + 72))
bot = im.crop((x0, y0 + H - 150, x0 + W, y0 + H))
out = Image.new("RGB", (W, 72 + 150 + 4), (60, 64, 74))
out.paste(top, (0, 0)); out.paste(bot, (0, 76))
out.save(name + "_bars.png"); print(name, "main", (L, T, W, H))
