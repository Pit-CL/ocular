#!/usr/bin/env bash
# Ocular Manzanilla Deutan — fragmento de color para ccmax
# Mismos nombres C_* que espera el script consumidor externo (ccmax del
# autor, bloque '# --- Catppuccin Mocha ---'). R y B (reset/bold) quedan
# intactos: no son roles de color, son códigos ANSI de control.

R=$'\e[0m'
B=$'\e[1m'
C_SUB=$'\e[38;2;161;156;148m'       # overlay0
C_SUB1=$'\e[38;2;145;139;132m'      # overlay1
C_MAUVE=$'\e[38;2;130;73;146m'     # mauve
C_LAV=$'\e[38;2;79;68;128m'       # lavender
C_GREEN=$'\e[38;2;63;107;38m'     # green
C_YELLOW=$'\e[38;2;97;74;0m'    # yellow
C_PEACH=$'\e[38;2;140;73;0m'     # peach
C_RED=$'\e[38;2;152;60;65m'      # red
C_TEAL=$'\e[38;2;0;101;97m'      # teal
C_SURF=$'\e[38;2;217;211;201m'      # surface1
