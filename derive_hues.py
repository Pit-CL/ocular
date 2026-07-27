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

from color_science import oklch_to_hex, hex_to_oklab, delta_e_oklab, delta_e_cvd, solve_L_for_lc, lc
from build import (
    ACCENTS, DARK_NEUTRALS, LIGHT_NEUTRALS,
    DARK_ACCENT_LC, DARK_ACCENT_CAP, LIGHT_ACCENT_LC, LIGHT_ACCENT_CAP,
    DARK_TEXT_TARGETS, LIGHT_TEXT_TARGETS,
    MIN_ACCENT_DE, MIN_ACCENT_DE_CVD, accent_de_pairs, _hues,
)
from audit import floor_for, SURFACES

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
# Perfil deutan — variante CVD-safe con luminancias deliberadamente desiguales
# (rompe a propósito el equal-weight de §6/SCIENCE.md: bajo deuteranopía el
# hue colapsa, así que la distinción pasa a depender del brillo).
#
# Variables por rol: (hue, sat, dlc). dlc es el offset de Lc APCA aplicado en
# ambos modos (dark target = DARK_ACCENT_LC+dlc, light target =
# LIGHT_ACCENT_LC+dlc) — mismo dlc en dark y light para que el rol mantenga
# su posición relativa de brillo en ambas variantes.
# --------------------------------------------------------------------------- #
WINDOWS_DEUTAN = {role: dict(win) for role, win in WINDOWS.items()}

SCHEDULE_DEUTAN = [(4, 0.05, 3.0), (2, 0.025, 1.5), (1, 0.01, 0.75),
                   (1, 0.01, 0.5), (1, 0.005, 0.25), (1, 0.002, 0.1)]

# Techo: el acento no puede acercarse a la luminancia del rol "text" (perdería
# la jerarquía visual código/prosa). Piso: no hay formula cerrada — lo impone
# la restriccion dura de floor_for() mas abajo; este numero solo acota el
# rango de busqueda del coordinate ascent.
DLC_CEILING = min(DARK_TEXT_TARGETS["text"][0] - 4 - DARK_ACCENT_LC,
                   LIGHT_TEXT_TARGETS["text"][0] - 4 - LIGHT_ACCENT_LC)
DLC_FLOOR = -25.0

VISIONS = ("normal", "deutan", "protan")

_SOLVE_CACHE_DEUTAN: dict[tuple[str, int, float, float], str] = {}


def resolve_hex_cvd(variant: str, hue: int, sat: float, dlc: float) -> str:
    """Como resolve_hex(), pero con Lc target variable por rol (accent_lc+dlc).
    Cache propio: a diferencia de _SOLVE_CACHE (perfil default, target fijo por
    variante), aca el target cambia por rol, asi que la key debe incluirlo —
    de lo contrario dos roles con distinto dlc pero mismo (hue, C) colisionan
    en la cache y devuelven el hex del primero que se calculo."""
    cfg = VARIANTS[variant]
    C = round(sat * cfg["cap"], 3)
    target_lc = cfg["target_lc"] + dlc
    key = (variant, hue, C, target_lc)
    hx = _SOLVE_CACHE_DEUTAN.get(key)
    if hx is None:
        _, hx, _ = solve_L_for_lc(target_lc, hue, C, cfg["base_hex"], lighter=cfg["lighter"])
        _SOLVE_CACHE_DEUTAN[key] = hx
    return hx


def variant_hexes_deutan(variant: str, table: dict) -> dict:
    return {role: resolve_hex_cvd(variant, *table[role]) for role in ACCENTS}


