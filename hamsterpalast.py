"""Hamsterpalast: parametrischer Generator fuer lasergeschnittene Teile.

Ohne Argumente ausfuehren. Schreibt nach docs/:
  svg/blatt_N.svg   Schnittplaene (rot = schneiden, blau = gravieren/ritzen,
                    gruen = nur Beschriftung, in der Lasersoftware ausschalten)
  svg/vorschau.svg  Frontansicht und Grundriss zur Kontrolle
  model.js          3D-Modell fuer die Browseransicht (docs/index.html)

Alle Masse in mm. Nur Standardbibliothek.
"""
import json
import math
import os

# ---------------------------------------------------------------- Parameter
T = 4.0            # Materialstaerke, NACHMESSEN (Sperrholz "4 mm" ist oft 3.7-3.9)
KERF = 0.15        # Schnittbreite des Lasers; mit dem Passprobe-Teil pruefen
HAMSTER = "gold"   # "gold" (Goldhamster) oder "zwerg" (Zwerghamster)
SHEET_W, SHEET_H = 600, 400   # Plattengroesse / Arbeitsbereich
ENGRAVE = True     # Mauerwerk, Torbogen, Fenster als Gravur

PASS_W, PASS_H = (70, 80) if HAMSTER == "gold" else (55, 65)  # Durchgaenge

L, D = 360, 200          # Hauptgebaeude aussen (Breite, Tiefe)
HL, HT = 140, 165        # Deckel-Auflage, Oberkante Zinnen
TW = 140                 # Turm aussen (quadratisch)
HL_T, HT_T = 175, 200    # Turm: Deckel-Auflage, Oberkante Zinnen
CD = 12                  # Zinnentiefe
FW = 16                  # Zielbreite eines Fingers der Eckverbindung
CLEAT_H = 10             # Auflageleisten fuer die Deckel
SLIT_W, SLIT_H = 4, 28   # Schiessscharten (Lueftung); 4 mm, kein Pfoten-Einklemmen
DIV_LEG = 18             # Steg zwischen Durchgang und Aussenwand in den Trennwaenden
HANDLE_W, HANDLE_TAB = 50, 30

ARC_SEG = 6              # Segmente pro Viertelkreis im 3D-Modell

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUT = os.path.join(DOCS, "svg")


# ---------------------------------------------------------------- Geometrie
class Path:
    """Pfad in lokalen Koordinaten, y nach oben. Boegen: sweep im Bildschirmsinn
    (1 = im Uhrzeigersinn, so wie man das fertige Teil ansieht)."""

    def __init__(self):
        self.cmds = []

    def M(self, x, y):
        self.cmds.append(("M", x, y))
        return self

    def L(self, x, y):
        self.cmds.append(("L", x, y))
        return self

    def A(self, r, x, y):
        self.cmds.append(("A", r, x, y))
        return self

    def Z(self):
        self.cmds.append(("Z",))
        return self

    def polylines(self):
        """Boegen in Streckenzuege aufgeloest: Liste von (Punkte, geschlossen)."""
        polys = []
        for c in self.cmds:
            if c[0] == "M":
                polys.append([[(c[1], c[2])], False])
            elif c[0] == "L":
                polys[-1][0].append((c[1], c[2]))
            elif c[0] == "A":
                r, x1, y1 = c[1:]
                x0, y0 = polys[-1][0][-1]
                dx, dy = x1 - x0, y1 - y0
                ch = math.hypot(dx, dy)
                hh = math.sqrt(max(r * r - ch * ch / 4, 0))
                cx, cy = (x0 + x1) / 2 + hh * dy / ch, (y0 + y1) / 2 - hh * dx / ch
                a0, a1 = math.atan2(y0 - cy, x0 - cx), math.atan2(y1 - cy, x1 - cx)
                while a1 > a0:          # Uhrzeigersinn = fallender Winkel
                    a1 -= 2 * math.pi
                for i in range(1, ARC_SEG + 1):
                    a = a0 + (a1 - a0) * i / ARC_SEG
                    polys[-1][0].append((cx + r * math.cos(a), cy + r * math.sin(a)))
            else:
                pts = polys[-1][0]
                if math.dist(pts[0], pts[-1]) < 1e-6:
                    pts.pop()
                polys[-1][1] = True
        return polys

    def d(self, tf):
        out = []
        for c in self.cmds:
            if c[0] == "Z":
                out.append("Z")
            elif c[0] == "A":
                X, Y = tf(c[2], c[3])
                out.append(f"A{c[1]:.3f} {c[1]:.3f} 0 0 1 {X:.3f} {Y:.3f}")
            else:
                X, Y = tf(c[1], c[2])
                out.append(f"{c[0]}{X:.3f} {Y:.3f}")
        return " ".join(out)


