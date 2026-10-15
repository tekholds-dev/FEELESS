import { tradeLevels } from './chartMarkers';

// 📏 LIVE LEVELS — every level a chart shows (your entry, a Fuse card's / the agents' stop · take · lock · trail · support · invalidation,
// Fee's read, the chart tools) as ONE list of rows the `ChartLevels` overlay draws itself: a lit line with a tag that says how far the
// LIVE price is from it, heats up as the price closes in and flashes when it crosses. No static dashed price lines anywhere.
// A row: { id, px (in the chart's own unit), title, tone: up | dn | gold | ice | violet | mute, key (drawn brighter, pinned at the edge
// when off the scale) }. Pure + tested; nothing here touches the DOM.
export const NEAR_PCT = 2.5;   // the live price is "at" a level inside this distance
export const TAG_GAP = 15;     // px two tags keep between them

const TONE_OF = c => ({ '#15d16a': 'up', '#45e486': 'up', '#7df9d0': 'up', '#ff8fa3': 'dn', '#fa708c': 'dn', '#ff5d73': 'dn', '#f5c542': 'gold', '#f5c451': 'gold', '#e9bd65': 'gold', '#ff9a3c': 'gold',
  '#9fe3ff': 'ice', '#5ec8ff': 'ice', '#b388ff': 'violet', '#9e8cff': 'violet', '#8a79ff': 'violet' }[String(c || '').toLowerCase().slice(0, 7)] || 'mute');
const row = (id, px, title, tone, key = false) => (Number(px) > 0 && Number.isFinite(Number(px)) ? { id, px: Number(px), title, tone, key } : null);

/** Your own fills + your entry + a Fuse card's / the agents' levels for this coin. `ratio` turns a price into the chart's unit (market cap). */
export function ownLevels({ userTrades, userEntry, fuse, ratio = 1 } = {}) {
  const out = [];
  const lv = tradeLevels(userTrades);
  if (lv.length > 1) lv.forEach((t, i) => out.push(row(`t${i}`, t.price * ratio, t.title, t.side === 'sell' ? 'dn' : 'up')));
  if (userEntry > 0) out.push(row('you', userEntry * ratio, '◆ your entry', 'gold', true));
  if (fuse?.entry > 0) {
    out.push(row('entry', fuse.entry * ratio, '⚛ entry', 'up', true));
    if (fuse.stop > 0) out.push(row('stop', fuse.stop * ratio, `🛑 stop −${fuse.slPct}%`, 'dn', true));
    if (fuse.lock > 0) out.push(row('lock', fuse.lock * ratio, `❄ locks +${fuse.lockPct}%`, 'ice', true));
    if (fuse.trail > 0) out.push(row('trail', fuse.trail * ratio, `🏔 trail −${fuse.trailPct}%`, 'gold', true));
  }
  (fuse?.lines || []).forEach((l, i) => out.push(row(`x${i}`, l?.px * ratio, l?.title || '', TONE_OF(l?.color), /take|stop|invalid|trail/i.test(l?.title || ''))));
  return out.filter(Boolean);
}

/** 🐱 Fee's read as rows; a level far outside the candles on screen is left out (it would mean nothing there). `band` = {lo, hi}. */
export function feeLevels(read, band, swing) {
  if (!read) return [];
  const ok = p => Number.isFinite(p) && p > 0 && !(band && (p < band.lo / 1.5 || p > band.hi * 1.5));
  const out = [];
  const add = (id, p, title, tone, key) => { if (ok(p)) out.push(row(id, p, title, tone, key)); };
  add('f-res', read.resistance, '🐱 resistance', 'dn'); add('f-sup', read.support, '🐱 support', 'up');
  if (read.vwap) add('f-fair', read.vwap, '🐱 fair value', 'gold');
  if (read.entry) { add('f-in', read.entry, '🐱 Fee entry', 'ice', true); add('f-sl', read.entry * 0.9, '🐱 stop −10%', 'dn', true); add('f-tp', read.entry * 1.22, '🐱 target +22%', 'up', true); }
  if (swing && swing.hi > swing.lo) [0.382, 0.5, 0.618].forEach(f => add(`f-fib${f}`, swing.hi - (swing.hi - swing.lo) * f, `🐱 fib ${f}`, 'violet'));
  return out.filter(Boolean);
}

/** 🧰 The chart tools' levels (gaps · magnets · gun line · germ). Their soft bands are still drawn by the tools themselves. */
export function toolLevels(read) {
  if (!read) return [];
  const out = [];
  (read.fvg || []).forEach((g, i) => out.push(row(`g${i}`, g.mid, g.dir === 'up' ? '🪜 gap' : '🪜 gap ↓', g.dir === 'up' ? 'up' : 'dn')));
  (read.magnets || []).forEach((m, i) => out.push(row(`m${i}`, m.price, `🧲 ${m.hits > 1 ? `×${m.hits} ` : ''}${m.side === 'above' ? 'highs' : 'lows'}`, 'gold')));
  if (read.gun) out.push(row('gun', read.gun.price, read.gun.fired ? '🔫 fired' : '🔫 gun line', read.gun.fired ? 'up' : 'gold', true));
  if (read.germ) out.push(row('germ', read.germ.bot, read.germ.lost ? '🦠 germ lost' : '🦠 germ', 'violet', true));
  return out.filter(Boolean);
}

