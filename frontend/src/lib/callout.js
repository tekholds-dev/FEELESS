// 📣 CALLOUTS (owner, 2026-10-16: "callout bubbles that act just like pump.fun's and show pnl and callout data live"): a chat post carries
// `📣 callout:<chain>:<pair>@<cap called at>|<SYM>` + the thesis; every viewer's bubble reads the live cap from the shared price poller.
export const CALLOUT_TAG = /📣\s?callout:([a-z]+):([A-Za-z0-9]{20,64})@(\d+(?:\.\d+)?)\|(\S{1,20})/i;

export function calloutPost(pair, why = '') {
  const mc = Math.round(Number(pair?.marketCap) || Number(pair?.fdv) || 0);
  const sym = String(pair?.baseToken?.symbol || '?').replace(/\s+/g, '').slice(0, 20);
  return `📣 callout:${pair.chainId}:${pair.pairAddress}@${mc}|${sym}${why ? ` ${String(why).slice(0, 220)}` : ''}`;
}

export function readCallout(text) {
  const m = CALLOUT_TAG.exec(String(text || ''));
  if (!m) return null;
  return { chain: m[1], pair: m[2], mc: Number(m[3]), sym: m[4], why: String(text).replace(CALLOUT_TAG, '').trim() };
}

// live read: × since the call, % P&L, bar fill (0..1 on a log scale −90% … 10×), tone
export function calloutLive(calledMc, nowMc) {
  const a = Number(calledMc), b = Number(nowMc);
  if (!(a > 0) || !(b > 0)) return { x: null, pct: null, fill: 0.5, tone: 'flat' };
  const x = b / a; const pct = (x - 1) * 100;
  const fill = Math.max(0, Math.min(1, (Math.log10(x) + 1) / 2));
  return { x, pct, fill, tone: pct >= 5 ? 'up' : pct <= -5 ? 'down' : 'flat' };
}
export const xWord = x => (x == null ? '—' : x >= 10 ? `${x.toFixed(0)}×` : x >= 2 ? `${x.toFixed(1)}×` : `${x.toFixed(2)}×`);
export const capWord = v => (!(v > 0) ? '—' : v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);
