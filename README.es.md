# Ocular

> 🇬🇧 [English version](README.md)

Theme **light + dark** para descanso ocular: la luminancia y la saturación de cada
color las fija la **ciencia** (OKLCH + APCA), no la estética. Construido sobre la
estructura de roles de [Catppuccin](https://github.com/catppuccin/catppuccin) — el
matiz de cada uno de los 14 acentos es propio de Ocular, derivado por optimización
max-min ΔE dentro de familias por nombre (`derive_hues.py`, ver [CIENCIA.md](CIENCIA.md)).

| Variante | Modo | Carácter |
|---|---|---|
| **Rooibos** | dark | fondo oscuro cálido, texto off-white cálido, acentos a Lc 71 |
| **Manzanilla** | light | papel cálido, tinta cálida, acentos a Lc 74 |

Sobre los nombres: Catppuccin nombra sus variantes con bebidas con café (Latte,
Mocha…). Las variantes de Ocular llevan nombres de **infusiones sin cafeína** —
rooibos y manzanilla — porque este theme está hecho para relajar la vista, no
para estimularla.

## Wallpapers

Fondo casi plano (mínima emisión) + olas simétricas de baja frecuencia espacial,
derivados de la misma paleta. Desktop 3840×2160 · iPhone 1284×2778 · iPad 2420×1668.

| Manzanilla (light) | Rooibos (dark) |
|---|---|
| ![Manzanilla](preview/manzanilla-pv.png) | ![Rooibos](preview/rooibos-pv.png) |

## La ciencia, en corto

1. **Polaridad**: la evidencia 2024-2025 muestra que el contraste de luminancia pesa
   más que la polaridad y que el factor dominante de confort es el calce
   pantalla↔luz ambiente → ambos modos de primera clase, pensados para conmutar
   automáticamente con el sistema.
2. **APCA en bandas, no en máximos**: texto cuerpo Lc 82 (dark) / 88 (light);
   jerarquías de texto secundario en escalones controlados. En dark no se persigue
   Lc 90: el exceso de brillo alimenta halación.
3. **Anti-halación**: nunca `#000` ni `#fff`; fondo dark gris cálido oscuro y texto
   off-white cálido (crítico con astigmatismo/miopía).
4. **Circadiano**: los neutros (≈90 % del área emisiva) viran a cálido — menos
   energía en la banda melanópica (~460-490 nm) a igual luminancia percibida. Los
   acentos fríos se conservan: su área es mínima.
5. **Chroma con tope** (0.11 dark / 0.13 light, auditado post-gamut):
   anti-chromostereopsis, menos fatiga por saturación sostenida.
6. **Acentos equal-weight**: los 14 acentos a la misma Lc — ningún token grita; la
   luminancia lee, el matiz categoriza.
7. **Matices propios, no heredados**: el matiz de cada acento vive dentro de una
   ventana por familia del nombre (red = algún rojo, green = algún verde…) y se
   optimiza con coordinate ascent determinista para maximizar el ΔE OKLab mínimo
   entre los 14 acentos — gate `MIN_ACCENT_DE = 0.025` (≈2× el JND de OKLab),
   verificado en `build.py` y `audit.py`.
8. **Wallpaper de baja frecuencia espacial**: bandas anchas con contraste local
   bajo, que no compiten por atención con las ventanas.

Detalle completo con fuentes: [CIENCIA.md](CIENCIA.md).

## Paleta

- [`palette/rooibos.json`](palette/rooibos.json) · [`palette/manzanilla.json`](palette/manzanilla.json) —
  roles Catppuccin completos + ANSI16, con la Lc real de cada rol en su metadata.
- [`palette/VALIDACION.md`](palette/VALIDACION.md) — tabla de validación completa.
- Estructura 100 % compatible con los roles de Catppuccin: cualquier port se adapta
  cambiando solo los hex.

## Uso

```bash
python3 -m venv venv && venv/bin/pip install numpy pillow   # solo para wallpapers
python3 build.py        # regenera la paleta y falla si un check no pasa
python3 audit.py        # auditoría cruzada texto × superficie (216 pares)
venv/bin/python wallpaper.py   # regenera los 6 wallpapers + previews
```

`build.py` y `audit.py` no tienen dependencias externas (solo `color_science.py`,
incluido).

`derive_hues.py` es una herramienta dev-only: optimiza y (re)escribe la tabla
congelada de matices `palette/hues.json`. Solo hace falta correrla de nuevo si
cambian las ventanas de hue por rol — `build.py` siempre solo LEE esa tabla,
nunca el optimizador.

## Ports y switcher

`ports/build_ports.py` genera desde los JSON de paleta los themes listos para:
kitty, ghostty, bat (tmTheme, reusado por delta), yazi, lazygit, btop, tmux,
gh-dash, oh-my-posh, nvim (spec de `catppuccin/nvim` con `color_overrides` y
flavour automático por `background`), VSCode, Chrome (theme MV3), Slack (cadena
de tema custom) y fragmentos shell genéricos — todo ×2 modos y validado
(sintaxis + pertenencia de cada hex a la paleta).

`ports/ocular-switch light|dark` aplica el modo en las apps presentes de la
máquina. kitty, ghostty y nvim quedan con **conmutación nativa** (se instalan
una vez y siguen la apariencia del sistema solos); el resto se re-apunta por
modo en cada corrida.

## Estado y limitaciones conocidas

El theme está en uso real (terminales, TUIs, editores y una app web shadcn/Tailwind
derivan de esta paleta). Limitaciones honestas del switch automático:

- **TUIs de larga vida** (btop, lazygit, gh-dash, yazi) leen su config al arrancar:
  las instancias abiertas no conmutan hasta reabrirse. btop además reescribe su
  config al salir (una instancia vieja puede pisar el theme; se corrige en el
  siguiente switch).
- **Chrome**: los themes (`out/chrome/`) se cargan como extensión descomprimida y
  son estáticos — el cambio de modo es manual (limitación de la plataforma).
- **Slack**: dos cadenas de tema custom (`out/slack/`), cambio manual.
- La regeneración es autocontenida: las plantillas fuente de la sustitución
  están vendorizadas en `ports/reference/` (ver
  [`ports/ATTRIBUTION.md`](ports/ATTRIBUTION.md)), así que cualquier clone
  limpio puede regenerar `ports/out/` sin depender de archivos instalados
  fuera de este repo. El CI (`.github/workflows/verify.yml`) regenera la
  paleta y cada port en cada PR y falla si hay drift.

## Créditos

- **[Catppuccin](https://github.com/catppuccin)** (MIT) — estructura de roles y
  nombres; `palette/catppuccin-oficial.json` es un extracto de su paleta oficial,
  usado por `ports/build_ports.py` como mapa hex→rol para sustituir las
  plantillas oficiales por los matices propios de Ocular, **y varios ports de
  `ports/out/` derivan directamente de sus ports oficiales** (bat, yazi, btop,
  lazygit, entre otros) con la paleta sustituida: detalle completo y aviso de
  copyright en [`ports/ATTRIBUTION.md`](ports/ATTRIBUTION.md).
- **[Björn Ottosson](https://bottosson.github.io/posts/oklab/)** — espacio de color
  OKLab/OKLCH.
- **[APCA](https://git.apcacontrast.com/)** (Andrew Somers / Myndex) — algoritmo de
  contraste perceptual APCA-W3 0.1.9, implementado en `color_science.py`.

## Licencia

[MIT](LICENSE)