/** How a level stands against the live price: signed % the price must move to reach it · near · which side it is on. */
export function levelRead(level, px) {
  const l = Number(level); const p = Number(px);
  if (!(l > 0) || !(p > 0)) return null;
  const dist = (l / p - 1) * 100;
  return { dist, near: Math.abs(dist) <= NEAR_PCT, above: dist >= 0 };
}
export const distWord = d => (d == null ? '' : Math.abs(d) < 0.05 ? 'AT IT' : `${d > 0 ? '▲' : '▼'} ${Math.abs(d) >= 1000 ? `${(Math.abs(d) / 100 + 1).toFixed(1)}x` : `${Math.abs(d).toFixed(Math.abs(d) >= 10 ? 0 : 1)}%`}`);

export const LIVE_ROOM = 16;   // px a level tag keeps from the LIVE price row (the P&L tag riding the candle + the axis's own price label sit there)

/** 🧹 Tags spread apart AND kept off fixed rows (`fixed` = y's that never move: the live price). A tag inside a fixed row's room goes to
 * the nearer side of it; after the spread any tag pushed back in drops below it. Same order as `ys`, null stays null. */
export function spreadAround(ys, h, fixed = [], gap = TAG_GAP, room = LIVE_ROOM) {
  const zones = (fixed || []).filter(y => y != null && Number.isFinite(y)).map(y => [y - room, y + room]);
  const out_ = y => { for (const [a, b] of zones) if (y > a && y < b) return y - a < b - y ? Math.max(0, a) : b; return y; };
  let out = spreadTags(ys.map(y => (y == null ? null : out_(y))), h, gap);
  for (let k = 0; k < 2 && zones.length; k += 1) {
    const again = out.map(y => (y == null ? null : zones.some(([a, b]) => y > a && y < b) ? zones.find(([a, b]) => y > a && y < b)[1] : y));
    if (again.every((y, i) => y === out[i])) break;
    out = spreadTags(again, h, gap);
  }
  return out;
}

/** Tags that would overlap are pushed apart: [{y}] (any order) → the y each TAG is drawn at, same order, at least `gap` apart inside [0, h]. */
export function spreadTags(ys, h, gap = TAG_GAP) {
  const idx = ys.map((y, i) => [y, i]).filter(([y]) => y != null).sort((a, b) => a[0] - b[0]);
  const out = ys.map(() => null);
  let prev = -Infinity;
  idx.forEach(([y, i]) => { const v = Math.max(y, prev + gap); out[i] = v; prev = v; });
  let over = prev - Math.max(gap, h - 4);   // ran past the bottom → walk back up
  for (let k = idx.length - 1; k >= 0 && over > 0; k -= 1) {
    const i = idx[k][1]; const lim = k === idx.length - 1 ? Math.max(gap, h - 4) : out[idx[k + 1][1]] - gap;
    if (out[i] > lim) out[i] = lim;
    over = k > 0 ? out[idx[k - 1][1]] - (out[i] - gap) : 0;
  }
  return out;
}

/** 📐 The prices the chart's own scale must keep on screen (owner, 2026-10-14: "chart entry etc needs fix" — the BUY at $34.71K sat above a
 *  $34.16–34.60K scale, so its line was gone and its chip floated over the vitals badge): your entry + your stop, each only when it is within
 *  `span` of the live price (a level 3× away would flatten the candles into a line). Pure. */
export function scaleKeep(levels, last, span = 0.35) {
  const l = Number(last);
  if (!(l > 0)) return [];
  return (levels || []).filter(r => r && r.px > 0 && (/^(entry|you|stop)$/.test(r.id) || /entry|stop/i.test(r.title || '')) && Math.abs(r.px / l - 1) <= span).map(r => r.px);
}

// 🧹 DECLUTTER (owner, 2026-10-14: "on-chart vitals almost clean but still cluttered"): levels within MERGE_PCT of each other are ONE tag
// ("⚛ entry · entry" twice at the same price read as two); at most MAX_TAGS tags, money levels first (entry · stop · take · your entry ·
// trail · lock, then invalidation / support, then the tools); the rest stay as faint lines with no tag (`quiet`).
export const MERGE_PCT = 0.4;
export const MAX_TAGS = 5;
const RANK = [[/entry|your entry/i, 0], [/stop/i, 1], [/take|target|tp/i, 2], [/trail|lock/i, 3], [/invalid|support|resist/i, 4], [/gun|germ|gap|magnet|fib|fair/i, 6]];
export const levelRank = l => { const t = String(l?.title || ''); const hit = RANK.find(([re]) => re.test(t)); return (hit ? hit[1] : 5) - (l?.key ? 0.5 : 0); };
const shortTitle = t => String(t || '').replace(/^[^\w$◆⚛🛑❄🏔🐱🪜🧲🔫🦠🎯]*/u, '').trim();
export function declutter(rows, max = MAX_TAGS) {
  const out = [];
  [...(rows || [])].filter(Boolean).sort((a, b) => levelRank(a) - levelRank(b)).forEach(l => {
    const twin = out.find(o => Math.abs(o.px / l.px - 1) * 100 <= MERGE_PCT);
    if (twin) {   // same price: one tag carries both names (the best-ranked first), no second line
      const a = shortTitle(twin.title).toLowerCase(); const b = shortTitle(l.title).toLowerCase();
      if (!a.includes(b) && !b.includes(a)) twin.title = `${twin.title} · ${shortTitle(l.title)}`;
      twin.key = twin.key || l.key;
      return;
    }
    out.push({ ...l });
  });
  return out.map((l, i) => ({ ...l, quiet: i >= max }));
}
