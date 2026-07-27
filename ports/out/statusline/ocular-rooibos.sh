#!/usr/bin/env bash
# Ocular Rooibos — fragmento de color para claude-statusline
# Mismos nombres C_* que espera el script consumidor externo (statusline
# del autor). 'source' este archivo en vez del bloque Mocha hardcodeado.
# NO incluye C_PR_OPEN: es el color fijo #42A0FA hardcodeado por gh-dash
# (no sale de ningún theme Catppuccin), así que no se remapea a ningún rol.

R=$'\e[0m'
C_PATH=$'\e[38;2;223;217;204m'          # text
C_SEP=$'\e[38;2;152;147;141m'        # overlay0 (separadores)
C_GIT=$'\e[38;2;222;183;252m'        # mauve    (git limpio)
C_GIT_DIRTY=$'\e[38;2;255;180;173m'  # red      (git sucio)
C_MODEL=$'\e[38;2;223;217;204m'      # text     (modelo)
C_CYAN=$'\e[38;2;112;216;203m'       # teal
C_YELLOW=$'\e[38;2;227;195;114m'      # yellow
C_RED=$'\e[38;2;255;180;173m'        # red
C_GREEN=$'\e[38;2;164;211;153m'       # green
