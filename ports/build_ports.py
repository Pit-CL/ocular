#!/usr/bin/env python3
"""
build_ports.py — FASE 1 del rollout de Ocular: genera los ports por app + el
switcher, a partir de palette/rooibos.json (dark) y palette/manzanilla.json
(light), SIN tocar ningún config vivo. Todo se escribe bajo ports/out/.

Dos estrategias según el artefacto:
  1. SUSTITUCIÓN de hex sobre el port oficial Catppuccin instalado localmente
     (bat, yazi, btop, oh-my-posh): se recorre el
     archivo de referencia, cada #hex oficial Mocha/Latte se reconoce por su
     ROL (via palette/catppuccin-oficial.json) y se reemplaza por el hex
     Ocular de ese mismo rol. Preserva estructura, comentarios y campos no
     visitados 1:1.
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
    keyword/control      -> mauve
    string                -> green
    function              -> blue
    number/constant/bool  -> peach
    type/class             -> yellow
    comment                -> overlay2
    variable                -> text
    operator/punctuation    -> sky / subtext0
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
HOME = Path.home()

# --------------------------------------------------------------------------
# Paletas Ocular + oficiales Catppuccin (para reconocer hex por rol)
# --------------------------------------------------------------------------
ROOIBOS = json.loads((ROOT / "palette" / "rooibos.json").read_text())
MANZANILLA = json.loads((ROOT / "palette" / "manzanilla.json").read_text())
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

ALLOWED_ROOIBOS = (
    {h(v) for v in ROOIBOS["colors"].values()}
    | {h(v) for v in ROOIBOS["ansi"]["normal"].values()}
    | {h(v) for v in ROOIBOS["ansi"]["bright"].values()}
)
ALLOWED_MANZANILLA = (
    {h(v) for v in MANZANILLA["colors"].values()}
    | {h(v) for v in MANZANILLA["ansi"]["normal"].values()}
    | {h(v) for v in MANZANILLA["ansi"]["bright"].values()}
)
ALLOWED_BOTH = ALLOWED_ROOIBOS | ALLOWED_MANZANILLA
OFICIAL_ALL_HEX = {h(v) for d in OFICIAL.values() for v in d.values()}

BARE_HEX_RE = re.compile(r"#([0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)")
QUOTED_HEX_RE = re.compile(r"([\"'])#([0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)\1")


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
#       searchingActiveBorderColor / markedBaseCommitBgColor -> yellow
#       optionsTextColor / markedBaseCommitFgColor      -> blue
#       selectedLineBgColor                             -> surface0
#       inactiveViewSelectedLineBgColor                 -> overlay0
#       cherryPickedCommitBgColor                       -> surface1
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
        f"      - '{c['overlay0']}'",
        "    cherryPickedCommitFgColor:",
        f"      - '{c['mauve']}'",
        "    cherryPickedCommitBgColor:",
        f"      - '{c['surface1']}'",
        "    markedBaseCommitFgColor:",
        f"      - '{c['blue']}'",
        "    markedBaseCommitBgColor:",
        f"      - '{c['yellow']}'",
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
# 5) STATUSLINE — fragmento bash con los MISMOS nombres C_* que
#    tools/claude-statusline/statusline-command.sh (líneas 71-94)
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
        "# Mismos nombres C_* que tools/claude-statusline/statusline-command.sh",
        "# (líneas 71-94). 'source' este archivo en vez del bloque Mocha hardcodeado.",
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
# 6b) CCMAX — fragmento con las MISMAS variables C_* que
#     tools/claude-monitor-max/ccmax líneas 83-95 ("# --- Catppuccin Mocha ---")
# --------------------------------------------------------------------------
def ccmax_sh(label, P):
    c = P["colors"]

    def seq(role):
        return hex_to_ansi_seq(c[role])

    return "\n".join([
        "#!/usr/bin/env bash",
        f"# Ocular {label} — fragmento de color para ccmax",
        "# Mismos nombres C_* que tools/claude-monitor-max/ccmax (líneas 83-95,",
        "# bloque '# --- Catppuccin Mocha ---'). R y B (reset/bold) quedan",
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
#       surface_dim  -> overlay0 (bg de la fila seleccionada del sidebar,
#                       decisión conservada del config original — ver comentario)
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
        "# 16 tokens soportados (CustomThemeColors, verificado 2026-07-15). Conserva la",
        "# decisión surface_dim=overlay0 (selección visible del sidebar) del original.",
        "[theme.custom]",
        f'panel_bg = "{c["base"]}"      # base',
        f'surface_dim = "{c["overlay0"]}"   # bg de la fila SELECCIONADA del sidebar (verificado empíricamente',
        "                          # con colores chillones). El mantle oficial (#181825) es más oscuro",
        "                          # que panel_bg y hacía la selección invisible de noche. Se usa el",
        "                          # overlay0 oficial de Mocha: visible de noche y texto claro legible",
        "                          # (~4.6:1). Descartados: morados de Mocha (mauve/lavender, muy claros",
        "                          # para bg), #8839ef mauve de Latte (muy eléctrico), #574b7d custom.",
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
# 6) NVIM — spec lazy.nvim para catppuccin/nvim (API verificada por WebFetch
#    al README oficial: color_overrides + flavour="auto" + background map)
# --------------------------------------------------------------------------
def nvim_lua():
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
        block(ROOIBOS),
        "      },",
        "      latte = {",
        block(MANZANILLA),
        "      },",
        "    },",
        "  },",
        "  config = function(_, opts)",
        '    require("catppuccin").setup(opts)',
        '    vim.cmd.colorscheme("catppuccin")',
        "  end,",
        "}",
        "",
    ])


# --------------------------------------------------------------------------
# 7) VSCODE — misma estructura que vscode_theme() de tools/pyvision-theme/
#    build_v2.py (mismos keys de colors + tokenColors), con el mapeo
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
        "editorBracketHighlight.foreground1": S["yellow"], "editorBracketHighlight.foreground2": S["purple"],
        "editorBracketHighlight.foreground3": S["blue"], "editorBracketHighlight.foreground4": S["green"],
        "editorBracketHighlight.foreground5": S["cyan"], "editorBracketHighlight.foreground6": S["red"],
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

    tokens = [
        tk("Comment", ["comment", "punctuation.definition.comment"], N["muted"], "italic"),
        tk("String", ["string", "string.quoted", "string.template"], S["green"]),
        tk("String escape", ["constant.character.escape"], S["cyan"]),
        tk("Number", ["constant.numeric"], S["orange"]),
        tk("Constant", ["constant.language", "constant.language.boolean", "support.constant"], S["orange"], "bold"),
        tk("Keyword", ["keyword", "storage.type", "storage.modifier", "keyword.control"], S["blue"]),
        tk("Operator", ["keyword.operator", "punctuation.separator.operator"], S["cyan"]),
        tk("Function", ["entity.name.function", "support.function", "meta.function-call.generic"], S["purple"]),
        tk("Decorator", ["meta.decorator", "entity.name.function.decorator", "punctuation.definition.decorator"], S["purple"], "italic"),
        tk("Class / Type", ["entity.name.type", "entity.name.class", "support.class", "support.type", "entity.other.inherited-class"], S["yellow"]),
        tk("Variable", ["variable", "variable.other.readwrite", "meta.definition.variable"], N["text"]),
        tk("Parameter", ["variable.parameter"], S["cyan"]),
        tk("Language variable (this/self)", ["variable.language", "variable.language.this", "variable.parameter.function.language.special.self.python"], S["red"], "italic"),
        tk("Property", ["variable.other.property", "support.variable.property", "meta.object-literal.key", "support.type.property-name"], S["cyan"]),
        tk("JSON / YAML key", ["support.type.property-name.json", "entity.name.tag.yaml", "entity.name.tag"], S["red"]),
        tk("Constant other (enum)", ["variable.other.constant", "variable.other.enummember"], S["orange"]),
        tk("Punctuation", ["punctuation", "meta.brace", "punctuation.separator", "punctuation.terminator"], N["subtle"]),
        tk("Regexp", ["string.regexp"], S["cyan"]),
        tk("Invalid", ["invalid", "invalid.illegal"], S["red"]),
        tk("Markup heading", ["markup.heading", "entity.name.section"], S["red"], "bold"),
        tk("Markup bold", ["markup.bold"], S["yellow"], "bold"),
        tk("Markup italic", ["markup.italic"], S["purple"], "italic"),
        tk("Markup code", ["markup.inline.raw", "markup.fenced_code.block"], S["green"]),
        tk("Markup link", ["markup.underline.link"], S["blue"], "underline"),
        tk("Tag", ["entity.name.tag.html", "entity.name.tag.tsx"], S["red"]),
        tk("Attribute", ["entity.other.attribute-name"], S["orange"]),
        tk("CSS value/unit", ["support.constant.property-value", "support.constant.font-name", "keyword.other.unit", "constant.numeric.css"], S["orange"]),
        tk("JSX component", ["support.class.component"], S["yellow"]),
    ]
    semantic = {
        "function": S["purple"], "method": S["purple"], "class": S["yellow"], "type": S["yellow"],
        "interface": S["yellow"], "enum": S["yellow"], "parameter": S["cyan"],
        "variable": N["text"], "variable.readonly": S["orange"], "property": S["cyan"],
        "enumMember": S["orange"], "decorator": S["purple"], "namespace": S["yellow"],
        "selfParameter": S["red"], "*.declaration": {"bold": True},
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

MV3 theme (`theme.colors` in decimal RGB), same structure as
`tools/chrome-catppuccin-mocha/manifest.json` in the Rollitos/Claude
workspace.

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
# MAIN — orquesta generación + validación de cada artefacto
# --------------------------------------------------------------------------
def main():
    ref = {
        "kitty": HOME / ".config/kitty/dark-theme.auto.conf",
        "bat_mocha": HOME / ".config/bat/themes/Catppuccin Mocha.tmTheme",
        "bat_latte": HOME / ".config/catppuccin/bat/themes/Catppuccin Latte.tmTheme",
        "yazi_mocha": HOME / ".config/yazi/flavors/catppuccin-mocha.yazi/flavor.toml",
        "btop_mocha": HOME / ".config/btop/themes/catppuccin_mocha.theme",
        "btop_latte": HOME / ".config/catppuccin/btop/themes/catppuccin_latte.theme",
        "ghdash": HOME / ".config/gh-dash/config.yml",
        "ohmyposh": HOME / ".config/ohmyposh/catppuccin_mocha.omp.json",
        # lazygit y herdr NO llevan entrada aquí: desde el fix del issue #7
        # (2026-07-26) generan directo por rol (lazygit_theme/herdr_theme),
        # sin leer ningún config vivo — ver docstring del módulo.
    }
    missing = [str(p) for p in ref.values() if not p.exists()]
    if missing:
        print("FALTAN referencias locales:", missing, file=sys.stderr)
        sys.exit(1)

    # ---------------- kitty ----------------
    write(OUT / "kitty/ocular-rooibos.conf", kitty_conf("Rooibos", ROOIBOS))
    write(OUT / "kitty/ocular-manzanilla.conf", kitty_conf("Manzanilla", MANZANILLA))

    # ---------------- ghostty ----------------
    write(OUT / "ghostty/ocular-rooibos", ghostty_theme("Rooibos", ROOIBOS))
    write(OUT / "ghostty/ocular-manzanilla", ghostty_theme("Manzanilla", MANZANILLA))

    # ---------------- bat ----------------
    mocha_text = ref["bat_mocha"].read_text()
    latte_text = ref["bat_latte"].read_text()
    rooibos_bat = bat_tmtheme(
        mocha_text, HEX2ROLE_MOCHA, ROOIBOS["colors"], EXC_BAT_MOCHA,
        "Catppuccin Mocha", "Ocular Rooibos",
        "theme.dark.catppuccin-mocha", "theme.dark.ocular-rooibos",
    )
    manzanilla_bat = bat_tmtheme(
        latte_text, HEX2ROLE_LATTE, MANZANILLA["colors"], EXC_BAT_LATTE,
        "Catppuccin Latte", "Ocular Manzanilla",
        "theme.light.catppuccin-latte", "theme.light.ocular-manzanilla",
    )
    write(OUT / "bat/Ocular Rooibos.tmTheme", rooibos_bat)
    write(OUT / "bat/Ocular Manzanilla.tmTheme", manzanilla_bat)

    # ---------------- yazi (flavor.toml + tmtheme.xml reusado de bat) ----------------
    yazi_mocha_text = ref["yazi_mocha"].read_text()
    yazi_rooibos = substitute_hexes(
        yazi_mocha_text, HEX2ROLE_MOCHA, ROOIBOS["colors"],
        keep=GLOBAL_KEEP, quoted=True,
    )
    # DESVIACIÓN: no existe un flavor catppuccin-latte.yazi instalado localmente
    # (fleet dark-only, ver private/CATASTRO.md) — se deriva manzanilla desde el
    # MISMO flavor.toml Mocha (mapa hex->rol Mocha), igual que oh-my-posh.
    yazi_manzanilla = substitute_hexes(
        yazi_mocha_text, HEX2ROLE_MOCHA, MANZANILLA["colors"],
        keep=GLOBAL_KEEP, quoted=True,
    )
    write(OUT / "yazi/ocular-rooibos.yazi/flavor.toml", yazi_rooibos)
    write(OUT / "yazi/ocular-manzanilla.yazi/flavor.toml", yazi_manzanilla)
    write(OUT / "yazi/ocular-rooibos.yazi/tmtheme.xml", rooibos_bat)
    write(OUT / "yazi/ocular-manzanilla.yazi/tmtheme.xml", manzanilla_bat)

    # ---------------- lazygit (generación directa por rol — fix issue #7,
    # ver lazygit_theme() para el mapeo campo->rol) ----------------
    write(OUT / "lazygit/ocular-rooibos.yml", lazygit_theme("Rooibos", ROOIBOS))
    write(OUT / "lazygit/ocular-manzanilla.yml", lazygit_theme("Manzanilla", MANZANILLA))

    # ---------------- btop (archivo completo) ----------------
    btop_mocha_text = ref["btop_mocha"].read_text()
    btop_latte_text = ref["btop_latte"].read_text()
    write(OUT / "btop/ocular-rooibos.theme",
          substitute_hexes(btop_mocha_text, HEX2ROLE_MOCHA, ROOIBOS["colors"], quoted=True))
    write(OUT / "btop/ocular-manzanilla.theme",
          substitute_hexes(btop_latte_text, HEX2ROLE_LATTE, MANZANILLA["colors"], quoted=True))

    # ---------------- tmux (generación directa) ----------------
    write(OUT / "tmux/ocular-rooibos.tmuxtheme", tmux_theme("Rooibos", ROOIBOS))
    write(OUT / "tmux/ocular-manzanilla.tmuxtheme", tmux_theme("Manzanilla", MANZANILLA))

    # ---------------- gh-dash (solo bloque theme:, generación directa por
    # rol semántico — NO sustitución del legado; ver gh_dash_theme()) ----------------
    write(OUT / "gh-dash/ocular-rooibos.yml", gh_dash_theme("Rooibos", ROOIBOS))
    write(OUT / "gh-dash/ocular-manzanilla.yml", gh_dash_theme("Manzanilla", MANZANILLA))

    # ---------------- oh-my-posh ----------------
    omp_text = ref["ohmyposh"].read_text()
    write(OUT / "ohmyposh/ocular-rooibos.omp.json",
          substitute_hexes(omp_text, HEX2ROLE_MOCHA, ROOIBOS["colors"], exceptions=EXC_OMP, quoted=True))
    write(OUT / "ohmyposh/ocular-manzanilla.omp.json",
          substitute_hexes(omp_text, HEX2ROLE_MOCHA, MANZANILLA["colors"], exceptions=EXC_OMP, quoted=True))

    # ---------------- statusline (generación directa) ----------------
    write(OUT / "statusline/ocular-rooibos.sh", statusline_sh("Rooibos", ROOIBOS))
    write(OUT / "statusline/ocular-manzanilla.sh", statusline_sh("Manzanilla", MANZANILLA))

    # ---------------- ccmax (generación directa) ----------------
    write(OUT / "ccmax/ocular-rooibos.sh", ccmax_sh("Rooibos", ROOIBOS))
    write(OUT / "ccmax/ocular-manzanilla.sh", ccmax_sh("Manzanilla", MANZANILLA))

    # ---------------- herdr (generación directa por rol — fix issue #7; ver
    # herdr_theme() para el mapeo campo->rol y el override accent=peach) ----------------
    write(OUT / "herdr/ocular-rooibos.toml", herdr_theme("Rooibos", ROOIBOS))
    write(OUT / "herdr/ocular-manzanilla.toml", herdr_theme("Manzanilla", MANZANILLA))

    # ---------------- nvim ----------------
    write(OUT / "nvim/ocular.lua", nvim_lua())

    # ---------------- vscode ----------------
    write(OUT / "vscode/ocular-rooibos-color-theme.json",
          json.dumps(vscode_theme("dark", "Rooibos", ROOIBOS), indent=2, ensure_ascii=False) + "\n")
    write(OUT / "vscode/ocular-manzanilla-color-theme.json",
          json.dumps(vscode_theme("light", "Manzanilla", MANZANILLA), indent=2, ensure_ascii=False) + "\n")

    # ---------------- chrome (modo desarrollador) ----------------
    write(OUT / "chrome/ocular-rooibos/manifest.json",
          json.dumps(chrome_manifest("Rooibos", "dark", ROOIBOS), indent=2, ensure_ascii=False) + "\n")
    write(OUT / "chrome/ocular-manzanilla/manifest.json",
          json.dumps(chrome_manifest("Manzanilla", "light", MANZANILLA), indent=2, ensure_ascii=False) + "\n")
    write(OUT / "chrome/README.md", CHROME_README)

    # ---------------- delta ----------------
    write(OUT / "delta/README.md", (
        "# delta — Ocular\n\n"
        "delta has no theme of its own: it reuses bat's tmTheme by name\n"
        "(`git config --global delta.syntax-theme`).\n\n"
        "```\n"
        'git config --global delta.syntax-theme "Ocular Rooibos"     # dark\n'
        'git config --global delta.syntax-theme "Ocular Manzanilla" # light\n'
        "```\n\n"
        "Requires `ports/out/bat/Ocular Rooibos.tmTheme` and `Ocular\n"
        "Manzanilla.tmTheme` to be installed in bat's theme dir (`bat\n"
        "--config-dir`/themes, with `bat cache --build` after copying them) —\n"
        "`ocular-switch` takes care of both steps.\n"
    ))

    # ------------------------------------------------------------------
    # VALIDACIÓN
    # ------------------------------------------------------------------
    pairs = [
        ("kitty", OUT / "kitty/ocular-rooibos.conf", OUT / "kitty/ocular-manzanilla.conf", "bare", "text"),
        ("ghostty", OUT / "ghostty/ocular-rooibos", OUT / "ghostty/ocular-manzanilla", "bare", "text"),
        ("bat", OUT / "bat/Ocular Rooibos.tmTheme", OUT / "bat/Ocular Manzanilla.tmTheme", "bare", "xml"),
        ("yazi-flavor", OUT / "yazi/ocular-rooibos.yazi/flavor.toml", OUT / "yazi/ocular-manzanilla.yazi/flavor.toml", "quoted", "toml"),
        ("yazi-tmtheme", OUT / "yazi/ocular-rooibos.yazi/tmtheme.xml", OUT / "yazi/ocular-manzanilla.yazi/tmtheme.xml", "bare", "xml"),
        ("lazygit", OUT / "lazygit/ocular-rooibos.yml", OUT / "lazygit/ocular-manzanilla.yml", "quoted", "text"),
        ("btop", OUT / "btop/ocular-rooibos.theme", OUT / "btop/ocular-manzanilla.theme", "quoted", "text"),
        ("tmux", OUT / "tmux/ocular-rooibos.tmuxtheme", OUT / "tmux/ocular-manzanilla.tmuxtheme", "bare", "text"),
        ("gh-dash", OUT / "gh-dash/ocular-rooibos.yml", OUT / "gh-dash/ocular-manzanilla.yml", "quoted", "text"),
        ("ohmyposh", OUT / "ohmyposh/ocular-rooibos.omp.json", OUT / "ohmyposh/ocular-manzanilla.omp.json", "quoted", "json"),
        ("statusline", OUT / "statusline/ocular-rooibos.sh", OUT / "statusline/ocular-manzanilla.sh", "bare", "bash"),
        ("herdr", OUT / "herdr/ocular-rooibos.toml", OUT / "herdr/ocular-manzanilla.toml", "quoted", "toml"),
        ("vscode", OUT / "vscode/ocular-rooibos-color-theme.json", OUT / "vscode/ocular-manzanilla-color-theme.json", "quoted", "json"),
    ]

    for name, rpath, mpath, mode, kind in pairs:
        for p, allowed in ((rpath, ALLOWED_ROOIBOS), (mpath, ALLOWED_MANZANILLA)):
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
    nvim_path = OUT / "nvim/ocular.lua"
    record("exists", nvim_path, nvim_path.exists())
    audit_hex_file("nvim", nvim_path, ALLOWED_BOTH, quoted=True)

    # chrome: JSON parse + membresía RGB->hex propia (no usa el motor de #hex)
    for p, allowed in (
        (OUT / "chrome/ocular-rooibos/manifest.json", ALLOWED_ROOIBOS),
        (OUT / "chrome/ocular-manzanilla/manifest.json", ALLOWED_MANZANILLA),
    ):
        record("exists", p, p.exists())
        validate_json(p)
        validate_chrome_rgb(p, allowed)

    # ccmax: bash -n + auditoría RGB->hex (mismo patrón que statusline, pero
    # con check explícito de las secuencias ANSI truecolor, no solo #hex)
    for p, allowed in (
        (OUT / "ccmax/ocular-rooibos.sh", ALLOWED_ROOIBOS),
        (OUT / "ccmax/ocular-manzanilla.sh", ALLOWED_MANZANILLA),
    ):
        record("exists", p, p.exists())
        validate_bash(p)
        audit_ansi_rgb_file(p, allowed)

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
