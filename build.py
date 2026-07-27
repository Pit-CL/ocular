#!/usr/bin/env python3
"""
Generador de paleta "Ocular" — Rooibos (dark) / Manzanilla (light).

Ciencia de color 100% reusada de herramientas externas del autor
(vendorizada en este repo como `color_science.py`): OKLCH<->sRGB con gamut
mapping + APCA-W3 0.1.9. Estructura de roles 100%
Catppuccin (drop-in): crust/mantle/base/surface0-2/overlay0-2/subtext0-1/text
+ 14 acentos + bloque ANSI16. Catppuccin queda solo como esqueleto de
nombres de rol.

Fuente de hues: palette/hues.json (tabla congelada de matices propios,
{rol: {hue, sat}}), derivada por `derive_hues.py` (optimizador dev-only que
maximiza el ΔE OKLab minimo entre los 14 acentos). Este script solo LEE esa
tabla; nunca corre el optimizador.

Falla con exit != 0 si la validacion APCA/WCAG/chroma/hue/ΔE no pasa.
"""
import itertools
import json
import os
import sys

from color_science import (oklch_to_hex, hex_to_oklch, solve_L_for_lc, lc, wcag,
                            clamp_chroma, delta_e_oklab, delta_e_cvd)

HERE = os.path.dirname(os.path.abspath(__file__))

ACCENTS = ["rosewater", "flamingo", "pink", "mauve", "red", "maroon", "peach",
           "yellow", "green", "teal", "sky", "sapphire", "blue", "lavender"]

# Lectura perezosa (no al importar el modulo): derive_hues.py importa constantes
# de este archivo para construir palette/hues.json (o hues-deutan.json) desde
# cero, y ese archivo todavia no existe la primera vez que se corre — leerlo
# aqui arriba rompia ese arranque en frio. Cache por nombre de tabla: build.py
# lee ambas tablas (hues.json y hues-deutan.json) en la misma corrida.
_HUES_CACHE: dict = {}


def _hues(table_name="hues"):
    if table_name not in _HUES_CACHE:
        with open(os.path.join(HERE, "palette", f"{table_name}.json")) as f:
            _HUES_CACHE[table_name] = json.load(f)
    return _HUES_CACHE[table_name]

# Gate de separacion de acentos (duplicado con comentario cruzado en audit.py,
# que re-verifica leyendo los JSON emitidos como defensa contra edicion a mano).
MIN_ACCENT_DE = 0.025

# Gate de separacion simulada (deuteranopia/protanopia), solo para las
# variantes *-deutan. Duplicado con comentario cruzado en audit.py. Congelado
# con margen bajo el minimo simulado global alcanzado por derive_hues.py
# --profile deutan (multi-start determinista + perturbacion dirigida): 0.0201
# (dark, protan, par sapphire-blue).
MIN_ACCENT_DE_CVD = 0.02

# --------------------------------------------------------------------------- #
# Parametros de la spec — neutros (L, C, H) y targets de texto (Lc, C, H)
# --------------------------------------------------------------------------- #
DARK_NEUTRALS = {
    "crust":    (0.180, 0.010, 70),
    "mantle":   (0.200, 0.011, 70),
    "base":     (0.220, 0.012, 70),
    "surface0": (0.270, 0.013, 70),
    "surface1": (0.320, 0.014, 70),
    "surface2": (0.370, 0.014, 70),
}
DARK_TEXT_TARGETS = {
    "text":     (82, 0.018, 85),
    "subtext1": (74, 0.016, 80),
    "subtext0": (68, 0.014, 80),
    "overlay2": (58, 0.012, 75),
    "overlay1": (50, 0.012, 75),
    "overlay0": (43, 0.010, 75),
}
DARK_ACCENT_LC = 71
DARK_ACCENT_CAP = 0.110

LIGHT_NEUTRALS = {
    "crust":    (0.910, 0.014, 78),
    "mantle":   (0.933, 0.013, 78),
    "base":     (0.955, 0.012, 78),
    "surface0": (0.900, 0.014, 78),
    "surface1": (0.868, 0.015, 78),
    "surface2": (0.830, 0.015, 78),
}
LIGHT_TEXT_TARGETS = {
    "text":     (88, 0.020, 70),
    "subtext1": (80, 0.018, 70),
    "subtext0": (72, 0.016, 72),
    "overlay2": (60, 0.014, 74),
    "overlay1": (52, 0.013, 74),
    "overlay0": (44, 0.012, 74),
}
LIGHT_ACCENT_LC = 74
LIGHT_ACCENT_CAP = 0.130

