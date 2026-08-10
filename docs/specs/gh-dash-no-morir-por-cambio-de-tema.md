# Spec — gh-dash deja de morir (y de romper el terminal) al cambiar el tema

**Estado:** listo para implementar
**Fecha:** 2026-08-10
**Repos que se tocan:** `Pit-CL/ocular` (causa raíz) y `Pit-CL/dotfiles` (blindaje)

---

## Objetivo

Hoy, cuando el usuario está usando `gh dash` en un pane de herdr en **nube** y el
tema del sistema cambia (dark ↔ light), pasan tres cosas seguidas:

1. gh-dash **muere** con `program was killed: read /dev/stdin: input/output error`.
2. Si estaba a mitad de una operación interactiva (apretó `m` para mergear un PR y
   `gh pr merge` le está preguntando el método de merge), **el prompt queda huérfano
   y el usuario no ve lo que le están preguntando** — responde a ciegas.
3. El terminal queda con el `termios` sin restaurar (sin `onlcr`), así que **todo el
   output posterior sale escalonado hacia la derecha e ilegible**, incluido el prompt
   del shell y las siguientes corridas de gh-dash.

Cuando esto esté listo: cambiar el tema **nunca** mata una sesión de gh-dash en uso, y
ningún TUI que muera de forma violenta deja el terminal inutilizable.

---

## Causa raíz (verificada, no inferida)

`ports/ocular-switch:235-303` — bloque *"gh-dash: reinicio automático de las instancias
corriendo dentro de panes de herdr"*. El switcher recorre los panes de herdr, y para
cada pane cuyo proceso en foreground tenga `argv == ["gh","dash"]`:

```
ocular-switch:282   kill -TERM "$gh_pid"
ocular-switch:299   "$HERDR_BIN" pane send-text "$pane_id" "gh dash"$'\n'
```

Es decir: **el crash es intencional**. El switcher mata gh-dash con `SIGTERM` y lo
relanza para que tome el tema nuevo, porque gh-dash no tiene recarga en caliente. El
mensaje `program was killed: read /dev/stdin: input/output error` es bubbletea
reportando que lo mataron mientras leía stdin — no es un bug de gh-dash.

Consecuencias no previstas cuando se escribió ese bloque (comentario del script:
*"Mecanismo verificado en vivo 2026-07-27"*, con gh-dash **inactivo**):

- Al morir por señal, gh-dash **no restaura el `termios`**: el tty queda en modo raw
  sin `onlcr` → el escalonado del texto. `ttyctl -f` (`~/dotfiles/linux/zshrc:481`,
  agregado hoy 2026-08-10 contra este mismo síntoma) **no lo cubre**: zsh restaura los
  settings *antes de imprimir el prompt*, pero no apaga el alt-screen ni el mouse
  tracking, ni evita que el output del crash y del relanzamiento ya salga escalonado.
- El `pane send-text "gh dash"` inyecta texto en el pane sin mirar qué estaba haciendo
  el usuario.
- Si gh-dash tenía un hijo interactivo (`gh pr merge`, lazygit por la tecla `z`), ese
  hijo queda huérfano pintando sobre un terminal cuyo dueño acaba de morir.

### Descartado con evidencia — no volver a intentarlo

- **Actualizar / recompilar gh-dash.** El binario instalado
  (`~/.local/share/gh/extensions/gh-dash/gh-dash`) es un build local de `main` del
  **2026-08-01** (`vcs.revision=4ea7c39fbe4d`, `+dirty` por los parches de branding),
  o sea **más nuevo que el último release v4.25.2** (10-jul-2026) y ya con los fixes
  `shared-state background color`, `markdown panic` y `discard browser launcher
  stdout/stderr`. `gh extension upgrade gh-dash` sería un **downgrade**. Esta vía se
  agotó en dos iteraciones (2026-07-02 y 2026-08-09).
