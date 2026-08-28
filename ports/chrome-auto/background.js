// Prefijos, no nombres exactos: bajo el perfil deutan los themes se llaman
// "Ocular Rooibos Deutan" / "Ocular Manzanilla Deutan" (ver dark_label/
// light_label en ports/build_ports.py).
const PREFIX = { dark: 'Ocular Rooibos', light: 'Ocular Manzanilla' };

async function ensureOffscreen() {
  if (await chrome.offscreen.hasDocument()) return;
  await chrome.offscreen.createDocument({
    url: 'offscreen.html',
    reasons: ['MATCH_MEDIA'],
    justification: 'Detectar prefers-color-scheme para alternar el theme Ocular.'
  });
}

async function log(entry) {
  const { history = [] } = await chrome.storage.local.get('history');
  history.unshift({ ts: new Date().toISOString(), ...entry });
  await chrome.storage.local.set({ history: history.slice(0, 20) });
  console.log('[ocular-auto]', entry);
}

async function apply(dark, origin) {
  const wanted = dark ? PREFIX.dark : PREFIX.light;
  const themes = (await chrome.management.getAll()).filter((e) => e.type === 'theme');
  const target = themes.find((t) => t.name.startsWith(wanted));

  if (!target) {
    await log({
      origin, wanted, result: 'not-installed',
      themes: themes.map((t) => `${t.name}${t.enabled ? ' (activo)' : ''}`)
    });
    return;
  }
  if (target.enabled) {
    await log({ origin, wanted: target.name, result: 'already-active' });
    return;
  }

  try {
    await chrome.management.setEnabled(target.id, true);
    // Chrome solo admite un theme activo; si el anterior quedó habilitado,
    // se apaga para que no reaparezca al desinstalar el nuevo.
    for (const t of themes) {
      if (t.id !== target.id && t.enabled) await chrome.management.setEnabled(t.id, false);
    }
    await log({ origin, wanted: target.name, result: 'applied' });
  } catch (e) {
    await log({ origin, wanted: target.name, result: 'error', error: String(e) });
  }
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg?.type !== 'scheme') return;
  chrome.storage.local.set({ lastDark: msg.dark });
  apply(msg.dark, `matchMedia:${msg.origin}`);
});

// Clic en el icono: el mismo trabajo, con gesto de usuario explícito. Sirve
// de escape si el service worker estaba dormido y se perdió un cambio.
chrome.action.onClicked.addListener(async () => {
  await ensureOffscreen();
  const { lastDark = false } = await chrome.storage.local.get('lastDark');
  await apply(lastDark, 'click');
});

chrome.runtime.onStartup.addListener(ensureOffscreen);
chrome.runtime.onInstalled.addListener(ensureOffscreen);