def min_delta_e_by_vision(table: dict) -> dict:
    """Minimo ΔE por vision (normal/deutan/protan), sobre la union de los 91
    pares de acentos de ambas variantes (dark/light)."""
    mins = {v: float("inf") for v in VISIONS}
    for variant in VARIANTS:
        hexes = variant_hexes_deutan(variant, table)
        labs = {role: hex_to_oklab(hx) for role, hx in hexes.items()}
        for r1, r2 in itertools.combinations(ACCENTS, 2):
            L1, a1, b1 = labs[r1]
            L2, a2, b2 = labs[r2]
            de = ((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2) ** 0.5
            if de < mins["normal"]:
                mins["normal"] = de
            for kind in ("deutan", "protan"):
                de_k = delta_e_cvd(hexes[r1], hexes[r2], kind)
                if de_k < mins[kind]:
                    mins[kind] = de_k
    return mins


def min_delta_e_deutan(table: dict) -> float:
    """Objetivo del optimizador: min sobre {normal, deutan, protan} x
    {dark, light} x 91 pares."""
    return min(min_delta_e_by_vision(table).values())


def candidate_valid(role: str, cand: tuple) -> bool:
    """Restriccion dura: el candidato debe respetar floor_for() (audit.py)
    sobre las 6 superficies en ambas variantes, y no perforar el techo de Lc."""
    hue, sat, dlc = cand
    if not (DLC_FLOOR <= dlc <= DLC_CEILING):
        return False
    for variant in VARIANTS:
        hx = resolve_hex_cvd(variant, hue, sat, dlc)
        neutrals = VARIANTS[variant]["neutrals"]
        for surf in SURFACES:
            floor = floor_for(role, surf)
            if floor is None:
                continue
            bg_hex = oklch_to_hex(*neutrals[surf])
            if lc(hx, bg_hex) < floor:
                return False
    return True


def initial_table_deutan() -> dict:
    table = {}
    for role in ACCENTS:
        win = WINDOWS_DEUTAN[role]
        hue = round((win["hue"][0] + win["hue"][1]) / 2)
        sat = round((win["sat"][0] + win["sat"][1]) / 2, 3)
        table[role] = (hue, sat, 0.0)  # dlc arranca en 0 (baseline equal-Lc)
    return table


def _run_phase(table: dict, step_deg: int, step_sat: float, step_dlc: float) -> dict:
    """Una fase del coordinate ascent (orden fijo de roles = ACCENTS) hasta punto
    fijo, tope MAX_ITERS_PER_PHASE. Factorizada de optimize_deutan() para poder
    reusarla como refinamiento acotado en la perturbacion dirigida post-convergencia."""
    for _ in range(MAX_ITERS_PER_PHASE):
        changed = False
        for role in ACCENTS:
            win = WINDOWS_DEUTAN[role]
            hue, sat, dlc = table[role]
            base_score = min_delta_e_deutan(table)
            best_score = base_score
            best_candidate = None
            candidates = []
            for dh in (step_deg, -step_deg):
                nh = int(clamp(hue + dh, win["hue"][0], win["hue"][1]))
                if nh != hue:
                    candidates.append((nh, sat, dlc))
            for ds in (step_sat, -step_sat):
                ns = round(clamp(sat + ds, win["sat"][0], win["sat"][1]), 3)
                if ns != sat:
                    candidates.append((hue, ns, dlc))
            for dd in (step_dlc, -step_dlc):
                nd = round(clamp(dlc + dd, DLC_FLOOR, DLC_CEILING), 3)
                if nd != dlc:
                    candidates.append((hue, sat, nd))
            for cand in candidates:
                if not candidate_valid(role, cand):
                    continue
                table[role] = cand
                score = min_delta_e_deutan(table)
                if score > best_score + IMPROVE_EPS:
                    best_score = score
                    best_candidate = cand
                table[role] = (hue, sat, dlc)
            if best_candidate is not None:
                table[role] = best_candidate
                changed = True
        if not changed:
            break
    return table


def optimize_deutan(table: dict) -> dict:
    """Coordinate ascent en 3 variables por rol (hue, sat, dlc), con
    candidate_valid() como filtro previo a puntuar."""
    for step_deg, step_sat, step_dlc in SCHEDULE_DEUTAN:
        table = _run_phase(table, step_deg, step_sat, step_dlc)
    return table


def _nearest_feasible_dlc(role: str, hue: int, sat: float, target_dlc: float) -> float:
    """Corrige target_dlc al valor factible (candidate_valid) mas cercano,
    buscando hacia afuera en pasos de 0.25. dlc=0 siempre es factible en el
    (hue, sat) por defecto (es el punto de partida de initial_table_deutan),
    asi que la busqueda termina como maximo en el rango completo."""
    target_dlc = clamp(target_dlc, DLC_FLOOR, DLC_CEILING)
    if candidate_valid(role, (hue, sat, target_dlc)):
        return target_dlc
    step, d = 0.25, 0.25
    span = DLC_CEILING - DLC_FLOOR
    while d <= span:
        for cand_dlc in (target_dlc + d, target_dlc - d):
            cand_dlc = round(clamp(cand_dlc, DLC_FLOOR, DLC_CEILING), 3)
            if candidate_valid(role, (hue, sat, cand_dlc)):
                return cand_dlc
        d += step
    return 0.0  # fallback: siempre factible en (hue, sat) por defecto


def _staggered_dlc_table(pattern: tuple) -> dict:
    """Init (ii)/(iii) del multi-start: dlc inicial ciclico de 3 niveles,
    roles ordenados por hue de la tabla congelada (palette/hues.json, el
    perfil default) — rompe a proposito la simetria dlc=0 que el greedy no
    resuelve por si solo cuando el par bloqueante es de familias vecinas."""
    table = initial_table_deutan()
    frozen_table = _hues("hues")["table"]
    ordered_roles = sorted(ACCENTS, key=lambda r: frozen_table[r]["hue"])
    staggered = {}
    for i, role in enumerate(ordered_roles):
        hue, sat, _ = table[role]
        target_dlc = pattern[i % len(pattern)]
        staggered[role] = (hue, sat, _nearest_feasible_dlc(role, hue, sat, target_dlc))
    return staggered


# Multi-start determinista: 3 inicializaciones FIJAS (sin random), en orden
# fijo — el greedy desde dlc=0 (baseline) no siempre rompe la simetria entre
# familias de hue vecinas (p.ej. mauve-sapphire); los patrones escalonados le
# dan un punto de partida con luminancias ya desiguales.
INIT_TABLES = {
    "baseline": lambda: initial_table_deutan(),
    "staggered_up_first": lambda: _staggered_dlc_table((6.0, 0.0, -2.0)),
    "staggered_down_first": lambda: _staggered_dlc_table((-2.0, 0.0, 6.0)),
}


def optimize_deutan_multistart() -> dict:
    """Corre optimize_deutan() desde cada init de INIT_TABLES (orden fijo) y
    se queda con el mejor score final."""
    best_table, best_score, best_name = None, -1.0, None
    for name, init_fn in INIT_TABLES.items():
        table = optimize_deutan(init_fn())
        score = min_delta_e_deutan(table)
        print(f"  init={name:22} min ΔE final = {score:.4f}")
        if score > best_score:
            best_score, best_table, best_name = score, table, name
    print(f"  mejor inicializacion: {best_name} (min ΔE = {best_score:.4f})")
    return best_table


def _find_worst_pair(table: dict) -> tuple:
    """(ΔE, vision, r1, r2) del par y la vision con el minimo global actual."""
    best = (float("inf"), None, None, None)
    for variant in VARIANTS:
        hexes = variant_hexes_deutan(variant, table)
        labs = {role: hex_to_oklab(hx) for role, hx in hexes.items()}
        for r1, r2 in itertools.combinations(ACCENTS, 2):
            L1, a1, b1 = labs[r1]
            L2, a2, b2 = labs[r2]
            de = ((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2) ** 0.5
            if de < best[0]:
                best = (de, "normal", r1, r2)
            for kind in ("deutan", "protan"):
                de_k = delta_e_cvd(hexes[r1], hexes[r2], kind)
                if de_k < best[0]:
                    best = (de_k, kind, r1, r2)
    return best


def perturb_worst_pair(table: dict, max_rounds: int = 8) -> dict:
    """Perturbacion dirigida post-convergencia: identifica el par/vision con
    el ΔE minimo global, mueve el dlc de cada rol del par en +-2/+-4 (orden
    fijo, solo candidatos factibles), refina con la ultima fase del schedule
    y acepta solo la mejor movida si mejora estrictamente. Repite hasta punto
    fijo, tope max_rounds."""
    last_step_deg, last_step_sat, last_step_dlc = SCHEDULE_DEUTAN[-1]
    for round_n in range(1, max_rounds + 1):
        current_score = min_delta_e_deutan(table)
        _, vision, r1, r2 = _find_worst_pair(table)
        best_trial, best_score = None, current_score
        for role in (r1, r2):
            hue, sat, dlc = table[role]
            for delta in (2.0, -2.0, 4.0, -4.0):
                nd = round(clamp(dlc + delta, DLC_FLOOR, DLC_CEILING), 3)
                if nd == dlc or not candidate_valid(role, (hue, sat, nd)):
                    continue
                trial = dict(table)
                trial[role] = (hue, sat, nd)
                trial = _run_phase(trial, last_step_deg, last_step_sat, last_step_dlc)
                score = min_delta_e_deutan(trial)
                if score > best_score + IMPROVE_EPS:
                    best_score, best_trial = score, trial
        if best_trial is None:
            print(f"  ronda {round_n}: sin mejora (bloqueaba {r1}-{r2}, vision {vision}) — fin")
            break
        table = best_trial
        print(f"  ronda {round_n}: mejora a {best_score:.4f} (bloqueaba {r1}-{r2}, vision {vision})")
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


def render_preview_deutan(table: dict) -> str:
    """Preview del perfil deutan: cada acento junto a su render simulado
    deutan/protan, para el checkpoint visual del usuario."""
    from color_science import hex_to_oklch, simulate_cvd

    variant_meta = {
        "dark": {"nombre": "Rooibos Deutan"},
        "light": {"nombre": "Manzanilla Deutan"},
    }

    sections = []
    for variant, meta in variant_meta.items():
        cfg = VARIANTS[variant]
        base_bg = cfg["base_hex"]
        hexes = variant_hexes_deutan(variant, table)

        swatch_rows = []
        for role in ACCENTS:
            hx = hexes[role]
            hx_deutan = simulate_cvd(hx, "deutan")
            hx_protan = simulate_cvd(hx, "protan")
            _, _, dlc = table[role]
            swatch_rows.append(f"""
              <div class="swatch" style="background:{base_bg}">
                <div class="chips">
                  <div class="chip" style="background:{hx}" title="normal {hx}"></div>
                  <div class="chip" style="background:{hx_deutan}" title="deutan {hx_deutan}"></div>
                  <div class="chip" style="background:{hx_protan}" title="protan {hx_protan}"></div>
                </div>
                <div class="info">
                  <strong>{role}</strong>
                  <code>{hx}</code>
                  <span>dlc {dlc:+.2f}</span>
                </div>
              </div>""")

        labs = {role: hex_to_oklab(hexes[role]) for role in ACCENTS}
        all_pairs = []
        for r1, r2 in itertools.combinations(ACCENTS, 2):
            L1, a1, b1 = labs[r1]
            L2, a2, b2 = labs[r2]
            de_n = ((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2) ** 0.5
            de_d = delta_e_cvd(hexes[r1], hexes[r2], "deutan")
            de_p = delta_e_cvd(hexes[r1], hexes[r2], "protan")
            all_pairs.append((min(de_n, de_d, de_p), r1, r2, de_n, de_d, de_p))
        all_pairs.sort(key=lambda p: p[0])

        pair_rows = []
        for _, r1, r2, de_n, de_d, de_p in all_pairs[:8]:
            pair_rows.append(f"""
              <tr>
                <td>{r1} — {r2}</td>
                <td>{de_n:.4f}</td>
                <td>{de_d:.4f}</td>
                <td>{de_p:.4f}</td>
              </tr>""")

        sections.append(f"""
        <section>
          <h2>{meta['nombre']} ({variant})</h2>
          <h3>Acentos: normal / simulado deutan / simulado protan</h3>
          <div class="swatches">{''.join(swatch_rows)}</div>
          <h3>8 pares con menor &Delta;E (normal / deutan / protan)</h3>
          <table>
            <tr><th>par</th><th>&Delta;E normal</th><th>&Delta;E deutan</th><th>&Delta;E protan</th></tr>
            {''.join(pair_rows)}
          </table>
        </section>""")

    vision_mins = min_delta_e_by_vision(table)
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Preview perfil deutan — Ocular</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", sans-serif; background:#1a1711; color:#ddd7c9; margin:0; padding:2rem; }}
  h1 {{ font-weight:600; }}
  h2 {{ margin-top:3rem; border-bottom:1px solid #444; padding-bottom:.5rem; }}
  h3 {{ margin-top:1.5rem; }}
  .swatches {{ display:flex; flex-wrap:wrap; gap:.75rem; }}
  .swatch {{ display:flex; align-items:center; gap:.5rem; padding:.6rem; border-radius:8px; min-width:220px; }}
  .chips {{ display:flex; gap:2px; flex-shrink:0; }}
  .chip {{ width:24px; height:36px; border-radius:4px; border:1px solid rgba(255,255,255,.15); }}
  .info {{ display:flex; flex-direction:column; font-size:.82rem; }}
  .info code {{ opacity:.8; }}
  table {{ border-collapse:collapse; width:100%; max-width:640px; margin-top:.5rem; }}
  th, td {{ text-align:left; padding:.35rem .6rem; border-bottom:1px solid #333; font-size:.85rem; }}
  .resumen {{ font-size:.9rem; opacity:.85; }}
</style>
</head>
<body>
  <h1>Preview del perfil deutan — Ocular</h1>
  <p class="resumen">Cada swatch: chip izquierdo = color normal, centro = simulado
  deuteranopia, derecho = simulado protanopia. min ΔE por vision (union de
  ambas variantes) — normal: <strong>{vision_mins['normal']:.4f}</strong>,
  deutan: <strong>{vision_mins['deutan']:.4f}</strong>, protan:
  <strong>{vision_mins['protan']:.4f}</strong> (gate CVD ≥ {MIN_ACCENT_DE_CVD}).</p>
  {''.join(sections)}
</body>
</html>
"""
    return html


def run_deutan_profile(preview_path: str | None) -> None:
    print("Multi-start determinista (3 inicializaciones fijas):")
    table = optimize_deutan_multistart()
    print()
    print("Perturbacion dirigida post-convergencia (tope 8 rondas):")
    table = perturb_worst_pair(table)
    print()

    vision_mins = min_delta_e_by_vision(table)
    min_de = min(vision_mins.values())

    data = {
        "comment": "Perfil CVD-safe (deuteranopia + protanopia) de los 14 acentos: hue, sat y "
                   "dlc (offset de Lc APCA aplicado en dark 71+dlc / light 74+dlc) por rol, "
                   "derivados por multi-start determinista (3 inicializaciones fijas) + "
                   "coordinate ascent + perturbacion dirigida post-convergencia, maximizando el "
                   "ΔE OKLab minimo sobre {normal, deutan, protan} x {dark, light} x 91 pares, "
                   "con piso duro de audit.floor_for sobre 6 superficies en ambas variantes. "
                   "Rompe a proposito el equal-weight de hues.json (SCIENCE.md §6): bajo "
                   "deuteranopia el hue colapsa, asi que la distincion pasa a depender del "
                   "brillo. Congelado y versionado; build.py solo LEE esta tabla.",
        "windows": WINDOWS_DEUTAN,
        "table": {role: {"hue": table[role][0], "sat": table[role][1], "dlc": table[role][2]}
                  for role in ACCENTS},
        "meta": {
            "min_delta_e_normal": round(vision_mins["normal"], 6),
            "min_delta_e_deutan": round(vision_mins["deutan"], 6),
            "min_delta_e_protan": round(vision_mins["protan"], 6),
            "min_delta_e": round(min_de, 6),
            "generated_by": "derive_hues.py --profile deutan",
        },
    }
    out_path = os.path.join(HERE, "palette", "hues-deutan.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"palette/hues-deutan.json escrito.")
    print(f"  min ΔE normal = {vision_mins['normal']:.4f}")
    print(f"  min ΔE deutan = {vision_mins['deutan']:.4f} (gate CVD >= {MIN_ACCENT_DE_CVD})")
    print(f"  min ΔE protan = {vision_mins['protan']:.4f} (gate CVD >= {MIN_ACCENT_DE_CVD})")
    print()
    print(f"{'rol':<10}{'hue':>6}{'sat':>8}{'dlc':>8}")
    for role in ACCENTS:
        hue, sat, dlc = table[role]
        print(f"{role:<10}{hue:>6}{sat:>8.3f}{dlc:>8.2f}")

    if preview_path:
        html = render_preview_deutan(table)
        with open(preview_path, "w") as f:
            f.write(html)
        size = os.path.getsize(preview_path)
        print()
        print(f"Preview HTML escrito en {preview_path} ({size} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Deriva y optimiza los matices propios de los 14 acentos de Ocular.")
    parser.add_argument("--preview", metavar="RUTA_HTML", help="Ademas del hues.json, escribe un preview HTML standalone en esta ruta (nunca dentro del repo).")
    parser.add_argument("--profile", choices=["default", "deutan"], default="default",
                         help="'default' escribe palette/hues.json (equal-Lc, sin cambios). "
                              "'deutan' escribe palette/hues-deutan.json (perfil CVD-safe, Lc desigual por rol).")
    args = parser.parse_args()

    if args.profile == "deutan":
        run_deutan_profile(args.preview)
        return

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
