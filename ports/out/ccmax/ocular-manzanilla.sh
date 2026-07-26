#!/usr/bin/env bash
# Ocular Manzanilla — fragmento de color para ccmax
# Mismos nombres C_* que espera el script consumidor externo (ccmax del
# autor, bloque '# --- Catppuccin Mocha ---'). R y B (reset/bold) quedan
# intactos: no son roles de color, son códigos ANSI de control.

R=$'\e[0m'
B=$'\e[1m'
C_SUB=$'\e[38;2;161;156;148m'       # overlay0
C_SUB1=$'\e[38;2;145;139;132m'      # overlay1
C_MAUVE=$'\e[38;2;104;76;158m'     # mauve
C_LAV=$'\e[38;2;70;85;165m'       # lavender
C_GREEN=$'\e[38;2;39;104;25m'     # green
C_YELLOW=$'\e[38;2;131;80;0m'    # yellow
C_PEACH=$'\e[38;2;152;63;21m'     # peach
C_RED=$'\e[38;2;155;57;63m'      # red
C_TEAL=$'\e[38;2;0;101;106m'      # teal
C_SURF=$'\e[38;2;217;211;201m'      # surface1