- **Buscar el bug upstream.** No existe issue en `dlvhdr/gh-dash` que calce con este
  crash; los abiertos (#916, #936, #939) son panics de Go distintos. No lo hay porque
  el crash lo causa el switcher local.
- **`ttyctl -f`.** Ya aplicado, insuficiente (ver arriba). Se conserva, no se revierte.

---

## Archivos e interfaces

### Fase 1 — que el switcher no mate sesiones en uso (repo `Pit-CL/ocular`)

**`ports/ocular-switch:235-303`** — eliminar el reinicio automático de gh-dash.

Se borra el bloque completo (desde el comentario `# --- gh-dash: reinicio automático…`
hasta el cierre del `while`/`if` y su mensaje `ok`/`note` de resumen). Se conserva
intacto el bloque anterior, `ocular-switch:219-233`, que reescribe el bloque `theme:`
de `~/.config/gh-dash/config.yml` vía `replace_block` — **ese sigue funcionando**: la
config queda con el tema correcto y gh-dash lo toma la próxima vez que se abra.

Actualizar en el mismo commit los comentarios de cabecera que describen el mecanismo
retirado: `ocular-switch:19-21` y `ocular-switch:33-37`.

Trade-off aceptado: una sesión de gh-dash ya abierta sigue pintando el tema viejo hasta
que el usuario la cierre y reabra. Es exactamente el mismo comportamiento que ya tienen
bat, yazi, lazygit y btop según el propio encabezado del script, y el usuario confirmó
que **los colores del TUI se leen bien** — el problema nunca fue el tema.

### Fase 2 — blindaje: que ningún TUI rompa el terminal (repo `Pit-CL/dotfiles`)

**`linux/zshrc`** — reemplazar el alias `gdash` por una función que restaura el
terminal pase lo que pase (crash, `SIGTERM`, `Ctrl-C`):

```zsh
# gdash — gh dash con restauración incondicional del terminal. Un TUI que muere
# por señal deja el tty en raw (sin onlcr → texto escalonado), el alt-screen
# activo y el mouse tracking encendido. `ttyctl -f` no cubre esos tres casos.
gdash() {
  local saved rc
  saved=$(stty -g 2>/dev/null)
  gh dash "$@"
  rc=$?
  [[ -n $saved ]] && stty "$saved" 2>/dev/null || stty sane 2>/dev/null
  # salir de alt-screen, mostrar cursor, apagar mouse tracking, resetear SGR, CR
  printf '\e[?1049l\e[?25h\e[?1000l\e[?1002l\e[?1003l\e[?1006l\e[0m\r'
  return $rc
}
```

**Además**: hoy `alias gdash='gh dash'` está **declarado dos veces** en el mismo archivo
(`linux/zshrc:199` y `linux/zshrc:345`). Dejar **una sola** definición (la función) y
borrar la otra.

Aplica a las tres máquinas vía dotfiles; el síntoma solo se ha visto en nube, pero la
función es inocua donde no ocurre.

### Fase 3 — CONDICIONAL: merge sin prompt (repo `Pit-CL/dotfiles`)

**No implementar de entrada.** Solo si, con las fases 1 y 2 aplicadas, al apretar `m`
sobre un PR el prompt de `gh pr merge` **sigue** sin verse (verificación V4 abajo).

En ese caso, en `config/gh-dash/config.yml` (y en `~/.config/gh-dash/config.yml` de
nube), dentro de `keybindings.prs`, agregar antes del binding `z`:

```yaml
        - key: m
          name: merge commit
          command: >
            gh pr merge {{.PrNumber}} --repo {{.RepoName}}
            --merge --delete-branch
```

Sobrescribir un keybinding built-in con un comando custom está soportado y documentado
upstream. Variables verificadas presentes en el binario instalado: `PrNumber`,
`RepoName`, `RepoPath`, `HeadRefName`, `BaseRefName`, `IssueNumber`.

`--merge` (no `--squash`) porque es el método que el usuario usa de hecho: se verificó
sobre un merge reciente de uno de sus repos privados que el commit resultante tiene
**dos padres** y el mensaje `Merge pull request #N from …` (identificadores omitidos:
este repo es público). `--delete-branch` replica el `Delete the branch on GitHub? Yes`
que responde a mano.

**Asunción declarada** (el usuario no tenía preferencia): se liga a `m` y **sin**
confirmación adicional, porque el flujo actual ya es un `m` + `y` mecánico y el PR
seleccionado está visible en pantalla. Si al usarlo resulta demasiado sensible, mover
la misma entrada a `key: "M"` — un carácter, sin otro cambio; es el patrón que ya usa
para `A` = *approve → deploy a prod*.

---

## Fuera de alcance

- **Recarga en caliente del tema en gh-dash.** Requiere soporte upstream; sin él, la
  única vía es matar el proceso, que es justo lo que causa el problema. Descartado.
- **Reiniciar gh-dash "solo si está idle"** (verificar que no tenga hijos antes de
  matarlo). Reduce la ventana pero no la cierra, y agrega lógica frágil a cambio de un
  beneficio que el usuario no pidió: él ve bien los colores.
- **Diferir el reinicio hasta que el pane vuelva al prompt.** Misma razón, más estado
  que mantener.
- **Volver al release oficial v4.25.2** (`gh extension upgrade`). Sería un downgrade
  respecto al build de `main` del 1-ago instalado, y reintroduce el branding que los
  parches locales quitan.
- **Quitar `preview.open: false`** de la config de nube. Es un workaround de otro bug
  (el panic del markdown renderer, issue #922) que el build actual probablemente ya
  arregla, pero es un cambio independiente y no toca el síntoma de este spec.
- **`ttyctl -f`.** Se conserva tal cual; no estorba.

---

## Casos borde acordados

| Caso | Comportamiento esperado |
|---|---|
| Cambio de tema con gh-dash abierto e inactivo | gh-dash sigue vivo, pintando el tema anterior. La config ya tiene el tema nuevo; al cerrar y reabrir se ve. |
| Cambio de tema con gh-dash a mitad de un merge | gh-dash sigue vivo; el prompt de `gh pr merge` no se interrumpe. |
| gh-dash muere por cualquier otra causa (panic upstream, `kill` manual) | La función `gdash` restaura el tty, sale del alt-screen y devuelve el cursor: el prompt siguiente sale alineado. |
| `Ctrl-C` sobre gh-dash | Igual que arriba: la restauración corre porque está después de la llamada, no en un `trap` que la señal pueda saltarse. |
| Salida normal (`q`) | Sin cambios visibles; la restauración es idempotente. |
| Mac / omen (sin servidor herdr local) | El bloque retirado ya era no-op ahí (`has_herdr_server=0`). Sin cambio de comportamiento. |
| `ocular-switch` corriendo sin ningún gh-dash abierto | Sin cambio: escribe el bloque `theme:` y termina. |

---

## Verificación end-to-end

Todas se corren **en nube**. V1 y V4 necesitan un pane de herdr con `gh dash` abierto.

**V1 — el switcher ya no mata gh-dash** (el fix central):

```bash
# con `gh dash` abierto en un pane de herdr, desde otra sesión:
PID=$(pgrep -x -f "gh dash" | head -1); echo "pid=$PID"
~/.local/bin/ocular-switch light >/dev/null 2>&1
sleep 3
kill -0 "$PID" 2>/dev/null && echo "VIVO ✅" || echo "MUERTO ❌"
```
Esperado: `VIVO ✅`. Hoy imprime `MUERTO ❌`.

**V2 — el tema sí se sigue escribiendo en la config** (no se rompió lo que funcionaba):

```bash
~/.local/bin/ocular-switch light >/dev/null 2>&1
sed -n '/^theme:/,/^pager:/p' ~/.config/gh-dash/config.yml | grep -c 'primary'
~/.local/bin/ocular-switch dark  >/dev/null 2>&1
sed -n '/^theme:/,/^pager:/p' ~/.config/gh-dash/config.yml | grep -c 'primary'
```
Esperado: ambos imprimen un número **≥ 3** (el bloque `theme:` sigue completo), y los
valores hex difieren entre las dos corridas.

**V3 — el terminal sobrevive a una muerte violenta** (el blindaje). En un pane:

```bash
gdash          # se abre el TUI
```
desde otra sesión: `pkill -TERM -x -f "gh dash"` — y de vuelta en el primer pane:

```bash
stty -a | grep -o onlcr || echo "TTY ROTO ❌"
```
Esperado: imprime `onlcr` y el prompt aparece alineado a la izquierda. Hoy imprime
`TTY ROTO ❌` y el texto sale escalonado.

**V4 — el prompt de merge se ve** (decide si hace falta la fase 3):

Con las fases 1 y 2 aplicadas, abrir `gdash`, pararse sobre un PR propio abierto y
apretar `m`. Esperado: se lee la pregunta *"What merge method would you like to use?"*
con sus opciones. Si **no** se lee → aplicar la fase 3 y repetir; tras la fase 3 el
esperado es que `m` mergee sin preguntar nada y el TUI vuelva a la lista.

**V5 — no se rompió el script:**

```bash
bash -n ~/Documents/Recursos/Proyectos/ocular/ports/ocular-switch && echo "sintaxis OK"
~/.local/bin/ocular-switch dark >/dev/null 2>&1; echo "exit=$?"
```
Esperado: `sintaxis OK` y `exit=0`.

---

## Entrega

Dos PRs, uno por repo, ambos mergeables al entregarlos:

1. `Pit-CL/ocular` — `fix(ocular-switch): no matar gh-dash al cambiar de tema`
2. `Pit-CL/dotfiles` — `fix(zsh): restaurar el terminal cuando gh-dash muere` (incluye
   el deduplicado del alias `gdash`, y la fase 3 solo si V4 la exige)

Tras mergear, propagar a nube: el `ocular-switch` vive en el clon
`~/Documents/Recursos/Proyectos/ocular`, y el `zshrc` se despliega por el flujo normal
de dotfiles (`install.sh` en Linux).
