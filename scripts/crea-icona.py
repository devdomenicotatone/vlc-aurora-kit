"""crea-icona.py - disegna config/aurora.ico, l'icona del kit in "App installate" e dell'EXE di installazione
(crea-exe.ps1 la mette nel modulo auto-estraente).

Stesso disegno di web/aurora/favicon.png (disco con il gradiente d'accento della skin e triangolo "play" bianco),
ridisegnato in grande e ridotto alle misure che Windows usa. Serve Python 3 con Pillow:  python scripts/crea-icona.py
"""
import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw

STOPS = [(0.0, (0xFF, 0x8A, 0x3D)), (0.55, (0xFF, 0x3D, 0x7F)), (1.0, (0x8B, 0x5C, 0xF6))]  # ACCENT_STOPS di build_aurora.py
MISURE = [16, 20, 24, 32, 40, 48, 64, 128, 256]
S = 1024  # lato del disegno di partenza


def colore(t):
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return STOPS[-1][1]


def disegna():
    # gradiente in diagonale, dall'angolo in alto a sinistra a quello in basso a destra
    riga = Image.new("RGB", (2 * S - 1, 1))
    riga.putdata([colore(i / (2 * S - 2)) for i in range(2 * S - 1)])
    grad = Image.new("RGB", (S, S))
    for y in range(S):
        grad.paste(riga.crop((y, 0, y + S, 1)), (0, y))
    u = S / 64  # le misure qui sotto sono quelle della favicon a 64 pixel
    disco = Image.new("L", (S, S), 0)
    ImageDraw.Draw(disco).ellipse([1 * u, 1 * u, 63 * u, 63 * u], fill=255)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(grad, (0, 0), disco)
    d = ImageDraw.Draw(img)
    punti = [(25 * u, 21 * u), (25 * u, 43 * u), (44 * u, 32 * u)]
    d.polygon(punti, fill="white")
    d.line(punti + punti[:2], fill="white", width=round(2 * u), joint="curve")  # angoli arrotondati
    return img


def voce(img, m):
    """i dati di una misura come li vuole un file .ico: bitmap per le piccole (la forma che ogni programma legge,
    anche quando l'icona e' una risorsa di un EXE), PNG per 256"""
    buf = io.BytesIO()
    img.save(buf, format="ICO", sizes=[(m, m)], bitmap_format="png" if m >= 256 else "bmp")
    d = buf.getvalue()
    dimensione, inizio = struct.unpack_from("<II", d, 6 + 8)
    dati = d[inizio:inizio + dimensione]
    if m < 256:
        # Pillow, per le bitmap a 32 bit, non scrive la maschera di trasparenza a 1 bit che il formato prevede dopo
        # i pixel (l'altezza dichiarata e' doppia proprio per lei): la aggiungiamo, ricavata dal canale alfa
        pixel = dati[40:40 + m * m * 4]             # intestazione di 40 byte, poi BGRA dal basso verso l'alto
        riga = ((m + 31) // 32) * 4                 # righe della maschera allineate a 32 bit
        maschera = bytearray(riga * m)
        for y in range(m):
            for x in range(m):
                if pixel[(y * m + x) * 4 + 3] < 128:
                    maschera[y * riga + x // 8] |= 0x80 >> (x % 8)
        dati += bytes(maschera)
    return dati


def scrivi_ico(img, dst):
    voci = [(m, voce(img, m)) for m in MISURE]
    testa = struct.pack("<HHH", 0, 1, len(voci))
    inizio = len(testa) + 16 * len(voci)
    elenco, corpo = b"", b""
    for m, dati in voci:
        # larghezza, altezza (0 = 256), colori, riservato, piani, bit per pixel, dimensione, posizione
        elenco += struct.pack("<BBBBHHII", m % 256, m % 256, 0, 0, 1, 32, len(dati), inizio + len(corpo))
        corpo += dati
    Path(dst).write_bytes(testa + elenco + corpo)


if __name__ == "__main__":
    dst = Path(__file__).resolve().parent.parent / "config" / "aurora.ico"
    scrivi_ico(disegna(), dst)
    print(dst)