def arch_top(p, cx, yb, r):
    """Halbkreis von (cx-r, yb) ueber oben nach (cx+r, yb)."""
    p.A(r, cx, yb + r).A(r, cx + r, yb)


def arch_bottom(p, cx, yb, r):
    """Halbkreis von (cx+r, yb) ueber unten nach (cx-r, yb)."""
    p.A(r, cx, yb - r).A(r, cx - r, yb)


def slit(cx, cy, w=SLIT_W, h=SLIT_H):
    r = w / 2
    p = Path().M(cx - r, cy - h / 2 + r).L(cx - r, cy + h / 2 - r)
    arch_top(p, cx, cy + h / 2 - r, r)
    p.L(cx + r, cy - h / 2 + r)
    arch_bottom(p, cx, cy - h / 2 + r, r)
    return p.Z(), (cx - r - 3, cy - h / 2 - 3, cx + r + 3, cy + h / 2 + 3)


def rect(x0, y0, x1, y1):
    return Path().M(x0, y0).L(x1, y0).L(x1, y1).L(x0, y1).Z()


def slot(x0, y0, x1, y1):
    """Durchbruch fuer eine Lasche; um KERF kleiner gezeichnet."""
    k = KERF / 2
    return rect(x0 + k, y0 + k, x1 - k, y1 - k), (x0 - 2, y0 - 2, x1 + 2, y1 + 2)


def line(x0, y0, x1, y1):
    return Path().M(x0, y0).L(x1, y1)


def finger_segs(H, kind):
    """Eckverbindung entlang der Hoehe. kind 'A': Finger unten/oben, 'B': komplementaer.
    Finger werden um KERF breiter gezeichnet, Luecken entsprechend schmaler."""
    n = max(3, round(H / FW))
    n += n % 2 == 0
    s = H / n

    def tab(i):
        return (i % 2 == 0) == (kind == "A")

    b = [0.0] + [i * s + (KERF / 2 if tab(i - 1) else -KERF / 2) for i in range(1, n)] + [H]
    return [(b[i], b[i + 1], tab(i)) for i in range(n)]


def crenels(W, mw=22, cw=16):
    k = max(1, round((W - mw) / (mw + cw)))
    m = (W - k * cw) / (k + 1)
    return [(m * (j + 1) + cw * j, m * (j + 1) + cw * (j + 1)) for j in range(k)]


def bricks(x0, x1, y0, y1, keep, rowh=18, bl=36):
    """Mauerwerk als Ritzlinien, ausgespart um die keep-Rechtecke."""
    paths = []
    y = y0 + rowh
    while y < y1 - 2:
        segs = [(x0, x1)]
        for kx0, ky0, kx1, ky1 in keep:
            if ky0 <= y <= ky1:
                nxt = []
                for a, b in segs:
                    if kx1 <= a or kx0 >= b:
                        nxt.append((a, b))
                        continue
                    if kx0 > a:
                        nxt.append((a, kx0))
                    if kx1 < b:
                        nxt.append((kx1, b))
                segs = nxt
        paths += [line(a, y, b, y) for a, b in segs if b - a > 3]
        y += rowh
    r = 0
    ya = y0
    while ya < y1 - 2:
        yb = min(ya + rowh, y1)
        x = x0 + (bl / 2 if r % 2 else bl * 0.75)
        while x < x1 - 4:
            if not any(kx0 <= x <= kx1 and ky0 < yb and ky1 > ya for kx0, ky0, kx1, ky1 in keep):
                paths.append(line(x, ya, x, yb))
            x += bl
        ya += rowh
        r += 1
    return paths


def gate_ring(cx, w, h, ring=8, stones=9):
    """Gravierter Torbogen um einen Durchgang."""
    r, R = w / 2, w / 2 + ring
    yc = h - r
    p = Path().M(cx - R, 0).L(cx - R, yc)
    arch_top(p, cx, yc, R)
    p.L(cx + R, 0)
    out = [p]
    for i in range(1, stones):
        a = math.pi * i / stones
        out.append(line(cx - r * math.cos(a), yc + r * math.sin(a),
                        cx - R * math.cos(a), yc + R * math.sin(a)))
    return out, (cx - R - 3, 0, cx + R + 3, h + ring + 3)


