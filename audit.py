#!/usr/bin/env python3
"""Auditoría cruzada de contraste: cada rol de texto sobre cada superficie.

Complementa la validación de build.py (que valida contra `base`): aquí se audita
la matriz completa texto x superficie con pisos APCA por contexto de uso, para
garantizar que nada quede ilegible en popups, selecciones o paneles.
Exit != 0 si algún par exigido queda bajo su piso.
"""
import itertools
import json
import os
import sys

from color_science import lc, delta_e_oklab, delta_e_cvd

HERE = os.path.dirname(os.path.abspath(__file__))
SURFACES = ["base", "mantle", "crust", "surface0", "surface1", "surface2"]
ACCENTS = ["rosewater", "flamingo", "pink", "mauve", "red", "maroon", "peach",
           "yellow", "green", "teal", "sky", "sapphire", "blue", "lavender"]

# Gate de separacion de acentos (duplicado con comentario cruzado en build.py,
# que es la fuente de verdad; aca se re-verifica leyendo los JSON emitidos como
# defensa contra edicion a mano de palette/{rooibos,manzanilla}.json).
MIN_ACCENT_DE = 0.025

# Gate de separacion simulada (deuteranopia/protanopia), solo para las
# variantes *-deutan. Duplicado con comentario cruzado en build.py, que es la
# fuente de verdad.
MIN_ACCENT_DE_CVD = 0.02


def floor_for(role: str, surf: str):
    """Piso APCA exigido por contexto de uso; None = solo informativo."""
    if role == "text":                     # cuerpo: legible hasta en seleccion
        return 60 if surf != "surface2" else None
    if role == "subtext1":                 # texto secundario en paneles
        return 55 if surf in ("base", "mantle", "crust", "surface0") else None
    if role == "subtext0":
        return 50 if surf in ("base", "mantle", "crust") else None
    if role == "overlay2":                 # line numbers / placeholder
        return 45 if surf == "base" else None
    if role in ACCENTS:                    # sintaxis / estados
        if surf in ("base", "mantle", "crust"):
            return 60
        if surf in ("surface0", "surface1"):   # linea resaltada / seleccion
            return 50
    return None


def audit(name: str) -> int:
    pal = json.load(open(os.path.join(HERE, "palette", f"{name}.json")))["colors"]
    roles = ["text", "subtext1", "subtext0", "overlay2"] + ACCENTS
    fails = 0
    print(f"\n== {name} ==")
    print(f"{'rol':<10}" + "".join(f"{s:>10}" for s in SURFACES))
    for role in roles:
        row = f"{role:<10}"
        for surf in SURFACES:
            v = lc(pal[role], pal[surf])
            fl = floor_for(role, surf)
            mark = ""
            if fl is not None and v < fl:
                mark = "!"
                fails += 1
            row += f"{v:>8.1f}{mark:<2}"
        print(row)
    return fails


def audit_accent_de(name: str) -> int:
    """Re-verifica el gate de separacion entre acentos leyendo el JSON emitido."""
    pal = json.load(open(os.path.join(HERE, "palette", f"{name}.json")))["colors"]
    pairs = []
    for r1, r2 in itertools.combinations(ACCENTS, 2):
        de = delta_e_oklab(pal[r1], pal[r2])
        pairs.append((de, r1, r2))
    pairs.sort(key=lambda p: p[0])

    print(f"\n== {name}: separacion de acentos (ΔE OKLab) ==")
    print(f"5 pares mas cercanos (gate >= {MIN_ACCENT_DE}):")
    for de, r1, r2 in pairs[:5]:
        mark = " !" if de < MIN_ACCENT_DE else ""
        print(f"  {r1:<10} {r2:<10} {de:.4f}{mark}")

    min_de = pairs[0][0]
    if min_de < MIN_ACCENT_DE:
        r1, r2 = pairs[0][1], pairs[0][2]
        print(f"FALLA: min ΔE {min_de:.4f} < {MIN_ACCENT_DE} (par {r1}-{r2})")
        return 1
    return 0


def audit_cvd_de(name: str) -> int:
    """Re-verifica el gate CVD (deutan y protan) leyendo el JSON emitido —
    mismo patron defensa-contra-edicion-a-mano que audit_accent_de, solo
    aplica a las variantes *-deutan."""
    pal = json.load(open(os.path.join(HERE, "palette", f"{name}.json")))["colors"]
    fails = 0
    print(f"\n== {name}: separacion simulada (ΔE OKLab, gate >= {MIN_ACCENT_DE_CVD}) ==")
    for kind, label in (("deutan", "deuteranopia"), ("protan", "protanopia")):
        pairs = []
        for r1, r2 in itertools.combinations(ACCENTS, 2):
            de = delta_e_cvd(pal[r1], pal[r2], kind)
            pairs.append((de, r1, r2))
        pairs.sort(key=lambda p: p[0])
        min_de, r1, r2 = pairs[0]
        mark = " !" if min_de < MIN_ACCENT_DE_CVD else ""
        print(f"  {label:<14} min ΔE = {min_de:.4f} (par {r1}-{r2}){mark}")
        if min_de < MIN_ACCENT_DE_CVD:
            fails += 1
    return fails


if __name__ == "__main__":
    PALETTES = ("rooibos", "manzanilla", "rooibos-deutan", "manzanilla-deutan")
    CVD_PALETTES = ("rooibos-deutan", "manzanilla-deutan")

    total = sum(audit(n) for n in PALETTES)
    total += sum(audit_accent_de(n) for n in PALETTES)
    total += sum(audit_cvd_de(n) for n in CVD_PALETTES)
    if total:
        print(f"\nFALLA: {total} problema(s) encontrado(s) (ver detalle arriba)")
        sys.exit(1)
    print("\nAUDITORIA CRUZADA OK: todos los pares exigidos sobre su piso, separacion de "
          "acentos y separacion simulada dentro de sus gates")
