#!/usr/bin/env bash
# Ocular Rooibos — fragmento de color para ccmax
# Mismos nombres C_* que espera el script consumidor externo (ccmax del
# autor, bloque '# --- Catppuccin Mocha ---'). R y B (reset/bold) quedan
# intactos: no son roles de color, son códigos ANSI de control.

R=$'\e[0m'
B=$'\e[1m'
C_SUB=$'\e[38;2;152;147;141m'       # overlay0
C_SUB1=$'\e[38;2;166;160;153m'      # overlay1
C_MAUVE=$'\e[38;2;217;185;255m'     # mauve
C_LAV=$'\e[38;2;186;196;255m'       # lavender
C_GREEN=$'\e[38;2;153;214;148m'     # green
C_YELLOW=$'\e[38;2;219;196;146m'    # yellow
C_PEACH=$'\e[38;2;254;183;138m'     # peach
C_RED=$'\e[38;2;255;177;196m'      # red
C_TEAL=$'\e[38;2;135;212;200m'      # teal
C_SURF=$'\e[38;2;56;50;43m'      # surface1
