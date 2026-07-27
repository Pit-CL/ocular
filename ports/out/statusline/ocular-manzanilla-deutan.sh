#!/usr/bin/env bash
# Ocular Manzanilla Deutan — fragmento de color para claude-statusline
# Mismos nombres C_* que espera el script consumidor externo (statusline
# del autor). 'source' este archivo en vez del bloque Mocha hardcodeado.
# NO incluye C_PR_OPEN: es el color fijo #42A0FA hardcodeado por gh-dash
# (no sale de ningún theme Catppuccin), así que no se remapea a ningún rol.

R=$'\e[0m'
C_PATH=$'\e[38;2;63;55;45m'          # text
C_SEP=$'\e[38;2;161;156;148m'        # overlay0 (separadores)
C_GIT=$'\e[38;2;130;73;146m'        # mauve    (git limpio)
C_GIT_DIRTY=$'\e[38;2;152;60;65m'  # red      (git sucio)
C_MODEL=$'\e[38;2;63;55;45m'      # text     (modelo)
C_CYAN=$'\e[38;2;0;101;97m'       # teal
C_YELLOW=$'\e[38;2;97;74;0m'      # yellow
C_RED=$'\e[38;2;152;60;65m'        # red
C_GREEN=$'\e[38;2;63;107;38m'       # green
