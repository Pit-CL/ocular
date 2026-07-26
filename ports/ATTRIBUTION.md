# Atribución — ports de Ocular

Varios artefactos de `ports/out/` **derivan de los ports oficiales del proyecto
[Catppuccin](https://github.com/catppuccin)** (licencia MIT): se tomó el archivo
del port oficial y se sustituyó su paleta por la de Ocular, conservando la
estructura, los scopes y el trabajo de mapeo original de sus autores. En
cumplimiento de la licencia MIT de Catppuccin:

> Copyright (c) 2021 Catppuccin
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files… (texto completo:
> [catppuccin/catppuccin/LICENSE](https://github.com/catppuccin/catppuccin/blob/main/LICENSE))

## Derivados directos de un port oficial (sustitución de paleta)

| Artefacto | Origen |
|---|---|
| `out/bat/*.tmTheme` (reusado por delta y yazi) | [catppuccin/bat](https://github.com/catppuccin/bat) |
| `out/yazi/*/flavor.toml` | [catppuccin/yazi](https://github.com/catppuccin/yazi) |
| `out/btop/*.theme` | [catppuccin/btop](https://github.com/catppuccin/btop) |
| `out/lazygit/*.yml` (estructura del bloque theme) | [catppuccin/lazygit](https://github.com/catppuccin/lazygit) |
| `out/ohmyposh/*.omp.json` | tema catppuccin de [oh-my-posh](https://ohmyposh.dev/docs/themes) |
| Mapeo ANSI16 (todas las variantes) | convención del port [catppuccin/kitty](https://github.com/catppuccin/kitty) |

## Generación propia con estructura de campos de referencia

kitty, ghostty, tmux, gh-dash (mapeo semántico propio desde PR #5), Chrome,
VSCode, nvim (spec sobre [catppuccin/nvim](https://github.com/catppuccin/nvim)
vía su API `color_overrides`), Slack, statusline y ccmax: archivos generados
desde cero por `build_ports.py`, usando los ports oficiales solo como referencia
de qué campos existen.

## Además

- Estructura de roles y matices de acento de la paleta: [catppuccin/palette](https://github.com/catppuccin/palette) (MIT) — ver créditos del README principal.
- OKLab/OKLCH: [Björn Ottosson](https://bottosson.github.io/posts/oklab/).
- APCA-W3 0.1.9: [Andrew Somers / Myndex](https://git.apcacontrast.com/).
