# -*- coding: utf-8 -*-
"""
Generatore della skin "Aurora" per VLC 3.x (interfaccia skins2, Windows).

Nota importante: su Windows skins2 non fonde l'alfa per pixel. I pixel semitrasparenti
vengono disegnati opachi e scuriti, e la forma della finestra usa solo alfa 0/255.
Per questo ogni immagine viene "cotta" (pre-composta) sullo sfondo esatto su cui poggia,
e la trasparenza residua e' sempre binaria (bordi netti).

Scala: skins2 disegna 1:1 in pixel fisici (il processo diventa consapevole dei DPI grazie
a Qt), quindi su uno schermo al 150% la skin va generata a 1,5x. La variabile d'ambiente
AURORA_SCALE (predefinito 1.5) moltiplica ogni misura del progetto (pensato a 960x600),
i font e le immagini. Le misure "logiche" passano sempre da sc() / scf().

Menu: e' un cassetto laterale DENTRO la finestra principale, realizzato come secondo layout
(mainMenuLayout) della stessa misura del primo: skins2 conserva la dimensione della finestra
nel passaggio e il video si riaggancia al controllo Video del layout attivo. Una finestra
separata non puo' restare sopra la principale (ogni clic chiama SetForegroundWindow solo
sulla finestra cliccata), per questo il menu non e' piu' una finestra a parte.
"""
import os, math, shutil, tarfile, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "Aurora")
IMG = os.path.join(OUT, "images")
FONTS_SRC = os.path.join(HERE, "fonts")
S = 4  # supercampionamento per l'antialias
K = float(os.environ.get("AURORA_SCALE", "1.5"))
DEBUG_FS = bool(os.environ.get("AURORA_DEBUG_FS"))  # aggiunge una copia visibile del controller schermo intero


def sc(v):
    """misura logica (progetto a 960x600) -> pixel reali, arrotondata"""
    return int(math.floor(v * K + 0.5))


def scf(v):
    """misura logica -> pixel reali, non arrotondata (per il disegno a 4x)"""
    return v * K


# ---------------------------------------------------------------- palette
def hx(c, a=255):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


TOP_1, TOP_2 = "#1C202B", "#161923"      # barra titolo (gradiente verticale)
BOT_1, BOT_2 = "#171A24", "#0F1117"      # barra comandi
MID          = "#0F1218"                 # area video / liste / corpo equalizzatore (colore piatto)
FS_BG        = "#0D0F15"                 # controller schermo intero
BORDER_C     = "#262A34"                 # bordo 1px opaco
SEP_C        = "#232732"                 # separatore
HILITE_C     = "#2A2F3B"                 # filetto chiaro in alto
ICON         = hx("#E4E8F0")             # icona normale
ICON_OFF     = hx("#B9C1D0")             # interruttore spento
ICON_HI      = hx("#FFFFFF")
ACC_A, ACC_B, ACC_C = "#FF8A3D", "#FF3D7F", "#8B5CF6"
ACCENT       = hx(ACC_B)
TRACK_A      = (255, 255, 255, 58)
TXT_PRI      = "#EEF1F7"
TXT_SEC      = "#9AA3B8"
TXT_DIM      = "#6E7789"
CLOSE_RED    = hx("#E5484D")
HOVER_A      = (255, 255, 255, 28)
DOWN_A       = (255, 255, 255, 44)
RING_A       = hx(ACC_B, 210)            # anello degli interruttori attivi al passaggio del mouse
RING_FILL    = hx(ACC_B, 34)
DOWN_ON      = hx(ACC_B, 100)
MENU_BG      = "#151822"                 # cassetto del menu

FLUENT = "C:/Windows/Fonts/SegoeIcons.ttf"
if not os.path.exists(FLUENT):
    FLUENT = "C:/Windows/Fonts/segmdl2.ttf"

# geometria condivisa (tutto gia' in pixel reali)
W, H = sc(960), sc(600)
TB, BB = sc(48), sc(100)
FW, FH = sc(720), sc(112)
BTN, CHR = sc(36), sc(32)
PLAY = sc(56)
PLAY_PAD = sc(10)
PLAY_BOX = PLAY + 2 * PLAY_PAD
RADIUS = sc(14)
# Cornice delle finestre. Con NATIVE_FRAME le finestre (principale, playlist, equalizzatore) sono rettangoli
# pieni e il contorno lo disegna Windows (DWM): angoli arrotondati con antialias, ombra e bordo su Windows 11,
# angoli vivi su Windows 10. Il plugin skins2 del kit non applica la sagoma (region) alle finestre rettangolari
# proprio per lasciar lavorare il DWM. AURORA_NATIVE_FRAME=0 torna alla sagoma ritagliata dalla skin (raggio
# RADIUS, bordi netti, niente ombra), utile con il plugin skins2 originale di VLC.
NATIVE_FRAME = os.environ.get("AURORA_NATIVE_FRAME", "1") != "0"
WIN_R = 0 if NATIVE_FRAME else RADIUS        # raggio della sagoma delle finestre nelle immagini
CORNER = sc(8) if NATIVE_FRAME else RADIUS   # ingombro dell'angolo (8 px logici = raggio di Windows 11)
SLICE = sc(28)
SEEK_FRAMES = 241
VOL_FRAMES = 51
BY = sc(44)                        # y dei pulsanti nella barra comandi
SEEK_Y = sc(10)                    # y del fotogramma seek nella barra comandi
FRAME_H = sc(20)
VOL_Y = BY + sc(8)
FS_BY = sc(54)
FS_SEEK_Y = sc(8)
FS_VOL_Y = FS_BY + sc(8)
FONT_TITLE, FONT_TEXT, FONT_SMALL = sc(14), sc(12), sc(11)

# equalizzatore (finestra separata)
EQ_MXL, EQ_MXR = sc(40), sc(22)    # margini sinistro (con etichette dB) e destro
EQ_PRE_W = sc(48)                  # colonna della preamplificazione
EQ_PITCH = sc(38)                  # passo delle 10 bande
EQ_W = EQ_MXL + EQ_PRE_W + 10 * EQ_PITCH + EQ_MXR
EQ_TY = TB + sc(14)                # inizio delle tracce
EQ_TH = sc(150)                    # altezza delle tracce
EQ_FW = sc(12)                     # larghezza del fotogramma di ogni slider
EQ_LBL_Y = EQ_TY + EQ_TH + sc(8)   # etichette delle frequenze
EQ_H = EQ_LBL_Y + sc(22)
EQ_FRAMES = 61
EQ_BANDS = ["60", "170", "310", "600", "1k", "3k", "6k", "12k", "14k", "16k"]
EQ_TIPS = ["60 Hz", "170 Hz", "310 Hz", "600 Hz", "1 kHz", "3 kHz", "6 kHz", "12 kHz", "14 kHz", "16 kHz"]
PILL_W, PILL_H = sc(66), sc(24)

# playlist: larga quanto l'equalizzatore, cosi' le due finestre impilate a destra sono a filo
PW, PH = EQ_W, sc(520)
PLB = sc(56)                       # barra inferiore della playlist

# cassetto del menu (dentro la finestra principale, layout mainMenuLayout)
MENU_W = sc(252)
MENU_IH = sc(26)
MENU_PAD = sc(8)
MENU_SEP = sc(9)
DRAWER_T = sc(8)                   # fetta superiore dello sfondo del cassetto
DRAWER_B = RADIUS + sc(2)          # fetta inferiore (angolo arrotondato come la finestra)
CLOSE_MENU = "main.setLayout(mainLayout)"
DONAZIONI = "https://www.paypal.com/paypalme/domenicotatone"   # voce "Offrimi un caffè" (niente ; nell'indirizzo)
MENU_ITEMS = [  # (id, glifo, etichetta, scorciatoia, sottomenu, azione) oppure None = separatore
    ("open_file",   0xE8E5, "Apri file…",             "Ctrl+O",  False, "dialogs.fileSimple();" + CLOSE_MENU),
    ("open_folder", 0xE8B7, "Apri cartella…",         "Ctrl+F",  False, "dialogs.directory();" + CLOSE_MENU),
    ("open_disc",   0xE958, "Apri disco…",            "Ctrl+D",  False, "dialogs.disc();" + CLOSE_MENU),
    ("open_net",    0xE774, "Apri flusso di rete…",   "Ctrl+N",  False, "dialogs.net();" + CLOSE_MENU),
    None,
    ("playlist",    0xE90B, "Playlist",               "Ctrl+L",  False, "playlist.show();" + CLOSE_MENU),
    ("equalizer",   0xE9E9, "Equalizzatore",          None,      False, "eqwin.show();" + CLOSE_MENU),
    ("info",        0xE946, "Informazioni sul media", "Ctrl+I",  False, "dialogs.fileInfo();" + CLOSE_MENU),
    ("snapshot",    0xE722, "Istantanea",             "Shift+S", False, "vlc.snapshot();" + CLOSE_MENU),
    ("fullscreen",  0xE740, "Schermo intero",         "F",       False, "vlc.fullscreen();" + CLOSE_MENU),
    # apre nel browser la pagina del telecomando: il comando esiste solo nel plugin skins2 del kit
    # (con quello ufficiale di VLC la voce chiude il menu e basta)
    ("web",         0xE8EA, "Telecomando web",        None,      False, "vlc.webInterface();" + CLOSE_MENU),
    None,
    ("audio",       0xE767, "Audio",                  None,      True,  "dialogs.audioPopup();" + CLOSE_MENU),
    ("video",       0xE714, "Video",                  None,      True,  "dialogs.videoPopup();" + CLOSE_MENU),
    ("playback",    0xEC4A, "Riproduzione",           None,      True,  "dialogs.miscPopup();" + CLOSE_MENU),
    ("allopts",     0xE712, "Tutte le opzioni VLC",   None,      True,  "dialogs.popup();" + CLOSE_MENU),
    None,
    ("prefs",       0xE713, "Preferenze…",            "Ctrl+P",  False, "dialogs.prefs();" + CLOSE_MENU),
    ("quit",        0xE7E8, "Esci",                   "Ctrl+Q",  False, "vlc.quit()"),
]
# Voce in fondo al cassetto, ancorata al bordo inferiore e con l'icona nei colori d'accento della skin: apre nel
# browser la pagina per sostenere l'autore del kit. Anche vlc.openLink() esiste solo nel plugin skins2 del kit.
MENU_FOOT = ("coffee", 0xEC32, "Buy me a coffee", None, False, "vlc.openLink(" + DONAZIONI + ");" + CLOSE_MENU)
# altezza minima del cassetto: le voci dall'alto, poi un separatore e la voce in fondo
MENU_H = MENU_PAD * 2 + sum(MENU_IH if it else MENU_SEP for it in MENU_ITEMS) + MENU_SEP + MENU_IH
MINW = sc(840)
MINH = max(sc(420), TB + MENU_H + sc(10))   # il cassetto deve stare tutto nella finestra


