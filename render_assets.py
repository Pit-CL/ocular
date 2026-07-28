#!/usr/bin/env python3
"""
Assets de identidad visual "Ocular" — logo (ojo), mockup de terminal,
comparativo CVD y (opcional) preview social PNG.

Deterministico igual que build.render_palette_svg: sin timestamps, sin
random, floats redondeados. Reusa ACCENTS/SVG_FONT de build.py (mismo
patron de import cruzado que ya usa derive_hues.py) y toda la ciencia de
color de color_science.py — sin dependencias externas para el modo SVG
(PIL solo se importa si se pide --png, y solo dentro de esa funcion).

Uso:
    python3 render_assets.py         # solo SVG (preview/*.svg), gate APCA
    python3 render_assets.py --png   # SVG + preview/social-preview.png (PIL)

Gate APCA (terminal mockup): cada par fg/bg que el script emite se mide con
lc() y debe superar su piso — 60 por defecto, 45 para los dots (decorativos,
tamano grande) y 75 para cualquier uso del rol "text" (texto principal:
comando del prompt, texto de las lineas de diff). Exit != 0 si algun par
queda bajo su piso.
"""
import json
import math
import os
import sys

from build import ACCENTS, SVG_FONT
from color_science import hex_to_oklab, oklch_to_hex, lc, simulate_cvd

HERE = os.path.dirname(os.path.abspath(__file__))
PREVIEW_DIR = os.path.join(HERE, "preview")
MONO_FONT = "ui-monospace, 'SF Mono', Menlo, monospace"


def _load_palette(name):
    with open(os.path.join(HERE, "palette", f"{name}.json")) as f:
        return json.load(f)


def _write(path, content):
    with open(path, "w") as f:
        f.write(content)


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Mezcla OKLab hex_a<-hex_b (t=peso de hex_b) — replica de mix_oklab en
# ports/build_ports.py:1210 (mismo pipeline: OKLab + gamut mapping via
# oklch_to_hex), duplicada aqui para no importar el script completo de
# ports/build_ports.py por una funcion de 8 lineas.
def mix_oklab(hex_a: str, hex_b: str, t: float) -> str:
    L1, a1, b1 = hex_to_oklab(hex_a)
    L2, a2, b2 = hex_to_oklab(hex_b)
    L = L1 + (L2 - L1) * t
    a = a1 + (a2 - a1) * t
    bb = b1 + (b2 - b1) * t
    C = math.hypot(a, bb)
    H = math.degrees(math.atan2(bb, a)) % 360
    return oklch_to_hex(L, C, H)


# --------------------------------------------------------------------------- #
# 1 — Logo: ojo minimalista (parpados = 2 arcos cubicos, iris = 14 arcos con
#     los acentos, pupila = crust). Fondo transparente, sin texto.
# --------------------------------------------------------------------------- #
LOGO_SIZE = 240
LOGO_CX = LOGO_SIZE // 2
LOGO_CY = LOGO_SIZE // 2
EYE_LEFT_X = 20
EYE_RIGHT_X = LOGO_SIZE - 20
EYE_CTRL_Y_UP = 44
EYE_CTRL_Y_DOWN = LOGO_SIZE - 44
EYE_CTRL_X1_T = 0.25
EYE_CTRL_X2_T = 0.75
EYE_STROKE_W = 7

IRIS_OUTER_R = round(LOGO_SIZE * 0.28, 2)
IRIS_THICKNESS = round(LOGO_SIZE * 0.10, 2)
IRIS_INNER_R = round(IRIS_OUTER_R - IRIS_THICKNESS, 2)
PUPIL_R = round(IRIS_INNER_R - 5, 2)


def _pt(cx, cy, r, deg):
    rad = math.radians(deg)
    return round(cx + r * math.cos(rad), 2), round(cy + r * math.sin(rad), 2)


