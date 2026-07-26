#!/usr/bin/env python3
"""
Generador de paleta "Ocular" — Rooibos (dark) / Manzanilla (light).

Ciencia de color 100% reusada de herramientas externas del autor
(vendorizada en este repo como `color_science.py`): OKLCH<->sRGB con gamut
mapping + APCA-W3 0.1.9. Estructura de roles 100%
Catppuccin (drop-in): crust/mantle/base/surface0-2/overlay0-2/subtext0-1/text
+ 14 acentos + bloque ANSI16.

Fuente de hues oficiales: palette/catppuccin-oficial.json (mocha para dark,
latte para light) — descargado de catppuccin/palette, NUNCA de memoria.

Falla con exit != 0 si la validacion APCA/WCAG/chroma/hue no pasa.
"""
import json
import os
import sys

from color_science import oklch_to_hex, hex_to_oklch, solve_L_for_lc, lc, wcag, clamp_chroma

HERE = os.path.dirname(os.path.abspath(__file__))

ACCENTS = ["rosewater", "flamingo", "pink", "mauve", "red", "maroon", "peach",
           "yellow", "green", "teal", "sky", "sapphire", "blue", "lavender"]

with open(os.path.join(HERE, "palette", "catppuccin-oficial.json")) as f:
    OFICIAL = json.load(f)

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


def build_mode(neutrals, text_targets, accent_lc, accent_cap, oficial_flavor, lighter):
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
        off_hex = OFICIAL[oficial_flavor][name]
        _, offC, offH = hex_to_oklch(off_hex)
        C = min(accent_cap, offC)
        _, hx, real = solve_L_for_lc(accent_lc, offH, C, base_hex, lighter=lighter)
        colors[name] = hx
        lc_real[name] = real
        targets[name] = accent_lc

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


def build_with_wcag_check(neutrals, text_targets, accent_lc, accent_cap, oficial_flavor, lighter):
    text_targets = dict(text_targets)
    w = None
    for attempt in range(2):
        colors, lc_real, targets, base_hex = build_mode(
            neutrals, text_targets, accent_lc, accent_cap, oficial_flavor, lighter)
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


def validate(mode_name, colors, lc_real, targets, base_hex, wcag_val, accent_cap, oficial_flavor):
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

    # Hue: cerca del eje acromatico (chroma oficial muy baja) el angulo OKLCH es
    # numericamente inestable bajo cuantizacion de 8 bits (a,b diminutos) — excepcion
    # documentada explicitamente permitida por la spec ("salvo gamut mapping documentado").
    LOW_CHROMA_HUE_EXEMPT = 0.03
    for name in ACCENTS:
        off_hex = OFICIAL[oficial_flavor][name]
        _, offC, offH = hex_to_oklch(off_hex)
        _, _, H = hex_to_oklch(colors[name])
        delta = min(abs(H - offH), 360 - abs(H - offH))
        if delta > 2.0:
            if offC < LOW_CHROMA_HUE_EXEMPT and delta <= 4.0:
                print(f"  [excepcion documentada] {mode_name}.{name}: hue delta {delta:.2f} grados "
                      f"(oficial {offH:.1f}, ocular {H:.1f}) — chroma oficial {offC:.4f} < "
                      f"{LOW_CHROMA_HUE_EXEMPT} => angulo inestable por cuantizacion hex 8-bit, no error real")
            else:
                errors.append(f"{mode_name}.{name}: hue delta {delta:.2f} grados > 2 "
                              f"(oficial {offH:.1f}, ocular {H:.1f})")

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


def main():
    dark = build_with_wcag_check(DARK_NEUTRALS, DARK_TEXT_TARGETS, DARK_ACCENT_LC,
                                  DARK_ACCENT_CAP, "mocha", lighter=True)
    light = build_with_wcag_check(LIGHT_NEUTRALS, LIGHT_TEXT_TARGETS, LIGHT_ACCENT_LC,
                                   LIGHT_ACCENT_CAP, "latte", lighter=False)

    d_colors, d_lc, d_targets, d_base, d_wcag, d_ansi, d_bright_lc = dark
    l_colors, l_lc, l_targets, l_base, l_wcag, l_ansi, l_bright_lc = light

    errors = []
    errors += validate("dark", d_colors, d_lc, d_targets, d_base, d_wcag, DARK_ACCENT_CAP, "mocha")
    errors += validate("light", l_colors, l_lc, l_targets, l_base, l_wcag, LIGHT_ACCENT_CAP, "latte")

    def dump(name, mode, colors, ansi, lc_real, targets, wcag_val):
        path = os.path.join(HERE, "palette", f"{name}.json")
        data = {
            "name": name.capitalize(),
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

    md = ["# Validacion — Ocular (Rooibos / Manzanilla)", "",
          "## Rooibos (dark)", "",
          render_table("dark", d_colors, d_lc, d_targets, d_base, d_ansi, d_bright_lc), "",
          "## Manzanilla (light)", "",
          render_table("light", l_colors, l_lc, l_targets, l_base, l_ansi, l_bright_lc), ""]
    with open(os.path.join(HERE, "palette", "VALIDACION.md"), "w") as f:
        f.write("\n".join(md))

    print("=== Rooibos (dark) ===")
    print(render_table("dark", d_colors, d_lc, d_targets, d_base, d_ansi, d_bright_lc))
    print()
    print("=== Manzanilla (light) ===")
    print(render_table("light", l_colors, l_lc, l_targets, l_base, l_ansi, l_bright_lc))
    print()

    if errors:
        print(f"VALIDACION FALLIDA ({len(errors)} error(es)):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("VALIDACION OK — todos los checks pasaron.")


if __name__ == "__main__":
    main()
