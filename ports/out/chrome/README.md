# Chrome (developer mode) — Ocular

MV3 theme (`theme.colors` in decimal RGB), same structure as an equivalent
manifest from the author's external tooling.

## Install (unpacked)

1. `chrome://extensions` -> enable "Developer mode".
2. "Load unpacked" -> the variant you want: `ocular-rooibos/` (dark) **or**
   `ocular-manzanilla/` (light). Load only one — see below.

## Auto dark/light is not possible (measured 2026-08-28)

Switching modes is manual, and no extension can fix it. Two independent
platform limits:

1. **Chrome keeps exactly one theme installed.** Applying a second theme
   uninstalls the first one — it does not stay behind as a disabled entry.
   Measured on Chrome 145 / macOS: after the companion extension enabled
   "Ocular Manzanilla", "Ocular Rooibos" was gone from `extensions.settings`
   in the profile's `Secure Preferences`, and the next `chrome.management
   .getAll()` reported it as `not-installed`. The reverse happened when the
   dark theme was loaded back by hand.
2. **No API installs a theme.** `chrome.management` only enables/disables
   already-installed extensions, and Chrome has no dynamic theme API
   (unlike Firefox's `browser.theme.update()`). So there is no way to bring
   the uninstalled variant back from an extension.

A companion extension that flipped the two themes with
`chrome.management.setEnabled` shipped in #38 and was removed here: it works
for exactly one transition and then destroys its own target. Verifying only
one transition, in one direction, is what let it through — check switches
both ways, twice, before calling them done.

Secondary finding, worth knowing if this is ever revisited: an MV3 service
worker plus its `MATCH_MEDIA` offscreen document go to sleep, and a real
appearance change with Chrome open produced no log entry at all. Any future
attempt needs a `chrome.alarms` heartbeat just to notice the change.

**What does switch automatically:** Chrome's own color setting. In
`chrome://settings/appearance`, reset the theme, set Mode to "Device" and
pick a custom color (`#8C4900`, the Manzanilla peach, or `#FEB782`, the
Rooibos one — same hue family as this palette). Chrome derives the light and
dark variants itself and follows the system. The trade-off is control: it is
a seed color, not the per-token palette these manifests define.

`ocular-switch` does not manage Chrome.
