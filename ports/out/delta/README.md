# delta — Ocular

Antes este directorio solo documentaba que delta reusa el tmTheme de bat por
nombre (`syntax-theme`). Eso sigue siendo cierto, pero delta también tiene
FONDOS de diff propios (plus/minus/blame/line-numbers) que el `syntax-theme`
no cubre — sin un feature dedicado quedan en los defaults de delta o, peor,
en los de un feature legado ajeno (ver "Por qué existe" abajo). Este puerto
genera un feature file `[delta "ocular"]` completo por modo.

## Archivos

- `ocular-rooibos.gitconfig` — dark.
- `ocular-manzanilla.gitconfig` — light.

Mismo nombre de feature **fijo** `ocular` en ambos: el `~/.gitconfig` del
usuario nunca cambia, solo el CONTENIDO del archivo incluido cambia por modo.

## Instalación (la hace `ocular-switch`)

```
cp ports/out/delta/ocular-<variante>.gitconfig ~/.config/delta/ocular.gitconfig
```

Y en `~/.gitconfig` (una sola vez, a mano):

```
[include]
    path = ~/.config/delta/ocular.gitconfig
```

delta no cachea nada: el próximo `git diff`/`git log -p | delta` ya toma el
archivo reescrito, sin reiniciar nada.

## Derivación de color

Todos los valores salen por ROL de `palette/{rooibos,manzanilla}.json`
(`build_ports.py`, función `delta_theme()`), igual que el resto de los ports:

- `syntax-theme` = el tmTheme de bat del mismo modo (`ports/out/bat/`).
- `plus-style`/`minus-style` = mezcla perceptual OKLab de `base` con
  `green`/`red` (~12%, `mix_oklab()`/`TINT_NORMAL`) — nunca el acento puro
  como fondo: los acentos Ocular están calibrados al mismo Lc que el texto
  normal frente a un neutro, así que usarlos de fondo colapsaría el
  contraste de lo que se dibuja encima.
- `plus-emph-style`/`minus-emph-style` = misma mezcla, más intensa (~28%,
  `TINT_EMPH`), para las palabras resaltadas dentro de la línea.
- `line-numbers-plus/minus-style` = `green`/`red` puros (ya calibrados).
- `line-numbers-zero/left/right-style`, `file-decoration-style`,
  `hunk-header-decoration-style`, `blame-palette` = neutros de superficie
  del mismo modo.
- `file-style`, `hunk-header-style`, `hunk-header-line-number-style`,
  `merge-conflict-*-style` = acentos directos (yellow/blue/peach).

Gate obligatorio (`check_delta_pairs()` en `build_ports.py`, corre en cada
`python3 ports/build_ports.py`): `Lc(text, bg) >= 60` (APCA,
`color_science.lc`) para los 4 fondos de diff y los 4 neutros de
blame-palette, más `Lc(green/red, base)` para line-numbers — exit != 0 si
alguno falla.

## Por qué existe este port

Sin un feature propio, cualquier feature LEGADO que un `~/.gitconfig` traiga
incluido (p.ej. uno pre-Ocular con fondos oscuros hardcodeados) pisa el
`[delta] syntax-theme` principal y deja el diff con fondos dark sobre
terminal light — el síntoma que motivó este port. `ocular-switch` instala
SIEMPRE el feature `ocular` del modo activo; basta con apuntar el `[include]`
de `~/.gitconfig` a `~/.config/delta/ocular.gitconfig` una vez.
