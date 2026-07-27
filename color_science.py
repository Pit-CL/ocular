#!/usr/bin/env python3
"""
Nucleo de ciencia de color para el tema "vision-theme".

Implementa, sin dependencias fragiles, la matematica exacta que necesita un tema
cientificamente amigable con la vista:

  - OKLab <-> sRGB lineal (matrices de Bjorn Ottosson, exactas).
  - OKLCH <-> sRGB con GAMUT MAPPING por reduccion de chroma (mantiene L y H,
    baja C hasta caber en sRGB). Es el comportamiento de CSS Color 4.
  - APCA-W3 (algoritmo 0.1.9): contraste perceptual de WCAG 3, que modela
    correctamente la asimetria del dark mode (texto claro sobre fondo oscuro).

Validado contra valores conocidos:
  negro #000 sobre blanco #fff  -> Lc ~ +106
  blanco #fff sobre negro #000  -> Lc ~ -108
"""
from __future__ import annotations
import math

# --------------------------------------------------------------------------- #
# sRGB transfer (piecewise, IEC 61966-2-1) — para conversion correcta de color
# --------------------------------------------------------------------------- #
def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def linear_to_srgb(c: float) -> float:
    c = max(0.0, c)
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

# --------------------------------------------------------------------------- #
# OKLab <-> linear sRGB  (Ottosson 2020)
# --------------------------------------------------------------------------- #
def linsrgb_to_oklab(r: float, g: float, b: float):
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (max(0.0, x) ** (1 / 3) for x in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, a, bb

def oklab_to_linsrgb(L: float, a: float, b: float):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return r, g, bb

# --------------------------------------------------------------------------- #
# OKLCH helpers
# --------------------------------------------------------------------------- #
def oklch_to_oklab(L: float, C: float, H_deg: float):
    h = math.radians(H_deg)
    return L, C * math.cos(h), C * math.sin(h)

def _in_gamut(rgb, eps=1e-4):
    return all(-eps <= c <= 1 + eps for c in rgb)

def oklch_to_srgb(L: float, C: float, H_deg: float):
    """OKLCH -> sRGB 0..1 con gamut mapping por reduccion de chroma (binaria)."""
    Lab = oklch_to_oklab(L, C, H_deg)
    lin = oklab_to_linsrgb(*Lab)
    if not _in_gamut(lin):
        lo, hi = 0.0, C
        for _ in range(40):
            mid = (lo + hi) / 2
            lin = oklab_to_linsrgb(*oklch_to_oklab(L, mid, H_deg))
            if _in_gamut(lin):
                lo = mid
            else:
                hi = mid
        lin = oklab_to_linsrgb(*oklch_to_oklab(L, lo, H_deg))
    return tuple(min(1.0, max(0.0, linear_to_srgb(c))) for c in lin)

def oklch_to_hex(L: float, C: float, H_deg: float) -> str:
    r, g, b = oklch_to_srgb(L, C, H_deg)
    return "#{:02x}{:02x}{:02x}".format(*(round(x * 255) for x in (r, g, b)))

def hex_to_srgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

def hex_to_oklch(h: str):
    r, g, b = (srgb_to_linear(c) for c in hex_to_srgb(h))
    L, a, bb = linsrgb_to_oklab(r, g, b)
    C = math.hypot(a, bb)
    H = math.degrees(math.atan2(bb, a)) % 360
    return L, C, H

def hex_to_oklab(h: str):
    """Convierte un hex sRGB a coordenadas OKLab (L, a, b)."""
    r, g, b = (srgb_to_linear(c) for c in hex_to_srgb(h))
    return linsrgb_to_oklab(r, g, b)

def delta_e_oklab(h1: str, h2: str) -> float:
    """Distancia euclidiana en OKLab entre dos colores hex (proxy perceptual simple)."""
    L1, a1, b1 = hex_to_oklab(h1)
    L2, a2, b2 = hex_to_oklab(h2)
    return math.sqrt((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)

def clamp_chroma(L: float, C: float, H: float) -> float:
    """Devuelve el chroma efectivo tras gamut mapping (para auditar saturacion real)."""
    return hex_to_oklch(oklch_to_hex(L, C, H))[1]

# --------------------------------------------------------------------------- #
# APCA-W3 0.1.9  (Lc perceptual)
# --------------------------------------------------------------------------- #
_R, _G, _B = 0.2126729, 0.7151522, 0.0721750
_TRC = 2.4
_BLK_THR, _BLK_CLMP = 0.022, 1.414
_SCALE = 1.14
_LO_OFFSET, _LO_CLIP, _DELTA = 0.027, 0.1, 0.0005
_NORM_BG, _NORM_TXT, _REV_TXT, _REV_BG = 0.56, 0.57, 0.62, 0.65

def _apca_y(rgb01):
    r, g, b = rgb01
    Y = _R * r ** _TRC + _G * g ** _TRC + _B * b ** _TRC
    return Y if Y >= _BLK_THR else Y + (_BLK_THR - Y) ** _BLK_CLMP

def apca(text_hex: str, bg_hex: str) -> float:
    """Lc APCA con signo (+ = texto oscuro sobre claro, - = texto claro sobre oscuro)."""
    yt = _apca_y(hex_to_srgb(text_hex))
    yb = _apca_y(hex_to_srgb(bg_hex))
    if abs(yb - yt) < _DELTA:
        return 0.0
    if yb > yt:  # polaridad normal (fondo claro)
        sapc = (yb ** _NORM_BG - yt ** _NORM_TXT) * _SCALE
        out = 0.0 if sapc < _LO_CLIP else sapc - _LO_OFFSET
    else:        # polaridad inversa (fondo oscuro)
        sapc = (yb ** _REV_BG - yt ** _REV_TXT) * _SCALE
        out = 0.0 if -sapc < _LO_CLIP else sapc + _LO_OFFSET
    return out * 100

def lc(text_hex: str, bg_hex: str) -> float:
    return abs(apca(text_hex, bg_hex))

# --------------------------------------------------------------------------- #
# WCAG 2.x (referencia secundaria)
# --------------------------------------------------------------------------- #
def _rel_lum(h: str):
    r, g, b = (srgb_to_linear(c) for c in hex_to_srgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def wcag(a_hex: str, b_hex: str) -> float:
    la, lb = _rel_lum(a_hex), _rel_lum(b_hex)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

# --------------------------------------------------------------------------- #
# HSL (para tokens shadcn: "H S% L%")
# --------------------------------------------------------------------------- #
def hex_to_hsl(h: str):
    r, g, b = hex_to_srgb(h)
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    L = (mx + mn) / 2
    if d == 0:
        return 0.0, 0.0, L
    S = d / (1 - abs(2 * L - 1))
    if mx == r:
        H = ((g - b) / d) % 6
    elif mx == g:
        H = (b - r) / d + 2
    else:
        H = (r - g) / d + 4
    return H * 60, S, L

def hsl_str(h: str) -> str:
    H, S, L = hex_to_hsl(h)
    return f"{round(H)} {round(S * 100)}% {round(L * 100)}%"

# --------------------------------------------------------------------------- #
# find_L: ajusta L de un color (C,H fijos) hasta alcanzar un Lc APCA objetivo
# --------------------------------------------------------------------------- #
def solve_L_for_lc(target_lc: float, H: float, C: float, bg_hex: str,
                   lighter: bool, lo=0.0, hi=1.0, iters=40) -> tuple:
    """Busca L tal que lc(color, bg) ~ target_lc. lighter=True busca en L>bg."""
    for _ in range(iters):
        mid = (lo + hi) / 2
        cur = lc(oklch_to_hex(mid, C, H), bg_hex)
        if (cur < target_lc) == lighter:
            lo = mid
        else:
            hi = mid
    L = (lo + hi) / 2
    hx = oklch_to_hex(L, C, H)
    return L, hx, lc(hx, bg_hex)

# --------------------------------------------------------------------------- #
# self-test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    print("APCA sanity:")
    print("  #000 on #fff:", round(apca("#000000", "#ffffff"), 2), "(esperado ~ +106)")
    print("  #fff on #000:", round(apca("#ffffff", "#000000"), 2), "(esperado ~ -108)")
    print("  #888 on #fff:", round(apca("#888888", "#ffffff"), 2))
    print()
    print("OKLCH roundtrip:")
    for hx in ("#1a1711", "#ddd7c9", "#7aaff4", "#ed7668", "#f8f3eb"):
        L, C, H = hex_to_oklch(hx)
        back = oklch_to_hex(L, C, H)
        print(f"  {hx} -> OKLCH(L={L:.3f} C={C:.3f} H={H:.1f}) -> {back}  {'OK' if back==hx else 'drift'}")
    print()
    print("Gamut map (chroma alto se reduce):")
    print("  OKLCH(0.7, 0.4, 30) ->", oklch_to_hex(0.7, 0.4, 30), "C_real=", round(clamp_chroma(0.7, 0.4, 30), 3))
    print()
    print("Delta E OKLab (distancia perceptual simple):")
    print("  #ff0000 vs #ff0000 ->", round(delta_e_oklab("#ff0000", "#ff0000"), 4), "(esperado 0.0)")
    print("  #ff0000 vs #00ff00 ->", round(delta_e_oklab("#ff0000", "#00ff00"), 4), "(esperado alto, colores muy distintos)")
