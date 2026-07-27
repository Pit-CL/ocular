# Scientific basis — Ocular

> 🇪🇸 [Versión en español](CIENCIA.md)

> A theme based on Catppuccin's role structure — the hues of its 14 accents
> are Ocular's own, derived by optimization (§8) — where **luminance and
> saturation are set by science**, not aesthetics.
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

APCA is a perceptual contrast algorithm developed as a candidate for WCAG
3, removed from the draft process in 2023; as of April 2026, WCAG 3's
contrast algorithm remains undetermined. It reports contrast as Lc and,
unlike WCAG 2.x, correctly models dark mode's asymmetry — the theme uses
it for that technical merit, not for its standardization status.

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

Code comments map to `subtext0` (Lc 68 dark / 72 light), not the overlay
band: they're text read continuously, not UI chrome — Lc 58/60 falls below
the APCA floor of Lc 60 for non-body content text, and the subtext band
preserves the hierarchy against body (82/88).

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
- The **cool-hued accents** (blue, sky, sapphire, lavender) stay cool by
  design: they occupy minimal area (syntax text) and at Lc 71 over an L 0.22
  background their absolute radiance is negligible — there's no circadian
  benefit to warming them, so their own hue windows (§8) stay in the blue
  family.
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
Crepúsculo theme, now applied to Ocular's own accent hues (§8).