def _donut_segment(cx, cy, r_outer, r_inner, start_deg, end_deg):
    """Path de un gajo de anillo (donut) entre dos angulos, para un acento."""
    x1, y1 = _pt(cx, cy, r_outer, start_deg)
    x2, y2 = _pt(cx, cy, r_outer, end_deg)
    x3, y3 = _pt(cx, cy, r_inner, end_deg)
    x4, y4 = _pt(cx, cy, r_inner, start_deg)
    large = 1 if (end_deg - start_deg) > 180 else 0
    return (f"M {x1} {y1} A {r_outer} {r_outer} 0 {large} 1 {x2} {y2} "
            f"L {x3} {y3} A {r_inner} {r_inner} 0 {large} 0 {x4} {y4} Z")


def render_logo_svg(colors):
    n = len(ACCENTS)
    step = 360 / n
    start = -90.0  # primer gajo arranca arriba

    lx, rx = EYE_LEFT_X, EYE_RIGHT_X
    c1x = round(lx + (rx - lx) * EYE_CTRL_X1_T, 2)
    c2x = round(lx + (rx - lx) * EYE_CTRL_X2_T, 2)
    eye_path = (f"M {lx} {LOGO_CY} C {c1x} {EYE_CTRL_Y_UP} {c2x} {EYE_CTRL_Y_UP} {rx} {LOGO_CY} "
                f"C {c2x} {EYE_CTRL_Y_DOWN} {c1x} {EYE_CTRL_Y_DOWN} {lx} {LOGO_CY} Z")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{LOGO_SIZE}" height="{LOGO_SIZE}" '
        f'viewBox="0 0 {LOGO_SIZE} {LOGO_SIZE}">',
        f'  <path d="{eye_path}" fill="none" stroke="{colors["text"]}" '
        f'stroke-width="{EYE_STROKE_W}" stroke-linejoin="round"/>',
    ]
    for i, name in enumerate(ACCENTS):
        a0 = round(start + i * step, 3)
        a1 = round(start + (i + 1) * step, 3)
        d = _donut_segment(LOGO_CX, LOGO_CY, IRIS_OUTER_R, IRIS_INNER_R, a0, a1)
        parts.append(f'  <path d="{d}" fill="{colors[name]}"/>')
    parts.append(f'  <circle cx="{LOGO_CX}" cy="{LOGO_CY}" r="{PUPIL_R}" fill="{colors["crust"]}"/>')
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------- #
# 2 — Terminal mockup: barra con 3 dots + titulo, prompt del fleet, snippet
#     corto real (reducido de build.py: el gate ΔE de accent_de_pairs() y el
#     sys.exit(1) de main()), 2 lineas de diff con fondo mezclado OKLab.
# --------------------------------------------------------------------------- #
TERM_W, TERM_H = 760, 420
TERM_RADIUS = 12
BAR_H = 36
DOT_R = 6
DOT_Y = BAR_H // 2
DOT_XS = (24, 46, 68)
LEFT_PAD = 24
LINE_H = 24
CODE_SIZE = 14
PROMPT_Y = BAR_H + 30
CODE_Y0 = PROMPT_Y + LINE_H + 6
DIFF_GAP = 12
DIFF_TINT = 0.12  # = TINT_NORMAL en ports/build_ports.py:1206

ROLE_FOR_TOKEN_TYPE = {
    "text": "text", "keyword": "mauve", "string": "green",
    "number": "peach", "comment": "subtext0", "function": "blue",
}


def _resolve(tokens):
    return [(text, ROLE_FOR_TOKEN_TYPE[kind]) for text, kind in tokens]


PROMPT_TOKENS = [
    ("~/proyectos/ocular", "peach"),
    (" main", "mauve"),
    (" ", "text"),
    ("❯", "green"),  # ❯
    (" python3 build.py", "text"),
]

# Reducido de build.py: accent_de_pairs() (linea ~239) + el sys.exit(1) de
# main() (linea ~479) — el gate de separacion perceptual entre acentos.
CODE_LINES = [_resolve(line) for line in [
    [("# gate: separacion perceptual minima entre acentos", "comment")],
    [("pairs", "text"), (" = ", "text"), ("accent_de_pairs", "function"), ("(colors)", "text")],
    [("min_de, r1, r2 = pairs[", "text"), ("0", "number"), ("]", "text")],
    [("if", "keyword"), (" min_de < MIN_ACCENT_DE:", "text")],
    [("    errors.", "text"), ("append", "function"),
     ('(f"ΔE {min_de:.4f} < {MIN_ACCENT_DE}")', "string")],
    [("if", "keyword"), (" errors:", "text")],
    [("    sys.", "text"), ("exit", "function"), ("(", "text"), ("1", "number"), (")", "text")],
]]