CHECKED_LC_ROLES = ["text", "subtext1", "subtext0", "overlay2"] + ACCENTS


def build_mode(neutrals, text_targets, accent_lc, accent_cap, lighter, hues_table="hues"):
    colors, lc_real, targets = {}, {}, {}
    for role, (L, C, H) in neutrals.items():
        colors[role] = oklch_to_hex(L, C, H)
    base_hex = colors["base"]

    for role, (target, C, H) in text_targets.items():
        _, hx, real = solve_L_for_lc(target, H, C, base_hex, lighter=lighter)
        colors[role] = hx
        lc_real[role] = real
        targets[role] = target

    for name in ACCENTS:
        hue = _hues(hues_table)["table"][name]["hue"]
        sat = _hues(hues_table)["table"][name]["sat"]
        C = round(sat * accent_cap, 3)
        # accent_lc: escalar (perfil default, mismo Lc para los 14) o dict por
        # rol (perfil deutan, Lc desigual a proposito — ver derive_hues.py).
        target = accent_lc[name] if isinstance(accent_lc, dict) else accent_lc
        _, hx, real = solve_L_for_lc(target, hue, C, base_hex, lighter=lighter)
        colors[name] = hx
        lc_real[name] = real
        targets[name] = target

    return colors, lc_real, targets, base_hex


def build_ansi(colors, base_hex, lighter):
    normal = {
        "black": colors["surface1"], "red": colors["red"], "green": colors["green"],
        "yellow": colors["yellow"], "blue": colors["blue"], "magenta": colors["pink"],
        "cyan": colors["teal"], "white": colors["subtext1"],
    }
    bright = {}
    bright_lc = {}
    for key, hx in normal.items():
        L, C, H = hex_to_oklch(hx)
        target = lc(hx, base_hex) + 6
        _, bhex, real = solve_L_for_lc(target, H, C, base_hex, lighter=lighter)
        bright[key] = bhex
        bright_lc[key] = real
    return {"normal": normal, "bright": bright}, bright_lc


def build_with_wcag_check(neutrals, text_targets, accent_lc, accent_cap, lighter, hues_table="hues"):
    text_targets = dict(text_targets)
    w = None
    for attempt in range(2):
        colors, lc_real, targets, base_hex = build_mode(
            neutrals, text_targets, accent_lc, accent_cap, lighter, hues_table)
        w = wcag(colors["text"], base_hex)
        if w >= 7.0:
            break
        if 6.5 <= w < 7.0 and attempt == 0:
            t, C, H = text_targets["text"]
            text_targets["text"] = (t + 2, C, H)
            continue
        break
    ansi, bright_lc = build_ansi(colors, base_hex, lighter)
    return colors, lc_real, targets, base_hex, w, ansi, bright_lc


def accent_de_pairs(colors):
    """Pares (ΔE, rol1, rol2) entre los 14 acentos, ordenados de mas cercano a mas lejano."""
    pairs = []
    for r1, r2 in itertools.combinations(ACCENTS, 2):
        de = delta_e_oklab(colors[r1], colors[r2])
        pairs.append((de, r1, r2))
    pairs.sort(key=lambda p: p[0])
    return pairs


def accent_cvd_de_pairs(colors, kind):
    """Como accent_de_pairs(), pero sobre los colores simulados (kind: 'deutan'|'protan')."""
    pairs = []
    for r1, r2 in itertools.combinations(ACCENTS, 2):
        de = delta_e_cvd(colors[r1], colors[r2], kind)
        pairs.append((de, r1, r2))
    pairs.sort(key=lambda p: p[0])
    return pairs