def window(cx, cy, w=20, h=34):
    """Graviertes Bogenfenster mit Sprossenkreuz."""
    r = w / 2
    p = Path().M(cx - r, cy - h / 2).L(cx - r, cy + h / 2 - r)
    arch_top(p, cx, cy + h / 2 - r, r)
    p.L(cx + r, cy - h / 2).Z()
    return [p, line(cx, cy - h / 2, cx, cy + h / 2), line(cx - r, cy - 2, cx + r, cy - 2),
            line(cx - r - 3, cy - h / 2 - 2, cx + r + 3, cy - h / 2 - 2)], \
        (cx - r - 6, cy - h / 2 - 5, cx + r + 6, cy + h / 2 + 3)


# ---------------------------------------------------------------- Teile
class Piece:
    def __init__(self, name, w, h, cut, eng=(), note=""):
        self.name, self.w, self.h, self.cut, self.eng, self.note = name, w, h, cut, list(eng), note
        self.frame = None   # (Ursprung, u, v, n, Gruppe, Explosionsrichtung)

    def place(self, o, u, v, n, group, ex):
        """Lage im Raum: Punkt = o + x*u + y*v + t*n, t in [0, T]; t = 0 ist die Aussenseite."""
        self.frame = (o, u, v, n, group, ex)
        return self


def wall(name, W, H, left=None, right=None, arches=(), holes=(), deco=(), note="",
         with_bricks=True, cren=True):
    """Wand von aussen gesehen. arches: (cx, w, h) offene Boegen an der Unterkante.
    holes: (Path, keepout); deco: (Pfadliste, keepout)."""
    segL = finger_segs(H, left) if left else [(0, H, True)]
    segR = finger_segs(H, right) if right else [(0, H, True)]

    def xl(tab):
        return 0 if tab else T

    def xr(tab):
        return W if tab else W - T

    p = Path().M(xl(segL[0][2]), 0)
    for cx, w, h in sorted(arches):
        r = w / 2
        p.L(cx - r, 0).L(cx - r, h - r)
        arch_top(p, cx, h - r, r)
        p.L(cx + r, 0)
    for ys, ye, tab in segR:
        p.L(xr(tab), ys).L(xr(tab), ye)
    if cren:
        for a, b in reversed(crenels(W)):
            p.L(b, H).L(b, H - CD).L(a, H - CD).L(a, H)
    for ys, ye, tab in reversed(segL):
        p.L(xl(tab), ye).L(xl(tab), ys)
    p.Z()

    cut = [p] + [h[0] for h in holes]
    eng, keep = [], [h[1] for h in holes]
    for paths, k in deco:
        eng += paths
        keep.append(k)
    for cx, w, h in arches:
        keep.append((cx - w / 2 - 3, 0, cx + w / 2 + 3, h + 3))
    if with_bricks:
        eng += bricks(T + 2, W - T - 2, 0, H - CD - 3, keep)
    return Piece(name, W, H, cut, eng if ENGRAVE else [], note)


def divider(name, pass_front):
    """Trennwand mit Laschen in die Schlitze von Vorder- und Rueckwand."""
    tabs = [(HL - 48, HL - 32), (HL - 24, HL - 8)]
    k = KERF / 2
    w, r = PASS_W, PASS_W / 2
    cx = T + DIV_LEG + r if pass_front else D - T - DIV_LEG - r
    p = Path().M(T, 0).L(cx - r, 0).L(cx - r, PASS_H - r)
    arch_top(p, cx, PASS_H - r, r)
    p.L(cx + r, 0).L(D - T, 0)
    for ya, yb in tabs:
        p.L(D - T, ya - k).L(D, ya - k).L(D, yb + k).L(D - T, yb + k)
    p.L(D - T, HL).L(T, HL)
    for ya, yb in reversed(tabs):
        p.L(T, yb + k).L(0, yb + k).L(0, ya - k).L(T, ya - k)
    p.Z()
    return Piece(name, D, HL, [p], note="links = vorne"), tabs


def lid(name, W, H):
    s = slot(W / 2 - HANDLE_TAB / 2, H / 2 - T / 2, W / 2 + HANDLE_TAB / 2, H / 2 + T / 2)[0]
    return Piece(name, W, H, [rect(0, 0, W, H), s])


