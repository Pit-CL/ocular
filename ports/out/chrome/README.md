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

## The fixed theme: `ocular-tabaco` (recommended)

Chrome is the only app in this set that cannot follow the system, and even
the manual switch below restarts the browser. The way out is not to switch at
all: `ocular-tabaco/` is a single theme meant to read well with the OS in
light **and** in dark.

It is not the literal midpoint between Rooibos and Manzanilla. Measured with
this repo's APCA engine, a mid-luminance frame (L 0.55-0.60) scores Lc 55/48
for light text and 21/28 for dark text — everything under the body floor of
60. A mid-tone would be the worst of the three themes. The band that works is
L 0.32 with light text (Lc 64-78).

Its neutrals are derived by deterministic OKLab mixing between both palettes'
bases (Rooibos has a gap between L 0.371 and L 0.666, so no role lands
there). That is why this manifest is validated by a dedicated APCA gate
instead of the palette-membership check the per-mode ones use.

The active tab is deliberately loud: Chrome paints the active tab with
`toolbar` and inactive ones with `frame`, and in the per-mode themes those
two are nearly identical (Manzanilla `238,232,223` vs `227,221,212`). Here
they sit 0.15 apart in OKLab lightness, plus a `text` -> `overlay2` jump in
the label. That matters most with the vertical tab strip.

Accent note: all 14 Rooibos accents are calibrated to the same Lc against
neutrals (equal-weight), so every one of them lands at Lc~53 over the active
tab and none clears the chrome floor of 55. The icon accent is therefore a
peach mixed 25% toward the cream base (Lc 59).

## Switching by hand: `ocular-chrome` (works, measured 2026-08-29)

Automatic is impossible, but switching on purpose is not. The trick is to
never have two themes: ONE unpacked directory whose `manifest.json` is
rewritten in place. The path does not change, so the extension ID does not
either, and there is no inactive theme left for Chrome to uninstall.

Two steps are needed, and the second one is the whole point:

1. Rewriting the manifest and relaunching Chrome is NOT enough. Chrome does
   not revalidate an unpacked theme's manifest on startup — it applies its
   `Cached Theme.pak`. Measured: manifest rewritten at 10:42, pak untouched
   from 10:40 after a full relaunch, old theme still on screen.
2. Deleting `Cached Theme.pak` while Chrome is closed forces Chrome to
   regenerate it from the manifest on the next start.

`ports/ocular-chrome rooibos|manzanilla|toggle` does exactly that: copy the
variant's manifest over the installed one, quit Chrome, delete the pak,
relaunch. It reads the target directory from the profile's
`extensions.theme.pack`, so it follows wherever the theme was loaded from.
Verified both ways, twice in a row (rooibos -> manzanilla -> rooibos ->
manzanilla): the extension ID stayed constant and nothing was uninstalled.

Because it restarts Chrome, it is deliberately NOT wired into
`ocular-switch`, which runs unattended from the Mac's appearance watcher —
restarting someone's browser without being asked is not acceptable. Run it
when you want it.

`ocular-switch` does not manage Chrome.
