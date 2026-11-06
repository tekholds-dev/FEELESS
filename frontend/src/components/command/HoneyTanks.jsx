import React, { Suspense, lazy } from 'react';
import { ProgressCircle } from '@heroui/react';
import '../../styles/honeyTanks.css';

const LedgerBars = lazy(() => import('./MoneyCharts').then(m => ({ default: m.LedgerBars })));
const solText = v => (v >= 0.01 ? v.toFixed(4) : v > 0 ? Number(v.toPrecision(2)).toString() : '0');
const Tile = ({ label, value, sub, tip, testid, color }) => <article className="ht-tile" style={{ '--c': color }} data-tip={tip} data-testid={testid}><small>{label}</small><b className="m-num" key={value}>{value}</b><em>{sub}</em></article>;

// Where its winnings are, on one real chart: earned, owed, in the pool, paid back. Plus how right its calls are, and how close the airdrop is.
export function HoneyTanks({ ledger, live, colony, px }) {
  const m = ledger || {}; const earned = Number(m.earnedSol) || 0; const owed = Number(m.owedSol) || 0; const pot = Number(m.transferredSol) || 0; const paid = Number(m.distributedSol) || 0;
  const usd = v => (v > 0 && px ? `$${(v * px).toFixed(v * px < 1 ? 3 : 2)}` : 'nothing yet');
  const rate = live?.graded ? (live.right || 0) / live.graded : null;
  const c = m.check;
  const rows = [['Earned', earned, '#57c7ff'], ['Owed', owed, '#c58bff'], ['In the pool', pot, '#3ee58a'], ['Paid back', paid, '#ffb454']];
  return <><div className="ht-row" data-testid="honey-tanks">
    <section className="ht-chart"><Suspense fallback={<div className="ht-wait" />}><LedgerBars rows={rows} fmt={solText} /></Suspense></section>
    <section className="ht-ring" data-tip="How many of its graded calls were right" data-testid="ht-right">
      <ProgressCircle aria-label="Right calls" value={Math.round((rate || 0) * 100)} className="ht-circle"><ProgressCircle.Track><ProgressCircle.TrackCircle /><ProgressCircle.FillCircle /></ProgressCircle.Track></ProgressCircle>
      <div><small>RIGHT CALLS</small><b className="m-num">{rate == null ? '—' : `${Math.round(rate * 100)}%`}</b><em>{live ? `${live.right || 0} of ${live.graded || 0} graded` : 'reading…'}</em></div>
    </section>
    <div className="ht-tiles">
      <Tile label="EARNED" color="#57c7ff" value={`${solText(earned)} SOL`} sub={usd(earned)} testid="ht-earned" tip="Profit from its closed real trades, after fees. Paper trades never count." />
      <Tile label="OWED" color="#c58bff" value={`${solText(owed)} SOL`} sub={m.owedCount ? `${m.owedCount} share${m.owedCount === 1 ? '' : 's'} not sent` : usd(owed)} testid="ht-owed" tip="Its share of wins it has not sent yet" />
      <Tile label="IN THE POOL" color="#3ee58a" value={`${solText(pot)} SOL`} sub={m.check?.transfers ? `${m.check.confirmed} of ${m.check.transfers} confirmed on-chain` : usd(pot)} testid="ht-pot" tip="SOL it has sent to the Pool" />
      <Tile label="PAID BACK" color="#ffb454" value={`${solText(paid)} SOL`} sub={usd(paid)} testid="ht-paid" tip="What the Collective has paid out on this agent's shares" />
    </div>
  </div>
  {c ? <p className={`ht-check${c.read && c.confirmed === c.transfers ? ' is-ok' : ' is-warn'}`} data-testid="ht-check" data-tip="Read from the chain against the Collective ledger. It moves nothing."><i aria-hidden="true" />
    <span>{!c.read ? 'Chain not reachable: transfers not checked' : c.transfers ? `${c.confirmed} of ${c.transfers} transfers confirmed on-chain` : 'No transfers to check yet'}</span>
    <span>{c.potOpen ? `Pot holds ${c.potSol == null ? '…' : `${solText(c.potSol)} SOL`} · ledger in ${solText(c.ledgerInSol)} · out ${solText(c.ledgerOutSol)}` : 'The Pool not created yet'}</span></p> : null}</>;
}