def handle(name):
    """Griff mit Lasche fuer den Deckelschlitz, oben zwei Zinnen."""
    k = KERF / 2
    h = 18
    a = (HANDLE_W - HANDLE_TAB) / 2
    p = Path().M(a - k, 0).L(a + HANDLE_TAB + k, 0).L(a + HANDLE_TAB + k, T)
    p.L(HANDLE_W, T).L(HANDLE_W, T + h)
    for x0, x1 in reversed(crenels(HANDLE_W, mw=10, cw=8)):
        p.L(x1, T + h).L(x1, T + h - 6).L(x0, T + h - 6).L(x0, T + h)
    p.L(0, T + h).L(0, T).L(a - k, T).Z()
    return Piece(name, HANDLE_W, T + h, [p])


def build():
    pieces = []
    c = (L - 4 * T) / 3                       # Kammerbreite innen
    xd = [T + c, 2 * T + 2 * c]               # linke Kante der Trennwaende
    cc = [T + c / 2, 2 * T + 1.5 * c, 3 * T + 2.5 * c]  # Kammermitten
    sy = 108                                  # Hoehe der Schiessscharten

    d1, tabs = divider("Trennwand 1 (Durchgang hinten)", pass_front=False)
    d2, _ = divider("Trennwand 2 (Durchgang vorne)", pass_front=True)

    def div_slots(mirror):
        out = []
        for x in xd:
            x0 = L - x - T if mirror else x
            out += [slot(x0, ya, x0 + T, yb) for ya, yb in tabs]
        return out

    pieces.append(wall("Haupthaus vorne", L, HT, "A", "A",
                       arches=[(cc[0], PASS_W, PASS_H)],
                       holes=[slit(x, sy) for x in cc[1:]] + [slit(cc[0], sy + 4)] + div_slots(False),
                       deco=[gate_ring(cc[0], PASS_W, PASS_H)]))
    pieces.append(wall("Haupthaus hinten", L, HT, "A", "A",
                       holes=[slit(L - x, sy) for x in cc] + div_slots(True)))
    pieces.append(wall("Haupthaus links", D, HT, "B", "B", holes=[slit(D / 2, sy)],
                       note="innen Auflageleiste"))
    right_holes = [slit((D - TW) / 2, sy)] if D - TW >= 30 else []
    pieces.append(wall("Haupthaus rechts (zum Turm)", D, HT, "B", "B",
                       arches=[(D - TW / 2, PASS_W, PASS_H)], holes=right_holes,
                       note="links = vorne"))
    pieces += [d1, d2]

    ty, wy = 95, HL_T - 35
    for nm in ("Turm vorne", "Turm hinten"):
        pieces.append(wall(nm, TW, HT_T, "A", "A", holes=[slit(TW / 2, ty)], deco=[window(TW / 2, wy)]))
    pieces.append(wall("Turm links (ans Haupthaus)", TW, HT_T, "B", "B",
                       arches=[(TW / 2, PASS_W, PASS_H)], with_bricks=False))
    pieces.append(wall("Turm rechts", TW, HT_T, "B", "B", holes=[slit(TW / 2, ty)],
                       deco=[window(TW / 2, wy)]))

    pieces.append(lid("Deckel Haupthaus", L - 2 * T - 1, D - 2 * T - 1))
    pieces.append(lid("Deckel Turm", TW - 2 * T - 1, TW - 2 * T - 1))
    pieces += [handle("Griff Haupthaus"), handle("Griff Turm")]
    for i in (1, 2):
        pieces.append(Piece(f"Leiste Haus {i}", D - 2 * T - 2, CLEAT_H,
                            [rect(0, 0, D - 2 * T - 2, CLEAT_H)]))
        pieces.append(Piece(f"Leiste Turm {i}", TW - 2 * T - 2, CLEAT_H,
                            [rect(0, 0, TW - 2 * T - 2, CLEAT_H)]))

    # Lage im Raum: x nach rechts, y nach hinten, z nach oben
    by = {p.name: p for p in pieces}
    X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    nX, nY = (-1, 0, 0), (0, -1, 0)
    by["Haupthaus vorne"].place((0, 0, 0), X, Z, Y, "haus", (0, -1, 0))
    by["Haupthaus hinten"].place((L, D, 0), nX, Z, nY, "haus", (0, 1, 0))
    by["Haupthaus links"].place((0, D, 0), nY, Z, X, "haus", (-1, 0, 0))
    by["Haupthaus rechts (zum Turm)"].place((L, 0, 0), Y, Z, nX, "haus", (0.4, 0, 0))
    by[d1.name].place((xd[0], 0, 0), Y, Z, X, "haus", (0, 0, 0.8))
    by[d2.name].place((xd[1], 0, 0), Y, Z, X, "haus", (0, 0, 0.8))
    tx, ty0, te = L, D - TW, (1.4, 0, 0)
    by["Turm vorne"].place((tx, ty0, 0), X, Z, Y, "turm", (te[0], -1, 0))
    by["Turm hinten"].place((tx + TW, D, 0), nX, Z, nY, "turm", (te[0], 1, 0))
    by["Turm links (ans Haupthaus)"].place((tx, D, 0), nY, Z, X, "turm", (te[0] - 0.4, 0, 0))
    by["Turm rechts"].place((tx + TW, ty0, 0), Y, Z, nX, "turm", (te[0] + 1, 0, 0))
    lw, ld = L - 2 * T - 1, D - 2 * T - 1
    by["Deckel Haupthaus"].place((T + 0.5, T + 0.5, HL), X, Y, Z, "deckel_haus", (0, 0, 1.5))
    by["Griff Haupthaus"].place((T + 0.5 + lw / 2 - HANDLE_W / 2, T + 0.5 + ld / 2 - T / 2, HL),
                                X, Z, Y, "deckel_haus", (0, 0, 2.2))
    tl = TW - 2 * T - 1
    by["Deckel Turm"].place((tx + T + 0.5, ty0 + T + 0.5, HL_T), X, Y, Z, "deckel_turm", (te[0], 0, 1.5))
    by["Griff Turm"].place((tx + T + 0.5 + tl / 2 - HANDLE_W / 2, ty0 + T + 0.5 + tl / 2 - T / 2, HL_T),
                           X, Z, Y, "deckel_turm", (te[0], 0, 2.2))
    zc, zt = HL - CLEAT_H, HL_T - CLEAT_H
    by["Leiste Haus 1"].place((T, T + 1, zc), Y, Z, X, "haus", (-0.5, 0, 0.3))
    by["Leiste Haus 2"].place((L - 2 * T, T + 1, zc), Y, Z, X, "haus", (0.3, 0, 0.3))
    by["Leiste Turm 1"].place((tx + T, ty0 + T + 1, zt), Y, Z, X, "turm", (te[0] - 0.3, 0, 0.3))
    by["Leiste Turm 2"].place((tx + TW - 2 * T, ty0 + T + 1, zt), Y, Z, X, "turm", (te[0] + 0.5, 0, 0.3))

    # Passprobe: zuerst allein schneiden und Sitz pruefen
    pa = wall("Probe A", 40, 48, None, "A", holes=[slot(14, 30, 14 + T, 42)], with_bricks=False, cren=False)
    pb = wall("Probe B", 40, 48, "B", None, with_bricks=False, cren=False)
    tab = Piece("Probe Lasche", 24, 12 + T, [Path().M(6 - KERF / 2, 0).L(18 + KERF / 2, 0)
                .L(18 + KERF / 2, T).L(24, T).L(24, T + 12).L(0, T + 12).L(0, T).L(6 - KERF / 2, T).Z()])
    for p in (pa, pb, tab):
        p.note = "Passprobe"
    pieces += [pa, pb, tab]
    return pieces


