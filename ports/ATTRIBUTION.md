# Attribution — Ocular ports

Several artifacts under `ports/out/` **derive from the official ports of the
[Catppuccin](https://github.com/catppuccin) project** (MIT license): the
official port file was taken and its palette substituted with Ocular's,
preserving the structure, scopes, and original mapping work of its authors.
In compliance with Catppuccin's MIT license:

> Copyright (c) 2021 Catppuccin
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files… (full text:
> [catppuccin/catppuccin/LICENSE](https://github.com/catppuccin/catppuccin/blob/main/LICENSE))

## Direct derivatives of an official port (palette substitution)

| Artifact | Source |
|---|---|
| `out/bat/*.tmTheme` (reused by delta and yazi) | [catppuccin/bat](https://github.com/catppuccin/bat) |
| `out/yazi/*/flavor.toml` | [catppuccin/yazi](https://github.com/catppuccin/yazi) |
| `out/btop/*.theme` | [catppuccin/btop](https://github.com/catppuccin/btop) |
| `out/lazygit/*.yml` (theme block structure) | [catppuccin/lazygit](https://github.com/catppuccin/lazygit) |
| `out/ohmyposh/*.omp.json` | catppuccin theme for [oh-my-posh](https://ohmyposh.dev/docs/themes) |
| ANSI16 mapping (all variants) | convention from the [catppuccin/kitty](https://github.com/catppuccin/kitty) port |

## Own generation, using reference field structure

kitty, ghostty, tmux, gh-dash (own semantic mapping since PR #5), Chrome,
VSCode, nvim (spec built on
[catppuccin/nvim](https://github.com/catppuccin/nvim) via its
`color_overrides` API), Slack, statusline, and ccmax: files generated from
scratch by `build_ports.py`, using the official ports only as a reference
for which fields exist.

## Vendored reference templates

`ports/reference/` holds the 6 upstream Catppuccin templates (MIT license)
that `build_ports.py` reads for the palette-substitution artifacts (bat,
yazi, btop, oh-my-posh — see table above). They used to be read from the
maintainer's local dotfiles; vendoring them makes the build self-contained
so CI and any clean clone can regenerate `ports/out/` without depending on
files installed outside this repo.

## Also

- Palette role structure and accent hues: [catppuccin/palette](https://github.com/catppuccin/palette) (MIT) — see credits in the main README.
- OKLab/OKLCH: [Björn Ottosson](https://bottosson.github.io/posts/oklab/).
- APCA-W3 0.1.9: [Andrew Somers / Myndex](https://git.apcacontrast.com/).
