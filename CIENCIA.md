# Base científica — Ocular

> 🇬🇧 [English version](SCIENCE.md)

> Theme basado en Catppuccin (estructura de roles + 14 hues de acento oficiales) donde
> la **luminancia y la saturación las fija la ciencia**, no la estética. Variantes:
> **Rooibos** (dark) y **Manzanilla** (light) — bebidas sin cafeína, coherentes con el
> naming de bebidas de Catppuccin y con la meta del theme: descanso.
> Fuentes verificadas por WebSearch el 2026-07-26.

## 1. Polaridad de contraste: por qué light Y dark con switch automático

La evidencia reciente es matizada, no dogmática:

- Estudios 2024 (ACHI 2024, smartphones) encuentran mejor desempeño en **polaridad
  positiva** (texto oscuro sobre fondo claro) en agudeza visual y proofreading,
  independiente de la edad: con fondo claro la pupila se contrae → mayor profundidad
  de campo y menos aberración esférica.
- Investigación 2025 (ETRA 2025, eye tracking) matiza: **el contraste de luminancia
  pesa más que la polaridad en sí**; y un estudio crowdsourced 2024 (arXiv 2409.10841,
  n=134) encontró que la polaridad óptima **varía por individuo** en proporciones
  comparables.
- MDPI 2025 (tablet users): la fatiga inmediata depende sobre todo del **calce entre
  luminancia de pantalla y luz ambiente**, no del modo per se.

**Decisión de diseño:** ambos modos son ciudadanos de primera clase y **todo el stack
conmuta automáticamente** con la apariencia del sistema: Manzanilla (light) para
trabajo diurno con luz ambiente, Rooibos (dark) para entornos oscuros. El factor
científico dominante es el calce pantalla↔ambiente, y eso solo lo entrega el switch
automático, nunca un modo fijo.

## 2. Contraste APCA: bandas controladas, no contraste máximo

APCA (algoritmo perceptual de WCAG 3) reporta contraste como Lc; a diferencia de
WCAG 2.x modela correctamente la asimetría del dark mode.

- Guía APCA: **Lc 90 preferido** para texto cuerpo ≥14px/400; **Lc 75 mínimo** para
  columnas de texto ≥18px; Lc 60 usable para texto grande; Lc 15 = umbral de
  invisibilidad.
- El contraste **excesivo** en dark mode agrava la halación (§3): más brillo del
  texto = más glow sobre fondo oscuro.

**Targets del theme** (resueltos numéricamente con `solve_L_for_lc`, APCA-W3 0.1.9):

| Rol | Rooibos (dark) | Manzanilla (light) |
|---|---|---|
| `text` (cuerpo) | Lc 82 | Lc 88 |
| `subtext1` / `subtext0` | Lc 74 / 68 | Lc 80 / 72 |
| `overlay2/1/0` (UI no-texto) | Lc 58 / 50 / 43 | Lc 60 / 52 / 44 |
| 14 acentos | Lc 71 ± 1.5 | Lc 74 ± 1.5 |

En dark el target de cuerpo queda deliberadamente en 82 (sobre el mínimo fluent 75,
bajo el 90 "preferido") porque el 90 está pensado para polaridad positiva; en fondo
oscuro ese extra de brillo alimenta halación. En light sí subimos a 88 (sin glow, el
contraste alto es gratis).

## 3. Anti-halación: sin #000, sin #fff, off-white cálido

- La **halación** (texto claro que "sangra" un halo sobre fondo oscuro) reduce
  legibilidad y golpea especialmente a personas con astigmatismo o miopía — con
  fondo oscuro la pupila se dilata y cualquier imperfección de foco se amplifica.
- Mitigación con evidencia: **fondo oscuro gris, no negro puro** (también la guía de
  Material Design) y **texto off-white ligeramente cálido**, no blanco puro.

**Decisión:** `base` dark = OKLCH L 0.22 (≈ luminancia del `base` de Mocha, familiar
pero nunca #000); `text` dark = off-white cálido H 85 (familia del #ded6c6 ya
validado en este workspace). En light, `base` = papel cálido L 0.955 (nunca #fff,
que deslumbra en pantallas ≥400 nits).

## 4. Circadiano: el fondo manda, los acentos no

- Los ipRGC con melanopsina (pico de sensibilidad ~460–490 nm, azul) señalizan al
  núcleo supraquiasmático; luz azul-enriquecida vespertina suprime melatonina y
  retrasa el sueño (revisiones 2024–2025; MDPI Life 2025 confirma supresión sostenida
  bajo azul vs recuperación bajo rojo).
