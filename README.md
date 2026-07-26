# Ocular

Theme **light + dark** para descanso ocular: la luminancia y la saturación de cada
color las fija la **ciencia** (OKLCH + APCA), no la estética. Construido sobre la
estructura de roles y los matices de acento de [Catppuccin](https://github.com/catppuccin/catppuccin).

| Variante | Modo | Carácter |
|---|---|---|
| **Rooibos** | dark | fondo oscuro cálido, texto off-white cálido, acentos a Lc 71 |
| **Manzanilla** | light | papel cálido, tinta cálida, acentos a Lc 74 |

Bebidas **sin cafeína**: este theme existe para descansar la vista.

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
7. **Wallpaper de baja frecuencia espacial**: bandas anchas con contraste local
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
python3 audit.py        # auditoría cruzada texto × superficie (228 pares)
venv/bin/python wallpaper.py   # regenera los 6 wallpapers + previews
```

`build.py` y `audit.py` no tienen dependencias externas (solo `color_science.py`,
incluido).

## Créditos

- **[Catppuccin](https://github.com/catppuccin/palette)** (MIT) — estructura de
  roles, nombres y matices de acento de referencia
  (`palette/catppuccin-oficial.json` es un extracto de su paleta oficial).
- **[Björn Ottosson](https://bottosson.github.io/posts/oklab/)** — espacio de color
  OKLab/OKLCH.
- **[APCA](https://git.apcacontrast.com/)** (Andrew Somers / Myndex) — algoritmo de
  contraste perceptual APCA-W3 0.1.9, implementado en `color_science.py`.

## Licencia

[MIT](LICENSE)