# ---------------------------------------------------------------- utilita'
def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


def grad_color(stops, t):
    t = max(0.0, min(1.0, t))
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]; p1, c1 = stops[i + 1]
        if t <= p1:
            return lerp(c0, c1, (t - p0) / (p1 - p0) if p1 > p0 else 0)
    return stops[-1][1]


ACCENT_STOPS = [(0.0, hx(ACC_A)), (0.55, hx(ACC_B)), (1.0, hx(ACC_C))]


def vgrad_rows(h, c1, c2):
    return [lerp(hx(c1), hx(c2), y / max(1, h - 1)) for y in range(h)]


TOP_ROWS = vgrad_rows(TB, TOP_1, TOP_2)
BOT_ROWS = vgrad_rows(BB, BOT_1, BOT_2)
PLB_ROWS = vgrad_rows(PLB, BOT_1, BOT_2)


def bg_from_rows(rows, y, w, h):
    """sfondo 1x (w x h) preso dalle righe y..y+h del gradiente `rows`"""
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for i in range(h):
        d.line([(0, i), (w, i)], fill=rows[min(len(rows) - 1, max(0, y + i))])
    return img


def bg_flat(color, w, h):
    return Image.new("RGBA", (w, h), hx(color))


def canvas(w, h):
    return Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))


def downsample(img):
    return img.resize((img.width // S, img.height // S), Image.LANCZOS)


def bake(img4x, bg, name, mask=None):
    """riduce il 4x, lo compone su bg (1x) e salva opaco; `mask` (L 1x, 0/255) rende binaria la sagoma"""
    fg = downsample(img4x)
    out = Image.alpha_composite(bg.convert("RGBA"), fg)
    if mask is None:
        out.putalpha(255)
    else:
        out.putalpha(mask.point(lambda v: 255 if v >= 128 else 0))
    out.save(os.path.join(IMG, name + ".png"))
    return out


def hgradient(w, h, stops):
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for x in range(w):
        d.line([(x, 0), (x, h)], fill=grad_color(stops, x / max(1, w - 1)))
    return img


def vgradient(w, h, stops):
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=grad_color(stops, y / max(1, h - 1)))
    return img


def dgradient(w, h, stops):
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = grad_color(stops, (x / max(1, w - 1) + y / max(1, h - 1)) / 2)
    return img


def glow(img, color, radius, strength=1.0):
    alpha = img.split()[3]
    g = Image.new("RGBA", img.size, color[:3] + (0,))
    a = alpha.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * strength)))
    g.putalpha(a)
    return g


def over(base, *layers):
    for l in layers:
        base = Image.alpha_composite(base, l)
    return base


def glyph(cp, size, color, box):
    img = canvas(box, box)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FLUENT, size * S)
    d.text((img.width / 2, img.height / 2), chr(cp), font=f, fill=color, anchor="mm")
    return img


def accent_glyph(cp, size, box):
    """glifo riempito con il gradiente d'accento della skin (in diagonale, sul solo ingombro del glifo)"""
    alpha = glyph(cp, size, (255, 255, 255, 255), box).split()[3]
    img = canvas(box, box)
    bb = alpha.getbbox()
    if bb:
        img.paste(dgradient(bb[2] - bb[0], bb[3] - bb[1], ACCENT_STOPS), (bb[0], bb[1]))
    img.putalpha(alpha)
    return img


def circle(box, cx, cy, r, fill):
    img = canvas(box, box)
    ImageDraw.Draw(img).ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=fill)
    return img


def ring(box, cx, cy, r, color, width):
    img = canvas(box, box)
    ImageDraw.Draw(img).ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S],
                                outline=color, width=max(1, int(round(width * S))))
    return img


def font(name, px):
    return ImageFont.truetype(os.path.join(FONTS_SRC, name), px * S)


def ty(center, px):
    """y di un controllo Text (Poppins) perche' cifre e maiuscole risultino centrate su `center`"""
    return int(math.floor(center - 0.70 * px + 0.5))


# ---------------------------------------------------------------- forme trasporto
def shape_play(size, color, cx, cy, box):
    img = canvas(box, box)
    s = size * S
    x0 = cx * S - s * 0.40
    ImageDraw.Draw(img).polygon([(x0, cy * S - s * 0.5), (x0, cy * S + s * 0.5), (x0 + s * 0.92, cy * S)], fill=color)
    return img.filter(ImageFilter.GaussianBlur(S * 0.3))


def shape_pause(size, color, cx, cy, box):
    img = canvas(box, box)
    d = ImageDraw.Draw(img)
    s = size * S; bw = s * 0.28; gap = s * 0.16
    for sx in (-(gap / 2 + bw), gap / 2):
        d.rounded_rectangle([cx * S + sx, cy * S - s / 2, cx * S + sx + bw, cy * S + s / 2], radius=S * scf(1.2), fill=color)
    return img


def shape_stop(size, color, cx, cy, box):
    img = canvas(box, box)
    s = size * S * 0.80
    ImageDraw.Draw(img).rounded_rectangle([cx * S - s / 2, cy * S - s / 2, cx * S + s / 2, cy * S + s / 2], radius=S * scf(2), fill=color)
    return img


def shape_skip(size, color, cx, cy, box, forward=True):
    img = canvas(box, box)
    d = ImageDraw.Draw(img)
    s = size * S; bw = s * 0.16; tri = s * 0.62; total = tri + s * 0.10 + bw
    x0 = cx * S - total / 2
    if forward:
        d.polygon([(x0, cy * S - s / 2), (x0, cy * S + s / 2), (x0 + tri, cy * S)], fill=color)
        d.rounded_rectangle([x0 + tri + s * 0.10, cy * S - s / 2, x0 + total, cy * S + s / 2], radius=S * scf(1), fill=color)
    else:
        d.rounded_rectangle([x0, cy * S - s / 2, x0 + bw, cy * S + s / 2], radius=S * scf(1), fill=color)
        xt = x0 + bw + s * 0.10
        d.polygon([(xt + tri, cy * S - s / 2), (xt + tri, cy * S + s / 2), (xt, cy * S)], fill=color)
    return img.filter(ImageFilter.GaussianBlur(S * 0.3))


SHAPES = {
    "prev": lambda s, c, cx, cy, box: shape_skip(s, c, cx, cy, box, False),
    "next": lambda s, c, cx, cy, box: shape_skip(s, c, cx, cy, box, True),
    "stop": shape_stop,
}


# ---------------------------------------------------------------- pulsanti icona
def icon_button(name, cp, bg, size, box=BTN, on=False, danger=False, shape=None,
                cp_on=None, off_col=None, active_only=False):
    """pulsante tondo a icona. Stati: up/over/down; con on=True anche gli stati attivi
    (icona color accento + puntino; al passaggio anello color accento). cp_on = glifo
    alternativo per lo stato attivo; off_col = colore dell'icona a interruttore spento;
    active_only=True genera direttamente {name}_* con l'aspetto attivo."""
    cx = cy = box / 2
    r_hover = box / 2 - scf(1)

    def make(state, active):
        img = canvas(box, box)
        if danger:
            if state == "over":
                img = over(img, circle(box, cx, cy, r_hover, CLOSE_RED))
            elif state == "down":
                img = over(img, circle(box, cx, cy, r_hover, hx("#C73A3F")))
            col = ICON_HI if state != "up" else ICON
        elif active:
            if state == "over":
                img = over(img, circle(box, cx, cy, r_hover, RING_FILL),
                           ring(box, cx, cy, r_hover - scf(0.75), RING_A, scf(1.5)))
                col = ACCENT
            elif state == "down":
                img = over(img, circle(box, cx, cy, r_hover, DOWN_ON))
                col = ICON_HI
            else:
                col = ACCENT
        else:
            if state == "over":
                img = over(img, circle(box, cx, cy, r_hover, HOVER_A))
                col = ICON_HI
            elif state == "down":
                img = over(img, circle(box, cx, cy, r_hover, DOWN_A))
                col = ACCENT
            else:
                col = off_col if (off_col is not None and on) else ICON
        g_cp = cp_on if (active and cp_on) else cp
        g = shape(size, col, cx, cy, box) if shape else glyph(g_cp, size, col, box)
        img = over(img, g)
        if active:
            d = ImageDraw.Draw(img)
            r = scf(1.7) * S
            dy = (box - scf(5)) * S
            d.ellipse([cx * S - r, dy - r, cx * S + r, dy + r], fill=ACCENT)
        return img

    if active_only:
        for st in ("up", "over", "down"):
            bake(make(st, True), bg, f"{name}_{st}")
        return
    for st in ("up", "over", "down"):
        bake(make(st, False), bg, f"{name}_{st}")
    if on:
        for st in ("up", "over", "down"):
            bake(make(st, True), bg, f"{name}_on_{st}")