- Nature Human Behaviour 2024 (Blume et al.): con **excitación melanópica igualada**,
  el "color" percibido no cambió las respuestas circadianas → lo que importa es la
  **radiancia espectral total que llega a los ipRGC**, no el matiz cosmético.

**Aplicación honesta de ese resultado:**
- El **fondo** es ~90% del área emisiva → es donde se decide el estímulo melanópico.
  Rooibos usa neutros cálidos (H 70–85, azul mínimo) y Manzanilla papel cálido:
  menos energía en 460–490 nm a igual luminancia percibida que los neutros azulados
  de Mocha/Latte originales (H ~285).
- Los **14 acentos fríos** (blue, sky, sapphire, lavender) se conservan: ocupan área
  mínima (texto de sintaxis) y a Lc 71 sobre fondo L 0.22 su radiancia absoluta es
  despreciable. La identidad Catppuccin no se sacrifica donde no hay beneficio.
- El cielo del wallpaper dark lleva acentos cálidos a baja luminancia: a L ~0.2 la
  emisión total es mínima.

## 5. Chroma moderado: anti-chromostereopsis

Colores muy saturados en extremos espectrales (rojo/azul puros) se perciben a
profundidades distintas (chromostereopsis) y "vibran"; la saturación alta sostenida
fatiga. Catppuccin ya es pastel; el theme lo formaliza: **cap de chroma OKLCH 0.11
(dark) / 0.13 (light)**, auditado post-gamut-mapping con `clamp_chroma`.

## 6. Acentos equal-weight: luminancia lee, el hue categoriza

Los 14 acentos se resuelven todos a la misma banda Lc (71 dark / 74 light): la vía
magnocelular (que guía la lectura) ve un peso uniforme — ningún token "grita" — y el
hue queda como canal puramente categórico (vía parvocelular). Es el mismo principio
validado en el theme Crepúsculo de este workspace, ahora aplicado a los hues de
Catppuccin extraídos de la paleta oficial (delta de hue ≤ 2°).

## 7. Wallpaper: fondo plano de baja emisión + olas de baja frecuencia

Mantiene el estilo del wallpaper dinámico actual del MacBook (wave-mauve: fondo casi
plano + olas en capas en dos esquinas opuestas), re-derivado con la paleta Ocular:

- **El fondo es el `base` del theme** y ocupa ~85% del área → en dark, la emisión
  total (y el estímulo melanópico, §4) del escritorio queda al mínimo; en light, el
  papel cálido evita el deslumbre del blanco puro.
- **Olas en capas = baja frecuencia espacial**: bandas anchas con borde ondulado
  suave y **contraste local bajo entre bandas adyacentes** — no disparan la vía
  magnocelular (sensible a alto contraste espacial) ni compiten por atención con las
  ventanas.
- Rampa de color por variante: Rooibos → rosewater/peach (té rojizo-ámbar) sobre
  fondo oscuro cálido; Manzanilla → miel/ámbar sobre papel cálido.
- **Grano sutil** anti-banding 8-bit y bordes anti-aliased.
- Formato final: HEIC dinámico light/dark (conmuta con la apariencia del sistema),
  igual que el actual, vía `make_heic.swift` en el Mac.

## Fuentes

- Dark/light y polaridad: [ETRA 2025](https://dl.acm.org/doi/10.1145/3715669.3725879) · [MDPI IJERPH 2025](https://www.mdpi.com/1660-4601/22/4/609) · [ACHI 2024](https://personales.upv.es/thinkmind/dl/conferences/achi/achi_2024/achi_2024_3_150_20069.pdf) · [arXiv 2409.10841](https://arxiv.org/html/2409.10841v2) · [NN/g](https://www.nngroup.com/articles/dark-mode/)
- APCA: [APCA in a Nutshell](https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html) · [Why APCA](https://git.apcacontrast.com/documentation/WhyAPCA)
- Halación/astigmatismo: [Level Access](https://www.levelaccess.com/blog/accessibility-for-people-with-astigmatism/) · [BOIA](https://www.boia.org/blog/dark-mode-can-improve-text-readability-but-not-for-everyone)
- Circadiano: [Nature Human Behaviour 2024](https://www.nature.com/articles/s41562-023-01791-7) · [MDPI Life 2025](https://www.mdpi.com/2075-1729/15/5/715) · [Chronobiology in Medicine 2024](https://www.chronobiologyinmedicine.org/journal/view.php?number=167)
