#!/usr/bin/env bash
# Ocular Rooibos Deutan — fragmento de color para claude-statusline
# Mismos nombres C_* que espera el script consumidor externo (statusline
# del autor). 'source' este archivo en vez del bloque Mocha hardcodeado.
# NO incluye C_PR_OPEN: es el color fijo #42A0FA hardcodeado por gh-dash
# (no sale de ningún theme Catppuccin), así que no se remapea a ningún rol.

R=$'\e[0m'
C_PATH=$'\e[38;2;223;217;204m'          # text
C_SEP=$'\e[38;2;152;147;141m'        # overlay0 (separadores)
C_GIT=$'\e[38;2;228;177;244m'        # mauve    (git limpio)
C_GIT_DIRTY=$'\e[38;2;255;178;177m'  # red      (git sucio)
C_MODEL=$'\e[38;2;223;217;204m'      # text     (modelo)
C_CYAN=$'\e[38;2;110;216;208m'       # teal
C_YELLOW=$'\e[38;2;238;205;124m'      # yellow
C_RED=$'\e[38;2;255;178;177m'        # red
C_GREEN=$'\e[38;2;165;206;146m'       # green
