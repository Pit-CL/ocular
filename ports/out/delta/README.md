# delta — Ocular

delta has no theme of its own: it reuses bat's tmTheme by name
(`git config --global delta.syntax-theme`).

```
git config --global delta.syntax-theme "Ocular Rooibos"     # dark
git config --global delta.syntax-theme "Ocular Manzanilla" # light
```

Requires `ports/out/bat/Ocular Rooibos.tmTheme` and `Ocular
Manzanilla.tmTheme` to be installed in bat's theme dir (`bat
--config-dir`/themes, with `bat cache --build` after copying them) —
`ocular-switch` takes care of both steps.
