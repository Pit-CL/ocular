#!/usr/bin/env python3
"""
build_ports.py — FASE 1 del rollout de Ocular: genera los ports por app + el
switcher, a partir de palette/rooibos.json (dark) y palette/manzanilla.json
(light), SIN tocar ningún config vivo. Todo se escribe bajo ports/out/.

Dos estrategias según el artefacto:
  1. SUSTITUCIÓN de hex sobre las plantillas oficiales de Catppuccin
     vendorizadas en ports/reference/ (bat, yazi, btop, oh-my-posh): se
     recorre la plantilla, cada #hex oficial Mocha/Latte se reconoce por su
     ROL (via palette/catppuccin-oficial.json) y se reemplaza por el hex
     Ocular de ese mismo rol. Preserva estructura, comentarios y campos no
     visitados 1:1. Las plantillas se vendorizaron el 2026-07-26 (PR #15,
     issue #7) para que el build sea autocontenido: antes se leían de los
     ports instalados localmente en la máquina del autor.
  2. GENERACIÓN directa por rol (kitty, ghostty, tmux, statusline, lazygit,
     herdr, nvim, vscode, gh-dash): no hay forma segura de sustituir (kitty/
     ghostty usan el bloque `ansi` dedicado, no roles puros; tmux/statusline
     no tienen port oficial de referencia con hex fijos). gh-dash pasó de
     sustitución a generación directa el 2026-07-26 (fix de rollout): el
     legado Catppuccin heredaba roles poco apropiados para su propio schema
     (p.ej. text.secondary/border.primary en lavender, un acento vívido, no
     un tono de texto secundario) — ver mapeo semántico por campo en
     gh_dash_theme(). lazygit y herdr pasaron de sustitución a generación
     directa el mismo 2026-07-26 (fix issue #7): usaban como fuente los
     configs VIVOS de la máquina (~/.config/lazygit/config.yml,
     ~/.config/herdr/config.toml), que la migración a Ocular ya reescribió
     con hex Ocular — el motor de sustitución dejó de reconocerlos como Mocha
     y la regeneración fallaba. El mapeo campo->rol se derivó comparando los
     hex de ports/out/{lazygit,herdr}/*.{yml,toml} ya versionados contra
     palette/{rooibos,manzanilla}.json — ver lazygit_theme() y herdr_theme().

Mapeo sintáctico común (para los artefactos de generación directa; los de
sustitución simplemente heredan el mapeo que ya trae el port oficial):
    keyword/string/function/number/type/comment/variable/operator/
    punctuation/parameter/property/decorator/builtin/typeParameter/
    interpolación/data-key (JSON·YAML·TOML·INI·.env), etc. -> ver la tabla
    ÚNICA `SYNTAX_MAP` (más abajo, justo antes de nvim_lua()/vscode_theme()):
    de ahí derivan tokenColors + semanticTokenColors de vscode_theme() y el
    bloque custom_highlights de nvim_lua() — un solo lugar para recalibrar
    un color de sintaxis en todo el fleet. Lo que sigue es el mapeo de
    campos NO sintácticos (estado de git, chrome de selección) que cada
    generador resuelve por su cuenta, fuera de SYNTAX_MAP:
    error                    -> red
    warning                  -> yellow
    added                    -> green
    modified                 -> yellow
    deleted                  -> red
    selección                -> surface1
    bordes activos           -> lavender (o el accent que use el port de
                                referencia de cada app puntual)

Uso: python3 ports/build_ports.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
import uuid
import xml.dom.minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORTS = ROOT / "ports"
OUT = PORTS / "out"

sys.path.insert(0, str(ROOT))
from color_science import lc as apca_lc  # noqa: E402 (requiere ROOT en sys.path)
from color_science import hex_to_oklab, oklch_to_hex  # noqa: E402 (mezcla OKLab de delta_theme)

# --------------------------------------------------------------------------
# Paletas Ocular + oficiales Catppuccin (para reconocer hex por rol)
# --------------------------------------------------------------------------
ROOIBOS = json.loads((ROOT / "palette" / "rooibos.json").read_text())
MANZANILLA = json.loads((ROOT / "palette" / "manzanilla.json").read_text())
ROOIBOS_DEUTAN = json.loads((ROOT / "palette" / "rooibos-deutan.json").read_text())
MANZANILLA_DEUTAN = json.loads((ROOT / "palette" / "manzanilla-deutan.json").read_text())
OFICIAL = json.loads((ROOT / "palette" / "catppuccin-oficial.json").read_text())

MODES = {"rooibos": ROOIBOS, "manzanilla": MANZANILLA}


def h(x: str) -> str:
    """hex sin '#', minúscula."""
    return x.lstrip("#").lower()


def hex2role(oficial_mode: str) -> dict[str, str]:
    return {h(v): k for k, v in OFICIAL[oficial_mode].items()}


HEX2ROLE_MOCHA = hex2role("mocha")
HEX2ROLE_LATTE = hex2role("latte")

# Excepciones documentadas: hex que aparecen en el port oficial pero NO son
# un rol puro Catppuccin (colores derivados a mano por el autor del port).
EXC_BAT_MOCHA = {"3e5767": "sapphire"}   # findHighlight de bat, tono derivado
EXC_BAT_LATTE = {"a9daf0": "sapphire"}   # equivalente claro de findHighlight
EXC_OMP = {"acb0be": "subtext0"}         # "os" de oh-my-posh, aproximación a subtext0/overlay muted

# Literales estructurales que el port de referencia usa sin atarlos a un rol
# (blanco puro / negro puro) — se dejan intactos y quedan permitidos en la
# auditoría de hex. "42a0fa" es el color fijo de PR abierto que gh-dash
# hardcodea (no sale de ningún theme Catppuccin, ver statusline-command.sh
# líneas 274-276) — el fragmento Ocular solo lo MENCIONA en un comentario.
GLOBAL_KEEP = {"ffffff", "000000", "42a0fa"}

# Los sets ALLOWED_* (hex permitidos por paleta) ya NO son globales: se
# construyen por perfil dentro de emit_profile(), a partir de dark_pal/
# light_pal — evita duplicar la fórmula para cada perfil nuevo (ver PR de
# refactor "build_ports emite por perfil").
OFICIAL_ALL_HEX = {h(v) for d in OFICIAL.values() for v in d.values()}

BARE_HEX_RE = re.compile(r"#([0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)")
QUOTED_HEX_RE = re.compile(r"([\"'])#([0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)\1")

# --------------------------------------------------------------------------
# Guarda de pares APCA EMITIDOS (audit 2026-07-26): tabla ESTÁTICA de los
# pares fg/bg que los generadores de este archivo de verdad producen — KISS,
# no un parser genérico de artefactos. Nace de encontrar acentos/neutros
# oscuros usados como fondo con Lc≈0 (yazi indicator/progress_error, lazygit
# markedBaseCommit, herdr surface_dim). Cada vez que se agregue un rol nuevo
# usado como bg en alguno de estos generadores, se agrega su par aquí.
# Piso por clase (color_science.lc, ver ese módulo para la fórmula APCA):
#   cuerpo (60)     -> texto largo/leído normalmente
#   chrome (55)     -> bordes, tabs, marcas de selección puntuales
#   decorativo (45) -> marks/highlights que no se leen como texto corrido
PAIR_FLOORS = {"cuerpo": 60, "chrome": 55, "decorativo": 45}

EMITTED_PAIRS = [
    # (app, campo, clase, rol_fg, rol_bg)
    ("yazi", "indicator.parent/preview", "cuerpo", "text", "surface1"),
    ("yazi", "indicator.current", "chrome", "base", "peach"),
    ("yazi", "status.progress_error", "chrome", "base", "red"),
    ("yazi", "status.count_copied", "chrome", "base", "green"),
    ("yazi", "status.count_cut", "chrome", "base", "red"),
    ("yazi", "status.count_selected", "chrome", "base", "mauve"),
    ("lazygit", "markedBaseCommit(fg/bg)", "chrome", "blue", "surface1"),
    ("lazygit", "cherryPickedCommit(fg/bg)", "chrome", "mauve", "surface1"),
    ("lazygit", "selectedLineBgColor (fg=defaultFgColor)", "cuerpo", "text", "surface0"),
    ("lazygit", "inactiveViewSelectedLineBgColor (fg=defaultFgColor)", "cuerpo", "text", "surface1"),
    ("herdr", "surface_dim (fg=text)", "cuerpo", "text", "surface1"),
    ("kitty", "selection_foreground/background", "chrome", "base", "rosewater"),
    ("kitty", "cursor/cursor_text_color", "chrome", "base", "rosewater"),
    ("kitty", "active_tab_foreground/background", "chrome", "crust", "mauve"),
    ("kitty", "inactive_tab_foreground/background", "chrome", "text", "mantle"),
    ("kitty", "mark1_foreground/background", "decorativo", "base", "lavender"),
    ("kitty", "mark2_foreground/background", "decorativo", "base", "mauve"),
    ("kitty", "mark3_foreground/background", "decorativo", "base", "sapphire"),
    ("tmux", "status-style", "cuerpo", "text", "mantle"),
    ("tmux", "window-status-current-style/mode-style", "chrome", "crust", "mauve"),
    ("ghostty", "cursor-color/cursor-text", "chrome", "crust", "rosewater"),
    ("ghostty", "selection-background/foreground", "cuerpo", "text", "surface1"),
]


def check_emitted_pairs():
    """Recorre EMITTED_PAIRS con la paleta real de cada modo y registra un
    check APCA (color_science.lc) por par — exit≠0 si alguno baja del piso
    de su clase. Vigila la clase entera de "acento/neutro-oscuro como bg"
    para siempre, no solo los casos puntuales de este audit."""
    for mode_name, P in (("rooibos", ROOIBOS), ("manzanilla", MANZANILLA)):
        for app, field, clase, fg_role, bg_role in EMITTED_PAIRS:
            fg_hex, bg_hex = P["colors"][fg_role], P["colors"][bg_role]
            val = apca_lc(fg_hex, bg_hex)
            floor = PAIR_FLOORS[clase]
            ok = val >= floor
            label = ROOT / "ports" / f"pares-apca:{app}:{mode_name}:{field}"
            record(
                "apca-pares", label, ok,
                f"Lc={val:.2f} (piso {clase}={floor}) fg={fg_role} bg={bg_role}",
            )


# --------------------------------------------------------------------------
# Motor de sustitución hex -> rol -> hex Ocular
# --------------------------------------------------------------------------
def substitute_hexes(text, hex2role, target_colors, exceptions=None, keep=None, quoted=False):
    exceptions = exceptions or {}
    keep = keep or set()
    unresolved = []

    def resolve(core):
        hex6 = core[:6].lower()
        alpha = core[6:]
        if hex6 in keep:
            return None  # dejar intacto
        role = hex2role.get(hex6) or exceptions.get(hex6)
        if role is None:
            unresolved.append("#" + core)
            return None
        new_hex = target_colors[role].lstrip("#")
        if core[:6].isupper():
            new_hex = new_hex.upper()
        return new_hex + alpha

    if quoted:
        def repl(m):
            q, core = m.group(1), m.group(2)
            new = resolve(core)
            return m.group(0) if new is None else f"{q}#{new}{q}"
        pattern = QUOTED_HEX_RE
    else:
        def repl(m):
            core = m.group(1)
            new = resolve(core)
            return m.group(0) if new is None else "#" + new
        pattern = BARE_HEX_RE

    new_text = pattern.sub(repl, text)
    if unresolved:
        raise ValueError(f"hex sin rol conocido: {sorted(set(unresolved))}")
    return new_text


def find_hexes(text, quoted=False):
    pattern = QUOTED_HEX_RE if quoted else BARE_HEX_RE
    group = 2 if quoted else 1
    return {m.group(group)[:6].lower() for m in pattern.finditer(text)}


# --------------------------------------------------------------------------
# Reporte / validación
# --------------------------------------------------------------------------
REPORT = []


def record(name, path, ok, detail=""):
    REPORT.append((name, str(path.relative_to(ROOT)), ok, detail))


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def audit_hex_file(name, path, allowed, quoted=False):
    text = path.read_text()
    found = find_hexes(text, quoted=quoted)
    unknown = found - allowed - GLOBAL_KEEP
    residual = (found & OFICIAL_ALL_HEX) - allowed - GLOBAL_KEEP
    ok = not unknown
    detail = ""
    if unknown:
        detail = f"hex fuera de paleta: {sorted(unknown)}"
    elif residual:
        detail = f"hex oficial residual: {sorted(residual)}"
    record("hex-audit", path, ok, detail or f"{len(found)} hex, todos en paleta")
    return ok


def validate_xml(path):
    try:
        xml.dom.minidom.parse(str(path))
        record("xml", path, True)
    except Exception as e:
        record("xml", path, False, str(e))


def validate_json(path):
    try:
        json.loads(path.read_text())
        record("json", path, True)
    except Exception as e:
        record("json", path, False, str(e))


def validate_toml(path):
    try:
        tomllib.loads(path.read_text())
        record("toml", path, True)
    except Exception as e:
        record("toml", path, False, str(e))


def validate_bash(path):
    r = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    record("bash -n", path, r.returncode == 0, r.stderr.strip())


def rgb_to_hex6(rgb):
    return "".join(f"{v:02x}" for v in rgb)


def validate_chrome_rgb(path, allowed):
    data = json.loads(path.read_text())
    colors = data["theme"]["colors"]
    bad = [(k, v, rgb_to_hex6(v)) for k, v in colors.items() if rgb_to_hex6(v) not in allowed]
    ok = not bad
    record("chrome-rgb", path, ok, "" if ok else f"RGB fuera de paleta: {bad}")
    return ok


ANSI_RGB_RE = re.compile(r"38;2;(\d{1,3});(\d{1,3});(\d{1,3})m")


def audit_ansi_rgb_file(path, allowed):
    """Como audit_hex_file, pero para fragmentos que NO llevan #hex literal
    sino secuencias ANSI truecolor `\\e[38;2;R;G;Bm` (statusline, ccmax)."""
    text = path.read_text()
    found = {f"{int(r):02x}{int(g):02x}{int(b):02x}" for r, g, b in ANSI_RGB_RE.findall(text)}
    unknown = found - allowed
    ok = not unknown
    detail = f"RGB fuera de paleta: {sorted(unknown)}" if unknown else f"{len(found)} RGB, todos en paleta"
    record("rgb-audit", path, ok, detail)
    return ok


# --------------------------------------------------------------------------
# 1) KITTY — generación directa (colors por rol, terminal por bloque ansi)
# --------------------------------------------------------------------------
def kitty_conf(label, P):
    c, ansi = P["colors"], P["ansi"]
    return "\n".join([
        "# vim:ft=kitty",
        "",
        f"## name:     Ocular Kitty {label}",
        "## author:   Rafael Farias (Ocular)",
        "## license:  MIT",
        "## blurb:    Port Ocular — misma estructura de campos que catppuccin/kitty.",
        "",
        "",
        "",
        "# The basic colors",
        f"foreground              {c['text']}",
        f"background              {c['base']}",
        f"selection_foreground    {c['base']}",
        f"selection_background    {c['rosewater']}",
        "",
        "# Cursor colors",
        f"cursor                  {c['rosewater']}",
        f"cursor_text_color       {c['base']}",
        "",
        "# Scrollbar colors",
        f"scrollbar_handle_color  {c['overlay2']}",
        f"scrollbar_track_color   {c['surface1']}",
        "",
        "# URL color when hovering with mouse",
        f"url_color               {c['rosewater']}",
        "",
        "# Kitty window border colors",
        f"active_border_color     {c['lavender']}",
        f"inactive_border_color   {c['overlay0']}",
        f"bell_border_color       {c['yellow']}",
        "",
        "# OS Window titlebar colors",
        "wayland_titlebar_color system",
        "macos_titlebar_color background",
        "",
        "# Tab bar colors",
        f"active_tab_foreground   {c['crust']}",
        f"active_tab_background   {c['mauve']}",
        f"inactive_tab_foreground {c['text']}",
        f"inactive_tab_background {c['mantle']}",
        f"tab_bar_background      {c['crust']}",
        "",
        "# Colors for marks (marked text in the terminal)",
        f"mark1_foreground {c['base']}",
        f"mark1_background {c['lavender']}",
        f"mark2_foreground {c['base']}",
        f"mark2_background {c['mauve']}",
        f"mark3_foreground {c['base']}",
        f"mark3_background {c['sapphire']}",
        "",
        "# The 16 terminal colors",
        "",
        "# black",
        f"color0 {ansi['normal']['black']}",
        f"color8 {ansi['bright']['black']}",
        "",
        "# red",
        f"color1 {ansi['normal']['red']}",
        f"color9 {ansi['bright']['red']}",
        "",
        "# green",
        f"color2  {ansi['normal']['green']}",
        f"color10 {ansi['bright']['green']}",
        "",
        "# yellow",
        f"color3  {ansi['normal']['yellow']}",
        f"color11 {ansi['bright']['yellow']}",
        "",
        "# blue",
        f"color4  {ansi['normal']['blue']}",
        f"color12 {ansi['bright']['blue']}",
        "",
        "# magenta",
        f"color5  {ansi['normal']['magenta']}",
        f"color13 {ansi['bright']['magenta']}",
        "",
        "# cyan",
        f"color6  {ansi['normal']['cyan']}",
        f"color14 {ansi['bright']['cyan']}",
        "",
        "# white",
        f"color7  {ansi['normal']['white']}",
        f"color15 {ansi['bright']['white']}",
        "",
    ])


# --------------------------------------------------------------------------
# 2) GHOSTTY — generación directa
# --------------------------------------------------------------------------
def ghostty_theme(label, P):
    c, ansi = P["colors"], P["ansi"]

    def hh(x):
        return x.lstrip("#")

    return "\n".join([
        f"# Ocular {label} — port Ghostty (estructura de catppuccin-mocha oficial)",
        "",
        f"palette = 0={hh(ansi['normal']['black'])}",
        f"palette = 1={hh(ansi['normal']['red'])}",
        f"palette = 2={hh(ansi['normal']['green'])}",
        f"palette = 3={hh(ansi['normal']['yellow'])}",
        f"palette = 4={hh(ansi['normal']['blue'])}",
        f"palette = 5={hh(ansi['normal']['magenta'])}",
        f"palette = 6={hh(ansi['normal']['cyan'])}",
        f"palette = 7={hh(ansi['normal']['white'])}",
        f"palette = 8={hh(ansi['bright']['black'])}",
        f"palette = 9={hh(ansi['bright']['red'])}",
        f"palette = 10={hh(ansi['bright']['green'])}",
        f"palette = 11={hh(ansi['bright']['yellow'])}",
        f"palette = 12={hh(ansi['bright']['blue'])}",
        f"palette = 13={hh(ansi['bright']['magenta'])}",
        f"palette = 14={hh(ansi['bright']['cyan'])}",
        f"palette = 15={hh(ansi['bright']['white'])}",
        f"background = {hh(c['base'])}",
        f"foreground = {hh(c['text'])}",
        f"cursor-color = {hh(c['rosewater'])}",
        f"cursor-text = {hh(c['crust'])}",
        f"selection-background = {hh(c['surface1'])}",
        f"selection-foreground = {hh(c['text'])}",
        f"split-divider-color = {hh(c['surface0'])}",
        "",
    ])


# --------------------------------------------------------------------------
# 3) BAT — sustitución sobre el tmTheme oficial (Mocha para rooibos, Latte
#    para manzanilla, ambos instalados localmente)
# --------------------------------------------------------------------------
def bat_tmtheme(mocha_or_latte_text, hex2role, target_colors, exceptions,
                 old_name, new_name, old_class, new_class):
    text = substitute_hexes(mocha_or_latte_text, hex2role, target_colors,
                             exceptions=exceptions, quoted=False)
    text = text.replace(old_name, new_name).replace(old_class, new_class)
    new_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ocular:{new_name}"))
    text = re.sub(
        r"(<key>uuid</key>\s*<string>)[^<]+(</string>)",
        rf"\g<1>{new_uuid}\g<2>",
        text,
    )
    return text


# --------------------------------------------------------------------------
# 3b) LAZYGIT — generación directa por rol (fix issue #7, 2026-07-26): el
#     config vivo (~/.config/lazygit/config.yml) ya migró a hex Ocular, así
#     que dejó de servir como fuente de sustitución. Mapeo campo->rol
#     derivado comparando ports/out/lazygit/*.yml ya versionados contra
#     palette/{rooibos,manzanilla}.json (cada hex mapea a un rol único):
#       activeBorderColor / cherryPickedCommitFgColor -> mauve
#       inactiveBorderColor                            -> subtext0
#       searchingActiveBorderColor                      -> yellow
#       optionsTextColor / markedBaseCommitFgColor      -> blue
#       selectedLineBgColor                             -> surface0
#       inactiveViewSelectedLineBgColor                 -> surface1 (fix APCA
#         2026-07-26: overlay0 daba Lc=38-42 con el texto por encima, mismo
#         patrón que cherryPickedCommitBgColor)
#       cherryPickedCommitBgColor                       -> surface1
#       markedBaseCommitBgColor                         -> surface1 (fix APCA
#         2026-07-26: blue sobre yellow daba Lc=0; bg=surface1 es el mismo
#         patrón que cherryPickedCommitBgColor, fg queda blue)
#       unstagedChangesColor                            -> red
#       defaultFgColor                                  -> text
# --------------------------------------------------------------------------
def lazygit_theme(label, P):
    c = P["colors"]
    return "\n".join([
        f"# Ocular {label} — fragmento gui.theme para ~/.config/lazygit/config.yml",
        "gui:",
        "  theme:",
        "    activeBorderColor:",
        f"      - '{c['mauve']}'",
        "      - bold",
        "    inactiveBorderColor:",
        f"      - '{c['subtext0']}'",
        "    searchingActiveBorderColor:",
        f"      - '{c['yellow']}'",
        "    optionsTextColor:",
        f"      - '{c['blue']}'",
        "    selectedLineBgColor:",
        f"      - '{c['surface0']}'",
        "    inactiveViewSelectedLineBgColor:",
        f"      - '{c['surface1']}'",
        "    cherryPickedCommitFgColor:",
        f"      - '{c['mauve']}'",
        "    cherryPickedCommitBgColor:",
        f"      - '{c['surface1']}'",
        "    markedBaseCommitFgColor:",
        f"      - '{c['blue']}'",
        "    markedBaseCommitBgColor:",
        f"      - '{c['surface1']}'",
        "    unstagedChangesColor:",
        f"      - '{c['red']}'",
        "    defaultFgColor:",
        f"      - '{c['text']}'",
        "",
        "",
    ])


# --------------------------------------------------------------------------
# 4) TMUX — generación directa standalone (sin plugin), estética coherente
#    con ~/.tmux.conf líneas 50-76 (status arriba, cápsulas redondeadas)
# --------------------------------------------------------------------------
def tmux_theme(label, P):
    c = P["colors"]
    return "\n".join([
        f"# tmux Ocular {label} — opciones standalone (SIN plugin catppuccin/tmux)",
        "# Recrea la estética actual de ~/.tmux.conf líneas 50-76 (status arriba,",
        "# ventana activa resaltada, borde de panel activo) sin depender del plugin.",
        "# `tmux source-file` este archivo para aplicarlo en caliente.",
        "# status-left/status-right son COMPLETOS y AUTOSUFICIENTES (sesión +",
        "# fecha/hora): tmux.conf no debe definir los suyos, o los pisa al cargar",
        "# después de este archivo.",
        "",
        "set -g status-position top",
        f'set -g status-style "bg={c["mantle"]},fg={c["text"]}"',
        "",
        f'set -g window-status-style "fg={c["overlay1"]},bg={c["mantle"]}"',
        f'set -g window-status-current-style "fg={c["crust"]},bg={c["mauve"]},bold"',
        'set -g window-status-format " #I:#W "',
        'set -g window-status-current-format " #I:#W "',
        'set -g window-status-separator ""',
        "",
        f'set -g pane-border-style "fg={c["surface1"]}"',
        f'set -g pane-active-border-style "fg={c["lavender"]}"',
        "",
        f'set -g message-style "bg={c["surface0"]},fg={c["text"]}"',
        f'set -g message-command-style "bg={c["surface0"]},fg={c["text"]}"',
        "",
        f'set -g mode-style "bg={c["mauve"]},fg={c["crust"]}"',
        "",
        f'set -g status-left-style "fg={c["subtext1"]},bg={c["mantle"]}"',
        f'set -g status-right-style "fg={c["subtext1"]},bg={c["mantle"]}"',
        "",
        # Izquierda: sesión en cápsula de acento (mismo mauve que la ventana
        # activa y mode-style). Derecha: host (#h, resuelto por tmux en runtime
        # — cero hardcode, identifica la máquina en un flujo SSH multi-host) en
        # tono sutil subtext0, luego fecha-hora formato Chile (DD-MM HH:MM) con
        # #[default] que vuelve a status-right-style de arriba — sin plugin.
        f'set -g status-left "#[fg={c["crust"]},bg={c["mauve"]},bold] #S #[fg={c["subtext1"]},bg={c["mantle"]},nobold]"',
        f'set -g status-right "#[fg={c["subtext0"]}] #h #[default]· %d-%m %H:%M "',
        "",
        f'set -g clock-mode-colour "{c["blue"]}"',
        "set -g clock-mode-style 24",
        "",
    ])


# --------------------------------------------------------------------------
# 4b) GH-DASH — generación directa por ROL semántico (NO sustitución del
#     legado Catppuccin — fix 2026-07-26, ver docstring del módulo). Campos
#     reales del schema (verificados contra ~/.config/gh-dash/config.yml
#     vivo, que ya trae theme.colors.* con estos nombres): text.{primary,
#     secondary,inverted,faint,warning,success,error}, background.selected,
#     border.{primary,secondary,faint} — el campo es "faint", no "faded".
#     Mapeo: primary=text, secondary=subtext0, inverted=base,
#     faint=overlay2 (Lc~58/60 sobre fondo normal — legible, no decorativo),
#     background.selected=surface1 (fondo del MISMO modo siempre, nunca el
#     opuesto), border.primary=surface2, border.secondary=surface1,
#     border.faint=surface0. text.primary sobre background.selected da
#     Lc 77.96 (rooibos) / 71.61 (manzanilla) — ambos ≥ 60.
# --------------------------------------------------------------------------
def gh_dash_theme(label, P):
    c = P["colors"]
    return "\n".join([
        f"# Ocular {label} — fragmento theme: para ~/.config/gh-dash/config.yml",
        "theme:",
        "    colors:",
        "        text:",
        f'            primary: "{c["text"]}"',
        f'            secondary: "{c["subtext0"]}"',
        f'            inverted: "{c["base"]}"',
        f'            faint: "{c["overlay2"]}"',
        f'            warning: "{c["yellow"]}"',
        f'            success: "{c["green"]}"',
        f'            error: "{c["red"]}"',
        "        background:",
        f'            selected: "{c["surface1"]}"',
        "        border:",
        f'            primary: "{c["surface2"]}"',
        f'            secondary: "{c["surface1"]}"',
        f'            faint: "{c["surface0"]}"',
        "    ui:",
        "        sectionsShowCount: true",
        "        table:",
        "            showSeparator: true",
        "            compact: false",
        "",
    ])


# --------------------------------------------------------------------------
# 5) STATUSLINE — fragmento bash con los MISMOS nombres C_* que espera el
#    script consumidor externo (statusline del autor).
# --------------------------------------------------------------------------
def hex_to_ansi_seq(hex_str):
    hh = hex_str.lstrip("#")
    r, g, b = int(hh[0:2], 16), int(hh[2:4], 16), int(hh[4:6], 16)
    return f"38;2;{r};{g};{b}"


def statusline_sh(label, P):
    c = P["colors"]

    def seq(role):
        return hex_to_ansi_seq(c[role])

    return "\n".join([
        "#!/usr/bin/env bash",
        f"# Ocular {label} — fragmento de color para claude-statusline",
        "# Mismos nombres C_* que espera el script consumidor externo (statusline",
        "# del autor). 'source' este archivo en vez del bloque Mocha hardcodeado.",
        "# NO incluye C_PR_OPEN: es el color fijo #42A0FA hardcodeado por gh-dash",
        "# (no sale de ningún theme Catppuccin), así que no se remapea a ningún rol.",
        "",
        "R=$'\\e[0m'",
        f"C_PATH=$'\\e[{seq('text')}m'          # text",
        f"C_SEP=$'\\e[{seq('overlay0')}m'        # overlay0 (separadores)",
        f"C_GIT=$'\\e[{seq('mauve')}m'        # mauve    (git limpio)",
        f"C_GIT_DIRTY=$'\\e[{seq('red')}m'  # red      (git sucio)",
        f"C_MODEL=$'\\e[{seq('text')}m'      # text     (modelo)",
        f"C_CYAN=$'\\e[{seq('teal')}m'       # teal",
        f"C_YELLOW=$'\\e[{seq('yellow')}m'      # yellow",
        f"C_RED=$'\\e[{seq('red')}m'        # red",
        f"C_GREEN=$'\\e[{seq('green')}m'       # green",
        "",
    ])


# --------------------------------------------------------------------------
# 6b) CCMAX — fragmento con las MISMAS variables C_* que espera el script
#     consumidor externo (ccmax del autor, bloque "# --- Catppuccin Mocha ---")
# --------------------------------------------------------------------------
def ccmax_sh(label, P):
    c = P["colors"]

    def seq(role):
        return hex_to_ansi_seq(c[role])

    return "\n".join([
        "#!/usr/bin/env bash",
        f"# Ocular {label} — fragmento de color para ccmax",
        "# Mismos nombres C_* que espera el script consumidor externo (ccmax del",
        "# autor, bloque '# --- Catppuccin Mocha ---'). R y B (reset/bold) quedan",
        "# intactos: no son roles de color, son códigos ANSI de control.",
        "",
        "R=$'\\e[0m'",
        "B=$'\\e[1m'",
        f"C_SUB=$'\\e[{seq('overlay0')}m'       # overlay0",
        f"C_SUB1=$'\\e[{seq('overlay1')}m'      # overlay1",
        f"C_MAUVE=$'\\e[{seq('mauve')}m'     # mauve",
        f"C_LAV=$'\\e[{seq('lavender')}m'       # lavender",
        f"C_GREEN=$'\\e[{seq('green')}m'     # green",
        f"C_YELLOW=$'\\e[{seq('yellow')}m'    # yellow",
        f"C_PEACH=$'\\e[{seq('peach')}m'     # peach",
        f"C_RED=$'\\e[{seq('red')}m'      # red",
        f"C_TEAL=$'\\e[{seq('teal')}m'      # teal",
        f"C_SURF=$'\\e[{seq('surface1')}m'      # surface1",
        "",
    ])


# --------------------------------------------------------------------------
# 6c) HERDR — generación directa por rol (fix issue #7, 2026-07-26): el
#     config vivo (~/.config/herdr/config.toml) ya migró a hex Ocular, así
#     que dejó de servir como fuente de sustitución. Mapeo campo->rol
#     derivado comparando ports/out/herdr/*.toml ya versionados contra
#     palette/{rooibos,manzanilla}.json — todos los campos son 1:1 con su
#     propio nombre de rol (blue->blue, mauve->mauve, ...), salvo:
#       panel_bg     -> base
#       surface_dim  -> surface1 (bg de la fila seleccionada del sidebar; fix
#                       APCA 2026-07-26, overlay0 daba Lc 38-42 — ver comentario)
#       accent       -> override deliberado a peach (NO al rol heredado
#                       lavender): el usuario reportó el marco del panel
#                       SELECCIONADO/con foco en azul saturado pese a estar
#                       calibrado en la paleta Ocular. `accent` es la MISMA
#                       clave que `ui.accent` upsertea ocular-switch, y herdr
#                       la documenta como "Accent color for highlights,
#                       borders, and navigation UI" (`herdr --default-config`,
#                       sección [ui]; confirmado en docs.herdr.dev/config-
#                       reference). peach da un marco activo cálido
#                       (identidad Rooibos/Manzanilla) y de paso tiñe la
#                       selección del sidebar (mismo token) — cambio
#                       intencional, no colateral (fix 2026-07-26).
# --------------------------------------------------------------------------
def herdr_theme(label, P):
    c = P["colors"]
    return "\n".join([
        f"# Ocular {label} — fragmento [theme.custom] para ~/.config/herdr/config.toml",
        "# 16 tokens soportados (CustomThemeColors, verificado 2026-07-15).",
        "[theme.custom]",
        f'panel_bg = "{c["base"]}"      # base',
        f'surface_dim = "{c["surface1"]}"   # bg de la fila SELECCIONADA del sidebar (fix APCA 2026-07-26:',
        "                          # overlay0 media Lc 38-42 con el texto por encima — WCAG 2.x aprueba",
        "                          # pares que APCA rechaza, y los pares de Ocular se validan con APCA",
        "                          # (color_science.lc), no con el ratio WCAG. surface1 da texto legible",
        "                          # (Lc ≥ 71 en ambos modos) y sigue siendo más oscuro que panel_bg, así",
        "                          # que la selección se ve. Descartados: morados de Mocha (mauve/",
        "                          # lavender, muy claros para bg), #8839ef mauve de Latte (muy",
        "                          # eléctrico), #574b7d custom.",
        f'surface0 = "{c["surface0"]}"',
        f'surface1 = "{c["surface1"]}"',
        f'overlay0 = "{c["overlay0"]}"',
        f'overlay1 = "{c["overlay1"]}"',
        f'text = "{c["text"]}"',
        f'subtext0 = "{c["subtext0"]}"',
        f'accent = "{c["peach"]}"        # peach — marco activo cálido + selección del sidebar (fix bordes azules, 2026-07-26)',
        f'blue = "{c["blue"]}"',
        f'mauve = "{c["mauve"]}"',
        f'green = "{c["green"]}"',
        f'red = "{c["red"]}"',
        f'yellow = "{c["yellow"]}"',
        f'peach = "{c["peach"]}"',
        f'teal = "{c["teal"]}"',
        "",
        "",
    ])


# --------------------------------------------------------------------------
# 6d) CLAUDE CODE — theme custom para ~/.claude/themes/<slug>.json (formato
#     verificado 2026-07-27 contra code.claude.com/docs/en/terminal-config:
#     {"name", "base": "dark"|"light", "overrides": {token: color}}, Claude
#     Code >=2.1.118, vigila la carpeta y repinta sesiones abiertas al
#     reescribir el archivo). SOLO overrides de los 8 tokens de subagentes
#     (<color>_FOR_SUBAGENTS_ONLY — nombres fijos de Claude Code, no roles de
#     Ocular): no hay overrides documentados para fondo/texto/chrome, eso lo
#     resuelve Claude Code nativo vía "base". Mapeo rol Ocular -> token
#     (pedido 2026-07-27): red->red, blue->blue, green->green, yellow->yellow,
#     purple->mauve, orange->peach, pink->pink, cyan->teal.
# --------------------------------------------------------------------------
SUBAGENT_TOKEN_ROLES = {
    "red_FOR_SUBAGENTS_ONLY": "red",
    "blue_FOR_SUBAGENTS_ONLY": "blue",
    "green_FOR_SUBAGENTS_ONLY": "green",
    "yellow_FOR_SUBAGENTS_ONLY": "yellow",
    "purple_FOR_SUBAGENTS_ONLY": "mauve",
    "orange_FOR_SUBAGENTS_ONLY": "peach",
    "pink_FOR_SUBAGENTS_ONLY": "pink",
    "cyan_FOR_SUBAGENTS_ONLY": "teal",
}


def claude_theme(base, P):
    c = P["colors"]
    overrides = {token: c[role] for token, role in SUBAGENT_TOKEN_ROLES.items()}
    return {"name": "Ocular", "base": base, "overrides": overrides}


# --------------------------------------------------------------------------
# SYNTAX_MAP — tabla semántica ÚNICA {categoría: (rol, estilo)} de la que
# derivan tokenColors/semanticTokenColors de vscode_theme() Y el bloque
# custom_highlights de nvim_lua(). Un solo lugar para recalibrar un color de
# sintaxis en TODO el fleet (VSCode + nvim, ambos modos, ambos perfiles).
# estilo ∈ {None, "italic", "bold", "underline"} — SOLO comment y parameter
# llevan itálica (decisión del usuario, 2026-07-27); markup_heading/
# markup_bold llevan "bold" y markup_link lleva "underline" (heredado del
# mapeo previo, sin cambios de fondo, solo de mecanismo).
#
# Categorías NUEVAS respecto del mapeo legado (antes hardcodeado inline en
# vscode_theme(), sin tabla ni nvim): interpolation, decorator (antes
# colisionaba con function=blue), type_parameter, builtin, key (antes
# hardcodeada a red solo para YAML/JSON; ahora unifica JSON/JSONC/JSONL/
# YAML/TOML/INI/.env — "en datos, la key es la protagonista"), yaml_anchor,
# yaml_tag, yaml_block_scalar (solo VSCode, ver nota en vscode_theme()),
# toml_table. `operator` pasa de sky a subtext0 (sky queda SOLO para
# escape/regexp/interpolación — antes sobrecargado con 5 categorías
# distintas). `attribute` (atributo JSX/HTML) pasa de peach a teal
# (colisionaba con number/constant=peach).
# --------------------------------------------------------------------------
SYNTAX_MAP = {
    # -- código: núcleo léxico --
    "keyword":        ("mauve", None),
    "string":         ("green", None),
    "escape":         ("sky", None),        # string escape + regexp
    "interpolation":  ("sky", None),        # f-string {}, template ${}, .env ${}
    "number":         ("peach", None),      # number/boolean/constant.language
    "function":       ("blue", None),
    "decorator":      ("pink", None),
    "type":           ("yellow", None),     # type/class/interface/enum/namespace
    "type_parameter": ("teal", None),       # <T>, genéricos
    "variable":       ("text", None),
    "parameter":      ("maroon", "italic"),
    "property":       ("lavender", None),   # campo/propiedad de CÓDIGO
    "self":           ("red", None),
    "builtin":        ("sapphire", None),   # len/print/console/process
    "operator":       ("subtext0", None),
    "punctuation":    ("overlay1", None),
    "comment":        ("subtext0", "italic"),
    "invalid":        ("red", None),
    # -- JSX/HTML --
    "tag":            ("red", None),
    "attribute":      ("teal", None),       # atributo de tag JSX/HTML
    "component":      ("yellow", None),     # componente JSX
    # -- markup (Markdown/AsciiDoc) — sin cambios de fondo --
    "markup_heading": ("red", "bold"),
    "markup_bold":    ("yellow", "bold"),
    "markup_italic":  ("blue", "italic"),
    "markup_link":    ("mauve", "underline"),
    "markup_code":    ("green", None),
    # -- formatos de datos (JSON/JSONC/JSONL/YAML/TOML/INI/.env) — la key es
    # la protagonista, el tipo del valor se lee por color (string/number ya
    # cubiertos arriba: mismo rol que en código, es el MISMO dato) --
    "key":               ("sapphire", None),  # JSON/YAML/TOML/INI/.env
    "yaml_anchor":       ("teal", None),      # &ancla / *alias
    "yaml_tag":          ("mauve", None),     # !!str
    "yaml_block_scalar": ("sky", None),       # indicadores | > (solo VSCode)
    "toml_table":        ("yellow", None),    # [section] / [[array]] (solo VSCode)
}


# --------------------------------------------------------------------------
# NVIM_HIGHLIGHT_GROUPS — grupos nvim (treesitter @... + LSP semantic
# @lsp.type./@lsp.mod.) que reciben un override vía custom_highlights, SOLO
# donde SYNTAX_MAP difiere de lo que catppuccin/nvim ya resuelve por
# defecto (plan original, "sección 3"). Nombres de captura treesitter
# verificados 2026-07-28 contra runtime/doc/treesitter.txt de
# neovim/neovim (lista "standard captures", líneas ~368-460) + las queries
# reales de nvim-treesitter (runtime/queries/{ecma,typescript,json,yaml,
# toml}/highlights.scm) — no de memoria. Hallazgos de esa verificación:
#   - `@property` en treesitter es "la key en un par key/value" (así lo
#     documenta el propio doc de neovim). En JS/TS los campos de objeto o
#     clase usan `@variable.member`, NO `@property`
#     (nvim-treesitter/runtime/queries/ecma/highlights.scm líneas 9-13). Por
#     eso `property` (código) mapea a `@variable.member`; `@property` queda
#     SIN override genérico y se especializa por lenguaje
#     (`@property.json/.yaml/.toml`, regla "las capturas se pueden
#     especializar por lenguaje agregando el nombre del lenguaje después de
#     un punto", treesitter.txt líneas ~360-367) para las keys de datos
#     (sapphire) — así no pisa el lavender de código.
#   - `typeParameter` NO tiene captura treesitter estándar (ninguna query
#     define un capture para el identificador de un generic `<T>`; solo
#     existe `@punctuation.bracket` para los `<`/`>`) — se resuelve vía LSP
#     semantic highlighting (`@lsp.type.typeParameter`, documentado en
#     runtime/doc/lsp.txt de neovim/neovim líneas ~645-715), igual que
#     `defaultLibrary` (`@lsp.mod.defaultLibrary`) para builtins — mismo
#     mecanismo que usa VSCode (semanticTokenColors) cuando el LSP está
#     activo.
#   - TOML table headers (`[section]`) NO son distinguibles de una key
#     normal en la query estándar de nvim-treesitter (ambos son
#     `(bare_key) @property`, runtime/queries/toml/highlights.scm) — no hay
#     override posible sin reescribir la query; queda solo en VSCode.
#   - Los indicadores de block scalar YAML (`|`/`>`) comparten
#     `@punctuation.delimiter` con `,`/`-`/`:`/`?` (runtime/queries/yaml/
#     highlights.scm) sin captura propia — solo VSCode los distingue.
# --------------------------------------------------------------------------
NVIM_HIGHLIGHT_GROUPS = [
    ("@operator", "operator"),
    ("@variable.parameter", "parameter"),
    ("@variable.member", "property"),
    ("@attribute", "decorator"),
    ("@type.builtin", "type_parameter"),
    ("@function.builtin", "builtin"),
    ("@constant.builtin", "number"),
    ("@tag.attribute", "attribute"),
    ("@string.escape", "escape"),
    ("@string.regexp", "escape"),
    ("@comment", "comment"),
    ("@property.json", "key"),
    ("@property.yaml", "key"),
    ("@property.toml", "key"),
    ("@label.yaml", "yaml_anchor"),
    ("@type.yaml", "yaml_tag"),
    ("@punctuation.special.yaml", "punctuation"),
    ("@lsp.type.typeParameter", "type_parameter"),
    ("@lsp.mod.defaultLibrary", "builtin"),
    ("@lsp.type.decorator", "decorator"),
    ("@lsp.type.parameter", "parameter"),
    ("@lsp.type.property", "property"),
]


def nvim_custom_highlights_block():
    """Lua fuente del bloque `custom_highlights = function(colors) ...
    end,` — MISMO bloque para Rooibos y Manzanilla: custom_highlights
    recibe la paleta `colors` ya resuelta por catppuccin según el flavour
    activo (mocha/latte), así que basta referenciar `colors.<rol>` (nunca
    un hex fijo) para que ambos modos queden correctos. Sintaxis CtpHighlight
    (campos fg/bg/style/link; style = lista de CtpHighlightArgs, "italic"
    incluido) verificada 2026-07-28 contra
    catppuccin/nvim lua/catppuccin/types.lua (líneas ~327-331)."""
    lines = ["    custom_highlights = function(colors)", "      return {"]
    for group, cat in NVIM_HIGHLIGHT_GROUPS:
        role, style = SYNTAX_MAP[cat]
        parts = [f"fg = colors.{role}"]
        if style:
            parts.append(f'style = {{ "{style}" }}')
        lines.append(f'        ["{group}"] = {{ {", ".join(parts)} }},')
    lines.append("      }")
    lines.append("    end,")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 6) NVIM — spec lazy.nvim para catppuccin/nvim (API verificada por WebFetch
#    al README oficial: color_overrides + flavour="auto" + background map;
#    custom_highlights verificado 2026-07-28, ver NVIM_HIGHLIGHT_GROUPS)
# --------------------------------------------------------------------------
def nvim_lua(dark_pal, light_pal):
    def block(P):
        c = P["colors"]
        rows = "\n".join(f'        {role} = "{hexv}",' for role, hexv in c.items())
        return rows

    return "\n".join([
        "-- Ocular — lazy.nvim spec para catppuccin/nvim",
        "-- Rooibos (dark) -> flavour \"mocha\" · Manzanilla (light) -> flavour \"latte\".",
        "-- API verificada 2026-07-26 contra github.com/catppuccin/nvim README:",
        "--   color_overrides = { all = {...}, mocha = {...}, latte = {...} }",
        "--   flavour = \"auto\" + background = { light = \"latte\", dark = \"mocha\" }",
        "-- custom_highlights (sintaxis SYNTAX_MAP, ver NVIM_HIGHLIGHT_GROUPS arriba)",
        "-- verificado 2026-07-28 contra catppuccin/nvim lua/catppuccin/types.lua.",
        "return {",
        '  "catppuccin/nvim",',
        '  name = "catppuccin",',
        "  priority = 1000,",
        "  opts = {",
        '    flavour = "auto",',
        "    background = {",
        '      light = "latte",',
        '      dark = "mocha",',
        "    },",
        "    color_overrides = {",
        "      mocha = {",
        block(dark_pal),
        "      },",
        "      latte = {",
        block(light_pal),
        "      },",
        "    },",
        nvim_custom_highlights_block(),
        "  },",
        "  config = function(_, opts)",
        '    require("catppuccin").setup(opts)',
        '    vim.cmd.colorscheme("catppuccin")',
        "  end,",
        "}",
        "",
    ])


# --------------------------------------------------------------------------
# 7) VSCODE — misma estructura que un generador equivalente de herramientas
#    externas del autor (mismos keys de colors + tokenColors), con el mapeo
#    sintáctico Catppuccin del enunciado en vez de la paleta OKLCH.
# --------------------------------------------------------------------------
def ocular_ui_palette(P):
    c = P["colors"]
    N = {
        "bg": c["base"], "surface": c["mantle"], "surf2": c["crust"],
        "overlay": c["surface1"], "muted": c["overlay2"], "subtle": c["overlay1"],
        "text": c["text"],
    }
    S = {
        "blue": c["mauve"], "green": c["green"], "purple": c["blue"],
        "orange": c["peach"], "yellow": c["yellow"], "cyan": c["sky"], "red": c["red"],
    }
    accent = c["lavender"]
    return N, S, accent


def vscode_theme(mode, label, P):
    N, S, accent = ocular_ui_palette(P)
    c = P["colors"]
    ansi = P["ansi"]
    ui = "vs" if mode == "light" else "vs-dark"
    onAccent = "#ffffff"
    a40, a20 = accent + "40", accent + "20"
    sel, selA = N["overlay"], N["overlay"] + "66"
    border = N["surf2"]
    colors = {
        "focusBorder": accent, "foreground": N["text"], "widget.shadow": "#00000033",
        "selection.background": a40, "errorForeground": S["red"], "icon.foreground": N["subtle"],
        "sash.hoverBorder": accent,
        "activityBar.background": N["surface"], "activityBar.foreground": N["text"],
        "activityBar.inactiveForeground": N["muted"], "activityBar.border": N["surface"],
        "activityBarBadge.background": accent, "activityBarBadge.foreground": onAccent,
        "activityBar.activeBorder": accent,
        "sideBar.background": N["surface"], "sideBar.foreground": N["text"], "sideBar.border": border,
        "sideBarTitle.foreground": N["text"],
        "sideBarSectionHeader.background": N["surf2"], "sideBarSectionHeader.foreground": N["text"],
        "sideBarSectionHeader.border": border,
        "list.activeSelectionBackground": N["overlay"], "list.activeSelectionForeground": N["text"],
        "list.hoverBackground": selA, "list.inactiveSelectionBackground": selA,
        "list.highlightForeground": accent, "tree.indentGuidesStroke": N["surf2"],
        "editorGroupHeader.tabsBackground": N["surface"], "editorGroupHeader.border": N["surface"],
        "tab.activeBackground": N["bg"], "tab.activeForeground": N["text"],
        "tab.inactiveBackground": N["surface"], "tab.inactiveForeground": N["muted"],
        "tab.activeBorderTop": accent, "tab.border": N["surface"],
        "tab.hoverBackground": N["bg"],
        "editor.background": N["bg"], "editor.foreground": N["text"],
        "editorLineNumber.foreground": N["overlay"], "editorLineNumber.activeForeground": N["subtle"],
        "editorCursor.foreground": accent,
        "editor.selectionBackground": sel, "editor.selectionHighlightBackground": selA,
        "editor.wordHighlightBackground": a20, "editor.wordHighlightStrongBackground": a40,
        "editor.findMatchBackground": S["yellow"] + "55", "editor.findMatchHighlightBackground": S["yellow"] + "33",
        "editor.lineHighlightBackground": N["surface"] + "88",
        "editor.lineHighlightBorder": "#00000000",
        "editorLink.activeForeground": accent,
        "editorWhitespace.foreground": N["overlay"],
        "editorIndentGuide.background1": N["surf2"], "editorIndentGuide.activeBackground1": N["subtle"],
        "editorRuler.foreground": N["surf2"], "editorCodeLens.foreground": N["muted"],
        "editorBracketMatch.background": a20, "editorBracketMatch.border": accent,
        # Secuencia bracket-pair verificada por HUE OKLCH real de la paleta
        # Ocular (color_science.hex_to_oklch), no por el orden convencional
        # de Catppuccin (Ocular re-optimizó sus hues, PR #20) — recorrido en
        # "estrella" (salta uno) sobre el círculo de hue para maximizar la
        # distancia angular entre niveles de anidamiento CONSECUTIVOS,
        # incluido el wraparound nivel6->nivel1: peach(57°) -> green(140°,
        # +82°) -> sapphire(241°, +102°) -> yellow(89°, +153°) ->
        # teal(185°, +96°) -> mauve(310°, +125°) -> peach (+107° al volver a
        # nivel1). Gap mínimo 82° (~3.2x el espaciado promedio entre los 14
        # roles), ninguno "vecino de hue" (verificado 2026-07-28).
        "editorBracketHighlight.foreground1": c["peach"], "editorBracketHighlight.foreground2": c["green"],
        "editorBracketHighlight.foreground3": c["sapphire"], "editorBracketHighlight.foreground4": c["yellow"],
        "editorBracketHighlight.foreground5": c["teal"], "editorBracketHighlight.foreground6": c["mauve"],
        "editorBracketHighlight.unexpectedBracket.foreground": c["red"],
        "editorError.foreground": S["red"], "editorWarning.foreground": S["orange"], "editorInfo.foreground": accent,
        "editorGutter.modifiedBackground": accent, "editorGutter.addedBackground": S["green"],
        "editorGutter.deletedBackground": S["red"],
        "diffEditor.insertedTextBackground": S["green"] + "22", "diffEditor.removedTextBackground": S["red"] + "22",
        "editorOverviewRuler.border": border,
        "editorWidget.background": N["surface"], "editorWidget.border": border,
        "editorSuggestWidget.background": N["surface"], "editorSuggestWidget.border": border,
        "editorSuggestWidget.selectedBackground": N["overlay"], "editorSuggestWidget.highlightForeground": accent,
        "editorHoverWidget.background": N["surface"], "editorHoverWidget.border": border,
        "peekView.border": accent, "peekViewEditor.background": N["surface"],
        "peekViewResult.background": N["surface"], "peekViewTitle.background": N["surf2"],
        "panel.background": N["bg"], "panel.border": border,
        "panelTitle.activeBorder": accent, "panelTitle.activeForeground": N["text"],
        "panelTitle.inactiveForeground": N["muted"],
        "statusBar.background": N["surface"], "statusBar.foreground": N["text"], "statusBar.border": N["surface"],
        "statusBar.noFolderBackground": N["surface"], "statusBar.debuggingBackground": S["orange"],
        "statusBarItem.remoteBackground": accent, "statusBarItem.remoteForeground": onAccent,
        "titleBar.activeBackground": N["surface"], "titleBar.activeForeground": N["text"],
        "titleBar.inactiveBackground": N["surface"], "titleBar.inactiveForeground": N["muted"],
        "titleBar.border": N["surface"],
        "menu.background": N["surface"], "menu.foreground": N["text"],
        "menu.selectionBackground": N["overlay"], "menu.separatorBackground": border,
        "input.background": N["surf2"], "input.foreground": N["text"], "input.border": border,
        "input.placeholderForeground": N["muted"], "inputOption.activeBorder": accent,
        "dropdown.background": N["surf2"], "dropdown.foreground": N["text"], "dropdown.border": border,
        "button.background": accent, "button.foreground": onAccent, "button.hoverBackground": accent + "cc",
        "badge.background": accent, "badge.foreground": onAccent,
        "scrollbarSlider.background": N["subtle"] + "55", "scrollbarSlider.hoverBackground": N["subtle"] + "88",
        "scrollbarSlider.activeBackground": N["subtle"] + "aa", "progressBar.background": accent,
        "terminal.background": N["bg"], "terminal.foreground": N["text"],
        "terminal.ansiBlack": ansi["normal"]["black"], "terminal.ansiRed": ansi["normal"]["red"],
        "terminal.ansiGreen": ansi["normal"]["green"], "terminal.ansiYellow": ansi["normal"]["yellow"],
        "terminal.ansiBlue": ansi["normal"]["blue"], "terminal.ansiMagenta": ansi["normal"]["magenta"],
        "terminal.ansiCyan": ansi["normal"]["cyan"], "terminal.ansiWhite": ansi["normal"]["white"],
        "terminal.ansiBrightBlack": ansi["bright"]["black"], "terminal.ansiBrightRed": ansi["bright"]["red"],
        "terminal.ansiBrightGreen": ansi["bright"]["green"], "terminal.ansiBrightYellow": ansi["bright"]["yellow"],
        "terminal.ansiBrightBlue": ansi["bright"]["blue"], "terminal.ansiBrightMagenta": ansi["bright"]["magenta"],
        "terminal.ansiBrightCyan": ansi["bright"]["cyan"], "terminal.ansiBrightWhite": ansi["bright"]["white"],
        "gitDecoration.modifiedResourceForeground": S["yellow"], "gitDecoration.deletedResourceForeground": S["red"],
        "gitDecoration.untrackedResourceForeground": S["green"], "gitDecoration.ignoredResourceForeground": N["muted"],
        "gitDecoration.conflictingResourceForeground": S["orange"],
        "notifications.background": N["surface"], "notifications.border": border,
        "notificationLink.foreground": accent,
        "breadcrumb.foreground": N["muted"], "breadcrumb.background": N["bg"],
        "breadcrumb.focusForeground": N["text"], "breadcrumb.activeSelectionForeground": accent,
    }

    def tk(name, scopes, fg, style=None):
        s = {"foreground": fg}
        if style:
            s["fontStyle"] = style
        return {"name": name, "scope": scopes, "settings": s}

    def role(cat):
        """(hex, style) de una categoría SYNTAX_MAP resuelta contra la
        paleta P de este perfil — única fuente de tokenColors/
        semanticTokenColors (ver tabla + docstring más arriba)."""
        r, style = SYNTAX_MAP[cat]
        return c[r], style

    # tokenColors (TextMate) — scopes verificados 2026-07-28 contra las
    # gramáticas reales: microsoft/vscode extensions/{typescript-basics,
    # python,json,ini,shellscript,sql,lua}/syntaxes/*.tmLanguage.json,
    # microsoft/vscode extensions/yaml/syntaxes/yaml-1.2.tmLanguage.json
    # (fork de RedCMD/YAML-Syntax-Highlighter), mikestead/vscode-dotenv
    # syntaxes/env.tmLanguage (.env, sin soporte nativo en VSCode) y el
    # tmTheme oficial de Catppuccin ya vendorizado en
    # ports/reference/bat-catppuccin-mocha.tmTheme (scopes TOML/INI/YAML
    # que ese theme ya usa en producción: support.type.property-name.toml,
    # entity.name.section.group-title.ini, entity.other.document.begin.yaml,
    # etc.) — no de memoria. Nota sobre cascada: un selector como "keyword"
    # o "string" ya matchea cualquier scope más específico del mismo prefijo
    # (p.ej. "keyword.other.DML.sql", "string.unquoted.plain.out.yaml"), así
    # que SQL/Lua/bash/YAML-plain-scalar heredan Keyword/String/Function sin
    # necesidad de una regla explícita — solo se agregan reglas nuevas donde
    # la categoría es distinta de lo genérico (builtins, decorator, keys de
    # datos, etc.). El frontmatter de Markdown inyecta "source.yaml" de
    # verdad (markdown.tmLanguage.json, contentName
    # "meta.embedded.block.frontmatter") -> las reglas YAML de abajo aplican
    # ahí también, sin trabajo extra.
    tokens = [
        tk("Comment", ["comment", "punctuation.definition.comment"], *role("comment")),
        tk("String", ["string", "string.quoted", "string.template"], *role("string")),
        tk("String escape / regexp", ["constant.character.escape", "string.regexp"], *role("escape")),
        tk("Interpolation (f-string / template literal / .env ${})", [
            "punctuation.definition.template-expression.begin", "punctuation.definition.template-expression.end",
            "constant.character.format.placeholder.other.python",
            "keyword.other.template.begin.env", "keyword.other.template.end.env",
        ], *role("interpolation")),
        tk("Number / boolean / constant.language", [
            "constant.numeric", "constant.language", "constant.language.boolean", "support.constant",
        ], *role("number")),
        tk("Keyword / storage", ["keyword", "storage.type", "storage.modifier", "keyword.control"], *role("keyword")),
        tk("Operator", ["keyword.operator", "punctuation.separator.operator"], *role("operator")),
        tk("Function / method", ["entity.name.function", "support.function", "meta.function-call.generic"], *role("function")),
        tk("Decorator", [
            "meta.decorator", "punctuation.decorator", "entity.name.function.decorator",
            "punctuation.definition.decorator", "entity.name.function.decorator.python",
            "punctuation.definition.decorator.python",
        ], *role("decorator")),
        tk("Type parameter / generics", [
            "meta.type.parameters", "entity.name.type.parameter", "punctuation.definition.typeparameters",
        ], *role("type_parameter")),
        tk("Class / Type", ["entity.name.type", "entity.name.class", "support.class", "support.type", "entity.other.inherited-class"], *role("type")),
        tk("Variable", ["variable", "variable.other.readwrite", "meta.definition.variable"], *role("variable")),
        tk("Parameter", ["variable.parameter"], *role("parameter")),
        tk("Language variable (this/self)", [
            "variable.language", "variable.language.this",
            "variable.parameter.function.language.special.self.python", "variable.language.special.self.python",
        ], *role("self")),
        tk("Builtin", [
            "support.function.builtin", "support.function.builtin.python", "support.function.builtin.shell",
            "support.function.library.lua", "support.function.lua", "support.class.builtin", "support.type.builtin",
        ], *role("builtin")),
        tk("Property", ["variable.other.property", "support.variable.property", "meta.object-literal.key", "support.type.property-name"], *role("property")),
        tk("Data key (JSON/JSONC/JSONL/YAML/TOML/INI/.env)", [
            "support.type.property-name.json", "support.type.property-name.toml", "entity.name.tag.yaml",
            "keyword.other.definition.ini", "variable.other.env",
        ], *role("key")),
        tk("Constant other (enum)", ["variable.other.constant", "variable.other.enummember"], *role("number")),
        tk("Punctuation", ["punctuation", "meta.brace", "punctuation.separator", "punctuation.terminator"], *role("punctuation")),
        tk("Invalid", ["invalid", "invalid.illegal"], *role("invalid")),
        tk("Markup heading", ["markup.heading", "entity.name.section"], *role("markup_heading")),
        tk("Markup bold", ["markup.bold"], *role("markup_bold")),
        tk("Markup italic", ["markup.italic"], *role("markup_italic")),
        tk("Markup code", ["markup.inline.raw", "markup.fenced_code.block"], *role("markup_code")),
        tk("Markup link", ["markup.underline.link"], *role("markup_link")),
        tk("Tag", ["entity.name.tag.html", "entity.name.tag.tsx", "entity.name.tag"], *role("tag")),
        tk("Attribute", ["entity.other.attribute-name", "entity.other.attribute-name.tsx"], *role("attribute")),
        tk("CSS value/unit", ["support.constant.property-value", "support.constant.font-name", "keyword.other.unit", "constant.numeric.css"], *role("number")),
        tk("JSX component", ["support.class.component"], *role("component")),
        tk("YAML anchor / alias", [
            "variable.other.anchor.yaml", "variable.other.alias.yaml", "entity.name.type.anchor.yaml",
            "punctuation.definition.anchor.yaml", "punctuation.definition.alias.yaml",
        ], *role("yaml_anchor")),
        tk("YAML tag (!!str)", [
            "storage.type.tag-handle.yaml", "storage.type.tag.shorthand.yaml",
            "storage.type.tag.verbatim.yaml", "storage.type.tag.non-specific.yaml",
        ], *role("yaml_tag")),
        tk("YAML block scalar indicator (| >)", [
            "keyword.control.flow.block-scalar.folded.yaml", "keyword.control.flow.block-scalar.literal.yaml",
        ], *role("yaml_block_scalar")),
        tk("YAML document separator (---)", ["entity.other.document.begin.yaml"], *role("punctuation")),
        tk("TOML table header ([section] / [[array]])", [
            "support.type.property-name.table", "entity.name.section.group-title.ini",
        ], *role("toml_table")),
    ]
    # semanticTokenColors — los semantic tokens (Pylance/tsserver/etc.) PISAN
    # a TextMate cuando el LSP está activo: deben decir lo mismo que tokens
    # arriba. Tipos/modificadores estándar LSP (code.visualstudio.com/api/
    # language-extensions/semantic-highlight-guide) + "selfParameter", tipo
    # custom que agrega Pylance a su semanticTokensLegend (no está en el set
    # estándar; se mantiene igual que en el mapeo legado).
    semantic = {
        "function": c["blue"], "method": c["blue"], "macro": c["blue"],
        "class": c["yellow"], "type": c["yellow"], "interface": c["yellow"],
        "enum": c["yellow"], "namespace": c["yellow"], "struct": c["yellow"],
        "typeParameter": c["teal"],
        "parameter": {"foreground": c["maroon"], "italic": True},
        "variable": c["text"], "variable.readonly": c["peach"],
        "property": c["lavender"],
        "enumMember": c["peach"],
        "decorator": c["pink"],
        "operator": c["subtext0"], "regexp": c["sky"],
        "selfParameter": c["red"],
        "*.defaultLibrary": c["sapphire"],
        "comment": {"foreground": c["subtext0"], "italic": True},
        "*.declaration": {"bold": True},
    }
    return {
        "name": f"Ocular {label}", "type": mode,
        "semanticHighlighting": True, "semanticTokenColors": semantic,
        "colors": colors, "tokenColors": tokens,
    }


# --------------------------------------------------------------------------
# 8) CHROME (modo desarrollador) — generación directa MV3, RGB decimal.
#    Mapeo por rol (mismo para ambos modos): frame=mantle,
#    frame_inactive/incognito/incognito_inactive=crust, toolbar=surface0,
#    toolbar_button_icon=mauve, tab_text=text, tab_background_text=overlay0,
#    bookmark_text=text, ntp_background=base, ntp_text=text, ntp_link=mauve,
#    button_background=mantle. tints/properties calcados del original.
# --------------------------------------------------------------------------
def chrome_manifest(label, mode_desc, P):
    c = P["colors"]

    def rgb(role):
        hx = c[role].lstrip("#")
        return [int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)]

    return {
        "manifest_version": 3,
        "name": f"Ocular {label}",
        "description": f"Theme Ocular para Chrome — {label} ({mode_desc}).",
        "version": "1.0.0",
        "theme": {
            "colors": {
                "frame": rgb("mantle"),
                "frame_inactive": rgb("crust"),
                "frame_incognito": rgb("crust"),
                "frame_incognito_inactive": rgb("crust"),
                "toolbar": rgb("surface0"),
                "toolbar_button_icon": rgb("mauve"),
                "tab_text": rgb("text"),
                "tab_background_text": rgb("overlay0"),
                "bookmark_text": rgb("text"),
                "ntp_background": rgb("base"),
                "ntp_text": rgb("text"),
                "ntp_link": rgb("mauve"),
                "button_background": rgb("mantle"),
            },
            "tints": {"buttons": [-1, -1, -1]},
            "properties": {"ntp_background_alignment": "bottom"},
        },
    }


CHROME_README = """# Chrome (developer mode) — Ocular