def play_button(prefix, bg):
    box = PLAY_BOX
    cx = cy = box / 2
    for kind, shape in (("play", shape_play), ("pause", shape_pause)):
        for st in ("up", "over", "down"):
            img = canvas(box, box)
            r = PLAY / 2 * (0.96 if st == "down" else 1.0)
            disc = canvas(box, box)
            g = dgradient(box * S, box * S, ACCENT_STOPS)
            if st == "over":
                g = Image.blend(g, Image.new("RGBA", g.size, (255, 255, 255, 255)), 0.10)
            if st == "down":
                g = Image.blend(g, Image.new("RGBA", g.size, (0, 0, 0, 255)), 0.12)
            m = Image.new("L", (box * S, box * S), 0)
            ImageDraw.Draw(m).ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=255)
            disc.paste(g, (0, 0), m)
            gl = glow(disc, hx(ACC_B), S * scf(5.5 if st == "over" else 3.5), 0.95 if st == "over" else 0.65)
            img = over(img, gl, disc)
            hi = canvas(box, box)
            hm = Image.new("L", (box * S, box * S), 0)
            ImageDraw.Draw(hm).ellipse([(cx - r * 0.78) * S, (cy - r * 0.95) * S, (cx + r * 0.78) * S, (cy - r * 0.15) * S], fill=255)
            hm = hm.filter(ImageFilter.GaussianBlur(S * scf(4)))
            hi.paste(Image.new("RGBA", hm.size, (255, 255, 255, 48)), (0, 0), hm)
            img = over(img, hi, shape(PLAY * 0.40, ICON_HI, cx + (scf(1.5) if kind == "play" else 0), cy, box))
            bake(img, bg, f"{prefix}{kind}_{st}")


def brand_emblem(bg):
    box = sc(22)
    cx = cy = box / 2
    disc = canvas(box, box)
    g = dgradient(box * S, box * S, ACCENT_STOPS)
    m = Image.new("L", (box * S, box * S), 0)
    ImageDraw.Draw(m).ellipse([scf(1) * S, scf(1) * S, (box - scf(1)) * S, (box - scf(1)) * S], fill=255)
    disc.paste(g, (0, 0), m)
    img = over(canvas(box, box), glow(disc, hx(ACC_B), S * scf(2.5), 0.6), disc,
               shape_play(sc(9), ICON_HI, cx + scf(0.8), cy, box))
    bake(img, bg, "brand")


def idle_emblem(bg_color):
    box = sc(300)
    cx = cy = box / 2
    R = sc(52)
    for st in ("up", "over", "down"):
        img = canvas(box, box)
        halo = canvas(box, box)
        hm = Image.new("L", (box * S, box * S), 0)
        hr = scf(95)
        ImageDraw.Draw(hm).ellipse([(cx - hr) * S, (cy - hr) * S, (cx + hr) * S, (cy + hr) * S], fill=255)
        hm = hm.filter(ImageFilter.GaussianBlur(S * scf(28))).point(lambda v: int(v * (0.32 if st == "up" else 0.45)))
        halo.paste(dgradient(box * S, box * S, ACCENT_STOPS), (0, 0), hm)
        ring_img = canvas(box, box)
        g = dgradient(box * S, box * S, ACCENT_STOPS)
        m = Image.new("L", (box * S, box * S), 0)
        dm = ImageDraw.Draw(m)
        rr = R if st != "down" else R - scf(2)
        th = scf(3.5)
        dm.ellipse([(cx - rr) * S, (cy - rr) * S, (cx + rr) * S, (cy + rr) * S], fill=255)
        dm.ellipse([(cx - rr + th) * S, (cy - rr + th) * S, (cx + rr - th) * S, (cy + rr - th) * S], fill=0)
        ring_img.paste(g, (0, 0), m)
        fill = canvas(box, box)
        fm = Image.new("L", (box * S, box * S), 0)
        ImageDraw.Draw(fm).ellipse([(cx - rr + th) * S, (cy - rr + th) * S, (cx + rr - th) * S, (cy + rr - th) * S], fill=255)
        fill.paste(Image.new("RGBA", fm.size, (255, 255, 255, 16 if st == "up" else 30)), (0, 0), fm)
        gl = glow(ring_img, hx(ACC_B), S * scf(9 if st == "over" else 6), 0.85 if st == "over" else 0.5)
        tri = shape_play(sc(40), ICON_HI if st != "up" else hx("#EEF1F7", 240), cx + scf(3), cy, box)
        img = over(img, halo, gl, fill, ring_img, tri)
        bake(img, bg_flat(bg_color, box, box), f"idle_{st}")
    return box


def art_fallback(bg_color):
    box = sc(320)
    cx = cy = box / 2
    img = canvas(box, box)
    halo = canvas(box, box)
    hm = Image.new("L", (box * S, box * S), 0)
    hr = scf(110)
    ImageDraw.Draw(hm).ellipse([(cx - hr) * S, (cy - hr) * S, (cx + hr) * S, (cy + hr) * S], fill=255)
    hm = hm.filter(ImageFilter.GaussianBlur(S * scf(30))).point(lambda v: int(v * 0.35))
    halo.paste(dgradient(box * S, box * S, ACCENT_STOPS), (0, 0), hm)
    ring_img = canvas(box, box)
    rm = Image.new("L", (box * S, box * S), 0)
    dr = ImageDraw.Draw(rm)
    r1, r2 = scf(100), scf(96)
    dr.ellipse([(cx - r1) * S, (cy - r1) * S, (cx + r1) * S, (cy + r1) * S], fill=255)
    dr.ellipse([(cx - r2) * S, (cy - r2) * S, (cx + r2) * S, (cy + r2) * S], fill=0)
    ring_img.paste(dgradient(box * S, box * S, ACCENT_STOPS), (0, 0), rm)
    note = glyph(0xEC4F, sc(88), hx("#FFFFFF", 235), box)
    img = over(img, halo, glow(ring_img, hx(ACC_B), S * scf(10), 0.5), ring_img, note)
    bake(img, bg_flat(bg_color, box, box), "art_fallback")
    return box


# ---------------------------------------------------------------- sfondi a fette (bordi netti)
def panel_slices(prefix, rows, top=True, sep_line=False):
    h = len(rows)
    full_w = SLICE * 2 + sc(64)
    base = bg_from_rows(rows, 0, full_w, h)
    mask = Image.new("L", (full_w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, full_w - 1, h - 1], radius=WIN_R, fill=255)
    if top:
        ImageDraw.Draw(mask).rectangle([0, h - RADIUS - 1, full_w, h], fill=255)
    else:
        ImageDraw.Draw(mask).rectangle([0, 0, full_w, RADIUS + 1], fill=255)
    panel = Image.new("RGBA", (full_w, h), (0, 0, 0, 0))
    panel.paste(base, (0, 0), mask)
    # bordo 1px opaco lungo la sagoma
    outline = Image.new("RGBA", (full_w, h), (0, 0, 0, 0))
    ImageDraw.Draw(outline).rounded_rectangle([0, 0, full_w - 1, h - 1], radius=WIN_R, outline=hx(BORDER_C), width=1)
    om = mask.copy()
    if top:
        ImageDraw.Draw(om).rectangle([0, h - 1, full_w, h], fill=0)
    else:
        ImageDraw.Draw(om).rectangle([0, 0, full_w, 0], fill=0)
    cut = Image.new("RGBA", (full_w, h), (0, 0, 0, 0))
    cut.paste(outline, (0, 0), om)
    panel = Image.alpha_composite(panel, cut)
    d = ImageDraw.Draw(panel)
    if sep_line:
        d.line([(1, 0), (full_w - 2, 0)], fill=hx(SEP_C), width=1)
    if top:
        d.line([(CORNER, 1), (full_w - CORNER - 1, 1)], fill=hx(HILITE_C), width=1)
    panel.putalpha(panel.split()[3].point(lambda v: 255 if v >= 128 else 0))
    panel.crop((0, 0, SLICE, h)).save(os.path.join(IMG, f"{prefix}_l.png"))
    panel.crop((SLICE, 0, SLICE + 4, h)).save(os.path.join(IMG, f"{prefix}_c.png"))
    panel.crop((full_w - SLICE, 0, full_w, h)).save(os.path.join(IMG, f"{prefix}_r.png"))


HND = sc(6)  # spessore delle maniglie di ridimensionamento


def flat_images():
    Image.new("RGBA", (4, 4), hx(MID)).save(os.path.join(IMG, "bg_mid.png"))
    Image.new("RGBA", (1, 4), hx(BORDER_C)).save(os.path.join(IMG, "edge.png"))
    Image.new("RGBA", (1, sc(20)), hx("#303542")).save(os.path.join(IMG, "vsep.png"))
    Image.new("RGBA", (4, 1), hx(SEP_C)).save(os.path.join(IMG, "sep_h.png"))
    Image.new("RGBA", (HND, 4), hx(MID)).save(os.path.join(IMG, "handle_e.png"))
    bg_from_rows(BOT_ROWS, BB - HND, 4, HND).save(os.path.join(IMG, "handle_s.png"))
    bg_from_rows(PLB_ROWS, PLB - HND, 4, HND).save(os.path.join(IMG, "handle_s56.png"))


def fs_panel():
    panel = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    mask = Image.new("L", (FW, FH), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, FW - 1, FH - 1], radius=RADIUS, fill=255)
    panel.paste(Image.new("RGBA", (FW, FH), hx(FS_BG)), (0, 0), mask)
    ImageDraw.Draw(panel).rounded_rectangle([0, 0, FW - 1, FH - 1], radius=RADIUS, outline=hx(BORDER_C), width=1)
    panel.putalpha(panel.split()[3].point(lambda v: 255 if v >= 128 else 0))
    panel.save(os.path.join(IMG, "fs_panel.png"))


GRIP = sc(18)


def resize_grip(name, bg):
    box = GRIP
    img = canvas(box, box)
    d = ImageDraw.Draw(img)
    for i in range(3):
        for j in range(3):
            if i + j >= 2:
                x = (scf(5) + i * scf(4.5)) * S; y = (scf(5) + j * scf(4.5)) * S
                rr = scf(1.2) * S
                d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 255, 255, 80))
    bake(img, bg, name)


