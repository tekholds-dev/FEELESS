// 🐱 FEE'S CALLS AS A CHAT (owner 2026-10-29, N15: "do a better call chat for Fee"). Pure, tested (feeCallChat.test.js).
// Her BUY / SELL events (public /api/cats/activity?catId=leader) → chat messages in her own words: what she did, WHY (the reason she gave,
// without the bookkeeping tail), her tags (setup · the AI's verdict), the market cap she called it at — and each BUY threaded to the SELL
// that closed it (the result + how long she held), or marked as still held.

const num = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
const sec = ts => (num(ts) > 1e12 ? num(ts) / 1000 : num(ts) || 0);

/** One event → { id, side, coin, sol, move, why, tags, pnl, cap, entryCap, at, pair } (null for anything that is not a call). */
export function callMsg(e) {
  if (!e || (e.type !== 'BUY' && e.type !== 'SELL')) return null;
  const t = String(e.detail || '').split('\n')[0].replace(/\s*\(paper[^)]*\)\.?/g, '').replace(/\s*\(fees apart[^)]*\)\.?/g, '');
  const coin = (t.match(/\bSOL of \$?([^\s,;]{1,16}?)(?=\s+at\b|[\s,;]|$)/) || t.match(/^(?:Sold|Trimmed|Banked)\s+\$?([^\s,;]{1,16})\s+at\b/i) || t.match(/\$([A-Za-z0-9]{1,12})\b/) || [])[1] || null;
  const sol = num((t.match(/\b(?:Bought|Added)\s+(\d+(?:\.\d+)?)\s*SOL/i) || [])[1]);
  const move = num((t.match(/\bat\s+([+-]?\d+(?:\.\d+)?)%/) || [])[1]);
  const body = t.split(/\s+—\s+/).slice(1).join(' — ');   // everything after "Bought … — " / "Sold … at x% — "
  let why = body; let tags = [];
  if (e.type === 'BUY') {
    const [lead, ...rest] = body.split(/;\s*/);
    why = lead.replace(/^.*?\bfavou?red it(?:\s*\([^)]*\))?:\s*/i, '').replace(/\.+$/, '').trim() || lead.trim();
    tags = rest.join(' · ').split(/\s+·\s+/).map(x => x.replace(/\(.*$/, '').trim())
      .filter(x => x && x.length <= 48 && !/\)/.test(x) && /[A-Za-z]{3}/.test(x)).slice(0, 4);   // a cut-off note ("waits f)") is not a tag
  } else {
    why = body.replace(/\.?\s*P&L\s+[+-]?\d.*$/i, '').replace(/^thesis broken:\s*/i, 'thesis broken — ').trim();
  }
  return { id: e.id, side: e.type, coin, sol, move, why: why || t, tags, pnl: num(e.pnlSol), cap: num(e.marketCapUsd), entryCap: num(e.entryMarketCapUsd), at: sec(e.ts), pair: e.pairAddress || null };
}

/** Events (newest first) + her open positions → messages newest first, each BUY carrying `closed` {pnl, move, heldMin} or `open` true. */
export function callThread(events, positions = []) {
  const msgs = (events || []).map(callMsg).filter(Boolean).sort((a, b) => b.at - a.at);   // newest first, whatever order the feed arrived in
  const held = new Set((positions || []).map(p => p.pairAddress).filter(Boolean));
  msgs.forEach((m, i) => {
    if (m.side !== 'BUY' || !m.pair) return;
    const sell = msgs.slice(0, i).reverse().find(x => x.side === 'SELL' && x.pair === m.pair && x.at >= m.at);   // the first SELL after it (newer = earlier in the list)
    if (sell) m.closed = { pnl: sell.pnl, move: sell.move, heldMin: Math.max(0, Math.round((sell.at - m.at) / 60)) };
    else if (held.has(m.pair)) m.open = true;
  });
  return msgs;
}

/** Her last 24h of calls: { calls, closed, won, pnl } — closed = SELLs with a P&L. */
export function callStats(msgs, now = Date.now() / 1000) {
  const d = (msgs || []).filter(m => now - m.at < 86400);
  const sells = d.filter(m => m.side === 'SELL' && m.pnl != null);
  return { calls: d.length, closed: sells.length, won: sells.filter(m => m.pnl > 0).length, pnl: Math.round(sells.reduce((a, m) => a + m.pnl, 0) * 1e6) / 1e6 };
}

export const capWord = v => (v == null ? null : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);
