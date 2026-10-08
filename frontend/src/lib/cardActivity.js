// 🫀 How ALIVE a Fuse card is right now, from its own coins — pure, tested. `legs` = [{ symbol, m5, pct, buying, locked, sold }]:
// m5 = the coin's live 5-minute move (the shared price poller), pct = its move on the card. Heat = how hard the coins are moving
// now (not how much the card made): 0 calm · 1 warm · 2 hot · 3 blazing. A read of activity for the card's effects, never a signal.
export const HEAT = ['calm', 'warm', 'hot', 'blazing'];
export const HEAT_AT = [1.5, 4, 9];          // avg |5m move| % that starts warm / hot / blazing
export const SPARKS = [0, 4, 7, 11];         // particles per heat
const n = v => (Number.isFinite(Number(v)) ? Number(v) : 0);

export function cardActivity(legs = [], pnlPct = 0) {
  const live = (legs || []).filter(l => l && !l.sold);
  const read = live.filter(l => l.m5 != null && Number.isFinite(Number(l.m5)));
  const avg = read.length ? read.reduce((a, l) => a + Math.abs(n(l.m5)), 0) / read.length : 0;
  const net = read.length ? read.reduce((a, l) => a + n(l.m5), 0) / read.length : 0;
  let heat = avg >= HEAT_AT[2] ? 3 : avg >= HEAT_AT[1] ? 2 : avg >= HEAT_AT[0] ? 1 : 0;
  const top = read.slice().sort((a, b) => Math.abs(n(b.m5)) - Math.abs(n(a.m5)))[0] || null;
  if (top && Math.abs(n(top.m5)) >= 15 && heat < 2) heat = 2;            // one coin ripping lights the card even when the rest sleep
  const dir = net > 0.4 ? 'up' : net < -0.4 ? 'down' : read.length ? 'flat' : n(pnlPct) > 0 ? 'up' : n(pnlPct) < 0 ? 'down' : 'flat';
  const locked = live.length > 0 && live.every(l => l.locked);
  return { heat, word: HEAT[heat], dir, sparks: SPARKS[heat], buying: live.some(l => l.buying), locked,
    movers: read.filter(l => Math.abs(n(l.m5)) >= 3).length,
    top: top && Math.abs(n(top.m5)) >= 3 ? { symbol: top.symbol, m5: n(top.m5) } : null,
    beat: [4.2, 2.6, 1.6, 1][heat] };
}
