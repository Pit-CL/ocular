# Ocular

> 🇪🇸 [Versión en español](README.es.md)

A **light + dark** theme for eye comfort: the luminance and saturation of every
color are set by **science** (OKLCH + APCA), not aesthetics. Built on the role
structure and accent hues of [Catppuccin](https://github.com/catppuccin/catppuccin).

| Variant | Mode | Character |
|---|---|---|
| **Rooibos** | dark | warm dark background, warm off-white text, accents at Lc 71 |
| **Manzanilla** (chamomile) | light | warm paper, warm ink, accents at Lc 74 |

About the names: Catppuccin names its flavors after coffee drinks (Latte,
Mocha…). Ocular's variants are named after **caffeine-free infusions** instead —
rooibos and chamomile — because this theme is built to relax your eyes, not to
stimulate them.

## Wallpapers

Near-flat background (minimal emission) + symmetric low-spatial-frequency
waves, derived from the same palette. Desktop 3840×2160 · iPhone 1284×2778 ·
iPad 2420×1668.

| Manzanilla (light) | Rooibos (dark) |
|---|---|
| ![Manzanilla](preview/manzanilla-pv.png) | ![Rooibos](preview/rooibos-pv.png) |

## The science, in short

1. **Contrast polarity**: 2024-2025 evidence shows that luminance contrast
   matters more than polarity itself, and that the dominant comfort factor is
   the match between screen and ambient light → both modes are first-class
   citizens, designed to switch automatically with the system.
2. **APCA in bands, not maxima**: body text at Lc 82 (dark) / 88 (light);
   secondary text hierarchies in controlled steps. In dark mode we don't chase
   Lc 90: excess brightness feeds halation.
3. **Anti-halation**: never `#000` or `#fff`; the dark background is a warm
   dark gray and text is warm off-white (critical for astigmatism/myopia).
4. **Circadian**: neutrals (~90% of the emissive area) shift warm — less
   energy in the melanopic band (~460-490 nm) at equal perceived luminance.
   Cool accents are preserved: their area is minimal.
5. **Capped chroma** (0.11 dark / 0.13 light, audited post-gamut):
   anti-chromostereopsis, less fatigue from sustained saturation.
6. **Equal-weight accents**: all 14 accents sit at the same Lc — no token
   shouts; luminance reads, hue categorizes.
7. **Low-spatial-frequency wallpaper**: wide bands with low local contrast,
   that don't compete for attention with windows.

Full detail with sources: [SCIENCE.md](SCIENCE.md).

## Palette

- [`palette/rooibos.json`](palette/rooibos.json) ·
  [`palette/manzanilla.json`](palette/manzanilla.json) — full Catppuccin roles
  + ANSI16, with the actual Lc of each role in its metadata.
- [`palette/VALIDACION.md`](palette/VALIDACION.md) — full validation table.
- Structure is 100% compatible with Catppuccin's roles: any port can be
  adapted by swapping only the hex values.

## Usage

```bash
python3 -m venv venv && venv/bin/pip install numpy pillow   # only for wallpapers
python3 build.py        # regenerates the palette and fails if a check doesn't pass
python3 audit.py        # cross-audit text × surface (228 pairs)
venv/bin/python wallpaper.py   # regenerates the 6 wallpapers + previews
```

`build.py` and `audit.py` have no external dependencies (only
`color_science.py`, included).

## Ports and switcher

`ports/build_ports.py` generates ready-to-use themes from the palette JSONs
for: kitty, ghostty, bat (tmTheme, reused by delta), yazi, lazygit, btop,
tmux, gh-dash, oh-my-posh, nvim (spec for `catppuccin/nvim` with
`color_overrides` and automatic flavour by `background`), VSCode, Chrome (MV3
theme), Slack (custom theme string) and generic shell fragments — all ×2
modes and validated (syntax + palette membership of every hex).

`ports/ocular-switch light|dark` applies the mode across the apps present on
the machine. kitty, ghostty, and nvim get **native switching** (installed
once, then they follow the system appearance on their own); the rest are
re-pointed per mode on every run.

## Status and known limitations

The theme is in real use (terminals, TUIs, editors, and a shadcn/Tailwind web
app all derive from this palette). Honest limitations of the automatic
switch:

- **Long-lived TUIs** (btop, lazygit, gh-dash, yazi) read their config at
  startup: already-open instances don't switch until reopened. btop also
  rewrites its config on exit (an old instance can overwrite the theme; this
  self-corrects on the next switch).
- **Chrome**: themes (`out/chrome/`) load as an unpacked extension and are
  static — switching modes is manual (a platform limitation).
- **Slack**: two custom theme strings (`out/slack/`), manual switch.
- The port generator assumes Catppuccin's official ports as the substitution
  source: to regenerate on a machine already migrated to Ocular, see the
  repo's references issue.

## Credits

- **[Catppuccin](https://github.com/catppuccin)** (MIT) — role structure,
  naming, and reference accent hues (`palette/catppuccin-oficial.json` is an
  extract of their official palette), **and several ports under `ports/out/`
  derive directly from their official ports** (bat, yazi, btop, lazygit,
  among others) with the palette substituted: full detail and copyright
  notice in [`ports/ATTRIBUTION.md`](ports/ATTRIBUTION.md).
- **[Björn Ottosson](https://bottosson.github.io/posts/oklab/)** — the
  OKLab/OKLCH color space.
- **[APCA](https://git.apcacontrast.com/)** (Andrew Somers / Myndex) — the
  APCA-W3 0.1.9 perceptual contrast algorithm, implemented in
  `color_science.py`.

## License

[MIT](LICENSE)
