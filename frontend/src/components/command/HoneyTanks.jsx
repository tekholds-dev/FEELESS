import React, { useId } from 'react';
import '../../styles/honeyTanks.css';

// 🍯 HONEY TANKS (owner 2026-11-03): each vital in its own glass vessel, filled with honey by its real number.
// The liquid is the two-wave, clipped-vessel technique of the open-source liquid gauges (D3 Liquid Fill Gauge, BSD-2; react-liquid-gauge, MIT),
// rebuilt on CSS transforms so it needs no library and no per-frame JavaScript.
const VESSEL = {
  vat: 'M14 20Q14 10 24 10H76Q86 10 86 20V100Q86 112 74 112H26Q14 112 14 100Z',
  jar: 'M34 8H66V22Q88 30 88 56V96Q88 112 72 112H28Q12 112 12 96V56Q12 30 34 22Z',
  hex: 'M50 6L92 30V90L50 114L8 90V30Z',
  flask: 'M40 8H60V40L90 96Q96 112 78 112H22Q4 112 10 96L40 40Z',
  drop: 'M50 6C50 6 88 50 88 76A38 38 0 0 1 12 76C12 50 50 6 50 6Z',
  barrel: 'M24 8H76Q92 34 92 60Q92 86 76 112H24Q8 86 8 60Q8 34 24 8Z',
};
const WAVE = 'M-100 6q25-9 50 0t50 0t50 0t50 0t50 0t50 0V130H-100Z';
const CYCLE_S = { daily: 86400, weekly: 604800 };

export function HoneyTank({ shape = 'vat', level = 0, label, value, sub, tip, tone = 'honey', i = 0, testid }) {
  const id = `ht${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  const l = Math.max(0, Math.min(1, Number(level) || 0));
  const y = 114 - l * 104;   // the honey line, in the vessel's own units
  return <article className={`ht-tank m-glass is-${tone}${l > 0 ? '' : ' is-empty'}`} style={{ '--i': i }} data-tip={tip} tabIndex={0} aria-label={`${label}: ${value}${sub ? `, ${sub}` : ''}`} data-testid={testid}>
    <svg className="ht-vessel" viewBox="0 0 100 120" aria-hidden="true">
      <defs>
        <clipPath id={id}><path d={VESSEL[shape]} /></clipPath>
        <linearGradient id={`${id}f`} x1="0" y1="0" x2="0" y2="1"><stop className="ht-hi" offset="0" /><stop className="ht-lo" offset="1" /></linearGradient>
      </defs>
      <path className="ht-back" d={VESSEL[shape]} />
      <g clipPath={`url(#${id})`}>
        <g className="ht-level" style={{ transform: `translateY(${y}px)` }}>
          <path className="ht-wave is-rear" d={WAVE} fill={`url(#${id}f)`} />
          <path className="ht-wave" d={WAVE} fill={`url(#${id}f)`} />
          {l > 0.08 ? [22, 50, 74].map((x, k) => <circle key={x} className="ht-bub" cx={x} cy={14 + k * 7} r={1.6 + k * 0.5} style={{ '--k': k }} />) : null}
        </g>
        <path className="ht-shine" d="M26 26V84" />
      </g>
      <path className="ht-glass" d={VESSEL[shape]} />
    </svg>
    <em>{label}</em>
    <b className="m-num" key={value}>{value}</b>
    <small>{sub}</small>
  </article>;
}

const solText = v => (v >= 0.01 ? v.toFixed(4) : v > 0 ? Number(v.toPrecision(2)).toString() : '0');

// One row of vessels: where its winnings are (earned → owed → in the pot → paid back), how right its calls are, how close the airdrop is.
export function HoneyTanks({ ledger, live, colony, px }) {
  const m = ledger || {}; const earned = Number(m.earnedSol) || 0; const owed = Number(m.owedSol) || 0; const pot = Number(m.transferredSol) || 0; const paid = Number(m.distributedSol) || 0;
  const top = Math.max(earned, owed, pot, paid); const of = v => (top > 0 ? v / top : 0);
  const usd = v => (v > 0 && px ? `$${(v * px).toFixed(v * px < 1 ? 3 : 2)}` : 'nothing yet');
  const rate = live?.graded ? (live.right || 0) / live.graded : null;
  const left = colony?.nextAirdrop ? Math.max(0, colony.nextAirdrop - Date.now() / 1000) : null; const cycle = CYCLE_S[colony?.cadence] || CYCLE_S.daily;
  const c = m.check;
  return <><div className="ht-row" data-testid="honey-tanks">
    <HoneyTank i={0} shape="barrel" tone="honey" level={of(earned)} label="EARNED" value={`${solText(earned)} SOL`} sub={usd(earned)} testid="ht-earned" tip="Profit from its closed real trades, after fees. Paper trades never count." />
    <HoneyTank i={1} shape="jar" tone="amber" level={of(owed)} label="OWED" value={`${solText(owed)} SOL`} sub={m.owedCount ? `${m.owedCount} share${m.owedCount === 1 ? '' : 's'} not sent` : usd(owed)} testid="ht-owed" tip="Its share of winning trades, on the ledger but not sent to the colony wallet yet" />
    <HoneyTank i={2} shape="hex" tone="deep" level={of(pot)} label="IN THE POT" value={`${solText(pot)} SOL`} sub={m.check?.transfers ? `${m.check.confirmed} of ${m.check.transfers} confirmed on-chain` : usd(pot)} testid="ht-pot" tip="SOL its wallet really sent to the colony pot, each with an on-chain signature" />
    <HoneyTank i={3} shape="drop" tone="mint" level={of(paid)} label="PAID BACK" value={`${solText(paid)} SOL`} sub={usd(paid)} testid="ht-paid" tip="What the colony has paid out on this agent's shares" />
    <HoneyTank i={4} shape="vat" tone="violet" level={rate || 0} label="RIGHT CALLS" value={rate == null ? '—' : `${Math.round(rate * 100)}%`} sub={live ? `${live.right || 0} of ${live.graded || 0} graded` : 'reading…'} testid="ht-right" tip="Graded calls it got right this epoch, judged an hour on" />
    <HoneyTank i={5} shape="flask" tone="cyan" level={left == null ? 0 : 1 - left / cycle} label="NEXT AIRDROP" value={left == null ? '—' : `${Math.floor(left / 3600)}h ${String(Math.floor(left / 60) % 60).padStart(2, '0')}m`} sub={colony?.cadence === 'weekly' ? 'weekly' : 'every 24 h'} testid="ht-airdrop" tip="Fills up as the next colony airdrop gets closer" />
  </div>
  {c ? <p className={`ht-check${c.read && c.confirmed === c.transfers ? ' is-ok' : ' is-warn'}`} data-testid="ht-check" data-tip="Read from the chain against the colony ledger. It moves nothing."><i aria-hidden="true" />
    <span>{!c.read ? 'Chain not reachable: transfers not checked' : c.transfers ? `${c.confirmed} of ${c.transfers} transfers confirmed on-chain` : 'No transfers to check yet'}</span>
    <span>{c.potOpen ? `Pot holds ${c.potSol == null ? '…' : `${solText(c.potSol)} SOL`} · ledger in ${solText(c.ledgerInSol)} · out ${solText(c.ledgerOutSol)}` : 'Colony pot not created yet'}</span></p> : null}</>;
}
