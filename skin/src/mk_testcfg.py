# -*- coding: utf-8 -*-
"""Crea test-vlcrc: copia del vlcrc dell'utente con la skin appena generata e posizioni di prova
per tutte le finestre (lette da Aurora/theme.xml). Uso: mk_testcfg.py [x0] [y0] [visibili...]"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.environ["APPDATA"], "vlc", "vlcrc")
DST = os.path.join(HERE, "test-vlcrc")
x0 = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
y0 = int(sys.argv[2]) if len(sys.argv) > 2 else 300
visible = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else {"main", "playlist", "eqwin", "fstest"}

xml = open(os.path.join(HERE, "Aurora", "theme.xml"), encoding="utf-8").read()
sizes = {}
for m in re.finditer(r'<Window id="(\w+)".*?<Layout id="(\w+)" width="(\d+)" height="(\d+)"', xml, re.S):
    sizes[m.group(1)] = (m.group(2), int(m.group(3)), int(m.group(4)))
W, H = sizes["main"][1], sizes["main"][2]
pos = {
    "main": (x0, y0),
    "playlist": (x0 + W, y0),
    "eqwin": (x0 + W, y0 + sizes["playlist"][2]),
    "fullscreenController": (x0, y0 + H + 400),
    "fstest": (x0, y0 + H + 30),
}
parts = []
for win, (layout, w, h) in sizes.items():
    x, y = pos.get(win, (x0, y0))
    parts.append('["%s" "%s" %d %d %d %d %d]' % (win, layout, x, y, w, h, 1 if win in visible else 0))
cfg = "".join(parts)
vlt = os.path.join(HERE, "Aurora.vlt").replace("/", os.sep)

lines = open(SRC, encoding="utf-8", errors="surrogateescape").read().split("\n")
out = []
for ln in lines:
    if ln.startswith("skins2-config=") or ln.startswith("#skins2-config="):
        out.append("skins2-config=" + cfg)
    elif ln.startswith("skins2-last=") or ln.startswith("#skins2-last="):
        out.append("skins2-last=" + vlt)
    else:
        out.append(ln)
open(DST, "w", encoding="utf-8", errors="surrogateescape", newline="\n").write("\n".join(out))
print("test-vlcrc scritto;", cfg)
