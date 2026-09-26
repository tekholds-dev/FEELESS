const TRAIL_PREFIX = 'feeless-price-trail:';
const FEED_PREFIX = 'feeless-market-feed:';
const MAX_TRAILS = 15;
const FEED_TTL = 24 * 60 * 60 * 1000;

const lastSeen = raw => {
  try {
    const v = JSON.parse(raw);
    if (Array.isArray(v)) return Number(v[v.length - 1]?.t) || 0;
    return Number(v?.savedAt) || 0;
  } catch {
    return 0;
  }
};

// Silent background hygiene: runs once per load, never shown to users.
export function cleanBrowserStorage(now = Date.now()) {
  try {
    const keys = Object.keys(localStorage);
    keys.filter(k => k.startsWith(FEED_PREFIX)).forEach(k => {
      if (now - lastSeen(localStorage.getItem(k)) > FEED_TTL) localStorage.removeItem(k);
    });
    keys.filter(k => k.startsWith(TRAIL_PREFIX))
      .map(k => [k, lastSeen(localStorage.getItem(k))])
      .sort((a, b) => b[1] - a[1])
      .slice(MAX_TRAILS)
      .forEach(([k]) => localStorage.removeItem(k));
  } catch {
    // Storage unavailable (private mode) — nothing to clean.
  }
}
