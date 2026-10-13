import React from 'react';
import { useLivePrices } from '../../lib/livePrices';
import { freshness, useOffice } from '../../lib/agentHub';
import { devilOf } from '../../lib/agentRead';
import '../../styles/seatOps.css';

// ⚙ THE KERNEL on the Agents tab: four hunter lanes (HUNTING · ARMED · HELD) + the candidates the ten-agent brain ranks — one row each:
// rank · trigger · Devil's WORST severity · Warden's size · Courier · Reaper · and how old the MARKET data vs the last DECISION vs the
// evidence are. It draws the office payload; it never decides. (The fresh-pipeline / RPC-lane / active-index blocks that lived here
// were only drawn by the retired room — removed 2026-10-12, with their payload sections.)
const LANE_CLS = { HELD: 'is-ok', ARMED: 'is-ready', HUNTING: 'is-wait' };
const DEVIL_CLS = { veto: 'is-bad', warn: 'is-warn', clear: '' };
const SCAN_WORD = { FRESH: 'fresh', STALE: 'stale', PENDING: 'pending', RATE_LIMITED: 'rate-limited', UNAVAILABLE: 'unavailable' };   // the EVIDENCE state of the holder scan — never a verdict on the coin
export function KernelBoard({ o: o0, onCoin }) {
  const o = useOffice(o0); const k = o?.kernel; const cands = (k?.candidates || []).slice(0, 8);
  const px = useLivePrices(cands.map(c => c.pair).filter(Boolean));
  if (!k) return null;
  const age = v => (v == null ? '—' : v < 60 ? `${Math.round(v)}s` : `${Math.round(v / 60)}m`);
  return <div className="sop-kernel" data-testid="kernel-board">
    <div className="sop-sum">{(k.lanes || []).map(l => <span key={l.lane} className={`sop-chip ${LANE_CLS[l.state] || ''}`} data-testid={`hunter-${l.lane}`} data-tip={l.state === 'HUNTING' ? 'searching — the best contender so far is shown' : l.state === 'ARMED' ? 'a READY coin is lined up for this lane' : 'capital deployed'}>
      <small>HUNTER {l.lane}</small><b>{l.state}{l.symbol ? ` · $${l.symbol}` : ''}</b></span>)}</div>
    <ul className="sop-board">{cands.map(c => { const dv = devilOf(c); const f = freshness(c, px.get(c.pair));
      return <li key={c.mint} data-testid={`kc-${c.symbol}`}>
        <span className="sop-k"><button type="button" className="sop-coin" onClick={() => onCoin && onCoin(c.symbol, c.mint)}>${c.symbol}</button></span>
        <span className="sop-v"><i className={`sop-tag ${c.status === 'READY' || c.status === 'HELD' ? 'is-ok' : 'is-wait'}`}>{c.status}</i> rank {Math.round(c.rank)} · {c.narrative?.toLowerCase()} · trigger {c.trigger}
          {dv.verdict !== 'clear' ? <i className={`sop-tag ${DEVIL_CLS[dv.verdict]}`} data-testid={`kc-devil-${c.symbol}`} data-tip={dv.objections.map(x => `${String(x.severity).replace(/_/g, ' ').toLowerCase()}: ${x.evidence}`).join(' · ')}>{dv.word}</i> : null}
          <u> size ×{c.size}</u>{c.courier ? null : <i className="sop-tag is-bad">EXECUTION BLOCKED</i>}{c.reaper ? <u> · reaper {c.reaper.action}</u> : null}</span>
        <span className="sop-full" data-testid={`kc-fresh-${c.symbol}`}>market {age(f.market)} ago · decision {age(f.decision)} ago · research {age(f.research)} · holders {age(f.holders)}{f.scan ? ` (scan ${SCAN_WORD[f.scan] || f.scan})` : ''}{c.unknown?.length ? ` · researching: ${c.unknown.join(', ')}` : ''}</span></li>; })}</ul>
  </div>;
}