# ---------------------------------------------------------------- Ausgabe
def transform(piece, x0, y0, rot):
    def tf(x, y):
        sx, sy = x, piece.h - y
        if rot:
            sx, sy = piece.h - sy, sx
        return x0 + sx, y0 + sy
    return tf


def pack(pieces, gap=4, margin=5):
    """Einfaches Regal-Packen; lange Seite waagerecht."""
    items = []
    for p in pieces:
        rot = p.h > p.w and p.h <= SHEET_W - 2 * margin
        w, h = (p.h, p.w) if rot else (p.w, p.h)
        if w > SHEET_W - 2 * margin or h > SHEET_H - 2 * margin:
            raise SystemExit(f"{p.name} ({w:.0f} x {h:.0f}) passt nicht auf {SHEET_W} x {SHEET_H}")
        items.append((p, rot, w, h))
    items.sort(key=lambda it: -it[3])
    sheets = []
    for it in items:
        p, rot, w, h = it
        placed = False
        for sh in sheets:
            for shelf in sh["shelves"]:
                if shelf["x"] + w <= SHEET_W - margin and h <= shelf["h"]:
                    sh["items"].append((p, rot, shelf["x"], shelf["y"]))
                    shelf["x"] += w + gap
                    placed = True
                    break
            if placed:
                break
            if sh["y"] + h <= SHEET_H - margin:
                sh["shelves"].append({"y": sh["y"], "h": h, "x": margin + w + gap})
                sh["items"].append((p, rot, margin, sh["y"]))
                sh["y"] += h + gap
                placed = True
                break
        if not placed:
            sheets.append({"y": margin + h + gap, "shelves": [{"y": margin, "h": h, "x": margin + w + gap}],
                           "items": [(p, rot, margin, margin)]})
    return [s["items"] for s in sheets]


