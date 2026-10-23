// ⚡ FeeCat's moves as chip rows, never sentence walls (owner, 2026-10-23: "no long text, more vital live visuals") — shared by HQ's live tape
// (FeeCatLive) and the public FeeCat page (FeeLiveTab). Pure.
// One event → coin · SOL · move % · P&L · 🔮 when FeeCat AI made the call · a short tag. The whole sentence stays on hover (data-tip).
export function tapeRow(e) {
  const t = String(e?.detail || '').split('\n')[0];
  const coin = (t.match(/\bSOL of \$?([^\s,;]{1,16}?)(?=\s+at\b|[\s,;]|$)/) || t.match(/^(?:Sold|Trimmed|Banked)\s+\$?([^\s,;]{1,16})\s+at\b/i)
    || t.match(/\$([A-Za-z0-9]{1,12})\b/) || t.match(/(?:of|winner|on)\s+\$?([A-Za-z0-9]{2,12})\b/) || [])[1] || null;   // a coin may be called "1" ($the was read off "on the")
  const sol = (t.match(/\b(?:Bought|Added|Add)\s+(\d+(?:\.\d+)?)\s*SOL/i) || (e?.type === 'SELL' ? [] : t.match(/(?<!P&L [+-]?)(\d+(?:\.\d+)?)\s*SOL(?!\/)/)) || [])[1];   // a sale's SOL is its P&L (its own chip)
  const move = (t.match(/at\s+([+-]\d+(?:\.\d+)?)%/) || [])[1];
  const ai = /FeeCat AI|AI desk|NEXA/i.test(t);
  const tag = /took profit/i.test(t) ? 'TP' : /Added/.test(t) ? 'ADD' : /stop|thesis broken|dumping/i.test(t) ? 'STOP' : /half size/.test(t) ? '½ SIZE'
    : e?.type === 'LEARN' ? (t.split(/[:—(]/)[0].trim().slice(0, 28) || 'LEARN') : null;
  return { coin, sol: sol != null ? +sol : null, move: move != null ? +move : null, pnl: e?.pnlSol ?? null, ai, tag, full: t };
}


// 🔎 one scan rejection → an icon chip (the full reason stays on hover)
const REASONS = [[/gun line/i, '🧱', 'under gun line'], [/chart says skip|compression|🔫/i, '🔫', 'chart skip'], [/liquidity|pool/i, '💧', 'thin pool'],
  [/too new/i, '🐣', 'too new'], [/older|max age/i, '⏳', 'too old'], [/market cap|cap band/i, '📏', 'cap band'], [/chas/i, '🏃', 'chasing'],
  [/holder|top ?10|insider|sniper|bundl/i, '👥', 'holders'], [/rug|safety|honeypot|mint|freeze/i, '🛡', 'rug guard'], [/seller|dump/i, '🔻', 'sellers lead']];
export function reasonChip(k) {
  const t = String(k || ''); const hit = REASONS.find(([re]) => re.test(t));
  return hit ? { icon: hit[1], label: hit[2], full: t } : { icon: '•', label: t.replace(/[^\w %$.+-]/g, '').trim().slice(0, 16) || 'other', full: t };
}

// 💬 FeeCat AI's desk words → chart bubbles (P0-QUICK #4): /api/cats/leader `talk` [{pair, word, why, at, mc}] for THIS coin, newest 10.
// Names are already scrubbed server-side; every bubble speaks as 🔮 FeeCat AI.
export function talkPins(talk, pair) {
  if (!pair) return [];
  return (talk || []).filter(t => t && t.pair === pair && Number(t.mc) > 0 && Number(t.at) > 0 && t.word).slice(-10)
    .map(t => ({ id: `fai-${t.at}-${t.word}`, at: Number(t.at), cap: Number(t.mc), who: 'FeeCat AI', kind: 'talk', action: String(t.word).toUpperCase(), text: String(t.why || '').slice(0, 160) || `said ${t.word}`, icon: '🔮' }));
}