DIFF_LINES = [
    ("+     DARK_ACCENT_LC = 71", "green"),
    ("-     DARK_ACCENT_LC = 68", "red"),
]

APCA_CHECKS = []  # (svg, label, fg, bg, floor) — poblado durante el render


def _check(svg, label, fg, bg, floor):
    APCA_CHECKS.append((svg, label, fg, bg, floor))


def _line_svg(svg_name, x, y, tokens, colors, bg_hex, size=CODE_SIZE, font=MONO_FONT):
    spans = []
    for text, role in tokens:
        color = colors[role]
        if text.strip():
            floor = 75 if role == "text" else 60
            _check(svg_name, text.strip()[:24], color, bg_hex, floor)
        spans.append(f'<tspan fill="{color}">{_esc(text)}</tspan>')
    return f'  <text x="{x}" y="{y}" font-family="{font}" font-size="{size}">{"".join(spans)}</text>'


def _diff_line_svg(svg_name, y_baseline, text, accent_role, colors):
    bg = mix_oklab(colors["base"], colors[accent_role], DIFF_TINT)
    rect_y = y_baseline - LINE_H + 7
    fg = colors["text"]
    _check(svg_name, f"diff {accent_role}", fg, bg, 75)
    rect = (f'  <rect x="12" y="{rect_y}" width="{TERM_W - 24}" height="{LINE_H}" fill="{bg}"/>')
    txt = (f'  <text x="{LEFT_PAD}" y="{y_baseline}" font-family="{MONO_FONT}" '
           f'font-size="{CODE_SIZE}" fill="{fg}">{_esc(text)}</text>')
    return rect + "\n" + txt


def render_terminal_svg(colors, variant):
    svg_name = f"terminal-{variant}"
    W, H, R = TERM_W, TERM_H, TERM_RADIUS
    clip_id = f"term-clip-{variant}"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'xml:space="preserve">',
        f'  <defs><clipPath id="{clip_id}"><rect x="0" y="0" width="{W}" height="{H}" rx="{R}"/>'
        f'</clipPath></defs>',
        f'  <rect x="0" y="0" width="{W}" height="{H}" rx="{R}" fill="{colors["base"]}"/>',
        f'  <g clip-path="url(#{clip_id})">',
        f'    <rect x="0" y="0" width="{W}" height="{BAR_H}" fill="{colors["mantle"]}"/>',
    ]
    for x, role in zip(DOT_XS, ("red", "yellow", "green")):
        color = colors[role]
        _check(svg_name, f"dot {role}", color, colors["mantle"], 45)
        parts.append(f'    <circle cx="{x}" cy="{DOT_Y}" r="{DOT_R}" fill="{color}"/>')

    title = f"ocular @ {variant}"
    _check(svg_name, "title", colors["subtext0"], colors["mantle"], 60)
    parts.append(f'    <text x="{W // 2}" y="{DOT_Y + 5}" font-family="{SVG_FONT}" font-size="13" '
                  f'fill="{colors["subtext0"]}" text-anchor="middle">{_esc(title)}</text>')
    parts.append('  </g>')
    parts.append(f'  <rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="{R}" '
                  f'fill="none" stroke="{colors["surface1"]}" stroke-width="1.5"/>')

    parts.append(_line_svg(svg_name, LEFT_PAD, PROMPT_Y, PROMPT_TOKENS, colors, colors["base"]))

    y = CODE_Y0
    for tokens in CODE_LINES:
        parts.append(_line_svg(svg_name, LEFT_PAD, y, tokens, colors, colors["base"]))
        y += LINE_H

    y += DIFF_GAP
    for text, role in DIFF_LINES:
        parts.append(_diff_line_svg(svg_name, y, text, role, colors))
        y += LINE_H

    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def gate_terminal_apca():
    rows, errors = [], []
    for svg, label, fg, bg, floor in APCA_CHECKS:
        val = lc(fg, bg)
        ok = val >= floor
        rows.append((svg, label, fg, bg, val, floor, ok))
        if not ok:
            errors.append(f"{svg}: {label!r} Lc {val:.2f} < piso {floor} (fg={fg} bg={bg})")
    return rows, errors


