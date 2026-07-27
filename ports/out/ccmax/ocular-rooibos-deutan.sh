#!/usr/bin/env bash
# Ocular Rooibos Deutan — fragmento de color para ccmax
# Mismos nombres C_* que espera el script consumidor externo (ccmax del
# autor, bloque '# --- Catppuccin Mocha ---'). R y B (reset/bold) quedan
# intactos: no son roles de color, son códigos ANSI de control.

R=$'\e[0m'
B=$'\e[1m'
C_SUB=$'\e[38;2;152;147;141m'       # overlay0
C_SUB1=$'\e[38;2;166;160;153m'      # overlay1
C_MAUVE=$'\e[38;2;228;177;244m'     # mauve
C_LAV=$'\e[38;2;208;203;255m'       # lavender
C_GREEN=$'\e[38;2;165;206;146m'     # green
C_YELLOW=$'\e[38;2;238;205;124m'    # yellow
C_PEACH=$'\e[38;2;254;183;130m'     # peach
C_RED=$'\e[38;2;255;178;177m'      # red
C_TEAL=$'\e[38;2;110;216;208m'      # teal
C_SURF=$'\e[38;2;56;50;43m'      # surface1
