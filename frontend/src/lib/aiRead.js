// 🧠 THE MODEL'S DECISIONS, READ (pure — the Agents cockpit's AI tab). A model answer is ADVISORY: these helpers only say how its
// stance sits next to what the kernel itself decided at that moment. Nothing here feeds a decision.
export const STANCE_TONE = { ENTER: 'is-good', HOLD: 'is-good', PROTECT: 'is-good', WATCH: 'is-hold', WAIT: 'is-warn', AVOID: 'is-bad', EXIT: 'is-bad', SKIP: 'is-bad' };
const BULL = new Set(['ENTER', 'HOLD', 'PROTECT']); const BEAR = new Set(['AVOID', 'EXIT', 'SKIP']);
const IN = new Set(['READY', 'ORDER_PENDING', 'HELD', 'HOLD', 'PROTECT']);

// model vs kernel: AGREES · DISAGREES · MORE EAGER (the model would enter, the kernel waits) · null (a closed trade / no kernel word)
export function agreeOf(row) {
  const st = String(row?.stance || '').toUpperCase(); const k = String(row?.kernel || '').toUpperCase();
  if (!st || !k || k.startsWith('CLOSED')) return null;
  const kin = IN.has(k);
  if (kin) return BEAR.has(st) ? { word: 'DISAGREES', cls: 'is-bad' } : BULL.has(st) ? { word: 'AGREES', cls: 'is-good' } : { word: 'CAUTIOUS', cls: 'is-warn' };
  return st === 'ENTER' ? { word: 'MORE EAGER', cls: 'is-warn' } : { word: 'AGREES', cls: 'is-good' };
}

// the log, newest first; `mint` = only that coin · `role` = only that desk
export function aiRows(ai, { mint = null, role = null, n = 30 } = {}) {
  return [...(ai?.log || [])].filter(r => (!mint || r.mint === mint) && (!role || r.role === role)).sort((a, b) => (b.at || 0) - (a.at || 0)).slice(0, n);
}

// −0.25 … +0.25 → a 0–1 fill either side of the centre line
export const deltaFill = d => { const v = Number(d); return Number.isFinite(v) ? Math.max(-1, Math.min(1, v / 0.25)) : 0; };

// how the model agrees with the kernel over the log: { n, agree, pct }
export function agreeStats(ai) {
  const rs = (ai?.log || []).map(agreeOf).filter(Boolean);
  const ok = rs.filter(a => a.word === 'AGREES').length;
  return { n: rs.length, agree: ok, pct: rs.length ? Math.round((ok / rs.length) * 100) : null };
}