# --------------------------------------------------------------------------- #
# 3 — CVD compare: fila A = acentos default vistos con deuteranopia (colapso
#     rojo/verde), fila B = variante *-deutan vista con la misma simulacion
#     (se distinguen por luminancia). Solo modo dark (rooibos).
# --------------------------------------------------------------------------- #
CVD_W, CVD_H = 840, 260
CVD_SQ, CVD_GAP, CVD_LEFT = 48, 8, 24


def render_cvd_svg():
    base_pal = _load_palette("rooibos")
    deutan_pal = _load_palette("rooibos-deutan")
    base_colors = base_pal["colors"]
    deutan_colors = deutan_pal["colors"]
    deutan_lc_real = deutan_pal["meta"]["lc_real"]

    bg = base_colors["base"]
    label_color = base_colors["subtext0"]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CVD_W}" height="{CVD_H}" '
        f'viewBox="0 0 {CVD_W} {CVD_H}">',
        f'  <rect x="0" y="0" width="{CVD_W}" height="{CVD_H}" rx="12" fill="{bg}"/>',
    ]

    row_a_label_y, row_a_y = 24, 34
    parts.append(f'  <text x="{CVD_LEFT}" y="{row_a_label_y}" font-family="{SVG_FONT}" '
                 f'font-size="13" fill="{label_color}">Default accents · deuteranopia '
                 f'simulation</text>')
    for i, name in enumerate(ACCENTS):
        x = CVD_LEFT + i * (CVD_SQ + CVD_GAP)
        sim = simulate_cvd(base_colors[name], "deutan")
        parts.append(f'  <rect x="{x}" y="{row_a_y}" width="{CVD_SQ}" height="{CVD_SQ}" rx="6" '
                      f'fill="{sim}"/>')

    row_b_label_y = row_a_y + CVD_SQ + 34
    row_b_y = row_b_label_y + 10
    parts.append(f'  <text x="{CVD_LEFT}" y="{row_b_label_y}" font-family="{SVG_FONT}" '
                 f'font-size="13" fill="{label_color}">Deutan variant · same '
                 f'simulation</text>')
    for i, name in enumerate(ACCENTS):
        x = CVD_LEFT + i * (CVD_SQ + CVD_GAP)
        sim = simulate_cvd(deutan_colors[name], "deutan")
        parts.append(f'  <rect x="{x}" y="{row_b_y}" width="{CVD_SQ}" height="{CVD_SQ}" rx="6" '
                      f'fill="{sim}"/>')
        cx = x + CVD_SQ // 2
        lc_val = deutan_lc_real[name]
        parts.append(f'  <text x="{cx}" y="{row_b_y + CVD_SQ + 13}" font-family="{SVG_FONT}" '
                      f'font-size="8" fill="{label_color}" text-anchor="middle">{lc_val:.1f}</text>')

    parts.append('</svg>')
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------- #
# 4 — Social preview PNG (1280x640), solo con --png. PIL puro (como
#     wallpaper.py), sin numpy. No corre en CI.
# --------------------------------------------------------------------------- #
SOCIAL_W, SOCIAL_H = 1280, 640

BOLD_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]
REGULAR_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]


def _find_font(ImageFont, candidates, size):
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size), p
    return ImageFont.load_default(), "PIL load_default() (no se encontro TTF DejaVu/Arial)"


def _fit_font(ImageFont, draw, candidates, text, max_width, size, min_size=14):
    font, path = _find_font(ImageFont, candidates, size)
    while size > min_size:
        box = draw.textbbox((0, 0), text, font=font)
        if (box[2] - box[0]) <= max_width:
            break
        size -= 2
        font, path = _find_font(ImageFont, candidates, size)
    return font, path