def validate(mode_name, colors, lc_real, targets, base_hex, wcag_val, accent_cap,
             hues_table="hues", check_cvd=False):
    errors = []

    all_hex = list(colors.values())
    for h in all_hex:
        if h.lower() in ("#000000", "#ffffff"):
            errors.append(f"{mode_name}: hex prohibido {h}")

    for role in CHECKED_LC_ROLES:
        real, target = lc_real[role], targets[role]
        if abs(real - target) > 1.5:
            errors.append(f"{mode_name}.{role}: Lc {real:.2f} vs target {target} "
                          f"(delta {abs(real - target):.2f} > 1.5)")

    if wcag_val < 7.0:
        errors.append(f"{mode_name}: WCAG text/base {wcag_val:.2f} < 7.0")

    # Tolerancia de cuantizacion hex (8-bit): redondear a #rrggbb y volver introduce
    # ruido de +-0.001..0.002 en el chroma reconstruido — no es una violacion real del cap.
    CHROMA_QUANT_EPS = 0.0015
    for name in ACCENTS:
        L, C, H = hex_to_oklch(colors[name])
        eff = clamp_chroma(L, C, H)
        if eff > accent_cap + CHROMA_QUANT_EPS:
            errors.append(f"{mode_name}.{name}: chroma efectivo {eff:.4f} > cap {accent_cap}")

    # 5a — fidelidad a la tabla congelada (palette/hues.json): el hue del hex final
    # debe quedar cerca del hue tabulado. Cerca del eje acromatico (C_eff baja) el
    # angulo OKLCH es numericamente inestable bajo cuantizacion de 8 bits (a,b
    # diminutos) — tolerancia ampliada documentada, igual que el patron anterior.
    HUE_DELTA_TIGHT = 2.0
    HUE_DELTA_LOOSE = 5.0
    LOW_CHROMA_HUE_THRESHOLD = 0.05
    for name in ACCENTS:
        table_hue = _hues(hues_table)["table"][name]["hue"]
        L, C, H = hex_to_oklch(colors[name])
        eff = clamp_chroma(L, C, H)
        delta = min(abs(H - table_hue), 360 - abs(H - table_hue))
        limit = HUE_DELTA_TIGHT if eff >= LOW_CHROMA_HUE_THRESHOLD else HUE_DELTA_LOOSE
        if delta > limit:
            errors.append(f"{mode_name}.{name}: hue delta {delta:.2f} grados > {limit} "
                          f"(tabla {table_hue}, ocular {H:.1f}, C_eff {eff:.4f})")
        elif eff < LOW_CHROMA_HUE_THRESHOLD and delta > HUE_DELTA_TIGHT:
            print(f"  [excepcion documentada] {mode_name}.{name}: hue delta {delta:.2f} grados "
                  f"(tabla {table_hue}, ocular {H:.1f}) — C_eff {eff:.4f} < {LOW_CHROMA_HUE_THRESHOLD} "
                  f"=> angulo inestable por cuantizacion hex 8-bit, tolerancia ampliada a "
                  f"{HUE_DELTA_LOOSE} grados, no error real")

        win_lo, win_hi = _hues(hues_table)["windows"][name]["hue"]
        if not (win_lo <= table_hue <= win_hi):
            errors.append(f"{mode_name}.{name}: hue de tabla {table_hue} fuera de su ventana "
                          f"declarada [{win_lo}, {win_hi}]")

    # 5b — gate de separacion perceptual: el minimo ΔE OKLab entre los 14 acentos
    # de esta variante debe superar MIN_ACCENT_DE (evita pares indistinguibles).
    pairs = accent_de_pairs(colors)
    min_de, r1, r2 = pairs[0]
    if min_de < MIN_ACCENT_DE:
        errors.append(f"{mode_name}: min ΔE OKLab entre acentos {min_de:.4f} < {MIN_ACCENT_DE} "
                      f"(par mas cercano: {r1}-{r2})")

    # 5c — gate CVD: solo para las variantes *-deutan. El minimo ΔE OKLab entre
    # los 14 acentos, visto bajo deuteranopia y bajo protanopia, debe superar
    # MIN_ACCENT_DE_CVD (evita pares indistinguibles para daltonismo rojo-verde).
    if check_cvd:
        for kind in ("deutan", "protan"):
            cvd_pairs = accent_cvd_de_pairs(colors, kind)
            min_de_cvd, r1c, r2c = cvd_pairs[0]
            if min_de_cvd < MIN_ACCENT_DE_CVD:
                errors.append(f"{mode_name}: min ΔE simulado {kind} entre acentos "
                              f"{min_de_cvd:.4f} < {MIN_ACCENT_DE_CVD} (par mas cercano: {r1c}-{r2c})")

    return errors