# ---------------------------------------------------------------- slider
def slider_frames(name, width, frames, bg_rows, y0, track_h=None):
    """fotogrammi impilati (traccia + riempimento progressivo), gia' composti sullo sfondo"""
    track_h = track_h or sc(4)
    Wd, Hd = width, FRAME_H
    bg = bg_from_rows(bg_rows, y0, Wd, Hd)
    sheet = Image.new("RGBA", (Wd, Hd * frames), (0, 0, 0, 0))
    ty0 = (Hd - track_h) / 2 * S
    track = Image.new("RGBA", (Wd * S, Hd * S), (0, 0, 0, 0))
    ImageDraw.Draw(track).rounded_rectangle([0, ty0, Wd * S - 1, ty0 + track_h * S - 1], radius=track_h * S / 2, fill=TRACK_A)
    track_1x = downsample(track)
    fill_full = hgradient(Wd * S, track_h * S, ACCENT_STOPS)
    for i in range(frames):
        t = i / (frames - 1)
        frame = Image.alpha_composite(bg, track_1x)
        fw = int(round(t * Wd * S))
        if fw > 0:
            fl = Image.new("RGBA", (Wd * S, Hd * S), (0, 0, 0, 0))
            m = Image.new("L", (Wd * S, track_h * S), 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, max(fw, track_h * S) - 1, track_h * S - 1], radius=track_h * S / 2, fill=255)
            fl.paste(fill_full, (0, int(ty0)), m)
            fl = Image.alpha_composite(glow(fl, hx(ACC_B), S * scf(2.4), 0.5), fl)
            frame = Image.alpha_composite(frame, downsample(fl))
        frame.putalpha(255)
        sheet.paste(frame, (0, i * Hd))
    sheet.save(os.path.join(IMG, f"{name}.png"))


def eq_frames(name, w, h, frames, bg_color, guides):
    """slider verticale bipolare: riempimento dal centro (0 dB) alla posizione del cursore.
    `guides` = [(y, colore)] righe guida da ridisegnare nel fotogramma (coprono lo sfondo)"""
    track_w = sc(4)
    bg = Image.new("RGBA", (w, h), hx(bg_color))
    d = ImageDraw.Draw(bg)
    for gy, col in guides:
        d.line([(0, gy), (w - 1, gy)], fill=col, width=1)
    sheet = Image.new("RGBA", (w, h * frames), (0, 0, 0, 0))
    tx0 = (w - track_w) / 2 * S
    track = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    ImageDraw.Draw(track).rounded_rectangle([tx0, 0, tx0 + track_w * S - 1, h * S - 1], radius=track_w * S / 2, fill=TRACK_A)
    track_1x = downsample(track)
    grad = vgradient(w * S, h * S, [(0.0, hx(ACC_C)), (0.5, hx(ACC_B)), (1.0, hx(ACC_A))])
    center = (h * S - 1) / 2
    min_len = track_w * S
    for i in range(frames):
        t = i / (frames - 1)
        ypos = (1 - t) * (h * S - 1)
        frame = Image.alpha_composite(bg, track_1x)
        y0, y1 = sorted((center, ypos))
        if y1 - y0 < min_len:
            pad = (min_len - (y1 - y0)) / 2
            y0 -= pad; y1 += pad
        m = Image.new("L", (w * S, h * S), 0)
        ImageDraw.Draw(m).rounded_rectangle([tx0, y0, tx0 + track_w * S - 1, y1], radius=track_w * S / 2, fill=255)
        fl = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        fl.paste(grad, (0, 0), m)
        fl = Image.alpha_composite(glow(fl, hx(ACC_B), S * scf(2.4), 0.5), fl)
        frame = Image.alpha_composite(frame, downsample(fl))
        frame.putalpha(255)
        sheet.paste(frame, (0, i * h))
    sheet.save(os.path.join(IMG, f"{name}.png"))


def knob(name, d, disc_color):
    """pallino bianco su un disco opaco color pannello (bordo netto), stati up/over"""
    for st in ("up", "over"):
        r = d / 2 * (1.0 if st == "up" else 1.15)
        box = int(2 * r) + sc(10)
        cx = cy = box / 2
        img = canvas(box, box)
        disc_r = r + scf(3)
        img = over(img, circle(box, cx, cy, disc_r, hx(disc_color)))
        if st == "over":
            img = over(img, circle(box, cx, cy, r + scf(1.5), ACCENT))
        img = over(img, circle(box, cx, cy, r, ICON_HI))
        mask = Image.new("L", (box, box), 0)
        ImageDraw.Draw(mask).ellipse([cx - disc_r, cy - disc_r, cx + disc_r, cy + disc_r], fill=255)
        bake(img, Image.new("RGBA", (box, box), (0, 0, 0, 0)), f"{name}_{st}", mask=mask)


def scroll_knob(bg_color):
    w, h = sc(8), sc(44)
    for st in ("up", "over"):
        img = canvas(w, h)
        m = scf(1) * S
        ImageDraw.Draw(img).rounded_rectangle([m, m, w * S - 1 - m, h * S - 1 - m], radius=scf(3) * S,
                                              fill=(255, 255, 255, 70 if st == "up" else 120))
        bake(img, bg_flat(bg_color, w, h), f"scroll_{st}")


def tree_glyphs(bg_color):
    box = sc(12)
    for name, cp in (("tree_item", None), ("tree_open", 0xE70D), ("tree_closed", 0xE76C)):
        img = canvas(box, box)
        if cp is None:
            a, b = scf(4) * S, scf(8) * S
            ImageDraw.Draw(img).ellipse([a, a, b, b], fill=(255, 255, 255, 110))
        else:
            img = over(img, glyph(cp, sc(8), hx(TXT_SEC), box))
        bake(img, bg_flat(bg_color, box, box), name)


def pill_toggle(prefix, bg, label_off, label_on):
    """interruttore a pillola con testo: {prefix}_off_* e {prefix}_on_*"""
    w, h = PILL_W, PILL_H
    f = font("Poppins-SemiBold.ttf", FONT_SMALL)
    for on in (False, True):
        for st in ("up", "over", "down"):
            img = canvas(w, h)
            d = ImageDraw.Draw(img)
            m = scf(1) * S
            box = [m, m, w * S - 1 - m, h * S - 1 - m]
            if on:
                g = hgradient(w * S, h * S, ACCENT_STOPS)
                if st == "over":
                    g = Image.blend(g, Image.new("RGBA", g.size, (255, 255, 255, 255)), 0.12)
                elif st == "down":
                    g = Image.blend(g, Image.new("RGBA", g.size, (0, 0, 0, 255)), 0.15)
                mk = Image.new("L", (w * S, h * S), 0)
                ImageDraw.Draw(mk).rounded_rectangle(box, radius=h * S / 2, fill=255)
                pill = canvas(w, h)
                pill.paste(g, (0, 0), mk)
                img = over(img, glow(pill, hx(ACC_B), S * scf(2.5), 0.5), pill)
                d = ImageDraw.Draw(img)
                d.text((w * S / 2, h * S / 2), label_on, font=f, fill=ICON_HI, anchor="mm")
            else:
                fill = (255, 255, 255, {"up": 14, "over": 30, "down": 44}[st])
                d.rounded_rectangle(box, radius=h * S / 2, fill=fill, outline=(255, 255, 255, 60), width=S)
                d.text((w * S / 2, h * S / 2), label_off, font=f,
                       fill=hx(TXT_SEC) if st == "up" else hx("#D4DAE6"), anchor="mm")
            bake(img, bg, f"{prefix}_{'on' if on else 'off'}_{st}")


# ---------------------------------------------------------------- cassetto del menu
def drawer_assets():
    """sfondo a tre fette del cassetto (bordo sinistro, separatore destro, angolo in basso come la finestra)"""
    h = DRAWER_T + 4 + DRAWER_B
    full = Image.new("RGBA", (MENU_W, h), (0, 0, 0, 0))
    mask = Image.new("L", (MENU_W, h), 0)
    dm = ImageDraw.Draw(mask)
    dm.rounded_rectangle([0, 0, MENU_W - 1, h - 1], radius=WIN_R, fill=255)
    dm.rectangle([0, 0, MENU_W, RADIUS + 1], fill=255)             # in alto nessun arrotondamento
    dm.rectangle([MENU_W - RADIUS - 1, 0, MENU_W, h], fill=255)    # a destra nessun arrotondamento
    full.paste(Image.new("RGBA", (MENU_W, h), hx(MENU_BG)), (0, 0), mask)
    # bordo: solo lato sinistro e inferiore (seguono la sagoma della finestra)
    outline = Image.new("RGBA", (MENU_W, h), (0, 0, 0, 0))
    ImageDraw.Draw(outline).rounded_rectangle([0, 0, MENU_W - 1, h - 1], radius=WIN_R, outline=hx(BORDER_C), width=1)
    om = Image.new("L", (MENU_W, h), 0)
    ImageDraw.Draw(om).rectangle([0, 0, 0, h - 1], fill=255)                 # colonna sinistra
    ImageDraw.Draw(om).rectangle([0, h - RADIUS - 1, RADIUS, h - 1], fill=255)   # angolo in basso a sinistra
    ImageDraw.Draw(om).rectangle([0, h - 1, MENU_W - 1, h - 1], fill=255)    # riga inferiore
    cut = Image.new("RGBA", (MENU_W, h), (0, 0, 0, 0))
    cut.paste(outline, (0, 0), om)
    full = Image.alpha_composite(full, cut)
    d = ImageDraw.Draw(full)
    d.line([(MENU_W - 1, 0), (MENU_W - 1, h - 2)], fill=hx(SEP_C), width=1)   # separatore verso il video
    full.putalpha(full.split()[3].point(lambda v: 255 if v >= 128 else 0))
    full.crop((0, 0, MENU_W, DRAWER_T)).save(os.path.join(IMG, "drawer_t.png"))
    full.crop((0, DRAWER_T, MENU_W, DRAWER_T + 4)).save(os.path.join(IMG, "drawer_c.png"))
    full.crop((0, h - DRAWER_B, MENU_W, h)).save(os.path.join(IMG, "drawer_b.png"))