def render_social_png(colors):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (SOCIAL_W, SOCIAL_H), colors["base"])
    draw = ImageDraw.Draw(img)

    # ojo simplificado: elipse (parpados) + gajos (iris) + circulo (pupila)
    cx, cy = 250, SOCIAL_H // 2
    eye_w, eye_h = 320, 180
    draw.ellipse((cx - eye_w // 2, cy - eye_h // 2, cx + eye_w // 2, cy + eye_h // 2),
                  outline=colors["text"], width=7)
    outer_r, inner_r = 75, 48
    n = len(ACCENTS)
    step = 360 / n
    for i, name in enumerate(ACCENTS):
        a0 = -90 + i * step
        a1 = -90 + (i + 1) * step
        draw.pieslice((cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r), a0, a1,
                      fill=colors[name])
    draw.ellipse((cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r), fill=colors["crust"])

    text_x = 520
    wordmark_font, wordmark_font_path = _find_font(ImageFont, BOLD_FONT_CANDIDATES, 120)
    wm_box = draw.textbbox((text_x, 150), "Ocular", font=wordmark_font)
    draw.text((text_x, 150), "Ocular", font=wordmark_font, fill=colors["text"])

    tagline = "relax your eyes — every color set by science"
    tagline_font, tagline_font_path = _fit_font(
        ImageFont, draw, REGULAR_FONT_CANDIDATES, tagline, SOCIAL_W - 40 - text_x, 28)
    draw.text((text_x, wm_box[3] + 40), tagline, font=tagline_font, fill=colors["subtext1"])

    stripe_y0, stripe_y1 = 560, 600
    left, right = 60, SOCIAL_W - 60
    band_w = (right - left) / n
    for i, name in enumerate(ACCENTS):
        x0 = round(left + i * band_w)
        x1 = round(left + (i + 1) * band_w)
        draw.rectangle((x0, stripe_y0, x1, stripe_y1), fill=colors[name])

    path = os.path.join(PREVIEW_DIR, "social-preview.png")
    img.save(path)
    return path, wordmark_font_path, tagline_font_path


def main():
    do_png = "--png" in sys.argv[1:]
    os.makedirs(PREVIEW_DIR, exist_ok=True)

    rooibos = _load_palette("rooibos")["colors"]
    manzanilla = _load_palette("manzanilla")["colors"]

    _write(os.path.join(PREVIEW_DIR, "logo-rooibos.svg"), render_logo_svg(rooibos))
    _write(os.path.join(PREVIEW_DIR, "logo-manzanilla.svg"), render_logo_svg(manzanilla))
    print(f"OK logo-rooibos.svg / logo-manzanilla.svg ({LOGO_SIZE}x{LOGO_SIZE})")

    _write(os.path.join(PREVIEW_DIR, "terminal-rooibos.svg"), render_terminal_svg(rooibos, "rooibos"))
    _write(os.path.join(PREVIEW_DIR, "terminal-manzanilla.svg"),
           render_terminal_svg(manzanilla, "manzanilla"))
    print(f"OK terminal-rooibos.svg / terminal-manzanilla.svg ({TERM_W}x{TERM_H})")

    rows, errors = gate_terminal_apca()
    print()
    print("=== Gate APCA -- terminal mockup ===")
    print(f"{'svg':<20}{'par':<26}{'fg':<9}{'bg':<9}{'Lc':>7}{'piso':>6}  check")
    for svg, label, fg, bg, val, floor, ok in rows:
        print(f"{svg:<20}{label:<26}{fg:<9}{bg:<9}{val:>7.2f}{floor:>6}  {'OK' if ok else 'FAIL'}")
    if errors:
        print()
        print(f"GATE APCA FALLIDO ({len(errors)} error(es)):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    _write(os.path.join(PREVIEW_DIR, "cvd-compare.svg"), render_cvd_svg())
    print(f"\nOK cvd-compare.svg ({CVD_W}x{CVD_H})")

    if do_png:
        path, wm_font, tag_font = render_social_png(rooibos)
        print(f"OK {path} ({SOCIAL_W}x{SOCIAL_H}) -- wordmark font: {wm_font}; "
              f"tagline font: {tag_font}")

    print()
    print("render_assets.py OK -- todos los gates pasaron.")


if __name__ == "__main__":
    main()
