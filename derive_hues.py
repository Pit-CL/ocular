#!/usr/bin/env python3
"""
Optimizador de matices propios para los 14 acentos de Ocular — herramienta DEV-ONLY.

Catppuccin queda solo como esqueleto de nombres de rol; los matices (hue) y la
saturacion relativa (sat, como fraccion del cap de croma por variante) ahora
son 100% nuestros. Este script NUNCA lo corre CI: se ejecuta a mano cuando se
quiere iterar el caracter estetico, y el resultado congelado se versiona en
`palette/hues.json`. `build.py` solo LEE esa tabla.

Algoritmo: coordinate ascent determinista (sin random). Orden fijo de roles
(= ACCENTS de build.py), schedule fijo de pasos (grados de hue, fraccion de
sat) que se va refinando: (+/-4, +/-0.05) -> (+/-2, +/-0.025) -> (+/-1, +/-0.01).
En cada fase se recorre la lista de roles en orden y, para cada uno, se prueban
los 4 vecinos (hue+paso, hue-paso, sat+paso, sat-paso) clampeados a la ventana
del rol; se aplica el vecino solo si mejora estrictamente (> 1e-6) el minimo
ΔE OKLab entre los 14 acentos. Se repite la fase hasta punto fijo (nadie mejora)
con tope de 20 iteraciones.

La funcion objetivo evalua colores FINALES (tras solve_L_for_lc + gamut mapping
+ cuantizacion a hex 8-bit) para AMBAS variantes (dark=Rooibos, light=Manzanilla)
y toma el minimo ΔE sobre la union de los 91 pares de cada variante.

Uso:
  python3 derive_hues.py                      # escribe palette/hues.json
  python3 derive_hues.py --preview out.html    # ademas genera un preview HTML
                                                # standalone (NUNCA dentro del repo)
"""
from __future__ import annotations
import argparse
import itertools
import json
import os
import subprocess
import sys

from color_science import oklch_to_hex, hex_to_oklab, delta_e_oklab, solve_L_for_lc
from build import (
    ACCENTS, DARK_NEUTRALS, LIGHT_NEUTRALS,
    DARK_ACCENT_LC, DARK_ACCENT_CAP, LIGHT_ACCENT_LC, LIGHT_ACCENT_CAP,
    MIN_ACCENT_DE, accent_de_pairs,
)

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- #
# Ventanas por rol — familia del nombre + anclas semanticas + caracter
# "crepusculo" (calido, polvoriento, en armonia con los neutrales cafe/te).
# Tabla EXACTA del plan aprobado (checkpoint visual decide la version final).
# --------------------------------------------------------------------------- #
WINDOWS = {
    "red":       {"hue": [20, 30],   "sat": [0.95, 1.00]},
    "maroon":    {"hue": [35, 50],   "sat": [0.60, 0.80]},
    "peach":     {"hue": [50, 65],   "sat": [0.95, 1.00]},
    "yellow":    {"hue": [80, 95],   "sat": [0.95, 1.00]},
    "green":     {"hue": [130, 150], "sat": [0.75, 0.95]},
    "teal":      {"hue": [175, 195], "sat": [0.80, 1.00]},
    "sky":       {"hue": [210, 228], "sat": [0.75, 0.95]},
    "sapphire":  {"hue": [238, 252], "sat": [0.90, 1.00]},
    "blue":      {"hue": [256, 270], "sat": [0.95, 1.00]},
    "lavender":  {"hue": [282, 298], "sat": [0.65, 0.85]},
    "mauve":     {"hue": [300, 320], "sat": [0.85, 1.00]},
    "pink":      {"hue": [335, 355], "sat": [0.80, 1.00]},
    "flamingo":  {"hue": [5, 25],    "sat": [0.50, 0.70]},
    "rosewater": {"hue": [15, 40],   "sat": [0.30, 0.45]},
}

SCHEDULE = [(4, 0.05), (2, 0.025), (1, 0.01)]
MAX_ITERS_PER_PHASE = 20
IMPROVE_EPS = 1e-6

VARIANTS = {
    "dark": {
        "neutrals": DARK_NEUTRALS,
        "target_lc": DARK_ACCENT_LC,
        "cap": DARK_ACCENT_CAP,
        "lighter": True,
    },
    "light": {
        "neutrals": LIGHT_NEUTRALS,
        "target_lc": LIGHT_ACCENT_LC,
        "cap": LIGHT_ACCENT_CAP,
        "lighter": False,
    },
}
for _v in VARIANTS.values():
    _v["base_hex"] = oklch_to_hex(*_v["neutrals"]["base"])

_SOLVE_CACHE: dict[tuple[str, int, float], str] = {}


def resolve_hex(variant: str, hue: int, sat: float) -> str:
    """Hex final del acento (H, sat) en la variante dada, cacheado por (variante, H, C)."""
    cfg = VARIANTS[variant]
    C = round(sat * cfg["cap"], 3)
    key = (variant, hue, C)
    hx = _SOLVE_CACHE.get(key)
    if hx is None:
        _, hx, _ = solve_L_for_lc(cfg["target_lc"], hue, C, cfg["base_hex"], lighter=cfg["lighter"])
        _SOLVE_CACHE[key] = hx
    return hx


