# Base científica — Ocular

> 🇬🇧 [English version](SCIENCE.md)

> Theme basado en la estructura de roles de Catppuccin — el matiz de sus 14 acentos
> es propio de Ocular, derivado por optimización (§8) — donde la **luminancia y la
> saturación las fija la ciencia**, no la estética. Variantes:
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

APCA es un algoritmo de contraste perceptual desarrollado como candidato para
WCAG 3, removido del proceso del draft en 2023; a abril de 2026 el algoritmo de
contraste de WCAG 3 sigue sin determinarse. Reporta contraste como Lc y, a
diferencia de WCAG 2.x, modela correctamente la asimetría del dark mode — el
theme lo usa por ese mérito técnico, no por su estatus de estandarización.

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

Los comentarios de código mapean a `subtext0` (Lc 68 dark / 72 light), no a la
banda overlay: son texto que se lee de forma sostenida, no chrome de UI — Lc
58/60 queda bajo el piso APCA de Lc 60 para texto de contenido no-cuerpo, y la
banda subtext preserva la jerarquía frente al cuerpo (82/88).

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
- Los **acentos de matiz frío** (blue, sky, sapphire, lavender) se mantienen fríos
  por diseño: ocupan área mínima (texto de sintaxis) y a Lc 71 sobre fondo L 0.22
  su radiancia absoluta es despreciable — no hay beneficio circadiano en calentarlos,
  así que sus ventanas de matiz propias (§8) se quedan en la familia del azul.
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
validado en el theme Crepúsculo de este workspace, ahora aplicado a los matices
propios de Ocular (§8).

**Trade-off:** acentos a luminancia uniforme eliminan la señal de brillo que
usuarios con deficiencia de visión de color usan cuando los matices colapsan
(p. ej. red vs green bajo deuteranopia). Ocular optimiza por defecto para
visión tricrómata típica; Ocular incluye exactamente la alternativa
CVD-safe que este trade-off pide — Rooibos Deutan / Manzanilla Deutan, con
luminancias deliberadamente desiguales (§9; cf. las variantes
-deuteranopia/-tritanopia de Modus themes).

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

## 8. Derivación de matices propios: familias por nombre + max-min ΔE

La primera versión de este theme heredaba tal cual los 14 hues de acento de
Catppuccin. Fijar todos los acentos a la misma Lc (§6) deja el matiz como el
*único* canal que distingue acentos entre sí — y los hues de Catppuccin no se
eligieron para eso. Medido sobre los colores finales (tras gamut mapping y
cuantización a hex): en Manzanilla el par red–maroon quedaba en ΔE OKLab =
0.0025 (indistinguible a la vista), flamingo–maroon 0.0058, flamingo–red
0.0066; en Rooibos red–maroon 0.0096, rosewater–flamingo 0.0192.

**Mecanismo**: el matiz de cada acento es ahora propio de Ocular, acotado a
una ventana derivada de su **familia por nombre** (red = algún rojo, green =
algún verde…) más anclas semánticas para los cuatro roles con significado
externo (red = error, green = éxito, yellow = advertencia, blue =
información). Dentro de esas ventanas, `derive_hues.py` (dev-only, nunca
corre en CI) ejecuta un optimizador coordinate ascent determinista — orden
fijo de roles, schedule de pasos decreciente, clamp a cada ventana, acepta
solo mejoras estrictas — que maximiza el **ΔE OKLab mínimo** sobre la unión
de los 91 pares de acentos de ambas variantes, evaluado sobre los colores
finales reales (tras `solve_L_for_lc`, gamut mapping y cuantización a hex de
8 bits). El resultado queda congelado en `palette/hues.json` (`{rol: {hue,
sat}}`, hue en grados enteros, sat a 3 decimales); `build.py` solo LEE esa
tabla.

**Gate**: `MIN_ACCENT_DE = 0.025` (≈2× el JND de OKLab) se verifica dos
veces — una en `build.py` justo después de generar cada variante, otra en
`audit.py` releyendo los JSON emitidos (defensa contra edición a mano de los
archivos de paleta). Bajo ese piso, el build falla con el par ofensor y su
ΔE.

**Techos de gamut que moldearon las ventanas**: algunas combinaciones de
matiz/luminancia no alcanzan el tope de chroma en sRGB. La banda
teal→sapphire de Manzanilla topa en C_eff ≈ 0.079–0.107 a su luminancia
(~0.46) — bien bajo el cap de 0.13 — y los rojos/azules de Rooibos están
limitados por gamut de forma similar bajo su cap; en ambos casos el chroma
solo no alcanza para separar acentos vecinos, así que sus ventanas quedan
separadas ≥ ~25° de matiz en su lugar.

## 9. Variante CVD-safe: romper equal-weight a propósito