MV3 theme (`theme.colors` in decimal RGB), same structure as an equivalent
manifest from the author's external tooling.

## Install (unpacked)

1. `chrome://extensions` -> enable "Developer mode".
2. "Load unpacked" -> point to `ocular-rooibos/` or `ocular-manzanilla/`.

## Limitation (documented, not a bug)

Chrome themes loaded as *unpacked* are **static**: they don't follow the
system appearance (no auto dark/light) and can't be reloaded by script —
Chrome doesn't expose an API for that to an unpacked extension. Switching
between Rooibos and Manzanilla is **manual**: `chrome://extensions` ->
disable the active theme -> enable the other one. `ocular-switch` does NOT
manage Chrome for this reason.
"""


# --------------------------------------------------------------------------
# 9) SLACK — README con el custom theme (string de 8 hex), generación
#    directa por rol. Mapeo (mismo para ambos modos, rediseñado 2026-07-28 —
#    feedback: el café del theme no se notaba con mantle de fondo y la UI
#    persistente debía llevar la firma cálida, mismo criterio que el accent
#    de herdr y el path de oh-my-posh, ver omp_colors()): Column BG=base
#    (antes mantle, demasiado oscuro), Menu Hover BG=surface0, Hover Item=
#    surface1, Active Item=peach (antes mauve — familia FIRMA, no un acento
#    frío de contenido), Active Item Text=crust en AMBOS modos (regla del
#    runbook: fg sobre bg de acento es SIEMPRE base/crust, nunca otro
#    acento), Text=text, Active Presence=green, Mention Badge=red. Gate APCA
#    dedicado en check_slack_pairs() (text/columnBG>=75, activeItemText/
#    activeItem>=60, text/hoverItem>=60, en las 4 variantes). Slack no
#    expone API para custom themes ni para recargarlos: la conmutación sigue
#    siendo manual (paste del string).
# --------------------------------------------------------------------------
def slack_theme_string(P):
    c = P["colors"]
    roles = [c["base"], c["surface0"], c["peach"], c["crust"],
             c["surface1"], c["text"], c["green"], c["red"]]
    return ",".join(f"#{r.lstrip('#').upper()}" for r in roles)


# slack/README.md es UN solo archivo compartido por todos los perfiles (Slack
# no tiene concepto de perfil: el usuario simplemente pega el string del que
# use). emit_profile() ya no lo escribe directo — acumula la sección de su
# perfil aquí y main() arma+escribe el archivo completo UNA vez, después de
# emitir todos los perfiles (si no, cada llamada pisaría la anterior y el
# README quedaría solo con las 2 cadenas del último perfil).
SLACK_SECTIONS: list[list[str]] = []


def slack_readme_section(dark_pal, light_pal, dark_label, light_label):
    return [
        f"## Ocular {dark_label} (dark)",
        "",
        "```",
        slack_theme_string(dark_pal),
        "```",
        "",
        f"## Ocular {light_label} (light)",
        "",
        "```",
        slack_theme_string(light_pal),
        "```",
        "",
    ]


def slack_readme(sections):
    lines = [
        "# Slack — Ocular custom theme",
        "",
        "Slack accepts an 8-hex string (Preferences → Themes → Custom theme, or paste",
        "it into a message and Slack offers \"Apply Slack theme\"). Field order: Column",
        "BG, Menu Hover BG, Active Item, Active Item Text, Hover Item, Text Color,",
        "Active Presence, Mention Badge.",
        "",
    ]
    for section in sections:
        lines.extend(section)
    lines.extend([
        "Mapping by role: Column BG = base · Menu Hover BG = surface0 · Active Item",
        "= peach · Active Item Text = crust · Hover Item = surface1 · Text = text ·",
        "Active Presence = green · Mention Badge = red.",
        "Slack doesn't support automatic switching of custom themes: paste the",
        "string for whichever mode you're using.",
        "",
    ])
    return "\n".join(lines)


def check_slack_pairs():
    """Gate APCA obligatorio del custom theme de Slack (exit != 0 si falla):
    los 3 pares fg/bg de lectura continua que el usuario ve al pegar la
    cadena Ocular — Column BG es la superficie de lectura principal (texto
    largo de canales/DMs, piso más estricto que el resto de los ports), Active
    Item es chrome persistente con Active Item Text encima, Hover Item es
    chrome puntual. Corre sobre las 4 variantes (default + deutan, dark +
    light): el perfil deutan reusa los mismos roles de superficie/firma para
    Slack, pero se vigila por si el mapeo de acentos CVD alguna vez diverge."""
    checks = [
        ("text/columnBG", "text", "base", 75),
        ("activeItemText/activeItem", "crust", "peach", 60),
        ("text/hoverItem", "text", "surface1", 60),
    ]
    variants = [
        ("rooibos", ROOIBOS), ("manzanilla", MANZANILLA),
        ("rooibos-deutan", ROOIBOS_DEUTAN), ("manzanilla-deutan", MANZANILLA_DEUTAN),
    ]
    for mode_name, P in variants:
        c = P["colors"]
        for field, fg_role, bg_role, floor in checks:
            val = apca_lc(c[fg_role], c[bg_role])
            ok = val >= floor
            label = ROOT / "ports" / f"slack-apca:{mode_name}:{field}"
            record(
                "apca-pares", label, ok,
                f"Lc={val:.2f} (piso={floor}) fg={fg_role} bg={bg_role}",
            )


DELTA_README = """# delta — Ocular