def variant_hexes(variant: str, table: dict) -> dict:
    return {role: resolve_hex(variant, *table[role]) for role in ACCENTS}


def min_delta_e(table: dict) -> float:
    """Minimo ΔE OKLab sobre la union de los 91 pares de cada variante (182 evaluaciones)."""
    best = float("inf")
    for variant in VARIANTS:
        hexes = variant_hexes(variant, table)
        labs = {role: hex_to_oklab(hx) for role, hx in hexes.items()}
        for r1, r2 in itertools.combinations(ACCENTS, 2):
            L1, a1, b1 = labs[r1]
            L2, a2, b2 = labs[r2]
            de = ((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2) ** 0.5
            if de < best:
                best = de
    return best


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def initial_table() -> dict:
    table = {}
    for role in ACCENTS:
        win = WINDOWS[role]
        hue = round((win["hue"][0] + win["hue"][1]) / 2)
        sat = round((win["sat"][0] + win["sat"][1]) / 2, 3)
        table[role] = (hue, sat)
    return table


def optimize(table: dict) -> dict:
    for step_deg, step_sat in SCHEDULE:
        for _ in range(MAX_ITERS_PER_PHASE):
            changed = False
            for role in ACCENTS:
                win = WINDOWS[role]
                hue, sat = table[role]
                base_score = min_delta_e(table)
                best_score = base_score
                best_candidate = None
                candidates = []
                for dh in (step_deg, -step_deg):
                    nh = int(clamp(hue + dh, win["hue"][0], win["hue"][1]))
                    if nh != hue:
                        candidates.append((nh, sat))
                for ds in (step_sat, -step_sat):
                    ns = round(clamp(sat + ds, win["sat"][0], win["sat"][1]), 3)
                    if ns != sat:
                        candidates.append((hue, ns))
                for cand in candidates:
                    table[role] = cand
                    score = min_delta_e(table)
                    if score > best_score + IMPROVE_EPS:
                        best_score = score
                        best_candidate = cand
                    table[role] = (hue, sat)
                if best_candidate is not None:
                    table[role] = best_candidate
                    changed = True
            if not changed:
                break
    return table


# --------------------------------------------------------------------------- #
# Preview HTML (checkpoint visual) — standalone, sin assets externos.
# --------------------------------------------------------------------------- #
def _old_palette(variant_file: str) -> dict:
    """Colores viejos desde HEAD (no del working tree, que ya estara regenerado)."""
    out = subprocess.run(
        ["git", "show", f"HEAD:palette/{variant_file}.json"],
        cwd=HERE, capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)["colors"]


def render_preview(table: dict) -> str:
    from color_science import hex_to_oklch

    variant_meta = {
        "dark": {"nombre": "Rooibos", "archivo": "rooibos", "bg": "#1a1711", "fg": "#ddd7c9"},
        "light": {"nombre": "Manzanilla", "archivo": "manzanilla", "bg": "#f8f3eb", "fg": "#3a3226"},
    }

    sections = []
    for variant, meta in variant_meta.items():
        cfg = VARIANTS[variant]
        neutrals = cfg["neutrals"]
        base_bg = oklch_to_hex(*neutrals["base"])
        mantle_bg = oklch_to_hex(*neutrals["mantle"])
        surface0_bg = oklch_to_hex(*neutrals["surface0"])
        new_hexes = variant_hexes(variant, table)
        old_colors = _old_palette(meta["archivo"])

        # swatches
        swatch_rows = []
        for role in ACCENTS:
            hx = new_hexes[role]
            L, C, H = hex_to_oklch(hx)
            swatch_rows.append(f"""
              <div class="swatch" style="background:{base_bg}">
                <div class="chip" style="background:{hx}"></div>
                <div class="info">
                  <strong>{role}</strong>
                  <code>{hx}</code>
                  <span>L={L:.3f} C={C:.3f} H={H:.1f}</span>
                </div>
              </div>""")

        # linea de codigo de ejemplo por acento
        code_rows = []
        for role in ACCENTS:
            hx = new_hexes[role]
            code_rows.append(
                f'<div class="codeline" style="background:{base_bg}">'
                f'<span style="color:{hx}">const {role} = "{hx}";</span>'
                f'</div>'
            )

        # comparativa viejo vs nuevo
        compare_rows = []
        for role in ACCENTS:
            old_hx = old_colors.get(role, "?")
            new_hx = new_hexes[role]
            compare_rows.append(f"""
              <tr>
                <td>{role}</td>
                <td><span class="dot" style="background:{old_hx}"></span> {old_hx}</td>
                <td><span class="dot" style="background:{new_hx}"></span> {new_hx}</td>
              </tr>""")

        # pares mas cercanos: nuevo (con viejo al lado)
        new_pairs = accent_de_pairs(new_hexes)[:8]
        pair_rows = []
        for de_new, r1, r2 in new_pairs:
            de_old = delta_e_oklab(old_colors.get(r1, "#000000"), old_colors.get(r2, "#000000"))
            pair_rows.append(f"""
              <tr>
                <td>{r1} — {r2}</td>
                <td>{de_new:.4f}</td>
                <td>{de_old:.4f}</td>
              </tr>""")

        sections.append(f"""
        <section>
          <h2>{meta['nombre']} ({variant})</h2>
          <h3>Acentos nuevos</h3>
          <div class="swatches">{''.join(swatch_rows)}</div>
          <h3>Linea de codigo de ejemplo (sobre base)</h3>
          <div class="codeblock" style="background:{base_bg}">{''.join(code_rows)}</div>
          <h3>Comparativa hex viejo vs nuevo</h3>
          <table>
            <tr><th>rol</th><th>viejo</th><th>nuevo</th></tr>
            {''.join(compare_rows)}
          </table>
          <h3>8 pares con menor &Delta;E nuevo (vs &Delta;E viejo)</h3>
          <table>
            <tr><th>par</th><th>&Delta;E nuevo</th><th>&Delta;E viejo</th></tr>
            {''.join(pair_rows)}
          </table>
          <p class="fondos">Fondos de referencia — base {base_bg} · mantle {mantle_bg} · surface0 {surface0_bg}</p>
        </section>""")

    min_de = min_delta_e(table)
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Preview acentos propios — Ocular</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", sans-serif; background:#1a1711; color:#ddd7c9; margin:0; padding:2rem; }}
  h1 {{ font-weight:600; }}
  h2 {{ margin-top:3rem; border-bottom:1px solid #444; padding-bottom:.5rem; }}
  h3 {{ margin-top:1.5rem; }}
  .swatches {{ display:flex; flex-wrap:wrap; gap:.75rem; }}
  .swatch {{ display:flex; align-items:center; gap:.5rem; padding:.6rem; border-radius:8px; min-width:220px; }}
  .chip {{ width:36px; height:36px; border-radius:6px; flex-shrink:0; border:1px solid rgba(255,255,255,.15); }}
  .info {{ display:flex; flex-direction:column; font-size:.82rem; }}
  .info code {{ opacity:.8; }}
  .codeblock {{ padding:.75rem; border-radius:8px; font-family: ui-monospace, monospace; }}
  .codeline {{ padding:.15rem 0; }}
  table {{ border-collapse:collapse; width:100%; max-width:640px; margin-top:.5rem; }}
  th, td {{ text-align:left; padding:.35rem .6rem; border-bottom:1px solid #333; font-size:.85rem; }}
  .dot {{ display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:.35rem; vertical-align:middle; border:1px solid rgba(255,255,255,.2); }}
  .fondos {{ font-size:.78rem; opacity:.7; margin-top:.75rem; }}
  .resumen {{ font-size:.9rem; opacity:.85; }}
</style>
</head>
<body>
  <h1>Preview de acentos propios — Ocular</h1>
  <p class="resumen">Optimizacion coordinate ascent determinista sobre las ventanas por rol.
  ΔE OKLab minimo logrado (union de ambas variantes): <strong>{min_de:.4f}</strong>
  (gate ≥ {MIN_ACCENT_DE}).</p>
  {''.join(sections)}
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Deriva y optimiza los matices propios de los 14 acentos de Ocular.")
    parser.add_argument("--preview", metavar="RUTA_HTML", help="Ademas del hues.json, escribe un preview HTML standalone en esta ruta (nunca dentro del repo).")
    args = parser.parse_args()

    table = optimize(initial_table())
    min_de = min_delta_e(table)

    data = {
        "comment": "Matices propios de los 14 acentos de Ocular, derivados por coordinate ascent "
                   "maximizando el minimo ΔE OKLab entre acentos. Catppuccin ya no es la fuente de "
                   "hues: solo aporta el esqueleto de nombres de rol. Congelado y versionado; "
                   "build.py solo LEE esta tabla (nunca corre este optimizador en CI).",
        "windows": WINDOWS,
        "table": {role: {"hue": table[role][0], "sat": table[role][1]} for role in ACCENTS},
        "meta": {"min_delta_e": round(min_de, 6), "generated_by": "derive_hues.py"},
    }
    out_path = os.path.join(HERE, "palette", "hues.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"palette/hues.json escrito. min ΔE OKLab logrado = {min_de:.4f} (gate >= {MIN_ACCENT_DE})")
    print()
    print(f"{'rol':<10}{'hue':>6}{'sat':>8}")
    for role in ACCENTS:
        hue, sat = table[role]
        print(f"{role:<10}{hue:>6}{sat:>8.3f}")

    if args.preview:
        html = render_preview(table)
        with open(args.preview, "w") as f:
            f.write(html)
        size = os.path.getsize(args.preview)
        print()
        print(f"Preview HTML escrito en {args.preview} ({size} bytes)")


if __name__ == "__main__":
    main()