def svg_sheet(items):
    cut, eng, lab = [], [], []
    for p, rot, x0, y0 in items:
        tf = transform(p, x0, y0, rot)
        cut += [f'<path d="{q.d(tf)}"/>' for q in p.cut]
        eng += [f'<path d="{q.d(tf)}"/>' for q in p.eng]
        w, h = (p.h, p.w) if rot else (p.w, p.h)
        lab.append(f'<text x="{x0 + w / 2:.1f}" y="{y0 + h / 2:.1f}">{p.name}'
                   f'{" | " + p.note if p.note else ""}</text>')
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W}mm" height="{SHEET_H}mm" viewBox="0 0 {SHEET_W} {SHEET_H}">
<!-- Hamsterpalast, Material {T} mm, Kerf {KERF} mm. rot = schneiden, blau = ritzen, gruen = nur Info -->
<g id="gravur" fill="none" stroke="#0000ff" stroke-width="0.1">
{chr(10).join(eng)}
</g>
<g id="schnitt" fill="none" stroke="#ff0000" stroke-width="0.1">
{chr(10).join(cut)}
</g>
<g id="info_nicht_lasern" fill="#00a000" font-family="sans-serif" font-size="5" text-anchor="middle">
{chr(10).join(lab)}
</g>
</svg>
'''


def svg_preview(pieces):
    by = {p.name: p for p in pieces}
    ox, ground = 20, 40 + HT_T

    def draw(p, x0, y0, fill="#e7c49a"):
        tf = transform(p, x0, y0, False)
        s = f'<path fill="{fill}" fill-rule="evenodd" stroke="#6b4320" stroke-width="0.6" ' \
            f'd="{" ".join(q.d(tf) for q in p.cut)}"/>'
        if p.eng:
            s += f'<path fill="none" stroke="#a8743f" stroke-width="0.4" ' \
                 f'd="{" ".join(q.d(tf) for q in p.eng)}"/>'
        return s

    el = [draw(by["Turm vorne"], ox + L, ground - HT_T, "#d9b27f"),
          draw(by["Haupthaus vorne"], ox, ground - HT)]

    # Grundriss, vorne = unten
    py = ground + 50

    def P(x, y):
        return ox + x, py + D - y

    def strip(x0, y0, x1, y1, gaps=(), axis="x"):
        segs = [(x0, x1) if axis == "x" else (y0, y1)]
        for g0, g1 in gaps:
            segs = [s for a, b in segs for s in ((a, min(b, g0)), (max(a, g1), b)) if s[1] - s[0] > 0.01]
        out = []
        for a, b in segs:
            ax0, ay0, ax1, ay1 = (a, y0, b, y1) if axis == "x" else (x0, a, x1, b)
            X0, Y1 = P(ax0, ay0)
            X1, Y0 = P(ax1, ay1)
            out.append(f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{X1 - X0:.1f}" height="{Y1 - Y0:.1f}"/>')
        return out

    c = (L - 4 * T) / 3
    xd = [T + c, 2 * T + 2 * c]
    cc = [T + c / 2, 2 * T + 1.5 * c, 3 * T + 2.5 * c]
    hw = PASS_W / 2
    gb = D - T - DIV_LEG - hw
    gf = T + DIV_LEG + hw
    walls = []
    walls += strip(0, 0, L, T, [(cc[0] - hw, cc[0] + hw)])
    walls += strip(0, D - T, L, D)
    walls += strip(0, 0, T, D, axis="y")
    walls += strip(L - T, 0, L, D, [(D - TW / 2 - hw, D - TW / 2 + hw)], axis="y")
    walls += strip(xd[0], T, xd[0] + T, D - T, [(gb - hw, gb + hw)], axis="y")
    walls += strip(xd[1], T, xd[1] + T, D - T, [(gf - hw, gf + hw)], axis="y")
    walls += strip(L, D - TW, L + TW, D - TW + T)
    walls += strip(L, D - T, L + TW, D)
    walls += strip(L, D - TW, L + T, D, [(D - TW / 2 - hw, D - TW / 2 + hw)], axis="y")
    walls += strip(L + TW - T, D - TW, L + TW, D, axis="y")

    txt = []
    for i, x in enumerate(cc):
        X, Y = P(x, D / 2)
        txt.append(f'<text x="{X:.1f}" y="{Y:.1f}">Kammer {i + 1}</text>')
    X, Y = P(L + TW / 2, D - TW / 2)
    txt.append(f'<text x="{X:.1f}" y="{Y:.1f}">Turm</text>')
    txt.append(f'<text x="{X:.1f}" y="{Y + 9:.1f}">(Schlafkammer)</text>')
    X, Y = P(cc[0], -12)
    txt.append(f'<text x="{X:.1f}" y="{Y:.1f}">Eingang</text>')
    W_total, H_total = ox * 2 + L + TW, py + D + 30
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W_total * 2}" height="{H_total * 2}" viewBox="0 0 {W_total} {H_total}">
<rect width="100%" height="100%" fill="#fbf8f2"/>
<text x="{ox}" y="22" font-family="sans-serif" font-size="11" font-weight="bold">Hamsterpalast ({"Goldhamster" if HAMSTER == "gold" else "Zwerghamster"})</text>
<text x="{ox}" y="33" font-family="sans-serif" font-size="6">Frontansicht, aussen {L + TW:.0f} x {D:.0f} mm, Turm {HT_T:.0f} mm hoch, Durchgaenge {PASS_W} x {PASS_H} mm, ohne Boden</text>
{"".join(el)}
<line x1="{ox - 10}" y1="{ground}" x2="{ox + L + TW + 10}" y2="{ground}" stroke="#6b4320" stroke-width="0.8"/>
<text x="{ox}" y="{py - 8}" font-family="sans-serif" font-size="7">Grundriss (vorne = unten), Weg: Eingang, Kammer 1, 2, 3, Turm</text>
<g fill="#b98a55">{"".join(walls)}</g>
<g font-family="sans-serif" font-size="7" text-anchor="middle" fill="#333">{"".join(txt)}</g>
</svg>
'''


