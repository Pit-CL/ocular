# Chrome (developer mode) — Ocular

MV3 theme (`theme.colors` in decimal RGB), same structure as an equivalent
manifest from the author's external tooling.

## Install (unpacked)

1. `chrome://extensions` -> enable "Developer mode".
2. "Load unpacked" -> `ocular-rooibos/` **and** `ocular-manzanilla/`. Load
   both: the companion extension below toggles between them.
3. "Load unpacked" -> `../../chrome-auto/` ("Ocular Auto", an extension, not
   a theme).

## Auto dark/light (verified 2026-08-28)

A Chrome theme is static by itself: the manifest has no dark variant and
Chrome exposes no API for a theme to reload itself. `ports/chrome-auto/`
works around that from the outside — an offscreen document watches
`prefers-color-scheme` (reason `MATCH_MEDIA`, since a MV3 service worker has
no `matchMedia`) and the worker enables the matching theme through
`chrome.management.setEnabled`. Themes are matched by name prefix, so the
`-deutan` profile works too.

Verified on Chrome 145 / macOS: `setEnabled` on a theme needs **no user
gesture** and shows no native confirmation dialog, so the switch is fully
automatic and follows the system appearance — the same source of truth
`ocular-switch` uses. Clicking the extension icon re-applies the current mode
by hand, in case the service worker was asleep and missed a change.

`ocular-switch` still does not manage Chrome: it no longer needs to.
