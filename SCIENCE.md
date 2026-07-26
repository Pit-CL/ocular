# Scientific basis — Ocular

> 🇪🇸 [Versión en español](CIENCIA.md)

> A theme based on Catppuccin (role structure + 14 official accent hues)
> where **luminance and saturation are set by science**, not aesthetics.
> Variants: **Rooibos** (dark) and **Manzanilla** (chamomile, light) —
> caffeine-free drinks, consistent with Catppuccin's beverage naming and with
> the theme's goal: rest.
> Sources verified via WebSearch on 2026-07-26.

## 1. Contrast polarity: why light AND dark with automatic switching

Recent evidence is nuanced, not dogmatic:

- 2024 studies (ACHI 2024, smartphones) find better performance with
  **positive polarity** (dark text on light background) in visual acuity and
  proofreading, regardless of age: a light background makes the pupil
  contract → greater depth of field and less spherical aberration.
- 2025 research (ETRA 2025, eye tracking) qualifies this: **luminance
  contrast matters more than polarity itself**; and a 2024 crowdsourced
  study (arXiv 2409.10841, n=134) found that optimal polarity **varies by
  individual** in comparable proportions.
- MDPI 2025 (tablet users): immediate fatigue depends mostly on the **match
  between screen luminance and ambient light**, not on the mode per se.

**Design decision:** both modes are first-class citizens and **the whole
stack switches automatically** with the system appearance: Manzanilla
(light) for daytime work with ambient light, Rooibos (dark) for dark
environments. The dominant scientific factor is the screen↔ambient match,
and only automatic switching delivers that — never a fixed mode.

## 2. APCA contrast: controlled bands, not maximum contrast