def model_js(pieces, sheets):
    def pl(paths):
        return [{"p": [round(v, 2) for pt in pts for v in pt], "c": closed}
                for q in paths for pts, closed in q.polylines()]
    data = {
        "T": T, "hamster": HAMSTER, "pass": [PASS_W, PASS_H],
        "size": [L + TW, D, HT_T],
        "sheets": [f"svg/blatt_{i}.svg" for i in range(1, len(sheets) + 1)],
        "pieces": [{"name": p.name, "w": p.w, "h": p.h, "o": p.frame[0], "u": p.frame[1],
                    "v": p.frame[2], "n": p.frame[3], "group": p.frame[4], "ex": p.frame[5],
                    "cut": pl(p.cut), "eng": pl(p.eng)} for p in pieces if p.frame],
    }
    return ("// Erzeugt von hamsterpalast.py, nicht von Hand bearbeiten.\n"
            "window.PALAST = " + json.dumps(data, separators=(",", ":")) + ";\n")


def main():
    pieces = build()
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.startswith("blatt_") and f.endswith(".svg"):
            os.remove(os.path.join(OUT, f))
    sheets = pack(pieces)
    for i, items in enumerate(sheets, 1):
        with open(os.path.join(OUT, f"blatt_{i}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg_sheet(items))
    with open(os.path.join(OUT, "vorschau.svg"), "w", encoding="utf-8") as fh:
        fh.write(svg_preview(pieces))
    with open(os.path.join(DOCS, "model.js"), "w", encoding="utf-8") as fh:
        fh.write(model_js(pieces, sheets))
    print(f"Material {T} mm, Kerf {KERF} mm, Platte {SHEET_W} x {SHEET_H} mm")
    for i, items in enumerate(sheets, 1):
        print(f"  blatt_{i}.svg: " + ", ".join(p.name for p, *_ in items))
    print(f"Ausgabe in {OUT}")


if __name__ == "__main__":
    main()