def menu_assets():
    """immagini delle voci del cassetto (tre stati); ritorna (y delle voci, y dei separatori) relative al cassetto"""
    ys, seps = [], []
    y = MENU_PAD
    for it in MENU_ITEMS:
        if it is None:
            seps.append(y + MENU_SEP // 2)
            y += MENU_SEP
        else:
            ys.append(y)
            y += MENU_IH
    iw = MENU_W - 2 * MENU_PAD
    font_l = font("Poppins-Medium.ttf", FONT_TEXT)
    font_s = font("Poppins-Regular.ttf", FONT_SMALL)
    bg = bg_flat(MENU_BG, iw, MENU_IH)
    for it in MENU_ITEMS + [MENU_FOOT]:
        if it is None:
            continue
        iid, cp, label, shortcut, submenu, _ = it
        for st in ("up", "over", "down"):
            img = canvas(iw, MENU_IH)
            dd = ImageDraw.Draw(img)
            if st == "over":
                dd.rounded_rectangle([0, 0, iw * S - 1, MENU_IH * S - 1], radius=scf(7) * S, fill=(255, 255, 255, 24))
            elif st == "down":
                dd.rounded_rectangle([0, 0, iw * S - 1, MENU_IH * S - 1], radius=scf(7) * S, fill=hx(ACC_B, 70))
            icon_col = hx("#A3ABBE") if st == "up" else ICON_HI
            label_col = hx("#E6EAF2") if st == "up" else ICON_HI
            hint_col = hx(TXT_DIM) if st == "up" else hx("#B8C0D0")
            g = accent_glyph(cp, sc(15), MENU_IH) if it is MENU_FOOT else glyph(cp, sc(15), icon_col, MENU_IH)
            img.alpha_composite(g, (sc(6) * S, 0))
            dd = ImageDraw.Draw(img)
            dd.text((sc(38) * S, MENU_IH * S / 2), label, font=font_l, fill=label_col, anchor="lm")
            if submenu:
                ch = glyph(0xE76C, sc(9), hint_col, MENU_IH)
                img.alpha_composite(ch, ((iw - sc(10) - MENU_IH) * S, 0))
            elif shortcut:
                dd.text(((iw - sc(12)) * S, MENU_IH * S / 2), shortcut, font=font_s, fill=hint_col, anchor="rm")
            bake(img, bg, f"mi_{iid}_{st}")
    return ys, seps


# ---------------------------------------------------------------- equalizzatore
def eq_columns():
    """x centrale della preamplificazione e delle 10 bande"""
    pre = EQ_MXL + EQ_PRE_W // 2
    bands = [EQ_MXL + EQ_PRE_W + i * EQ_PITCH + EQ_PITCH // 2 for i in range(10)]
    return pre, bands


def eq_assets():
    """sfondo della finestra equalizzatore (titolo, guide dB, etichette), fotogrammi degli slider, pillola"""
    r = 0 if NATIVE_FRAME else sc(12)    # raggio della sagoma
    hl = CORNER if NATIVE_FRAME else r   # il filetto chiaro parte dopo l'angolo
    panel = Image.new("RGBA", (EQ_W, EQ_H), (0, 0, 0, 0))
    mask = Image.new("L", (EQ_W, EQ_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, EQ_W - 1, EQ_H - 1], radius=r, fill=255)
    base = Image.new("RGBA", (EQ_W, EQ_H), hx(MID))
    base.paste(bg_from_rows(TOP_ROWS, 0, EQ_W, TB), (0, 0))
    panel.paste(base, (0, 0), mask)
    d = ImageDraw.Draw(panel)
    d.line([(1, TB), (EQ_W - 2, TB)], fill=hx(SEP_C), width=1)
    d.line([(hl, 1), (EQ_W - hl - 1, 1)], fill=hx(HILITE_C), width=1)
    # guide: +20 dB (alto), 0 dB (centro), -20 dB (basso)
    y_top = EQ_TY
    y_mid = EQ_TY + (EQ_TH - 1) // 2
    y_bot = EQ_TY + EQ_TH - 1
    guides = [(y_top, hx("#1C2029")), (y_mid, hx("#2E3340")), (y_bot, hx("#1C2029"))]
    gx0, gx1 = EQ_MXL - sc(6), EQ_W - EQ_MXR + sc(6)
    for gy, col in guides:
        d.line([(gx0, gy), (gx1, gy)], fill=col, width=1)
    pre, bands = eq_columns()
    sepx = EQ_MXL + EQ_PRE_W
    d.line([(sepx, EQ_TY - sc(4)), (sepx, EQ_TY + EQ_TH + sc(4))], fill=hx(SEP_C), width=1)
    d.rounded_rectangle([0, 0, EQ_W - 1, EQ_H - 1], radius=r, outline=hx("#2C313D"), width=1)
    # etichette (disegnate a 4x e composte)
    lab = canvas(EQ_W, EQ_H)
    dl = ImageDraw.Draw(lab)
    f_lbl = font("Poppins-Medium.ttf", FONT_SMALL)
    f_db = font("Poppins-Regular.ttf", sc(9))
    for cx, txt in [(pre, "Pre")] + list(zip(bands, EQ_BANDS)):
        dl.text((cx * S, (EQ_LBL_Y + sc(7)) * S), txt, font=f_lbl, fill=hx(TXT_SEC), anchor="mm")
    for gy, txt in ((y_top, "+20"), (y_mid, "0"), (y_bot, "−20")):
        dl.text(((EQ_MXL - sc(10)) * S, gy * S), txt, font=f_db, fill=hx(TXT_DIM), anchor="rm")
    panel = Image.alpha_composite(panel, downsample(lab))
    panel.putalpha(mask.point(lambda v: 255 if v >= 128 else 0))
    panel.save(os.path.join(IMG, "eq_bg.png"))
    # fotogrammi (le guide passano sotto le tracce: vengono ridisegnate nel fotogramma)
    eq_frames("eq_frames", EQ_FW, EQ_TH, EQ_FRAMES, MID, [(gy - EQ_TY, col) for gy, col in guides])
    knob("eknob", sc(11), MID)
    # pillola Attivo/Spento nella barra del titolo
    pill_y = (TB - PILL_H) // 2
    pill_toggle("eq", bg_from_rows(TOP_ROWS, pill_y, PILL_W, PILL_H), "Spento", "Attivo")


# ---------------------------------------------------------------- theme.xml
def build_xml(idle_box, art_box, seek_w, vol_w, fs_seek_w, menu_ys, sep_ys):
    b = BTN; pb = PLAY_BOX; play_off = PLAY_PAD
    L = []; A = L.append
    A('<?xml version="1.0" encoding="UTF-8"?>')
    A('<!DOCTYPE Theme PUBLIC "-//VideoLAN//DTD VLC Skins V2.0//EN" "skin.dtd">')
    A(f'<Theme version="2.0" magnet="{sc(16)}" alpha="255" movealpha="235">')
    A('  <ThemeInfo name="Aurora" author="Domenico Tatone" email="" webpage=""/>')
    A(f'  <Font id="fontTitle" file="fonts/Poppins-SemiBold.ttf" size="{FONT_TITLE}"/>')
    A(f'  <Font id="fontText" file="fonts/Poppins-Medium.ttf" size="{FONT_TEXT}"/>')
    A(f'  <Font id="fontList" file="fonts/Poppins-Regular.ttf" size="{FONT_TEXT}"/>')
    for bm in sorted(f[:-4] for f in os.listdir(IMG) if f.endswith(".png")):
        A(f'  <Bitmap id="{bm}" file="images/{bm}.png" alphacolor="#FF00FF"/>')

    def slices(prefix, y, h, width, lt, rb, extra="", x0=0):
        return [
            f'<Image image="{prefix}_l" x="{x0}" y="{y}" width="{SLICE}" height="{h}" lefttop="{lt}" rightbottom="{lt}" action="move" resize="scale"{extra}/>',
            f'<Image image="{prefix}_c" x="{x0 + SLICE}" y="{y}" width="{width - 2 * SLICE}" height="{h}" lefttop="{lt}" rightbottom="{rb}" action="move" resize="scale"{extra}/>',
            f'<Image image="{prefix}_r" x="{x0 + width - SLICE}" y="{y}" width="{SLICE}" height="{h}" lefttop="{rb}" rightbottom="{rb}" action="move" resize="scale"{extra}/>',
        ]

    def btn(x, y, name, action, tip, lt="lefttop", rb="lefttop", extra=""):
        return (f'<Button x="{x}" y="{y}" up="{name}_up" over="{name}_over" down="{name}_down" '
                f'action="{action}" tooltiptext="{tip}" lefttop="{lt}" rightbottom="{rb}"{extra}/>')

    def chk(x, y, n1, n2, state, a1, a2, t1, t2, lt="lefttop", rb="lefttop", extra=""):
        return (f'<Checkbox x="{x}" y="{y}" state="{state}" up1="{n1}_up" over1="{n1}_over" down1="{n1}_down" '
                f'up2="{n2}_up" over2="{n2}_over" down2="{n2}_down" action1="{a1}" action2="{a2}" '
                f'tooltiptext1="{t1}" tooltiptext2="{t2}" lefttop="{lt}" rightbottom="{rb}"{extra}/>')

    def text(txt, x, y, width, fnt, color, align, lt="lefttop", rb="lefttop", scrolling="none", extra=""):
        return (f'<Text text="{txt}" x="{x}" y="{y}" width="{width}" font="{fnt}" color="{color}" '
                f'alignment="{align}" scrolling="{scrolling}" focus="false" lefttop="{lt}" rightbottom="{rb}"{extra}/>')

    def resize_handles(width, height, bot_h, handle_s, grip, x_s=RADIUS):
        return [
            f'<Image image="handle_e" x="{width - HND}" y="{TB}" width="{HND}" height="{height - TB - bot_h}" lefttop="righttop" rightbottom="rightbottom" action="resizeE" resize="scale"/>',
            f'<Image image="{handle_s}" x="{x_s}" y="{height - HND}" width="{width - x_s - GRIP - sc(8)}" height="{HND}" lefttop="leftbottom" rightbottom="rightbottom" action="resizeS" resize="scale"/>',
            f'<Image image="{grip}" x="{width - GRIP - sc(4)}" y="{height - GRIP - sc(4)}" lefttop="rightbottom" rightbottom="rightbottom" action="resizeSE"/>',
        ]

    vh = H - TB - BB
    cy = (TB - CHR) // 2                       # y dei pulsanti nelle barre del titolo
    t_title = ty(TB // 2, FONT_TITLE)          # y dei titoli

    # ------------------------------------------------ finestra principale: due layout (senza / con cassetto)
    def main_layout(lid, drawer):
        sfx = "M" if drawer else ""
        vx = MENU_W if drawer else 0
        vw = W - vx
        A(f'    <Layout id="{lid}" width="{W}" height="{H}" minwidth="{MINW}" minheight="{MINH}" maxwidth="99999" maxheight="99999">')
        # area video
        A(f'      <Panel id="videoPanel{sfx}" x="{vx}" y="{TB}" width="{vw}" height="{vh}" lefttop="lefttop" rightbottom="rightbottom">')
        A(f'        <Image image="bg_mid" x="0" y="0" width="{vw}" height="{vh}" lefttop="lefttop" rightbottom="rightbottom" action="move" resize="scale"/>')
        if not drawer:
            A(f'        <Image image="edge" x="0" y="0" width="1" height="{vh}" lefttop="lefttop" rightbottom="leftbottom" resize="scale"/>')
        A(f'        <Image image="edge" x="{vw - 1}" y="0" width="1" height="{vh}" lefttop="righttop" rightbottom="rightbottom" resize="scale"/>')
        A(f'        <Image image="art_fallback" x="{(vw - art_box) // 2}" y="{(vh - art_box) // 2}" width="{art_box}" height="{art_box}" xkeepratio="true" ykeepratio="true" art="true" resize="fit" visible="not vlc.isStopped and not vlc.hasVout"/>')
        # emblema + testo in un unico pannello centrato: restano sempre allineati tra loro
        A(f'        <Panel id="idleGroup{sfx}" x="{(vw - idle_box) // 2}" y="{(vh - idle_box) // 2}" width="{idle_box}" height="{idle_box}" lefttop="lefttop" rightbottom="lefttop" xkeepratio="true" ykeepratio="true">')
        A(f'          <Button x="0" y="0" up="idle_up" over="idle_over" down="idle_down" action="dialogs.fileSimple()" tooltiptext="Apri un file" visible="vlc.isStopped"/>')
        A("          " + text("Apri un file oppure trascinalo qui", (idle_box - sc(420)) // 2, idle_box - sc(58), sc(420), "fontText", TXT_SEC, "center",
                              extra=' visible="vlc.isStopped"'))
        A('        </Panel>')
        A(f'        <Video id="video{sfx}" x="0" y="0" width="{vw}" height="{vh}" lefttop="lefttop" rightbottom="rightbottom" autoresize="false" visible="vlc.hasVout"/>')
        A('      </Panel>')
        # barra titolo
        A(f'      <Panel id="topPanel{sfx}" x="0" y="0" width="{W}" height="{TB}" lefttop="lefttop" rightbottom="righttop">')
        for tag in slices("bg_top", 0, TB, W, "lefttop", "righttop", ' action2="main.maximize()" visible="not main.isMaximized"'):
            A("        " + tag)
        for tag in slices("bg_top", 0, TB, W, "lefttop", "righttop", ' action2="main.unmaximize()" visible="main.isMaximized"'):
            A("        " + tag)
        A("        " + chk(sc(12), cy, "menu", "menu_on", "mainMenuLayout.isActive", "main.setLayout(mainMenuLayout)", CLOSE_MENU, "Menu", "Chiudi menu"))
        A(f'        <Image image="brand" x="{sc(52)}" y="{(TB - sc(22)) // 2}" action="move"/>')
        A("        " + text("$N", sc(200), t_title, W - sc(400), "fontTitle", TXT_PRI, "center", "lefttop", "righttop", "auto", ' visible="not vlc.isStopped"'))
        A("        " + text("Aurora", sc(200), t_title, W - sc(400), "fontTitle", TXT_SEC, "center", "lefttop", "righttop", "none", ' visible="vlc.isStopped"'))
        rx = W - sc(12) - CHR
        A("        " + btn(rx, cy, "close", "vlc.quit()", "Chiudi", "righttop", "righttop")); rx -= CHR + sc(4)
        A("        " + chk(rx, cy, "maximize", "restore", "main.isMaximized", "main.maximize()", "main.unmaximize()", "Ingrandisci", "Ripristina", "righttop", "righttop")); rx -= CHR + sc(4)
        A("        " + btn(rx, cy, "minimize", "vlc.minimize()", "Riduci a icona", "righttop", "righttop")); rx -= CHR + sc(4)
        A("        " + chk(rx, cy, "pin", "pin_on", "vlc.isOnTop", "vlc.onTop()", "vlc.onTop()", "Sempre in primo piano", "Disattiva primo piano", "righttop", "righttop"))
        A('      </Panel>')
        # barra comandi
        A(f'      <Panel id="bottomPanel{sfx}" x="0" y="{H - BB}" width="{W}" height="{BB}" lefttop="leftbottom" rightbottom="rightbottom">')
        for tag in slices("bg_bot", 0, BB, W, "lefttop", "righttop"):
            A("        " + tag)
        t_time = ty(SEEK_Y + FRAME_H // 2, FONT_TEXT)
        if not drawer:
            A("        " + text("$T", sc(22), t_time, sc(70), "fontText", TXT_SEC, "left"))
        A("        " + text("$D", W - sc(92), t_time, sc(70), "fontText", TXT_SEC, "right", "righttop", "righttop"))
        A(f'        <Slider x="{sc(100)}" y="{SEEK_Y}" points="(0,{FRAME_H // 2}),({seek_w - 1},{FRAME_H // 2})" thickness="{sc(22)}" value="time" tooltiptext="$T / $D" up="knob_up" over="knob_over" down="knob_over" lefttop="lefttop" rightbottom="righttop">')
        A(f'          <SliderBackground image="seek_frames" nbhoriz="1" nbvert="{SEEK_FRAMES}"/>')
        A('        </Slider>')
        if not drawer:
            A("        " + btn(sc(16), BY, "open_file", "dialogs.fileSimple()", "Apri file"))
            A("        " + btn(sc(56), BY, "open_folder", "dialogs.directory()", "Apri cartella"))
            A("        " + btn(sc(96), BY, "open_disc", "dialogs.disc()", "Apri disco"))
            # velocita' di riproduzione: [<<] 1× [>>] (solo durante la riproduzione)
            vis_play = ' visible="not vlc.isStopped"'
            A(f'        <Image image="vsep" x="{sc(140)}" y="{BY + (b - sc(20)) // 2}" width="1" height="{sc(20)}" resize="scale" visible="not vlc.isStopped"/>')
            sx = sc(148)
            A("        " + btn(sx, BY, "slower", "vlc.slower()", "Rallenta (passi fissi di VLC; tasto [ per passi di 0,1)", extra=vis_play)); sx += b + sc(2)
            A("        " + text("$R×", sx, ty(BY + b // 2, FONT_TEXT), sc(46), "fontText", TXT_SEC, "center", extra=vis_play)); sx += sc(46) + sc(2)
            A("        " + btn(sx, BY, "faster", "vlc.faster()", "Accelera (passi fissi di VLC; tasto ] per passi di 0,1)", extra=vis_play))
        cw = b + sc(8) + b + sc(10) + pb + sc(10) + b + sc(8) + b
        cx0 = (W - cw) // 2
        A(f'        <Panel id="transport{sfx}" x="{cx0}" y="{BY - sc(10) - play_off}" width="{cw}" height="{pb}" lefttop="lefttop" rightbottom="lefttop" xkeepratio="true">')
        x = 0; tyb = sc(10) + play_off
        A("          " + chk(x, tyb, "shuffle", "shuffle_on", "playlist.isRandom", "playlist.setRandom(true)", "playlist.setRandom(false)", "Riproduzione casuale", "Disattiva casuale")); x += b + sc(8)
        A("          " + btn(x, tyb, "prev", "playlist.previous()", "Precedente")); x += b + sc(10)
        A("          " + chk(x, 0, "play", "pause", "vlc.isPlaying", "vlc.play()", "vlc.pause()", "Riproduci", "Pausa")); x += pb + sc(10)
        A("          " + btn(x, tyb, "next", "playlist.next()", "Successivo")); x += b + sc(8)
        # ripetizione a tre stati: spenta -> tutta la playlist -> un solo brano -> spenta
        A("          " + chk(x, tyb, "loop", "loop_on", "playlist.isLoop", "playlist.setLoop(true)", "playlist.setLoop(false);playlist.setRepeat(true)",
                             "Ripeti la playlist", "Ripeti un solo brano", extra=' visible="not playlist.isRepeat"'))
        A("          " + chk(x, tyb, "repeat1", "repeat1_on", "playlist.isRepeat", "playlist.setRepeat(true)", "playlist.setRepeat(false)",
                             "Ripeti un solo brano", "Disattiva ripetizione", extra=' visible="playlist.isRepeat and true"'))
        # nota: la visibilita' NON deve essere lo stesso oggetto della variabile di stato (CtrlGeneric::onUpdate
        # tratterebbe il cambiamento solo come visibilita' e il set di immagini non verrebbe mai aggiornato)
        A('        </Panel>')
        rx = W - sc(16) - b
        A("        " + btn(rx, BY, "fullscreen", "vlc.fullscreen()", "Schermo intero", "righttop", "righttop")); rx -= sc(12) + vol_w
        A(f'        <Slider x="{rx}" y="{VOL_Y}" points="(0,{FRAME_H // 2}),({vol_w - 1},{FRAME_H // 2})" thickness="{sc(20)}" value="volume" tooltiptext="Volume: $V%" up="vknob_up" over="vknob_over" down="vknob_over" lefttop="righttop" rightbottom="righttop">')
        A(f'          <SliderBackground image="vol_frames" nbhoriz="1" nbvert="{VOL_FRAMES}"/>')
        A('        </Slider>')
        rx -= sc(4) + b
        A("        " + chk(rx, BY, "volume", "mute", "vlc.isMute", "vlc.mute()", "vlc.mute()", "Muto", "Riattiva audio", "righttop", "righttop")); rx -= sc(8) + b
        A("        " + chk(rx, BY, "playlist", "playlist_on", "playlist.isVisible", "playlist.show()", "playlist.hide()", "Mostra playlist", "Nascondi playlist", "righttop", "righttop")); rx -= sc(4) + b
        A("        " + btn(rx, BY, "stop", "vlc.stop()", "Stop", "righttop", "righttop"))
        A('      </Panel>')
        # cassetto del menu (sopra le barre, dal bordo inferiore del titolo al fondo della finestra)
        if drawer:
            dh = H - TB
            A(f'      <Panel id="drawer" x="0" y="{TB}" width="{MENU_W}" height="{dh}" lefttop="lefttop" rightbottom="leftbottom">')
            A(f'        <Image image="drawer_t" x="0" y="0" width="{MENU_W}" height="{DRAWER_T}" lefttop="lefttop" rightbottom="lefttop" action="move" resize="scale"/>')
            A(f'        <Image image="drawer_c" x="0" y="{DRAWER_T}" width="{MENU_W}" height="{dh - DRAWER_T - DRAWER_B}" lefttop="lefttop" rightbottom="leftbottom" action="move" resize="scale"/>')
            A(f'        <Image image="drawer_b" x="0" y="{dh - DRAWER_B}" width="{MENU_W}" height="{DRAWER_B}" lefttop="leftbottom" rightbottom="leftbottom" action="move" resize="scale"/>')
            for sy in sep_ys:
                A(f'        <Image image="sep_h" x="{sc(14)}" y="{sy}" width="{MENU_W - sc(29)}" height="1" resize="scale"/>')
            for it, y in zip([i for i in MENU_ITEMS if i], menu_ys):
                iid, _, label, _, _, action = it
                A(f'        <Button x="{MENU_PAD}" y="{y}" up="mi_{iid}_up" over="mi_{iid}_over" down="mi_{iid}_down" action="{action}" tooltiptext=""/>')
            # voce in fondo: segue il bordo inferiore del cassetto quando la finestra cambia altezza
            fid, fy = MENU_FOOT[0], dh - MENU_PAD - MENU_IH
            A(f'        <Image image="sep_h" x="{sc(14)}" y="{fy - MENU_SEP + MENU_SEP // 2}" width="{MENU_W - sc(29)}" height="1" lefttop="leftbottom" rightbottom="leftbottom" resize="scale"/>')
            A(f'        <Button x="{MENU_PAD}" y="{fy}" up="mi_{fid}_up" over="mi_{fid}_over" down="mi_{fid}_down" action="{MENU_FOOT[5]}" tooltiptext="" lefttop="leftbottom" rightbottom="leftbottom"/>')
            A('      </Panel>')
        for tag in resize_handles(W, H, BB, "handle_s", "grip", x_s=(MENU_W if drawer else RADIUS)):
            A("      " + tag)
        A(f'      <Anchor x="{W}" y="0" lefttop="righttop" priority="10" range="{sc(28)}"/>')
        A('    </Layout>')

    A('  <Window id="main" position="Center" dragdrop="true" playondrop="true">')
    main_layout("mainLayout", False)
    main_layout("mainMenuLayout", True)
    A('  </Window>')

    # ------------------------------------------------ playlist
    pl_visible = "true" if os.environ.get("AURORA_DEBUG_PLAYLIST") else "false"
    A(f'  <Window id="playlist" position="East" xmargin="{sc(48)}" visible="{pl_visible}" dragdrop="true" playondrop="false">')
    A(f'    <Layout id="playlistLayout" width="{PW}" height="{PH}" minwidth="{sc(280)}" minheight="{sc(320)}" maxwidth="99999" maxheight="99999">')
    A(f'      <Panel id="plTop" x="0" y="0" width="{PW}" height="{TB}" lefttop="lefttop" rightbottom="righttop">')
    for tag in slices("bg_top", 0, TB, PW, "lefttop", "righttop"):
        A("        " + tag)
    A("        " + text("Playlist", sc(20), t_title, sc(200), "fontTitle", TXT_PRI, "left"))
    A("        " + btn(PW - sc(12) - CHR, cy, "close", "playlist.hide()", "Nascondi playlist", "righttop", "righttop"))
    A('      </Panel>')
    mh = PH - TB - PLB
    A(f'      <Panel id="plMid" x="0" y="{TB}" width="{PW}" height="{mh}" lefttop="lefttop" rightbottom="rightbottom">')
    A(f'        <Image image="bg_mid" x="0" y="0" width="{PW}" height="{mh}" lefttop="lefttop" rightbottom="rightbottom" action="move" resize="scale"/>')
    A(f'        <Image image="edge" x="0" y="0" width="1" height="{mh}" lefttop="lefttop" rightbottom="leftbottom" resize="scale"/>')
    A(f'        <Image image="edge" x="{PW - 1}" y="0" width="1" height="{mh}" lefttop="righttop" rightbottom="rightbottom" resize="scale"/>')
    tw = PW - sc(14) - sc(24); th = mh - sc(12)
    A(f'        <Playtree id="tree" x="{sc(14)}" y="{sc(6)}" width="{tw}" height="{th}" font="fontList" fgcolor="#C9CFDC" playcolor="{ACC_B}" bgcolor1="{MID}" bgcolor2="#13161E" selcolor="#2A3040" flat="false" itemimage="tree_item" openimage="tree_open" closedimage="tree_closed" lefttop="lefttop" rightbottom="rightbottom">')
    A(f'          <Slider x="{PW - sc(16)}" y="{sc(6)}" points="(0,0),(0,{th - 1})" thickness="{sc(14)}" up="scroll_up" over="scroll_over" down="scroll_over" lefttop="righttop" rightbottom="rightbottom"/>')
    A('        </Playtree>')
    A('      </Panel>')
    A(f'      <Panel id="plBot" x="0" y="{PH - PLB}" width="{PW}" height="{PLB}" lefttop="leftbottom" rightbottom="rightbottom">')
    for tag in slices("bg_bot56", 0, PLB, PW, "lefttop", "righttop"):
        A("        " + tag)
    py = (PLB - b) // 2
    A("        " + btn(sc(14), py, "pl_add", "playlist.add()", "Aggiungi file"))
    A("        " + btn(sc(54), py, "pl_remove", "playlist.del()", "Rimuovi selezionati"))
    A("        " + btn(sc(94), py, "pl_sort", "playlist.sort()", "Ordina"))
    A("        " + btn(PW - sc(14) - b, py, "pl_save", "playlist.save()", "Salva playlist", "righttop", "righttop"))
    A("        " + btn(PW - sc(14) - b - sc(40), py, "pl_load", "playlist.load()", "Carica playlist", "righttop", "righttop"))
    A('      </Panel>')
    for tag in resize_handles(PW, PH, PLB, "handle_s56", "grip56"):
        A("      " + tag)
    A(f'      <Anchor x="0" y="0" lefttop="lefttop" priority="5" range="{sc(28)}"/>')
    A(f'      <Anchor x="0" y="{PH}" lefttop="leftbottom" priority="7" range="{sc(28)}"/>')
    A('    </Layout>')
    A('  </Window>')

    # ------------------------------------------------ equalizzatore
    pre, bands = eq_columns()
    A('  <Window id="eqwin" position="Center" visible="false" dragdrop="false">')
    A(f'    <Layout id="eqLayout" width="{EQ_W}" height="{EQ_H}">')
    A('      <Image image="eq_bg" x="0" y="0" action="move"/>')
    A("      " + text("Equalizzatore", sc(18), t_title, sc(220), "fontTitle", TXT_PRI, "left"))
    close_x = EQ_W - sc(12) - CHR
    A("      " + btn(close_x, cy, "close", "eqwin.hide()", "Chiudi"))
    A("      " + chk(close_x - sc(10) - PILL_W, (TB - PILL_H) // 2, "eq_off", "eq_on", "equalizer.isEnabled", "equalizer.enable()", "equalizer.disable()",
                     "Attiva l'equalizzatore", "Disattiva l'equalizzatore"))

    def vslider(cx, value, tip):
        return (f'<Slider x="{cx - EQ_FW // 2}" y="{EQ_TY}" points="({EQ_FW // 2},{EQ_TH - 1}),({EQ_FW // 2},0)" thickness="{sc(16)}" '
                f'value="{value}" tooltiptext="{tip}" up="eknob_up" over="eknob_over" down="eknob_over">'
                f'<SliderBackground image="eq_frames" nbhoriz="1" nbvert="{EQ_FRAMES}"/></Slider>')
    A("      " + vslider(pre, "equalizer.preamp", "Preamplificazione"))
    for i, cx in enumerate(bands):
        A("      " + vslider(cx, f"equalizer.band({i})", EQ_TIPS[i]))
    A(f'      <Anchor x="0" y="0" lefttop="lefttop" priority="6" range="{sc(28)}"/>')
    A('    </Layout>')
    A('  </Window>')

    # ------------------------------------------------ controller schermo intero
    def fs_window(win_id, layout_id, suffix, win_attrs):
        A(f'  <Window id="{win_id}" {win_attrs}>')
        A(f'    <Layout id="{layout_id}" width="{FW}" height="{FH}">')
        A('      <Image image="fs_panel" x="0" y="0" action="move"/>')
        t_fs = ty(FS_SEEK_Y + FRAME_H // 2, FONT_TEXT)
        A("      " + text("$T", sc(22), t_fs, sc(64), "fontText", TXT_SEC, "left"))
        A("      " + text("$D", FW - sc(86), t_fs, sc(64), "fontText", TXT_SEC, "right"))
        A(f'      <Slider x="{sc(92)}" y="{FS_SEEK_Y}" points="(0,{FRAME_H // 2}),({fs_seek_w - 1},{FRAME_H // 2})" thickness="{sc(22)}" value="time" tooltiptext="$T / $D" up="fknob_up" over="fknob_over" down="fknob_over">')
        A(f'        <SliderBackground image="fs_seek_frames" nbhoriz="1" nbvert="{SEEK_FRAMES}"/>')
        A('      </Slider>')
        A("      " + text("$N", sc(22), ty(FS_BY + b // 2, FONT_TEXT), sc(230), "fontText", TXT_PRI, "left", scrolling="auto"))
        cw2 = b + sc(8) + pb + sc(8) + b + sc(8) + b
        cx2 = (FW - cw2) // 2
        A(f'      <Panel id="fsTransport{suffix}" x="{cx2}" y="{FS_BY - sc(10) - play_off}" width="{cw2}" height="{pb}" lefttop="lefttop" rightbottom="lefttop" xkeepratio="true">')
        x = 0; tyb = sc(10) + play_off
        A("        " + btn(x, tyb, "fs_prev", "playlist.previous()", "Precedente")); x += b + sc(8)
        A("        " + chk(x, 0, "fs_play", "fs_pause", "vlc.isPlaying", "vlc.play()", "vlc.pause()", "Riproduci", "Pausa")); x += pb + sc(8)
        A("        " + btn(x, tyb, "fs_next", "playlist.next()", "Successivo")); x += b + sc(8)
        A("        " + btn(x, tyb, "fs_stop", "vlc.stop()", "Stop"))
        A('      </Panel>')
        rx = FW - sc(16) - b
        A("      " + btn(rx, FS_BY, "fs_exit", "vlc.fullscreen()", "Esci da schermo intero", "righttop", "righttop")); rx -= sc(12) + vol_w
        A(f'      <Slider x="{rx}" y="{FS_VOL_Y}" points="(0,{FRAME_H // 2}),({vol_w - 1},{FRAME_H // 2})" thickness="{sc(20)}" value="volume" tooltiptext="Volume: $V%" up="fvknob_up" over="fvknob_over" down="fvknob_over" lefttop="righttop" rightbottom="righttop">')
        A(f'        <SliderBackground image="fs_vol_frames" nbhoriz="1" nbvert="{VOL_FRAMES}"/>')
        A('      </Slider>')
        rx -= sc(4) + b
        A("      " + chk(rx, FS_BY, "fs_volume", "fs_mute", "vlc.isMute", "vlc.mute()", "vlc.mute()", "Muto", "Riattiva audio", "righttop", "righttop"))
        A('    </Layout>')
        A('  </Window>')

    fs_window("fullscreenController", "fsLayout", "", f'position="South" ymargin="{sc(40)}" visible="false"')
    if DEBUG_FS:
        fs_window("fstest", "fsLayout2", "2", 'position="Center" visible="true"')
    A('</Theme>')
    with open(os.path.join(OUT, "theme.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


# ---------------------------------------------------------------- main
def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(IMG)
    shutil.copytree(FONTS_SRC, os.path.join(OUT, "fonts"))

    # sfondi
    panel_slices("bg_top", TOP_ROWS, top=True)
    panel_slices("bg_bot", BOT_ROWS, top=False, sep_line=True)
    panel_slices("bg_bot56", PLB_ROWS, top=False, sep_line=True)
    flat_images()
    fs_panel()
    drawer_assets()
    resize_grip("grip", bg_from_rows(BOT_ROWS, BB - GRIP - sc(4), GRIP, GRIP))
    resize_grip("grip56", bg_from_rows(PLB_ROWS, PLB - GRIP - sc(4), GRIP, GRIP))

    # barra titolo
    top_btn_bg = bg_from_rows(TOP_ROWS, (TB - CHR) // 2, CHR, CHR)
    brand_emblem(bg_from_rows(TOP_ROWS, (TB - sc(22)) // 2, sc(22), sc(22)))
    icon_button("menu", 0xE700, top_btn_bg, size=sc(14), box=CHR, on=True)
    icon_button("minimize", 0xE921, top_btn_bg, size=sc(12), box=CHR)
    icon_button("maximize", 0xE922, top_btn_bg, size=sc(12), box=CHR)
    icon_button("restore", 0xE923, top_btn_bg, size=sc(12), box=CHR)
    icon_button("close", 0xE8BB, top_btn_bg, size=sc(12), box=CHR, danger=True)
    icon_button("pin", 0xE718, top_btn_bg, size=sc(14), box=CHR)
    icon_button("pin_on", 0xE841, top_btn_bg, size=sc(14), box=CHR, active_only=True)

    # barra comandi
    bot_btn_bg = bg_from_rows(BOT_ROWS, BY, BTN, BTN)
    for name, cp in (("open_file", 0xE8E5), ("open_folder", 0xE8B7), ("open_disc", 0xE958), ("volume", 0xE767)):
        icon_button(name, cp, bot_btn_bg, size=sc(19))
    icon_button("mute", 0xE74F, bot_btn_bg, size=sc(19), active_only=True)
    for name, cp in (("shuffle", 0xE8B1), ("loop", 0xE8EE), ("repeat1", 0xE8ED), ("playlist", 0xE90B)):
        icon_button(name, cp, bot_btn_bg, size=sc(19), on=True, off_col=ICON_OFF)
    icon_button("slower", 0xEB9E, bot_btn_bg, size=sc(16))
    icon_button("faster", 0xEB9D, bot_btn_bg, size=sc(16))
    icon_button("fullscreen", 0xE740, bot_btn_bg, size=sc(18))
    for name in ("prev", "next", "stop"):
        icon_button(name, 0, bot_btn_bg, size=sc(17), shape=SHAPES[name])
    play_button("", bg_from_rows(BOT_ROWS, BY - sc(10) - PLAY_PAD, PLAY_BOX, PLAY_BOX))

    # playlist
    pl_btn_bg = bg_from_rows(PLB_ROWS, (PLB - BTN) // 2, BTN, BTN)
    for name, cp in (("pl_add", 0xE710), ("pl_remove", 0xE738), ("pl_sort", 0xE8CB), ("pl_save", 0xE74E), ("pl_load", 0xE8DA)):
        icon_button(name, cp, pl_btn_bg, size=sc(18))
    scroll_knob(MID)
    tree_glyphs(MID)

    # controller schermo intero (sfondo piatto)
    fs_btn_bg = bg_flat(FS_BG, BTN, BTN)
    icon_button("fs_volume", 0xE767, fs_btn_bg, size=sc(19))
    icon_button("fs_mute", 0xE74F, fs_btn_bg, size=sc(19), active_only=True)
    icon_button("fs_exit", 0xE73F, fs_btn_bg, size=sc(18))
    for name in ("prev", "next", "stop"):
        icon_button("fs_" + name, 0, fs_btn_bg, size=sc(17), shape=SHAPES[name])
    play_button("fs_", bg_flat(FS_BG, PLAY_BOX, PLAY_BOX))

    # area video
    idle_box = idle_emblem(MID)
    art_box = art_fallback(MID)

    # slider
    seek_w = W - sc(200)
    vol_w = sc(100)
    fs_seek_w = FW - sc(184)
    slider_frames("seek_frames", seek_w, SEEK_FRAMES, BOT_ROWS, SEEK_Y)
    slider_frames("vol_frames", vol_w, VOL_FRAMES, BOT_ROWS, VOL_Y)
    fs_rows = [hx(FS_BG)] * FH
    slider_frames("fs_seek_frames", fs_seek_w, SEEK_FRAMES, fs_rows, FS_SEEK_Y)
    slider_frames("fs_vol_frames", vol_w, VOL_FRAMES, fs_rows, FS_VOL_Y)
    seek_disc = "#%02X%02X%02X" % BOT_ROWS[SEEK_Y + FRAME_H // 2][:3]
    vol_disc = "#%02X%02X%02X" % BOT_ROWS[VOL_Y + FRAME_H // 2][:3]
    knob("knob", sc(14), seek_disc)
    knob("vknob", sc(11), vol_disc)
    knob("fknob", sc(14), FS_BG)
    knob("fvknob", sc(11), FS_BG)

    menu_ys, sep_ys = menu_assets()
    eq_assets()
    build_xml(idle_box, art_box, seek_w, vol_w, fs_seek_w, menu_ys, sep_ys)

    vlt = os.path.join(HERE, "Aurora.vlt")
    with tarfile.open(vlt, "w:gz") as tar:
        tar.add(OUT, arcname="Aurora")
    with open(os.path.join(HERE, "Aurora.json"), "w", encoding="utf-8") as jf:
        json.dump({"scala": K, "main": [W, H], "minimo": [MINW, MINH], "playlist": [PW, PH],
                   "eqwin": [EQ_W, EQ_H], "fullscreenController": [FW, FH], "menu": "cassetto nel layout mainMenuLayout",
                   "cornice": "nativa (DWM)" if NATIVE_FRAME else "sagoma della skin"}, jf, indent=1)
    print("scritto", vlt, os.path.getsize(vlt), "byte;", len(os.listdir(IMG)), "immagini; scala", K,
          "; finestre: main %dx%d (min %dx%d) playlist %dx%d eq %dx%d fs %dx%d; cassetto %dx%d" % (W, H, MINW, MINH, PW, PH, EQ_W, EQ_H, FW, FH, MENU_W, MENU_H))


if __name__ == "__main__":
    main()