ALL_ROLE_ORDER = ["crust", "mantle", "base", "surface0", "surface1", "surface2",
                   "overlay0", "overlay1", "overlay2", "subtext0", "subtext1", "text"] + ACCENTS


def render_table(mode_name, colors, lc_real, targets, base_hex, ansi, bright_lc):
    lines = ["| rol | hex | Lc real | target | WCAG (vs base) | check |",
             "|---|---|---|---|---|---|"]
    for role in ALL_ROLE_ORDER:
        hx = colors[role]
        w = wcag(hx, base_hex)
        if role in lc_real:
            real, target = lc_real[role], targets[role]
            check = "OK" if abs(real - target) <= 1.5 else "FAIL"
            if role not in CHECKED_LC_ROLES:
                check += " (info, no exigido)"
            lines.append(f"| {role} | {hx} | {real:.2f} | {target} | {w:.2f} | {check} |")
        else:
            lines.append(f"| {role} | {hx} | n/a | n/a | {w:.2f} | info |")
    lines.append("")
    lines.append(f"WCAG text/base = {wcag(colors['text'], base_hex):.2f} (target >= 7.0)")
    lines.append("")
    lines.append("### ANSI16")
    lines.append("| color | normal hex | Lc normal | bright hex | Lc bright (+6 sobre normal) |")
    lines.append("|---|---|---|---|---|")
    for key, hx in ansi["normal"].items():
        bhx = ansi["bright"][key]
        lines.append(f"| {key} | {hx} | {lc(hx, base_hex):.2f} | {bhx} | {bright_lc[key]:.2f} |")
    return "\n".join(lines)


def render_accent_de_section(colors):
    """Seccion de VALIDACION.md: min ΔE entre acentos + tabla de los 5 pares mas cercanos."""
    pairs = accent_de_pairs(colors)
    min_de = pairs[0][0]
    lines = [f"min ΔE entre acentos = {min_de:.4f} (gate >= {MIN_ACCENT_DE})", "",
             "| par | ΔE OKLab |", "|---|---|"]
    for de, r1, r2 in pairs[:5]:
        lines.append(f"| {r1} — {r2} | {de:.4f} |")
    return "\n".join(lines)


def render_cvd_de_section(colors):
    """Seccion de VALIDACION.md (solo variantes *-deutan): min ΔE simulado
    (deuteranopia y protanopia) entre acentos + tabla de los 5 pares mas cercanos."""
    lines = []
    for kind, label in (("deutan", "deuteranopia"), ("protan", "protanopia")):
        pairs = accent_cvd_de_pairs(colors, kind)
        min_de = pairs[0][0]
        lines.append(f"min ΔE simulado ({label}) entre acentos = {min_de:.4f} "
                      f"(gate >= {MIN_ACCENT_DE_CVD})")
        lines.append("")
        lines.append("| par | ΔE OKLab simulado |")
        lines.append("|---|---|")
        for de, r1, r2 in pairs[:5]:
            lines.append(f"| {r1} — {r2} | {de:.4f} |")
        lines.append("")
    return "\n".join(lines)


SVG_FONT = "-apple-system, 'Segoe UI', sans-serif"
NEUTRAL_ORDER = ALL_ROLE_ORDER[:12]  # crust..text, sin acentos


