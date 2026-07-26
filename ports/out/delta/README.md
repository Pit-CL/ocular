# delta — Ocular

delta no tiene theme propio: reusa el tmTheme de **bat** por nombre (`git config --global delta.syntax-theme`).

```
git config --global delta.syntax-theme "Ocular Rooibos"     # dark
git config --global delta.syntax-theme "Ocular Manzanilla" # light
```

Requiere que `ports/out/bat/Ocular Rooibos.tmTheme` y `Ocular Manzanilla.tmTheme` estén instalados en el theme dir de bat (`bat --config-dir`/themes, con `bat cache --build` tras copiarlos) — `ocular-switch` se encarga de ambos pasos.