Antes este directorio solo documentaba que delta reusa el tmTheme de bat por
nombre (`syntax-theme`). Eso sigue siendo cierto, pero delta también tiene
FONDOS de diff propios (plus/minus/blame/line-numbers) que el `syntax-theme`
no cubre — sin un feature dedicado quedan en los defaults de delta o, peor,
en los de un feature legado ajeno (ver "Por qué existe" abajo). Este puerto
genera un feature file `[delta "ocular"]` completo por modo.

## Archivos

- `ocular-rooibos.gitconfig` — dark.
- `ocular-manzanilla.gitconfig` — light.

Mismo nombre de feature **fijo** `ocular` en ambos: el `~/.gitconfig` del
usuario nunca cambia, solo el CONTENIDO del archivo incluido cambia por modo.

## Instalación (la hace `ocular-switch`)

```
cp ports/out/delta/ocular-<variante>.gitconfig ~/.config/delta/ocular.gitconfig
```

Y en `~/.gitconfig` (una sola vez, a mano):

```
[include]
    path = ~/.config/delta/ocular.gitconfig
```

delta no cachea nada: el próximo `git diff`/`git log -p | delta` ya toma el
archivo reescrito, sin reiniciar nada.

## Derivación de color

Todos los valores salen por ROL de `palette/{rooibos,manzanilla}.json`
(`build_ports.py`, función `delta_theme()`), igual que el resto de los ports:

- `syntax-theme` = el tmTheme de bat del mismo modo (`ports/out/bat/`).
- `plus-style`/`minus-style` = mezcla perceptual OKLab de `base` con
  `green`/`red` (~12%, `mix_oklab()`/`TINT_NORMAL`) — nunca el acento puro
  como fondo: los acentos Ocular están calibrados al mismo Lc que el texto
  normal frente a un neutro, así que usarlos de fondo colapsaría el
  contraste de lo que se dibuja encima.
- `plus-emph-style`/`minus-emph-style` = misma mezcla, más intensa (~28%,
  `TINT_EMPH`), para las palabras resaltadas dentro de la línea.
- `line-numbers-plus/minus-style` = `green`/`red` puros (ya calibrados).
- `line-numbers-zero/left/right-style`, `file-decoration-style`,
  `hunk-header-decoration-style`, `blame-palette` = neutros de superficie
  del mismo modo.
- `file-style`, `hunk-header-style`, `hunk-header-line-number-style`,
  `merge-conflict-*-style` = acentos directos (yellow/blue/peach).

Gate obligatorio (`check_delta_pairs()` en `build_ports.py`, corre en cada
`python3 ports/build_ports.py`): `Lc(text, bg) >= 60` (APCA,
`color_science.lc`) para los 4 fondos de diff y los 4 neutros de
blame-palette, más `Lc(green/red, base)` para line-numbers — exit != 0 si
alguno falla.