**Trade-off:** equal-luminance accents drop the brightness cue that
color-vision-deficient users rely on when hues collapse (e.g. red vs.
green under deuteranopia). Ocular optimizes for typical trichromatic
vision by default; Ocular ships exactly the colorblind-safe alternative this
trade-off calls for — Rooibos Deutan / Manzanilla Deutan, with deliberately
unequal luminances (§9; cf. Modus themes' -deuteranopia/-tritanopia variants).

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

## 8. Own hue derivation: name families + max-min ΔE

The first version of this theme inherited Catppuccin's 14 accent hues
verbatim. Fixing every accent at the same Lc (§6) turns hue into the *only*
channel left to tell accents apart — and Catppuccin's hues weren't chosen for
that. Measured on the final, gamut-mapped, hex-quantized colors: Manzanilla's
red–maroon pair sat at ΔE OKLab = 0.0025 (visually indistinguishable),
flamingo–maroon 0.0058, flamingo–red 0.0066; Rooibos' red–maroon 0.0096,
rosewater–flamingo 0.0192.

**Mechanism**: each accent's hue is now Ocular's own, constrained to a window
derived from its **name family** (red = some red, green = some green…) plus
semantic anchors for the four roles with an external meaning (red = error,
green = success, yellow = warning, blue = info). Inside those windows,
`derive_hues.py` (dev-only, never run in CI) runs a deterministic
coordinate-ascent optimizer — fixed role order, a shrinking step schedule,
clamped to each window, accepting only strict improvements — that maximizes
the **minimum OKLab ΔE** across the union of both variants' 91 accent pairs,
evaluated on the actual final colors (post `solve_L_for_lc`, gamut mapping,
and 8-bit hex quantization). The result is frozen into `palette/hues.json`
(`{role: {hue, sat}}`, hue in whole degrees, sat to 3 decimals); `build.py`
only ever *reads* that table.

**Gate**: `MIN_ACCENT_DE = 0.025` (~2× the OKLab just-noticeable-difference)
is enforced twice — once in `build.py` right after generating each variant,
once more in `audit.py` reading the emitted JSONs back (defense against
hand-editing the palette files). Below that floor, the build fails loudly
with the offending pair and its ΔE.

**Gamut ceilings that shaped the windows**: some hue/lightness combinations
simply can't reach the chroma cap in sRGB. Manzanilla's teal→sapphire band
tops out around C_eff ≈ 0.079–0.107 at its lightness (~0.46) — well under the
0.13 cap — and Rooibos' reds/blues are similarly gamut-limited under its cap;
in both cases chroma alone can't separate neighboring accents, so their
windows are spread ≥ ~25° apart in hue instead.

## 9. CVD-safe variant: breaking equal-weight on purpose

§6 fixes every accent to the same Lc so hue is the only channel that
categorizes — but that is exactly what fails under dichromacy: when hues
collapse (red vs. green under deuteranopia), the one channel left standing
is luminance, and §6 deliberately flattens it. Rooibos Deutan / Manzanilla
Deutan (`palette/{rooibos,manzanilla}-deutan.json`) break that rule on
purpose: same neutrals, same chroma caps, same name-family hue windows as
the default palette, but each accent's Lc is now `71+dlc` (dark) /
`74+dlc` (light) — a **per-role offset**, not a shared constant.

**Simulation**: `color_science.simulate_cvd(hex, kind)` implements Viénot,
Brettel & Mollon (1999) — sRGB linear → LMS → single-plane projection → sRGB
linear collapsed to one 3×3 matrix per dichromacy kind (`protan`/`deutan`;
tritanopia is out of scope, negligible prevalence). Coefficients cross-checked
against the reference implementation
[libDaltonLens](https://github.com/DaltonLens/libDaltonLens), which cites the
1999 paper. `delta_e_cvd(hex1, hex2, kind)` is `delta_e_oklab` of the two
simulated colors.

**Objective**: `derive_hues.py --profile deutan` optimizes `(hue, sat, dlc)`
per role to maximize the **minimum ΔE** over {normal, deutan, protan} ×
{dark, light} × 91 pairs — three visual systems, not one. `dlc` is bounded
above by keeping the accent's Lc under `text`'s Lc − 4 in both modes (so
accents never approach body-text luminance), and below by a hard constraint:
every candidate must still clear `audit.floor_for`'s APCA floors (≥60 over
base/mantle/crust, ≥50 over surface0/1) in *both* variants before it's even
scored.

**Why the optimizer needed more than one attempt**: a plain coordinate ascent
starting from the equal-Lc baseline (`dlc=0` everywhere) got stuck at
0.0147 protan ΔE — below the 0.015 floor — because the two colliding pairs
(`mauve`–`sapphire` under protan, `flamingo`–`red` in normal vision) are
adjacent name-families by design, and nothing pushed their luminances apart
first. Widening their hue windows made it *worse* (0.0093–0.0101): greedy,
order-fixed ascent is path-dependent, not monotonic in search-space size. The
fix that worked was breaking the dlc=0 symmetry at the start: a **deterministic
multi-start** (three fixed initializations — the equal-Lc baseline, and two
role-cyclic `dlc` staggers of `(+6, 0, −2)` ordered by `hues.json`'s hue,
forward and reversed) followed by a **directed post-convergence
perturbation** (nudge the two roles of the current worst pair by ±2/±4 `dlc`,
re-refine, keep only strict improvements, repeat to a fixed point). All of it
stays deterministic — fixed candidates, fixed order, no randomness — the
multi-start just tries more *fixed* starting points instead of one.

**Gate**: `MIN_ACCENT_DE_CVD = 0.02`, enforced the same way as `MIN_ACCENT_DE`
(once in `build.py`, once in `audit.py` re-reading the emitted JSON). Achieved
minimums: dark protan 0.0201 (`sapphire`–`blue`, the binding constraint),
dark deutan 0.0214, light deutan 0.0216, light protan 0.0223 — comfortably
above the floor, with normal-vision separation still ≥ 0.025 in both variants
(0.0328 dark, 0.0420 light).

## Sources

- Dark/light and polarity: [ETRA 2025](https://dl.acm.org/doi/10.1145/3715669.3725879) · [MDPI IJERPH 2025](https://www.mdpi.com/1660-4601/22/4/609) · [ACHI 2024](https://personales.upv.es/thinkmind/dl/conferences/achi/achi_2024/achi_2024_3_150_20069.pdf) · [arXiv 2409.10841](https://arxiv.org/html/2409.10841v2) · [NN/g](https://www.nngroup.com/articles/dark-mode/)
- APCA: [APCA in a Nutshell](https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html) · [Why APCA](https://git.apcacontrast.com/documentation/WhyAPCA) · [WCAG3 Contrast as of April 2026 — Adrian Roselli](https://adrianroselli.com/2026/04/wcag3-contrast-as-of-april-2026.html)
- Halation/astigmatism: [Level Access](https://www.levelaccess.com/blog/accessibility-for-people-with-astigmatism/) · [BOIA](https://www.boia.org/blog/dark-mode-can-improve-text-readability-but-not-for-everyone)
- Circadian: [Nature Human Behaviour 2024](https://www.nature.com/articles/s41562-023-01791-7) · [MDPI Life 2025](https://www.mdpi.com/2075-1729/15/5/715) · [Chronobiology in Medicine 2024](https://www.chronobiologyinmedicine.org/journal/view.php?number=167)
- CVD simulation: [Viénot, Brettel & Mollon (1999), Color Research & Application](https://onlinelibrary.wiley.com/doi/10.1002/(SICI)1520-6378(199908)24:4%3C243::AID-COL5%3E3.0.CO;2-3) · [libDaltonLens](https://github.com/DaltonLens/libDaltonLens) · [DaltonLens — Understanding LMS-based CVD simulations](https://daltonlens.org/understanding-cvd-simulation/)
