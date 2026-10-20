import React from 'react';
import { usePrime } from '../ArenaPrime';
import { useLivePrices } from '../../lib/livePrices';
import { pct, usd } from '../../lib/num';
import '../../styles/brainCards.css';

// 🃏 BRAIN POP-OUT › LIVE CARDS (owner, 2026-10-20: "brain popout with amazing vitals on current cards"): the real card(s) beside the chat — value,
// all-time, cash, and every coin as a live row: who holds it (you · OSSY · G4 · agents), % now with a bar, peak, held time, its own lines.
// Reads the shared /fuses/prime poll + the shared live prices — no new request.
export const holderOf = l => l.picked ? ['👤', 'YOU'] : l.aiBy === 'lan' ? ['🔁', 'G4'] : l.aiBy === 'local' ? ['🔁', 'OSSY'] : ['🤖', 'AGENTS'];
export function legLive(l, px) {
  const now = px?.price > 0 ? px.price : Number(l.now) || 0; const e = Number(l.entry) || 0;
  const p = e > 0 && now > 0 ? (now / e - 1) * 100 : Number(l.pnlPct) || 0;
  const pk = e > 0 && Number(l.high) > 0 ? (Number(l.high) / e - 1) * 100 : null;
  return { p, pk: pk != null ? Math.max(pk, p) : null, usd: (Number(l.usd) || 0) * (l.now > 0 && now > 0 ? now / l.now : 1) };
}
const held = t => { const s = Date.now() / 1000 - t; return !t ? '—' : s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : `${(s / 3600).toFixed(1)}h`; };

export default function BrainCards() {
  const d = usePrime(15000);
  const cards = (d?.cards || []).filter(c => c.real);
  const legs = cards.flatMap(c => (c.legs || []).filter(l => !l.placeholder && l.mint));
  const live = useLivePrices(legs.map(l => l.pairAddress).filter(Boolean));
  if (!cards.length) return <div className="bcd" data-testid="brain-cards"><p className="bcd-empty">No real card running.</p></div>;
  return <div className="bcd" data-testid="brain-cards">{cards.map(c => {
    const all = c.math?.pnlUsd; const rows = (c.legs || []).filter(l => !l.placeholder && l.mint);
    return <section key={c.id} className="bcd-card">
      <header><b>{c.label}</b><span className={`bcd-pnl ${(c.pnlPct || 0) >= 0 ? 'up' : 'dn'}`}>{pct(c.pnlPct, 1)}</span></header>
      <div className="bcd-kpi"><span><em>IN CARD</em><b>{usd(c.valueUsd)}</b></span><span><em>ALL-TIME</em><b className={all >= 0 ? 'up' : 'dn'}>{all != null ? `${all >= 0 ? '+' : '−'}${usd(Math.abs(all))}` : '—'}</b></span>
        <span><em>CASH</em><b>{usd(c.cash)}</b></span><span><em>SEATS</em><b>{rows.length} / {(c.legs || []).length}</b></span><span><em>ROUND</em><b>{pct(c.roundPct, 1)}</b></span></div>
      <ol className="bcd-legs">{rows.map((l, i) => { const v = legLive(l, live.get(l.pairAddress)); const [ic, who] = holderOf(l);
        return <li key={`${l.mint}-${i}`} style={{ '--i': i }} className={v.p >= 0 ? 'up' : 'dn'}>
          <span className="bcd-who" data-tip={who}>{ic}<small>{who}</small></span><b>${l.symbol}</b>
          <i className="bcd-bar"><u style={{ transform: `scaleX(${Math.min(1, Math.abs(v.p) / 50)})` }} /></i>
          <span className="bcd-p" key={Math.round(v.p * 10)}>{pct(v.p, 1)}</span>
          <small className="bcd-meta">{usd(v.usd)} · peak {v.pk != null ? pct(v.pk, 0) : '—'} · {held(l.at)}{l.tp ? ` · TP +${Math.round(l.tp)}` : ''}{l.sl ? ` · SL −${Math.round(l.sl)}` : ''}</small></li>; })}</ol>
    </section>; })}</div>;
}
