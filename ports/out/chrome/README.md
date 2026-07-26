# Chrome (modo desarrollador) — Ocular

Theme MV3 (`theme.colors` en RGB decimal), misma estructura que
`tools/chrome-catppuccin-mocha/manifest.json` del workspace Rollitos/Claude.

## Instalar (unpacked)

1. `chrome://extensions` -> activar "Modo de desarrollador".
2. "Cargar descomprimida" -> apuntar a `ocular-rooibos/` o `ocular-manzanilla/`.

## Limitación (documentar, no es un bug)

Los themes de Chrome cargados como *unpacked* son **estáticos**: no siguen la
apariencia del sistema (no hay auto dark/light) ni pueden recargarse por
script — Chrome no expone una API para eso a una extensión unpacked. El
cambio entre Rooibos y Manzanilla es **manual**: `chrome://extensions` ->
desactivar el theme activo -> activar el otro. `ocular-switch` NO gestiona
Chrome por este motivo.
