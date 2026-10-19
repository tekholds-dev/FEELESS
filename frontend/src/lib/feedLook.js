// 🎨 FEEd LOOK (owner, 2026-10-18: "bg layout customization, text, fonts etc — make FEEd meta"): one remembered choice per browser
// (localStorage `feeless.feedLook`) → CSS variables on the FEEd shell. Fonts are stacks already on the device / already loaded by the app
// (no outside font request). `handles` = the user's own public X / Reddit / Bluesky / Telegram names (never a password or a token).
export const LOOK_KEY = 'feeless.feedLook';
export const FEED_BGS = [['void', '⬛ Void'], ['royal', '🌌 Royal aurora'], ['nebula', '🟣 Nebula'], ['sunset', '🌅 Sunset'], ['matrix', '🟩 Matrix'], ['paper', '📄 Paper']];
export const FEED_FONTS = [['sans', 'Clean', 'system-ui, -apple-system, "Segoe UI", sans-serif'], ['mono', 'Mono', '"JetBrains Mono", ui-monospace, monospace'],
  ['serif', 'Serif', 'Georgia, "Times New Roman", serif'], ['loud', 'Loud', '"Bungee", "Impact", "Arial Black", sans-serif']];
export const FEED_SIZES = [['s', 'S', 13], ['m', 'M', 15], ['l', 'L', 17], ['xl', 'XL', 19]];
export const FEED_ACCENTS = [['green', '#15d16a'], ['violet', '#a66bff'], ['ice', '#5ad7ff'], ['gold', '#f5c451'], ['pink', '#ff5fa2']];
export const FEED_DENSITY = [['comfy', 'Comfy'], ['tight', 'Tight']];
export const HANDLE_SITES = [['x', '𝕏', 'https://x.com/'], ['reddit', '👽', 'https://www.reddit.com/user/'], ['bluesky', '🦋', 'https://bsky.app/profile/'], ['telegram', '✈', 'https://t.me/']];
export const DEFAULT_LOOK = { bg: 'royal', font: 'sans', size: 'm', accent: 'green', density: 'comfy', handles: {} };

const pick = (list, v, d) => (list.some(x => x[0] === v) ? v : d);
/** pure: anything stored → a valid look (unknown values fall back, handles keep letters / digits / _ . - only) */
export function cleanLook(v) {
  const o = v && typeof v === 'object' ? v : {};
  const h = {};
  HANDLE_SITES.forEach(([k]) => { const s = String((o.handles || {})[k] || '').replace(/^@/, '').replace(/[^A-Za-z0-9_.-]/g, '').slice(0, 40); if (s) h[k] = s; });
  return { bg: pick(FEED_BGS, o.bg, 'royal'), font: pick(FEED_FONTS, o.font, 'sans'), size: pick(FEED_SIZES, o.size, 'm'), accent: pick(FEED_ACCENTS, o.accent, 'green'),
    density: pick(FEED_DENSITY, o.density, 'comfy'), handles: h };
}
export const readLook = () => { try { return cleanLook(JSON.parse(localStorage.getItem(LOOK_KEY) || 'null')); } catch { return cleanLook(null); } };
export const saveLook = v => { const c = cleanLook(v); try { localStorage.setItem(LOOK_KEY, JSON.stringify(c)); } catch { /* private */ } return c; };
/** pure: a look → the CSS variables + classes for the FEEd shell */
export function lookVars(l) {
  const c = cleanLook(l);
  return { style: { '--fx-font': FEED_FONTS.find(f => f[0] === c.font)[2], '--fx-size': `${FEED_SIZES.find(s => s[0] === c.size)[2]}px`, '--fx-accent': FEED_ACCENTS.find(a => a[0] === c.accent)[1] },
    cls: `fx-bg-${c.bg} fx-d-${c.density}` };
}
export const handleUrl = (site, h) => { const s = HANDLE_SITES.find(x => x[0] === site); return s && h ? s[2] + encodeURIComponent(h) : null; };
