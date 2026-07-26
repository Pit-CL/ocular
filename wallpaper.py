#!/usr/bin/env python3
"""
Wallpapers "Ocular" — Rooibos (dark) / Manzanilla (light).

Renderer standalone (numpy + PIL): bandas concentricas eliptico-onduladas,
moduladas con senoidales de baja frecuencia, emanando de dos esquinas opuestas
(sup-izq / inf-der), oscureciendose banda a banda hasta fundirse con el fondo.
Replica el estilo del wallpaper HEIC activo (wave-mauve: fondo casi plano +
ondas en 2 esquinas) — NO el de build_wallpaper.py (cerros+sol+neblina), que
es un sistema distinto y no aplica aqui.

De tools/vision-theme/color_science.py se reusa SOLO oklch_to_hex (la unica
pieza de ciencia de color que este renderer necesita: OKLCH -> sRGB con gamut
mapping). Nada de APCA aqui — el wallpaper no lleva texto encima.
"""
import os
import sys

import numpy as np
from PIL import Image

from color_science import oklch_to_hex

HERE = os.path.dirname(os.path.abspath(__file__))
# Resoluciones nativas de los dispositivos del usuario (mismas del renderer
# previo del workspace): iPhone 12 Pro Max retrato, iPad Pro 11" M4 horizontal.
PRESETS = {
    "desktop": (3840, 2160, 800),   # (W, H, ancho del preview)
    "iphone": (1284, 2778, 320),
    "ipad": (2420, 1668, 600),
}
SS = 2                 # supersample para anti-aliasing de bordes de banda
GRAIN_SIGMA = 0.8
N_BANDS = 7
MAX_REACH = 0.50       # alcance normalizado del campo (0=punta esquina .. 1=ultima banda)
FADE = 0.18            # franja extra tras MAX_REACH: surface0 -> base (fusion con el fondo)

# Dos esquinas opuestas SIMETRICAS (pedido 2026-07-26): mismos parametros en
# ambas; como la geometria "br" es la reflexion de "tl", el resultado tiene
# simetria central perfecta (cada esquina es espejo de la otra).
_WAVE = {"freqs": (2.0, 3.5, 5.0), "phases": (0.0, 1.7, 3.1),
         "amps": (0.035, 0.020, 0.010)}
CORNERS = [
    {"origin": "tl", **_WAVE},
    {"origin": "br", **_WAVE},
]

MODES = {
    "dark": dict(
        base=(0.220, 0.012, 70), surface0=(0.270, 0.013, 70), tip=(0.80, 0.055, 40),
    ),
    # El wallpaper light NO es superficie de texto: puede ser mas profundo y
    # calido ("true tone") que el base del theme (0.955) sin costo de
    # legibilidad — menos deslumbre y menos estimulo melanopico.
    "light": dict(
        base=(0.935, 0.018, 78), surface0=(0.885, 0.020, 78), tip=(0.70, 0.075, 68),
    ),
}


def hex_to_srgb01(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


def oklch_lerp_srgb01(a, b, t):
    """Interpola (L,C,H) linealmente y convierte el punto interpolado a sRGB 0..1."""
    L = a[0] + (b[0] - a[0]) * t
    C = a[1] + (b[1] - a[1]) * t
    Hh = a[2] + (b[2] - a[2]) * t
    return hex_to_srgb01(oklch_to_hex(L, C, Hh))


def band_field(Wp, Hp, corner):
    """Campo t: 0 en la punta de la esquina, creciente hacia afuera, elipse
    (por la relacion de aspecto W:H) modulada con 2-3 senoidales sobre el angulo."""
    yy, xx = np.mgrid[0:Hp, 0:Wp].astype(np.float32)
    if corner["origin"] == "tl":
        dx, dy = xx, yy
    else:
        dx, dy = (Wp - 1 - xx), (Hp - 1 - yy)
    nx, ny = dx / Wp, dy / Hp
    d = np.sqrt(nx ** 2 + ny ** 2)
    theta = np.arctan2(ny, nx + 1e-6)
    mod = np.zeros_like(d)
    for f, p, a in zip(corner["freqs"], corner["phases"], corner["amps"]):
        mod += a * np.sin(f * theta + p)
    return d + mod


def render_hires(mode, Wp, Hp):
    cfg = MODES[mode]
    base_rgb = hex_to_srgb01(oklch_to_hex(*cfg["base"]))
    surface0_rgb = hex_to_srgb01(oklch_to_hex(*cfg["surface0"]))

    # colores planos de cada una de las 7 bandas: tip (t=0) -> surface0 (t=1)
    band_colors = [oklch_lerp_srgb01(cfg["tip"], cfg["surface0"], (i + 0.5) / N_BANDS)
                   for i in range(N_BANDS)]

    img = np.tile(base_rgb, (Hp, Wp, 1)).astype(np.float32)

    for corner in CORNERS:
        field = band_field(Wp, Hp, corner)
        t = field / MAX_REACH
        within = t < (1.0 + FADE)

        band_i = np.clip(np.floor(t * N_BANDS), 0, N_BANDS - 1).astype(np.int32)
        col = np.zeros((Hp, Wp, 3), dtype=np.float32)
        for i, c in enumerate(band_colors):
            col[band_i == i] = c

        beyond = t >= 1.0
        fade_t = np.clip((t - 1.0) / FADE, 0, 1)
        col[beyond] = (surface0_rgb * (1 - fade_t[beyond, None])
                       + base_rgb * fade_t[beyond, None])

        img[within] = col[within]

    return np.clip(img, 0, 1)


def render(mode, W, H):
    hi = render_hires(mode, W * SS, H * SS)
    im_hi = Image.fromarray((hi * 255).astype(np.uint8), "RGB")
    im = im_hi.resize((W, H), Image.LANCZOS)

    arr = np.asarray(im, dtype=np.float32)
    rng = np.random.default_rng(7)
    arr = arr + rng.normal(0, GRAIN_SIGMA, arr.shape).astype(np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def main():
    out_wp = os.path.join(HERE, "wallpapers")
    out_pv = os.path.join(HERE, "preview")
    os.makedirs(out_wp, exist_ok=True)
    os.makedirs(out_pv, exist_ok=True)

    names = {"dark": "rooibos", "light": "manzanilla"}
    targets = sys.argv[1:] or list(PRESETS)
    for preset in targets:
        W, H, pw = PRESETS[preset]
        suffix = "" if preset == "desktop" else f"-{preset}"
        for mode, name in names.items():
            im = render(mode, W, H)
            wp_path = os.path.join(out_wp, f"{name}{suffix}.png")
            im.save(wp_path)
            ph = int(pw * H / W)
            preview = im.resize((pw, ph), Image.LANCZOS)
            pv_path = os.path.join(out_pv, f"{name}{suffix}-pv.png")
            preview.save(pv_path)
            print(f"OK {preset} {name}: {wp_path} ({im.width}x{im.height})  "
                  f"preview: {pv_path} ({preview.width}x{preview.height})")


if __name__ == "__main__":
    main()