§6 fija todos los acentos a la misma Lc para que el hue sea el único canal
que categoriza — pero eso es justo lo que falla bajo dicromacia: cuando los
matices colapsan (red vs green bajo deuteranopia), el único canal que queda
en pie es la luminancia, y §6 la aplana a propósito. Rooibos Deutan /
Manzanilla Deutan (`palette/{rooibos,manzanilla}-deutan.json`) rompen esa
regla a propósito: mismos neutros, mismos caps de chroma, mismas ventanas de
hue por familia de nombre que la paleta default, pero la Lc de cada acento
ahora es `71+dlc` (dark) / `74+dlc` (light) — un **offset por rol**, no una
constante compartida.

**Simulación**: `color_science.simulate_cvd(hex, kind)` implementa Viénot,
Brettel & Mollon (1999) — sRGB lineal → LMS → proyección de plano único →
sRGB lineal, reducido a una sola matriz 3×3 por tipo de dicromacia
(`protan`/`deutan`; tritanopía fuera de alcance, prevalencia ínfima).
Coeficientes verificados contra la implementación de referencia
[libDaltonLens](https://github.com/DaltonLens/libDaltonLens), que cita el
paper de 1999. `delta_e_cvd(hex1, hex2, kind)` es `delta_e_oklab` de los dos
colores simulados.

**Objetivo**: `derive_hues.py --profile deutan` optimiza `(hue, sat, dlc)`
por rol para maximizar el **ΔE mínimo** sobre {normal, deutan, protan} ×
{dark, light} × 91 pares — tres sistemas visuales, no uno. `dlc` esta acotado
hacia arriba manteniendo la Lc del acento bajo la Lc de `text` menos 4 en
ambos modos (para que el acento nunca se acerque a la luminancia del cuerpo
de texto), y hacia abajo por una restricción dura: cada candidato debe seguir
cumpliendo los pisos APCA de `audit.floor_for` (≥60 sobre base/mantle/crust,
≥50 sobre surface0/1) en **ambas** variantes antes de siquiera puntuarse.

**Por qué el optimizador necesitó más de un intento**: un coordinate ascent
simple arrancando desde el baseline equal-Lc (`dlc=0` en todos) quedaba
atascado en 0.0147 de ΔE protan — bajo el piso de 0.015 — porque los dos
pares que colisionan (`mauve`–`sapphire` bajo protan, `flamingo`–`red` en
visión normal) son familias de nombre vecinas por diseño, y nada empujaba sus
luminancias a separarse primero. Ensanchar sus ventanas de hue lo empeoró
(0.0093–0.0101): un ascent greedy de orden fijo es dependiente del camino, no
monótono respecto al tamaño del espacio de búsqueda. Lo que funcionó fue
romper la simetría `dlc=0` desde el arranque: un **multi-start
determinista** (tres inicializaciones fijas — el baseline equal-Lc, y dos
escalonados cíclicos de `dlc` `(+6, 0, −2)` por rol, ordenados por el hue de
`hues.json`, en un sentido y en el inverso) seguido de una **perturbación
dirigida post-convergencia** (mover los dos roles del peor par actual en
±2/±4 de `dlc`, re-refinar, aceptar solo mejoras estrictas, repetir hasta
punto fijo). Todo sigue siendo determinista — candidatos fijos, orden fijo,
sin aleatoriedad — el multi-start solo prueba más puntos de partida *fijos*
en lugar de uno solo.

**Gate**: `MIN_ACCENT_DE_CVD = 0.02`, verificado igual que `MIN_ACCENT_DE`
(una vez en `build.py`, otra en `audit.py` releyendo el JSON emitido).
Mínimos alcanzados: dark protan 0.0201 (`sapphire`–`blue`, la restricción
vinculante), dark deutan 0.0214, light deutan 0.0216, light protan 0.0223 —
comodamente sobre el piso, con la separación en visión normal todavía ≥ 0.025
en ambas variantes (0.0328 dark, 0.0420 light).

## 10. Tipografía e interlineado (complementario)

El theme gobierna solo el color — la comodidad de lectura la completa la
tipografía. Estos son los ajustes complementarios con respaldo empírico que
el autor aplica en su fleet junto a Ocular; no son parte de la paleta ni de
los ports, es solo una nota práctica.

- **Interlineado de código ≈1.3-1.4×**: dos mecanismos distintos empujan a
  ese rango. El amontonamiento vertical — líneas demasiado juntas dejan que
  las adyacentes interfieran con el reconocimiento de letras, sobre todo en
  visión parafoveal (la periferia del punto de fijación de lectura) —
  empuja el interlineado hacia arriba. La precisión del barrido de retorno
  — la sacada que salta del final de una línea al inicio de la siguiente —
  empeora con interlineado apretado, aumentando los errores de aterrizaje
  en la línea equivocada. La curva de beneficio se aplana pasado ~1.4×: más
  espacio no suma mucha precisión adicional y sí cuesta densidad vertical y
  diluye la estructura de un bloque de código, donde la proximidad (qué tan
  cerca quedan las líneas adyacentes) es en sí misma una señal de
  agrupación — el cuerpo de una función, un callback, un objeto literal se
  leen como una unidad visual solo si sus líneas se mantienen
  suficientemente juntas. El código además se lee en líneas más cortas que
  la prosa y se escanea verticalmente mucho más (repasar una firma de
  función, buscar una llave de cierre) — así que el óptimo para código
  queda en el extremo conservador del rango general, no estirado hacia los
  valores de prosa.
- **Prosa ≈1.5-1.6× con una medida de 65-75 caracteres**: el texto largo se
  beneficia de un interlineado más suelto que el código — cf. el Criterio
  de Éxito 1.4.12 de WCAG (Text Spacing), cuyo requisito de adaptabilidad de
  espaciado pide que el contenido siga siendo usable con una altura de
  línea de al menos 1.5× el tamaño de fuente, tratando esa proporción como
  un piso de lectura cómoda, no como un extremo.
- **Fuente: la familiaridad domina.** El efecto más grande y reproducible
  en la investigación de legibilidad es la familiaridad con la propia
  fuente habitual: cambiar a una fuente "más legible" impone un costo real
  de adaptación — el ojo y el sistema de lectura están afinados a las
  formas de letra que se ven a diario — que suele pesar más que cualquier
  ganancia marginal de forma que ofrezca la fuente nueva, para visión
  normal (corregida). Las fuentes diseñadas específicamente para
  accesibilidad muestran su evidencia más fuerte en contextos de baja
  visión, no en lectores típicos que cambian una fuente que ya conocen
  bien. Lo que sí importa en la forma de una fuente, cuando importa:
  x-height alto (las minúsculas se ven más grandes al mismo tamaño de
  punto), formas abiertas (los counters — los espacios encerrados o
  parcialmente encerrados de letras como 'a', 'e', 'o' — se mantienen
  abiertos en vez de taparse a tamaños chicos), y 0/O y 1/l/I sin ambigüedad
  (los clásicos confundibles del monospace). El fleet usa JetBrains Mono,
  cuyos propios settings recomendados traen un interlineado nativo bastante
  apretado (~1.2×) — llevado a ≈1.32× efectivo con un ajuste de +10% en
  cell-height, dentro del target de código de ~1.3-1.4× de arriba.
- One-liners concretos: kitty `modify_font cell_height 110%`, ghostty
  `adjust-cell-height = 10%`, VSCode `"editor.lineHeight": 1.4`.

## Fuentes

- Dark/light y polaridad: [ETRA 2025](https://dl.acm.org/doi/10.1145/3715669.3725879) · [MDPI IJERPH 2025](https://www.mdpi.com/1660-4601/22/4/609) · [ACHI 2024](https://personales.upv.es/thinkmind/dl/conferences/achi/achi_2024/achi_2024_3_150_20069.pdf) · [arXiv 2409.10841](https://arxiv.org/html/2409.10841v2) · [NN/g](https://www.nngroup.com/articles/dark-mode/)
- APCA: [APCA in a Nutshell](https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html) · [Why APCA](https://git.apcacontrast.com/documentation/WhyAPCA) · [WCAG3 Contrast as of April 2026 — Adrian Roselli](https://adrianroselli.com/2026/04/wcag3-contrast-as-of-april-2026.html)
- Halación/astigmatismo: [Level Access](https://www.levelaccess.com/blog/accessibility-for-people-with-astigmatism/) · [BOIA](https://www.boia.org/blog/dark-mode-can-improve-text-readability-but-not-for-everyone)
- Simulación CVD: [Viénot, Brettel & Mollon (1999), Color Research & Application](https://onlinelibrary.wiley.com/doi/10.1002/(SICI)1520-6378(199908)24:4%3C243::AID-COL5%3E3.0.CO;2-3) · [libDaltonLens](https://github.com/DaltonLens/libDaltonLens) · [DaltonLens — Understanding LMS-based CVD simulations](https://daltonlens.org/understanding-cvd-simulation/)
- Circadiano: [Nature Human Behaviour 2024](https://www.nature.com/articles/s41562-023-01791-7) · [MDPI Life 2025](https://www.mdpi.com/2075-1729/15/5/715) · [Chronobiology in Medicine 2024](https://www.chronobiologyinmedicine.org/journal/view.php?number=167)
- Tipografía: [WCAG 2.1 SC 1.4.12 Text Spacing — Understanding](https://www.w3.org/WAI/WCAG21/Understanding/text-spacing.html) · [JetBrains Mono — discusión de settings recomendados](https://github.com/JetBrains/JetBrainsMono/issues/670)
