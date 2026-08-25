# Reinicio automático de TUIs al cambiar el tema (herdr CLI)

**Fecha:** 2026-08-25 · **Estado:** spec listo para implementar · **Repos:** `Pit-CL/dotfiles` (privado) + `Pit-CL/ocular` (público)

## Problema

`btop` y `gh dash` leen su configuración de color **solo al arrancar**. Cuando el Mac cambia de apariencia y `ocular-watcher.sh` propaga el modo a nube/omen, `ocular-switch` reescribe sus configs, pero **una instancia ya abierta sigue pintando el tema anterior**. Hoy el usuario tiene que cerrar y reabrir el tab a mano cada vez.

## Historial: qué se intentó y por qué falló

Entre el **2026-07-27 y el 2026-08-10** `ocular-switch` reiniciaba `gh dash` automáticamente: **SIGTERM al proceso en foreground del pane + relanzamiento con `herdr pane send-text`**. Se retiró (documentado en `ports/ocular-switch:33-42`) porque:

- mataba sesiones EN USO — el TUI moría con `program was killed: read /dev/stdin: input/output error`;
- un `gh pr merge` a medio responder quedaba huérfano;
- **el tty quedaba sin OPOST** — todo el output posterior salía escalonado y sin eco.

## Por qué el enfoque nuevo es distinto (y no repite el fallo)

La causa del tty roto era matar el proceso **dentro** de un pane cuyo pty sobrevivía en el estado que el TUI había dejado. El enfoque nuevo **cierra el tab entero**: el pty se destruye completo y se crea uno nuevo, así que no hay tty que pueda quedar corrupto.

**Verificado en vivo el 2026-08-25 (nube, herdr 0.8.2)**, ciclo completo:

```
herdr tab create --workspace w5 --cwd /tmp --label "zz-test-claude" --no-focus
  → devuelve result.root_pane.pane_id (w5:pZ) y result.tab.tab_id (w5:t6)
herdr pane run w5:pZ btop
  → process-info confirma foreground_processes[].cmdline == "btop"
herdr tab close w5:t6
  → el proceso muere con el tab (verificado: no queda huérfano en pgrep)
  → btop.conf NO se altera (md5 idéntico antes/después — el gotcha de
    "btop reescribe su conf al salir" no se dispara por esta vía)
```

## Contrato de la CLI de herdr (verificado, 0.8.2)

| Comando | Devuelve / hace |
|---|---|
| `herdr tab list` | JSON: `tab_id`, `workspace_id`, `label` (ej. `"2: gdash"`), `focused`, `pane_count` |
| `herdr pane list` | JSON: `pane_id`, `tab_id`, `workspace_id`, `cwd`, `focused`, `revision`, `terminal_title` |
| `herdr pane process-info --pane <id>` | `foreground_processes[]` con `cmdline` exacto (`"gh dash"`), `cwd`, `pid` |
| `herdr tab close <tab_id>` | cierra el tab y mata su proceso |
| `herdr tab create --workspace <ws> --cwd <path> --label <text> --no-focus` | crea el tab; **no acepta comando** → hay que lanzarlo aparte |
| `herdr pane run <pane_id> <cmd...>` | ejecuta el comando en el pane |

`revision` del pane sube con el output: sirve como detector de actividad.

## Diseño

### 1. `dotfiles/bin/tui-theme-restart.sh` (nuevo)

Recorre los panes de herdr y recicla los que corren una TUI de la lista blanca.

**Lista blanca (exacta, por `cmdline`):** `gh dash`, `btop`.
**Excluidos a propósito:** `lazygit`, `yazi`, `nvim` — tienen estado en curso (un commit a medio escribir, un buffer sin guardar) que un cierre destruye. No agregarlos sin pedido explícito.

**Guardas antes de tocar un pane — todas obligatorias:**

1. **Pane enfocado → saltar.** Si el usuario está mirando ese pane, no se le cierra debajo.
2. **`pane_count > 1` → saltar.** Un tab con splits perdería su layout al recrearse.
3. **Actividad reciente → saltar.** Snapshot de `revision`, esperar 2 s, comparar; si cambió, posponer. (Si en la práctica `gh dash` repinta por polling y esta guarda salta siempre, degradar a solo las guardas 1 y 2 y anotarlo en el script — no eliminarla en silencio.)
4. **`cmdline` exacto.** Si hay un pager o un editor encima de la TUI, el cmdline es otro → no tocar.

**Acción por pane que pasa las 4 guardas:**

```
tab close <tab_id>
tab create --workspace <ws> --cwd <cwd> --label <label> --no-focus
pane run <root_pane.pane_id> <cmdline>
```

El `label` se preserva textual (`"2: gdash"` vuelve a ser `"2: gdash"`).

**Pendientes y reintento:** los panes salteados se anotan en `~/.cache/tui-theme-restart-pending/` y se reintentan en la corrida siguiente — mismo patrón que `PENDING_DIR` de `ocular-watcher.sh`.

**Robustez:** `set -euo pipefail`; no-op silencioso si `herdr` no está en PATH o el socket no responde (el script corre en 3 máquinas, no en todas hay sesión viva); log a `~/.cache/tui-theme-restart.log`.

### 2. Hook en `ocular/ports/ocular-switch` (PR al repo público)

Al final del switcher, una sola línea sin lógica de fleet:

```bash
[ -x "$HOME/.local/bin/ocular-post-switch" ] && "$HOME/.local/bin/ocular-post-switch" "$mode" || true
```

Y **actualizar el comentario de cabecera (líneas 27-47)**: hoy dice "no reintroducirlo". Debe explicar que el reinicio volvió por otra vía —cerrar el tab, no matar el proceso— y por qué esa vía no reproduce el tty roto.

### 3. `dotfiles/install.sh`

Symlink `~/.local/bin/ocular-post-switch` → `bin/tui-theme-restart.sh`, idempotente, en la misma sección donde ya se instala `ocular-switch`.

## Criterio de éxito (verificable por comando)

1. `bash -n bin/tui-theme-restart.sh` y `shellcheck` sin errores.
2. Test funcional en `scripts/tests/` que: crea un tab con label conocido → lanza `btop` → corre el script → verifica que existe un tab con **el mismo label** y `btop` corriendo dentro → limpia el tab. Sale 0.
3. El script sale 0 y no hace nada cuando no hay sesión de herdr viva.
4. Correr el script dos veces seguidas no recicla dos veces el mismo pane (idempotente dentro de un mismo cambio de modo).

## Fuera de alcance

- Recarga en caliente sin reinicio (necesitaría soporte upstream de gh-dash).
- Migrar btop/gh-dash a colores ANSI del terminal — es la alternativa que evita el reinicio por completo; el usuario eligió el reinicio. Anotada aquí como plan B, no se implementa.
- TUIs corriendo fuera de un pane de herdr (verificado: hay un `btop` en `pts/11` sin pane): quedan fuera, el script no las ve.