def render_palette_svg(title, colors):
    """SVG determinista de preview (sin timestamps ni floats sin redondear):
    fila 1 = 14 acentos (cuadrados), fila 2 = 12 neutrales (barra contigua)."""
    width, height = 840, 230
    base, text, subtext0, surface2 = (colors["base"], colors["text"],
                                       colors["subtext0"], colors["surface2"])

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'  <rect x="0" y="0" width="{width}" height="{height}" rx="12" fill="{base}"/>',
        f'  <text x="24" y="34" font-family="{SVG_FONT}" font-size="15" font-weight="bold" '
        f'fill="{text}">{title}</text>',
    ]

    sq, gap, row1_y = 48, 8, 54
    for i, name in enumerate(ACCENTS):
        x = 24 + i * (sq + gap)
        cx = x + sq // 2
        parts.append(f'  <rect x="{x}" y="{row1_y}" width="{sq}" height="{sq}" rx="6" '
                      f'fill="{colors[name]}"/>')
        parts.append(f'  <text x="{cx}" y="{row1_y + sq + 13}" font-family="{SVG_FONT}" '
                      f'font-size="9" fill="{subtext0}" text-anchor="middle">{name}</text>')

    bw, bh, row2_y = 62, 26, 150
    for i, name in enumerate(NEUTRAL_ORDER):
        x = 24 + i * bw
        cx = x + bw // 2
        parts.append(f'  <rect x="{x}" y="{row2_y}" width="{bw}" height="{bh}" '
                      f'fill="{colors[name]}" stroke="{surface2}" stroke-width="1"/>')
        parts.append(f'  <text x="{cx}" y="{row2_y + bh + 13}" font-family="{SVG_FONT}" '
                      f'font-size="8" fill="{subtext0}" text-anchor="middle">{name}</text>')

    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def dump_svg(name, title, colors):
    path = os.path.join(HERE, "preview", f"palette-{name}.svg")
    with open(path, "w") as f:
        f.write(render_palette_svg(title, colors))
    return path


