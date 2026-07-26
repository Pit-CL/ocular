# Chrome (developer mode) — Ocular

MV3 theme (`theme.colors` in decimal RGB), same structure as
`tools/chrome-catppuccin-mocha/manifest.json` in the Rollitos/Claude
workspace.

## Install (unpacked)

1. `chrome://extensions` -> enable "Developer mode".
2. "Load unpacked" -> point to `ocular-rooibos/` or `ocular-manzanilla/`.

## Limitation (documented, not a bug)

Chrome themes loaded as *unpacked* are **static**: they don't follow the
system appearance (no auto dark/light) and can't be reloaded by script —
Chrome doesn't expose an API for that to an unpacked extension. Switching
between Rooibos and Manzanilla is **manual**: `chrome://extensions` ->
disable the active theme -> enable the other one. `ocular-switch` does NOT
manage Chrome for this reason.
