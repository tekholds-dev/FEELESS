// 📋 Copy that works on iPhone Safari. Over plain http (the owner's phone on the LAN) Safari has NO navigator.clipboard at all,
// and on https it rejects a write that lands after an await. So: in an insecure context copy synchronously inside the tap
// (hidden textarea + execCommand), in a secure one try the native API and fall back to the same trick. Installed once at boot,
// so every `navigator.clipboard.writeText(...)` call site in the app works unchanged.

export function legacyCopy(text) {
  const doc = typeof document !== 'undefined' ? document : null;
  if (!doc?.body) return false;
  const active = doc.activeElement;
  const ta = doc.createElement('textarea');
  ta.value = text;
  ta.setAttribute('aria-hidden', 'true');
  // 16px keeps iOS from zooming on the focus; off-screen but still "visible" so iOS lets it select.
  ta.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;padding:0;border:0;opacity:0;font-size:16px;pointer-events:none';
  doc.body.appendChild(ta);
  let ok = false;
  try {
    ta.focus({ preventScroll: true });
    ta.select();
    ta.setSelectionRange(0, text.length);
    ok = !!doc.execCommand?.('copy');
  } catch { ok = false; }
  ta.remove();
  try { active?.focus?.({ preventScroll: true }); } catch { /* element gone */ }
  return ok;
}

export function copyText(value) {
  const text = String(value ?? '');
  const native = typeof navigator !== 'undefined' ? navigator.__nativeWriteText : null;
  const secure = typeof window !== 'undefined' && window.isSecureContext;
  if (!secure || !native) return legacyCopy(text) ? Promise.resolve() : Promise.reject(new Error('Copy blocked by the browser'));
  return native(text).catch(() => (legacyCopy(text) ? undefined : Promise.reject(new Error('Copy blocked by the browser'))));
}

export function installClipboard() {
  if (typeof navigator === 'undefined' || navigator.__feelessClipboard) return;
  const cb = navigator.clipboard;
  if (cb?.writeText) navigator.__nativeWriteText = cb.writeText.bind(cb);
  try {
    if (cb) cb.writeText = copyText;
    else Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: copyText, readText: () => Promise.reject(new Error('Paste with a long-press')) } });
  } catch { /* locked down: call sites keep their own fallbacks */ }
  navigator.__feelessClipboard = true;
}

// iOS zooms the page when an input under 16px gets focus (chat, paste a CA). maximum-scale=1 stops that focus-zoom on iOS
// while pinch-zoom keeps working there (iOS ignores the cap for gestures); Android keeps its default viewport.
export function installNoFocusZoom() {
  if (typeof navigator === 'undefined' || typeof document === 'undefined') return;
  const ios = /iP(hone|ad|od)/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const meta = document.querySelector('meta[name="viewport"]');
  if (!ios || !meta || /maximum-scale/.test(meta.content)) return;
  meta.content = `${meta.content}, maximum-scale=1`;
}