def main():
    dark = build_with_wcag_check(DARK_NEUTRALS, DARK_TEXT_TARGETS, DARK_ACCENT_LC,
                                  DARK_ACCENT_CAP, lighter=True)
    light = build_with_wcag_check(LIGHT_NEUTRALS, LIGHT_TEXT_TARGETS, LIGHT_ACCENT_LC,
                                   LIGHT_ACCENT_CAP, lighter=False)

    # Variantes deutan: mismos neutros/caps/text-targets (el trade-off vive
    # 100% en el Lc de los acentos); accent_lc es un dict por rol = Lc base +
    # dlc, leido de la tabla congelada hues-deutan.json (derive_hues.py).
    hues_deutan = _hues("hues-deutan")
    dark_accent_lc_deutan = {r: DARK_ACCENT_LC + hues_deutan["table"][r]["dlc"] for r in ACCENTS}
    light_accent_lc_deutan = {r: LIGHT_ACCENT_LC + hues_deutan["table"][r]["dlc"] for r in ACCENTS}
    dark_deutan = build_with_wcag_check(DARK_NEUTRALS, DARK_TEXT_TARGETS, dark_accent_lc_deutan,
                                         DARK_ACCENT_CAP, lighter=True, hues_table="hues-deutan")
    light_deutan = build_with_wcag_check(LIGHT_NEUTRALS, LIGHT_TEXT_TARGETS, light_accent_lc_deutan,
                                          LIGHT_ACCENT_CAP, lighter=False, hues_table="hues-deutan")

    d_colors, d_lc, d_targets, d_base, d_wcag, d_ansi, d_bright_lc = dark
    l_colors, l_lc, l_targets, l_base, l_wcag, l_ansi, l_bright_lc = light
    dd_colors, dd_lc, dd_targets, dd_base, dd_wcag, dd_ansi, dd_bright_lc = dark_deutan
    ld_colors, ld_lc, ld_targets, ld_base, ld_wcag, ld_ansi, ld_bright_lc = light_deutan

    errors = []
    errors += validate("dark", d_colors, d_lc, d_targets, d_base, d_wcag, DARK_ACCENT_CAP)
    errors += validate("light", l_colors, l_lc, l_targets, l_base, l_wcag, LIGHT_ACCENT_CAP)
    errors += validate("dark-deutan", dd_colors, dd_lc, dd_targets, dd_base, dd_wcag,
                        DARK_ACCENT_CAP, hues_table="hues-deutan", check_cvd=True)
    errors += validate("light-deutan", ld_colors, ld_lc, ld_targets, ld_base, ld_wcag,
                        LIGHT_ACCENT_CAP, hues_table="hues-deutan", check_cvd=True)

    def dump(name, mode, colors, ansi, lc_real, targets, wcag_val, display_name=None):
        path = os.path.join(HERE, "palette", f"{name}.json")
        data = {
            "name": display_name if display_name else name.capitalize(),
            "mode": mode,
            "colors": colors,
            "ansi": ansi,
            "meta": {
                "lc_real": {k: round(v, 2) for k, v in lc_real.items()},
                "lc_target": targets,
                "wcag_text_base": round(wcag_val, 2),
            },
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        return path

    dump("rooibos", "dark", d_colors, d_ansi, d_lc, d_targets, d_wcag)
    dump("manzanilla", "light", l_colors, l_ansi, l_lc, l_targets, l_wcag)
    dump("rooibos-deutan", "dark", dd_colors, dd_ansi, dd_lc, dd_targets, dd_wcag,
         display_name="Rooibos Deutan")
    dump("manzanilla-deutan", "light", ld_colors, ld_ansi, ld_lc, ld_targets, ld_wcag,
         display_name="Manzanilla Deutan")

    dump_svg("rooibos", "Ocular Rooibos (dark)", d_colors)
    dump_svg("manzanilla", "Ocular Manzanilla (light)", l_colors)
    dump_svg("rooibos-deutan", "Ocular Rooibos Deutan (dark)", dd_colors)
    dump_svg("manzanilla-deutan", "Ocular Manzanilla Deutan (light)", ld_colors)

    md = ["# Validacion — Ocular (Rooibos / Manzanilla / *-Deutan)", "",
          "## Rooibos (dark)", "",
          render_table("dark", d_colors, d_lc, d_targets, d_base, d_ansi, d_bright_lc), "",
          "### Separacion de acentos (ΔE OKLab) — dark", "",
          render_accent_de_section(d_colors), "",
          "## Manzanilla (light)", "",
          render_table("light", l_colors, l_lc, l_targets, l_base, l_ansi, l_bright_lc), "",
          "### Separacion de acentos (ΔE OKLab) — light", "",
          render_accent_de_section(l_colors), "",
          "## Rooibos Deutan (dark)", "",
          render_table("dark-deutan", dd_colors, dd_lc, dd_targets, dd_base, dd_ansi, dd_bright_lc), "",
          "### Separacion de acentos (ΔE OKLab) — dark deutan", "",
          render_accent_de_section(dd_colors), "",
          "### Separacion simulada CVD — dark deutan", "",
          render_cvd_de_section(dd_colors), "",
          "## Manzanilla Deutan (light)", "",
          render_table("light-deutan", ld_colors, ld_lc, ld_targets, ld_base, ld_ansi, ld_bright_lc), "",
          "### Separacion de acentos (ΔE OKLab) — light deutan", "",
          render_accent_de_section(ld_colors), "",
          "### Separacion simulada CVD — light deutan", "",
          render_cvd_de_section(ld_colors), ""]
    with open(os.path.join(HERE, "palette", "VALIDACION.md"), "w") as f:
        f.write("\n".join(md))

    print("=== Rooibos (dark) ===")
    print(render_table("dark", d_colors, d_lc, d_targets, d_base, d_ansi, d_bright_lc))
    print()
    print(render_accent_de_section(d_colors))
    print()
    print("=== Manzanilla (light) ===")
    print(render_table("light", l_colors, l_lc, l_targets, l_base, l_ansi, l_bright_lc))
    print()
    print(render_accent_de_section(l_colors))
    print()
    print("=== Rooibos Deutan (dark) ===")
    print(render_table("dark-deutan", dd_colors, dd_lc, dd_targets, dd_base, dd_ansi, dd_bright_lc))
    print()
    print(render_accent_de_section(dd_colors))
    print()
    print(render_cvd_de_section(dd_colors))
    print()
    print("=== Manzanilla Deutan (light) ===")
    print(render_table("light-deutan", ld_colors, ld_lc, ld_targets, ld_base, ld_ansi, ld_bright_lc))
    print()
    print(render_accent_de_section(ld_colors))
    print()
    print(render_cvd_de_section(ld_colors))
    print()

    if errors:
        print(f"VALIDACION FALLIDA ({len(errors)} error(es)):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("VALIDACION OK — todos los checks pasaron.")


if __name__ == "__main__":
    main()
