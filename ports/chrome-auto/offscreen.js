// Único trabajo del documento offscreen: reportar prefers-color-scheme al
// service worker. matchMedia no existe en un service worker MV3; por eso el
// rodeo (chrome.offscreen con reason MATCH_MEDIA).
const mq = matchMedia('(prefers-color-scheme: dark)');

function report(origin) {
  chrome.runtime.sendMessage({ type: 'scheme', dark: mq.matches, origin });
}

mq.addEventListener('change', () => report('system-change'));
report('startup');