APCA (WCAG 3's perceptual algorithm) reports contrast as Lc; unlike WCAG
2.x, it correctly models dark mode's asymmetry.

- APCA guidance: **Lc 90 preferred** for body text ≥14px/400; **Lc 75
  minimum** for text columns ≥18px; Lc 60 usable for large text; Lc 15 =
  invisibility threshold.
- **Excessive** contrast in dark mode worsens halation (§3): brighter text
  means more glow against a dark background.

**Theme targets** (solved numerically with `solve_L_for_lc`, APCA-W3 0.1.9):

| Role | Rooibos (dark) | Manzanilla (light) |
|---|---|---|
| `text` (body) | Lc 82 | Lc 88 |
| `subtext1` / `subtext0` | Lc 74 / 68 | Lc 80 / 72 |
| `overlay2/1/0` (non-text UI) | Lc 58 / 50 / 43 | Lc 60 / 52 / 44 |
| 14 accents | Lc 71 ± 1.5 | Lc 74 ± 1.5 |

In dark mode the body target deliberately sits at 82 (above the fluent
minimum of 75, below the "preferred" 90) because 90 is meant for positive
polarity; on a dark background, that extra brightness feeds halation. In
light mode we do go up to 88 (no glow, high contrast is free).

## 3. Anti-halation: no #000, no #fff, warm off-white

- **Halation** (light text that "bleeds" a halo over a dark background)
  reduces legibility and hits people with astigmatism or myopia especially
  hard — a dark background dilates the pupil, and any focus imperfection
  gets amplified.
- Evidence-based mitigation: **a dark gray background, not pure black**
  (also Material Design's guidance) and **slightly warm off-white text**,
  not pure white.

**Decision:** dark `base` = OKLCH L 0.22 (≈ the luminance of Mocha's `base`,
familiar but never #000); dark `text` = warm off-white H 85 (in the family
of the #ded6c6 already validated in this workspace). In light mode, `base` =
warm paper L 0.955 (never #fff, which glares on screens ≥400 nits).

## 4. Circadian: the background rules, the accents don't

- Melanopsin-containing ipRGCs (peak sensitivity ~460–490 nm, blue) signal
  the suprachiasmatic nucleus; blue-enriched evening light suppresses
  melatonin and delays sleep (2024–2025 reviews; MDPI Life 2025 confirms
  sustained suppression under blue vs. recovery under red).
- Nature Human Behaviour 2024 (Blume et al.): with **matched melanopic
  excitation**, perceived "color" did not change circadian responses → what
  matters is the **total spectral radiance reaching the ipRGCs**, not the
  cosmetic hue.

**Honest application of that result:**

- The **background** is ~90% of the emissive area → it's where the
  melanopic stimulus gets decided. Rooibos uses warm neutrals (H 70–85,
  minimal blue) and Manzanilla a warm paper: less energy in 460–490 nm at
  equal perceived luminance than the original Mocha/Latte's bluish neutrals
  (H ~285).
- The **14 cool accents** (blue, sky, sapphire, lavender) are preserved: they
  occupy minimal area (syntax text) and at Lc 71 over an L 0.22 background
  their absolute radiance is negligible. Catppuccin's identity isn't
  sacrificed where there's no benefit.
- The dark wallpaper's sky carries warm accents at low luminance: at L ~0.2
  the total emission is minimal.

## 5. Moderate chroma: anti-chromostereopsis

Highly saturated colors at spectral extremes (pure red/blue) are perceived
at different depths (chromostereopsis) and "vibrate"; sustained high
saturation causes fatigue. Catppuccin is already pastel; the theme
formalizes that: **OKLCH chroma cap of 0.11 (dark) / 0.13 (light)**, audited
post-gamut-mapping with `clamp_chroma`.

## 6. Equal-weight accents: luminance reads, hue categorizes

All 14 accents resolve to the same Lc band (71 dark / 74 light): the
magnocellular pathway (which guides reading) sees uniform weight — no token
"shouts" — and hue remains a purely categorical channel (parvocellular
pathway). This is the same principle validated in this workspace's
Crepúsculo theme, now applied to Catppuccin's hues extracted from the
official palette (hue delta ≤ 2°).

## 7. Wallpaper: low-emission flat background + low-frequency waves

Keeps the style of the MacBook's current dynamic wallpaper (wave-mauve:
near-flat background + layered waves in two opposite corners), re-derived
with the Ocular palette:

- **The background is the theme's `base`** and covers ~85% of the area → in
  dark mode, the desktop's total emission (and melanopic stimulus, §4) stays
  at a minimum; in light mode, the warm paper avoids the glare of pure
  white.
- **Layered waves = low spatial frequency**: wide bands with a smooth wavy
  edge and **low local contrast between adjacent bands** — they don't
  trigger the magnocellular pathway (sensitive to high spatial contrast) nor
  compete for attention with windows.
- Color ramp per variant: Rooibos → rosewater/peach (reddish-amber tea) over
  a warm dark background; Manzanilla → honey/amber over warm paper.
- **Subtle grain** for 8-bit anti-banding and anti-aliased edges.
- Final format: dynamic light/dark HEIC (switches with the system
  appearance), same as the current one, via `make_heic.swift` on the Mac.

## Sources

- Dark/light and polarity: [ETRA 2025](https://dl.acm.org/doi/10.1145/3715669.3725879) · [MDPI IJERPH 2025](https://www.mdpi.com/1660-4601/22/4/609) · [ACHI 2024](https://personales.upv.es/thinkmind/dl/conferences/achi/achi_2024/achi_2024_3_150_20069.pdf) · [arXiv 2409.10841](https://arxiv.org/html/2409.10841v2) · [NN/g](https://www.nngroup.com/articles/dark-mode/)
- APCA: [APCA in a Nutshell](https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html) · [Why APCA](https://git.apcacontrast.com/documentation/WhyAPCA)
- Halation/astigmatism: [Level Access](https://www.levelaccess.com/blog/accessibility-for-people-with-astigmatism/) · [BOIA](https://www.boia.org/blog/dark-mode-can-improve-text-readability-but-not-for-everyone)
- Circadian: [Nature Human Behaviour 2024](https://www.nature.com/articles/s41562-023-01791-7) · [MDPI Life 2025](https://www.mdpi.com/2075-1729/15/5/715) · [Chronobiology in Medicine 2024](https://www.chronobiologyinmedicine.org/journal/view.php?number=167)
