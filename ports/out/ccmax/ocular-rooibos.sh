#!/usr/bin/env bash
# Ocular Rooibos — fragmento de color para ccmax
# Mismos nombres C_* que espera el script consumidor externo (ccmax del
# autor, bloque '# --- Catppuccin Mocha ---'). R y B (reset/bold) quedan
# intactos: no son roles de color, son códigos ANSI de control.

R=$'\e[0m'
B=$'\e[1m'
C_SUB=$'\e[38;2;152;147;141m'       # overlay0
C_SUB1=$'\e[38;2;166;160;153m'      # overlay1
C_MAUVE=$'\e[38;2;222;183;252m'     # mauve
C_LAV=$'\e[38;2;199;191;251m'       # lavender
C_GREEN=$'\e[38;2;164;211;153m'     # green
C_YELLOW=$'\e[38;2;227;195;114m'    # yellow
C_PEACH=$'\e[38;2;254;183;130m'     # peach
C_RED=$'\e[38;2;255;180;173m'      # red
C_TEAL=$'\e[38;2;112;216;203m'      # teal
C_SURF=$'\e[38;2;56;50;43m'      # surface1
