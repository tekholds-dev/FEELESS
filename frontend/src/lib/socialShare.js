// ✍ One-tap cross-post from FEEd (owner, 2026-10-18: "post from FEEd to those platforms"): each platform's OWN compose page, pre-filled.
// The user's own login there presses Post — FEELESS never holds their account, password or token.
const clean = t => String(t || '').replace(/[\u0000-\u0008\u000b-\u001f\u007f]/g, '').trim();
const safe = u => (/^https?:\/\//.test(String(u || '')) ? String(u) : '');
export const SHARE_TO = [['x', '𝕏', 'X'], ['reddit', '👽', 'Reddit'], ['bluesky', '🦋', 'Bluesky'], ['telegram', '✈', 'Telegram'], ['farcaster', '🟪', 'Farcaster']];
export function shareLinks(text, url) {
  const t = clean(text).slice(0, 270); const u = safe(url); const full = u ? `${t} ${u}` : t; const q = encodeURIComponent;
  return {
    x: `https://x.com/intent/post?text=${q(full)}`,
    reddit: `https://www.reddit.com/submit?title=${q(t.slice(0, 290))}${u ? `&url=${q(u)}` : `&text=${q(t)}&type=TEXT`}`,
    bluesky: `https://bsky.app/intent/compose?text=${q(full)}`,
    telegram: `https://t.me/share/url?url=${q(u || 'https://feeless.app')}&text=${q(t)}`,
    farcaster: `https://warpcast.com/~/compose?text=${q(full)}`,
  };
}