## Por qué existe este port

Sin un feature propio, cualquier feature LEGADO que un `~/.gitconfig` traiga
incluido (p.ej. uno pre-Ocular con fondos oscuros hardcodeados) pisa el
`[delta] syntax-theme` principal y deja el diff con fondos dark sobre
terminal light — el síntoma que motivó este port. `ocular-switch` instala
SIEMPRE el feature `ocular` del modo activo; basta con apuntar el `[include]`
de `~/.gitconfig` a `~/.config/delta/ocular.gitconfig` una vez.
"""


# --------------------------------------------------------------------------
# 10) DELTA — feature file propio (`[delta "ocular"]`), reemplaza el README-
#    only anterior (delta reusaba SOLO el tmTheme de bat por nombre; no
#    tenía fondos de diff propios). Nombre de feature FIJO "ocular" en
#    AMBOS modos — así ~/.gitconfig no cambia nunca, solo el CONTENIDO del
#    archivo incluido cambia por modo (ver ocular-switch). Estructura calcada
#    del feature legado pre-Ocular '~/.config/delta/crepusculo.gitconfig'
#    (dark hardcodeado) pero con TODOS los colores derivados por ROL de la
#    paleta Ocular del modo — ese era justo el bug que motivó el port: el
#    feature legado pisaba syntax-theme/plus-style/minus-style del [delta]
#    principal con fondos oscuros fijos, ilegibles en Manzanilla (light).
#
#    plus-style/minus-style: fondo = mezcla OKLab base+green/red al
#    TINT_NORMAL (~12%) — NUNCA el acento puro como bg: los 14 acentos están
#    calibrados al MISMO Lc que texto normal frente a neutros (ver nota
#    "Pares acento-como-fondo" del runbook ocular-theme), así que usarlos de
#    fondo colapsa el contraste de lo que se dibuja encima. plus-emph/minus-
#    emph: mezcla al TINT_EMPH (~28%), mismo mecanismo con más intensidad
#    para las palabras resaltadas dentro de la línea. zero-style = syntax
#    (colores de sintaxis normales, sin tinte de fondo, para contexto).
#
#    line-numbers-zero/left/right-style son DECORATIVOS (columna de números
#    sin cambios / separador visual entre paneles) — no se leen como cuerpo
#    de texto, así que no están sujetos al piso de lectura (60 Lc) que sí
#    aplica a los fondos de diff y a blame-palette (ver check_delta_pairs).
#    Se elige el neutro de mayor Lc frente a `base` entre los roles
#    ofrecidos (overlay1 sobre overlay0; surface2 sobre surface1) — en
#    Rooibos ninguno de los dos candidatos de left/right despega de Lc≈0
#    frente a base (son neutros de SUPERFICIE, pensados para verse como
#    fondo adyacente, no como texto encima de `base`): es la misma sutileza
#    intencional que ya tenía el separador del legado crepusculo
#    ("#36322c" casi idéntico a su propio fondo).
# --------------------------------------------------------------------------
TINT_NORMAL = 0.12
TINT_EMPH = 0.28


def mix_oklab(hex_a: str, hex_b: str, t: float) -> str:
    """Mezcla perceptual hex_a<-hex_b en OKLab (t=peso de hex_b, 0..1), con
    el mismo pipeline de color_science (OKLab + gamut mapping por reducción
    de chroma vía oklch_to_hex) — sin dependencias nuevas."""
    import math
    L1, a1, b1 = hex_to_oklab(hex_a)
    L2, a2, b2 = hex_to_oklab(hex_b)
    L = L1 + (L2 - L1) * t
    a = a1 + (a2 - a1) * t
    bb = b1 + (b2 - b1) * t
    C = math.hypot(a, bb)
    H = math.degrees(math.atan2(bb, a)) % 360
    return oklch_to_hex(L, C, H)


def delta_diff_tints(P):
    """(plus, plus_emph, minus, minus_emph) — fondos derivados por mezcla
    OKLab base+green/red, NUNCA el acento puro (ver docstring de arriba)."""
    c = P["colors"]
    return (
        mix_oklab(c["base"], c["green"], TINT_NORMAL),
        mix_oklab(c["base"], c["green"], TINT_EMPH),
        mix_oklab(c["base"], c["red"], TINT_NORMAL),
        mix_oklab(c["base"], c["red"], TINT_EMPH),
    )


def delta_theme(label, P):
    c = P["colors"]
    plus, plus_emph, minus, minus_emph = delta_diff_tints(P)
    return "\n".join([
        f"# delta — feature 'ocular' (Ocular {label})",
        "# Generado por ports/build_ports.py — plus/minus derivados por mezcla",
        "# OKLab (base + green/red @ 12%/28%, ver mix_oklab/delta_diff_tints) +",
        "# gate APCA obligatorio (check_delta_pairs, piso cuerpo=60 Lc). Comparte",
        f"# el tmTheme de bat (syntax-theme = Ocular {label}). Nombre de feature",
        "# FIJO 'ocular' en ambos modos: ocular-switch reescribe el CONTENIDO de",
        "# este archivo, nunca el include de ~/.gitconfig.",
        "",
        "[delta]",
        "    features = ocular",
        "",
        '[delta "ocular"]',
        f"    syntax-theme = Ocular {label}",
        "    true-color = always",
        f'    plus-style = syntax "{plus}"',
        f'    plus-emph-style = syntax "{plus_emph}"',
        f'    minus-style = syntax "{minus}"',
        f'    minus-emph-style = syntax "{minus_emph}"',
        "    zero-style = syntax",
        f'    line-numbers-plus-style = "{c["green"]}"',
        f'    line-numbers-minus-style = "{c["red"]}"',
        f'    line-numbers-zero-style = "{c["overlay1"]}"',
        f'    line-numbers-left-style = "{c["surface2"]}"',
        f'    line-numbers-right-style = "{c["surface2"]}"',
        f'    file-style = "{c["yellow"]}" bold',
        f'    file-decoration-style = "{c["surface1"]}" ul',
        f'    hunk-header-style = "{c["blue"]}" bold',
        f'    hunk-header-decoration-style = "{c["surface0"]}" box',
        f'    hunk-header-file-style = "{c["subtext0"]}"',
        f'    hunk-header-line-number-style = "{c["yellow"]}"',
        f'    blame-palette = "{c["mantle"]}" "{c["base"]}" "{c["surface0"]}" "{c["crust"]}"',
        f'    whitespace-error-style = "{c["red"]}" reverse',
        f'    merge-conflict-ours-style = "{c["peach"]}" bold',
        f'    merge-conflict-theirs-style = "{c["blue"]}" bold',
        "",
    ])


def check_delta_pairs():
    """Gate APCA obligatorio de delta (exit != 0 si falla): los 4 fondos de
    diff derivados (mezcla OKLab, no son un rol directo de la paleta -> no
    caben en la tabla estática EMITTED_PAIRS) + los 4 neutros de blame-
    palette + line-numbers green/red frente a base deben leerse con
    Lc(text, bg) >= 60 (piso 'cuerpo', mismo criterio que check_emitted_pairs
    salvo que aquí el bg es calculado, no un P["colors"][rol] fijo)."""
    floor = PAIR_FLOORS["cuerpo"]
    for mode_name, P in (("rooibos", ROOIBOS), ("manzanilla", MANZANILLA)):
        c = P["colors"]
        plus, plus_emph, minus, minus_emph = delta_diff_tints(P)
        # (campo, fg, bg) — fg="text" para los fondos de diff/blame (se lee
        # texto normal encima); fg=green/red, bg=base para line-numbers (el
        # propio acento ES el texto, ya calibrado, se vigila igual por drift).
        checks = [
            ("plus-style", "text", plus),
            ("plus-emph-style", "text", plus_emph),
            ("minus-style", "text", minus),
            ("minus-emph-style", "text", minus_emph),
            ("blame-palette:mantle", "text", c["mantle"]),
            ("blame-palette:base", "text", c["base"]),
            ("blame-palette:surface0", "text", c["surface0"]),
            ("blame-palette:crust", "text", c["crust"]),
            ("line-numbers-plus-style", c["green"], c["base"]),
            ("line-numbers-minus-style", c["red"], c["base"]),
        ]
        for field, fg, bg in checks:
            fg_hex = c["text"] if fg == "text" else fg
            val = apca_lc(fg_hex, bg)
            ok = val >= floor
            label = ROOT / "ports" / f"delta-apca:{mode_name}:{field}"
            record("apca-pares", label, ok, f"Lc={val:.2f} (piso cuerpo={floor}) fg={fg_hex} bg={bg}")


# --------------------------------------------------------------------------
# Plantillas de referencia (Catppuccin oficial vendorizado) — las mismas para
# cualquier perfil: lo único que cambia por perfil es el mapeo rol->hex de
# destino, no la plantilla fuente.
# --------------------------------------------------------------------------
REF = {
    "bat_mocha": PORTS / "reference/bat-catppuccin-mocha.tmTheme",
    "bat_latte": PORTS / "reference/bat-catppuccin-latte.tmTheme",
    "yazi_mocha": PORTS / "reference/yazi-catppuccin-mocha-flavor.toml",
    "btop_mocha": PORTS / "reference/btop-catppuccin-mocha.theme",
    "btop_latte": PORTS / "reference/btop-catppuccin-latte.theme",
    "ohmyposh": PORTS / "reference/ohmyposh-catppuccin-mocha.omp.json",
    # kitty y ghdash NO llevan entrada aquí: generan directo por rol (sin
    # leer ninguna plantilla) desde siempre. lazygit y herdr tampoco: desde
    # el fix del issue #7 (2026-07-26) generan directo por rol
    # (lazygit_theme/herdr_theme), sin leer ningún config vivo — ver
    # docstring del módulo.
}


# --------------------------------------------------------------------------
# EMIT_PROFILE — genera + valida todos los ports de UN perfil (paleta dark +
# paleta light). slug: sufijo de archivo ("" default, "-deutan" perfil CVD
# futuro). label: sufijo legible (""  default, " Deutan" perfil CVD futuro).
# Con el perfil default (slug="", label="", dark_pal=ROOIBOS,
# light_pal=MANZANILLA) produce EXACTAMENTE los mismos bytes que el main()
# monolítico previo al refactor de este archivo.
# --------------------------------------------------------------------------
def emit_profile(slug, label, dark_pal, light_pal):
    dark_label, light_label = f"Rooibos{label}", f"Manzanilla{label}"

    allowed_dark = (
        {h(v) for v in dark_pal["colors"].values()}
        | {h(v) for v in dark_pal["ansi"]["normal"].values()}
        | {h(v) for v in dark_pal["ansi"]["bright"].values()}
    )
    allowed_light = (
        {h(v) for v in light_pal["colors"].values()}
        | {h(v) for v in light_pal["ansi"]["normal"].values()}
        | {h(v) for v in light_pal["ansi"]["bright"].values()}
    )
    allowed_both = allowed_dark | allowed_light

    # ---------------- kitty ----------------
    write(OUT / f"kitty/ocular-rooibos{slug}.conf", kitty_conf(dark_label, dark_pal))
    write(OUT / f"kitty/ocular-manzanilla{slug}.conf", kitty_conf(light_label, light_pal))

    # ---------------- ghostty ----------------
    write(OUT / f"ghostty/ocular-rooibos{slug}", ghostty_theme(dark_label, dark_pal))
    write(OUT / f"ghostty/ocular-manzanilla{slug}", ghostty_theme(light_label, light_pal))

    # ---------------- bat ----------------
    mocha_text = REF["bat_mocha"].read_text()
    latte_text = REF["bat_latte"].read_text()
    dark_bat = bat_tmtheme(
        mocha_text, HEX2ROLE_MOCHA, dark_pal["colors"], EXC_BAT_MOCHA,
        "Catppuccin Mocha", f"Ocular Rooibos{label}",
        "theme.dark.catppuccin-mocha", f"theme.dark.ocular-rooibos{slug}",
    )
    light_bat = bat_tmtheme(
        latte_text, HEX2ROLE_LATTE, light_pal["colors"], EXC_BAT_LATTE,
        "Catppuccin Latte", f"Ocular Manzanilla{label}",
        "theme.light.catppuccin-latte", f"theme.light.ocular-manzanilla{slug}",
    )
    write(OUT / f"bat/Ocular Rooibos{label}.tmTheme", dark_bat)
    write(OUT / f"bat/Ocular Manzanilla{label}.tmTheme", light_bat)

    # ---------------- yazi (flavor.toml + tmtheme.xml reusado de bat) ----------------
    yazi_mocha_text = REF["yazi_mocha"].read_text()
    yazi_dark = substitute_hexes(
        yazi_mocha_text, HEX2ROLE_MOCHA, dark_pal["colors"],
        keep=GLOBAL_KEEP, quoted=True,
    )
    # DESVIACIÓN: no existe un flavor catppuccin-latte.yazi instalado localmente
    # (fleet dark-only) — se deriva manzanilla desde el
    # MISMO flavor.toml Mocha (mapa hex->rol Mocha), igual que oh-my-posh.
    yazi_light = substitute_hexes(
        yazi_mocha_text, HEX2ROLE_MOCHA, light_pal["colors"],
        keep=GLOBAL_KEEP, quoted=True,
    )
    # EXCEPCIÓN post-sustitución (audit 2026-07-26): el mapeo genérico por rol
    # deja [indicator] con pares equivocados en AMBOS modos — parent/preview
    # heredan base/text (bg=text da una barra casi negra en Manzanilla, donde
    # "text" es oscuro) y current hereda mauve (chrome morado que no calza con
    # la identidad del acento). Se sobreescriben con los roles APCA correctos:
    # parent/preview = highlight neutro sutil (fg=text/bg=surface1), current =
    # identidad cálida del acento (fg=base/bg=peach). Y status.progress_error
    # (yellow sobre red, Lc=0) -> fg=base sobre bg=red, mismo patrón que los
    # chips count_* de arriba (fg=base/bg=acento).
    for name, P in (("rooibos", dark_pal), ("manzanilla", light_pal)):
        c = P["colors"]
        text = yazi_dark if name == "rooibos" else yazi_light
        text = re.sub(
            r'parent = \{ fg = "#[0-9a-fA-F]{6}", bg = "#[0-9a-fA-F]{6}" \}',
            f'parent = {{ fg = "{c["text"]}", bg = "{c["surface1"]}" }}',
            text,
        )
        text = re.sub(
            r'current = \{ fg = "#[0-9a-fA-F]{6}", bg = "#[0-9a-fA-F]{6}" \}',
            f'current = {{ fg = "{c["base"]}", bg = "{c["peach"]}" }}',
            text,
        )
        text = re.sub(
            r'preview = \{ fg = "#[0-9a-fA-F]{6}", bg = "#[0-9a-fA-F]{6}" \}',
            f'preview = {{ fg = "{c["text"]}", bg = "{c["surface1"]}" }}',
            text,
        )
        text = re.sub(
            r'progress_error(\s*)= \{ fg = "#[0-9a-fA-F]{6}", bg = "#[0-9a-fA-F]{6}" \}',
            rf'progress_error\1= {{ fg = "{c["base"]}", bg = "{c["red"]}" }}',
            text,
        )
        if name == "rooibos":
            yazi_dark = text
        else:
            yazi_light = text
    write(OUT / f"yazi/ocular-rooibos{slug}.yazi/flavor.toml", yazi_dark)
    write(OUT / f"yazi/ocular-manzanilla{slug}.yazi/flavor.toml", yazi_light)
    write(OUT / f"yazi/ocular-rooibos{slug}.yazi/tmtheme.xml", dark_bat)
    write(OUT / f"yazi/ocular-manzanilla{slug}.yazi/tmtheme.xml", light_bat)

    # ---------------- lazygit (generación directa por rol — fix issue #7,
    # ver lazygit_theme() para el mapeo campo->rol) ----------------
    write(OUT / f"lazygit/ocular-rooibos{slug}.yml", lazygit_theme(dark_label, dark_pal))
    write(OUT / f"lazygit/ocular-manzanilla{slug}.yml", lazygit_theme(light_label, light_pal))

    # ---------------- btop (archivo completo) ----------------
    btop_mocha_text = REF["btop_mocha"].read_text()
    btop_latte_text = REF["btop_latte"].read_text()
    write(OUT / f"btop/ocular-rooibos{slug}.theme",
          substitute_hexes(btop_mocha_text, HEX2ROLE_MOCHA, dark_pal["colors"], quoted=True))
    write(OUT / f"btop/ocular-manzanilla{slug}.theme",
          substitute_hexes(btop_latte_text, HEX2ROLE_LATTE, light_pal["colors"], quoted=True))

    # ---------------- tmux (generación directa) ----------------
    write(OUT / f"tmux/ocular-rooibos{slug}.tmuxtheme", tmux_theme(dark_label, dark_pal))
    write(OUT / f"tmux/ocular-manzanilla{slug}.tmuxtheme", tmux_theme(light_label, light_pal))

    # ---------------- gh-dash (solo bloque theme:, generación directa por
    # rol semántico — NO sustitución del legado; ver gh_dash_theme()) ----------------
    write(OUT / f"gh-dash/ocular-rooibos{slug}.yml", gh_dash_theme(dark_label, dark_pal))
    write(OUT / f"gh-dash/ocular-manzanilla{slug}.yml", gh_dash_theme(light_label, light_pal))

    # ---------------- oh-my-posh ----------------
    # Override de identidad (2026-07-26, feedback del usuario): el prompt es UI
    # PERSISTENTE (siempre en pantalla) — lleva la familia FIRMA cálida del
    # theme, no los acentos fríos que heredaba del mapeo Mocha original.
    # path: pink -> peach (misma firma que el marco activo de herdr);
    # rama: lavender -> mauve (mismo rol que la cápsula de sesión de tmux).
    # Los acentos fríos quedan para contenido/sintaxis, donde el hue categoriza.
    def omp_colors(palette):
        c = dict(palette["colors"])
        c["pink"] = c["peach"]
        c["lavender"] = c["mauve"]
        return c

    omp_text = REF["ohmyposh"].read_text()
    write(OUT / f"ohmyposh/ocular-rooibos{slug}.omp.json",
          substitute_hexes(omp_text, HEX2ROLE_MOCHA, omp_colors(dark_pal), exceptions=EXC_OMP, quoted=True))
    write(OUT / f"ohmyposh/ocular-manzanilla{slug}.omp.json",
          substitute_hexes(omp_text, HEX2ROLE_MOCHA, omp_colors(light_pal), exceptions=EXC_OMP, quoted=True))

    # ---------------- statusline (generación directa) ----------------
    write(OUT / f"statusline/ocular-rooibos{slug}.sh", statusline_sh(dark_label, dark_pal))
    write(OUT / f"statusline/ocular-manzanilla{slug}.sh", statusline_sh(light_label, light_pal))

    # ---------------- ccmax (generación directa) ----------------
    write(OUT / f"ccmax/ocular-rooibos{slug}.sh", ccmax_sh(dark_label, dark_pal))
    write(OUT / f"ccmax/ocular-manzanilla{slug}.sh", ccmax_sh(light_label, light_pal))

    # ---------------- herdr (generación directa por rol — fix issue #7; ver
    # herdr_theme() para el mapeo campo->rol y el override accent=peach) ----------------
    write(OUT / f"herdr/ocular-rooibos{slug}.toml", herdr_theme(dark_label, dark_pal))
    write(OUT / f"herdr/ocular-manzanilla{slug}.toml", herdr_theme(light_label, light_pal))

    # ---------------- claude code (theme custom, solo tokens de subagentes) --
    write(OUT / f"claude/ocular-rooibos{slug}.json",
          json.dumps(claude_theme("dark", dark_pal), indent=2, ensure_ascii=False) + "\n")
    write(OUT / f"claude/ocular-manzanilla{slug}.json",
          json.dumps(claude_theme("light", light_pal), indent=2, ensure_ascii=False) + "\n")

    # ---------------- nvim ----------------
    write(OUT / f"nvim/ocular{slug}.lua", nvim_lua(dark_pal, light_pal))

    # ---------------- vscode ----------------
    write(OUT / f"vscode/ocular-rooibos{slug}-color-theme.json",
          json.dumps(vscode_theme("dark", dark_label, dark_pal), indent=2, ensure_ascii=False) + "\n")
    write(OUT / f"vscode/ocular-manzanilla{slug}-color-theme.json",
          json.dumps(vscode_theme("light", light_label, light_pal), indent=2, ensure_ascii=False) + "\n")

    # ---------------- chrome (modo desarrollador) ----------------
    write(OUT / f"chrome/ocular-rooibos{slug}/manifest.json",
          json.dumps(chrome_manifest(dark_label, "dark", dark_pal), indent=2, ensure_ascii=False) + "\n")
    write(OUT / f"chrome/ocular-manzanilla{slug}/manifest.json",
          json.dumps(chrome_manifest(light_label, "light", light_pal), indent=2, ensure_ascii=False) + "\n")
    write(OUT / "chrome/README.md", CHROME_README)

    # ---------------- slack (README con custom theme, generación directa) --
    # No se escribe aquí: es un archivo compartido entre perfiles, ver
    # SLACK_SECTIONS/slack_readme() arriba y el ensamblado final en main().
    SLACK_SECTIONS.append(slack_readme_section(dark_pal, light_pal, dark_label, light_label))

    # ---------------- delta (feature file propio, generación directa por rol
    # + mezcla OKLab — ver delta_theme()/mix_oklab arriba) ----------------
    write(OUT / f"delta/ocular-rooibos{slug}.gitconfig", delta_theme(dark_label, dark_pal))
    write(OUT / f"delta/ocular-manzanilla{slug}.gitconfig", delta_theme(light_label, light_pal))
    write(OUT / "delta/README.md", DELTA_README)

    # ------------------------------------------------------------------
    # VALIDACIÓN
    # ------------------------------------------------------------------
    pairs = [
        ("kitty", OUT / f"kitty/ocular-rooibos{slug}.conf", OUT / f"kitty/ocular-manzanilla{slug}.conf", "bare", "text"),
        ("ghostty", OUT / f"ghostty/ocular-rooibos{slug}", OUT / f"ghostty/ocular-manzanilla{slug}", "bare", "text"),
        ("bat", OUT / f"bat/Ocular Rooibos{label}.tmTheme", OUT / f"bat/Ocular Manzanilla{label}.tmTheme", "bare", "xml"),
        ("yazi-flavor", OUT / f"yazi/ocular-rooibos{slug}.yazi/flavor.toml", OUT / f"yazi/ocular-manzanilla{slug}.yazi/flavor.toml", "quoted", "toml"),
        ("yazi-tmtheme", OUT / f"yazi/ocular-rooibos{slug}.yazi/tmtheme.xml", OUT / f"yazi/ocular-manzanilla{slug}.yazi/tmtheme.xml", "bare", "xml"),
        ("lazygit", OUT / f"lazygit/ocular-rooibos{slug}.yml", OUT / f"lazygit/ocular-manzanilla{slug}.yml", "quoted", "text"),
        ("btop", OUT / f"btop/ocular-rooibos{slug}.theme", OUT / f"btop/ocular-manzanilla{slug}.theme", "quoted", "text"),
        ("tmux", OUT / f"tmux/ocular-rooibos{slug}.tmuxtheme", OUT / f"tmux/ocular-manzanilla{slug}.tmuxtheme", "bare", "text"),
        ("gh-dash", OUT / f"gh-dash/ocular-rooibos{slug}.yml", OUT / f"gh-dash/ocular-manzanilla{slug}.yml", "quoted", "text"),
        ("ohmyposh", OUT / f"ohmyposh/ocular-rooibos{slug}.omp.json", OUT / f"ohmyposh/ocular-manzanilla{slug}.omp.json", "quoted", "json"),
        ("statusline", OUT / f"statusline/ocular-rooibos{slug}.sh", OUT / f"statusline/ocular-manzanilla{slug}.sh", "bare", "bash"),
        ("herdr", OUT / f"herdr/ocular-rooibos{slug}.toml", OUT / f"herdr/ocular-manzanilla{slug}.toml", "quoted", "toml"),
        ("vscode", OUT / f"vscode/ocular-rooibos{slug}-color-theme.json", OUT / f"vscode/ocular-manzanilla{slug}-color-theme.json", "quoted", "json"),
        ("claude", OUT / f"claude/ocular-rooibos{slug}.json", OUT / f"claude/ocular-manzanilla{slug}.json", "quoted", "json"),
    ]

    for name, rpath, mpath, mode, kind in pairs:
        for p, allowed in ((rpath, allowed_dark), (mpath, allowed_light)):
            exists = p.exists()
            record("exists", p, exists)
            if not exists:
                continue
            audit_hex_file(name, p, allowed, quoted=(mode == "quoted"))
            if kind == "xml":
                validate_xml(p)
            elif kind == "json":
                validate_json(p)
            elif kind == "toml":
                validate_toml(p)
            elif kind == "bash":
                validate_bash(p)

    # nvim.lua mezcla ambas paletas en un solo archivo -> allowed = unión
    nvim_path = OUT / f"nvim/ocular{slug}.lua"
    record("exists", nvim_path, nvim_path.exists())
    audit_hex_file("nvim", nvim_path, allowed_both, quoted=True)

    # slack/README.md: validación diferida a main() (archivo compartido entre
    # perfiles, se escribe una sola vez después de emitir todos).

    # chrome: JSON parse + membresía RGB->hex propia (no usa el motor de #hex)
    for p, allowed in (
        (OUT / f"chrome/ocular-rooibos{slug}/manifest.json", allowed_dark),
        (OUT / f"chrome/ocular-manzanilla{slug}/manifest.json", allowed_light),
    ):
        record("exists", p, p.exists())
        validate_json(p)
        validate_chrome_rgb(p, allowed)

    # ccmax: bash -n + auditoría RGB->hex (mismo patrón que statusline, pero
    # con check explícito de las secuencias ANSI truecolor, no solo #hex)
    for p, allowed in (
        (OUT / f"ccmax/ocular-rooibos{slug}.sh", allowed_dark),
        (OUT / f"ccmax/ocular-manzanilla{slug}.sh", allowed_light),
    ):
        record("exists", p, p.exists())
        validate_bash(p)
        audit_ansi_rgb_file(p, allowed)

    # delta: gitconfig con hex derivados por mezcla OKLab (plus/plus-emph/
    # minus/minus-emph) que NO pertenecen a la paleta base -> allowed =
    # paleta del modo + los 4 derivados de ESTE generador (ver delta_theme()/
    # mix_oklab arriba; se agregan como "derivados válidos" en vez de tocar
    # el set allowed_* del perfil, que representa la paleta canónica).
    for p, allowed in (
        (OUT / f"delta/ocular-rooibos{slug}.gitconfig",
         allowed_dark | {h(x) for x in delta_diff_tints(dark_pal)}),
        (OUT / f"delta/ocular-manzanilla{slug}.gitconfig",
         allowed_light | {h(x) for x in delta_diff_tints(light_pal)}),
    ):
        exists = p.exists()
        record("exists", p, exists)
        if not exists:
            continue
        audit_hex_file("delta", p, allowed, quoted=True)

    # pares fg/bg emitidos (guarda APCA permanente, ver EMITTED_PAIRS arriba)
    check_emitted_pairs()
    # gate APCA obligatorio de delta (fondos derivados, ver check_delta_pairs)
    check_delta_pairs()


# --------------------------------------------------------------------------
# MAIN — orquesta la emisión de cada perfil + el reporte final. Perfil
# default (Rooibos/Manzanilla) + perfil deutan (Rooibos Deutan/Manzanilla
# Deutan, CVD-safe con luminancias desiguales — ver SCIENCE.md).
# --------------------------------------------------------------------------
PROFILES = [
    ("", "", ROOIBOS, MANZANILLA),
    ("-deutan", " Deutan", ROOIBOS_DEUTAN, MANZANILLA_DEUTAN),
]


def main():
    missing = [str(p) for p in REF.values() if not p.exists()]
    if missing:
        print("FALTAN referencias locales:", missing, file=sys.stderr)
        sys.exit(1)

    allowed_slack = set()
    for slug, label, dark_pal, light_pal in PROFILES:
        emit_profile(slug, label, dark_pal, light_pal)
        allowed_slack |= (
            {h(v) for v in dark_pal["colors"].values()}
            | {h(v) for v in light_pal["colors"].values()}
        )

    # slack/README.md: archivo compartido entre perfiles, se escribe UNA vez
    # con las secciones de TODOS los perfiles emitidos (ver SLACK_SECTIONS).
    slack_path = OUT / "slack/README.md"
    write(slack_path, slack_readme(SLACK_SECTIONS))
    record("exists", slack_path, slack_path.exists())
    audit_hex_file("slack", slack_path, allowed_slack, quoted=False)
    # gate APCA obligatorio del custom theme de Slack (ver check_slack_pairs)
    check_slack_pairs()

    # ------------------------------------------------------------------
    # Imprimir reporte
    # ------------------------------------------------------------------
    fails = [r for r in REPORT if not r[2]]
    print(f"{'CHECK':<12}{'ARCHIVO':<55}{'OK':<5}DETALLE")
    for kind, path, ok, detail in REPORT:
        print(f"{kind:<12}{path:<55}{'SI' if ok else 'NO':<5}{detail}")
    print()
    if fails:
        print(f"FALLÓ: {len(fails)} check(s) de {len(REPORT)}")
        sys.exit(1)
    print(f"OK: {len(REPORT)} checks, 0 fallos.")


if __name__ == "__main__":
    main()
