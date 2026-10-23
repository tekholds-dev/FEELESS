import React, { useEffect, useState } from 'react';
import '../../styles/catBrain.css';

// 🪟🐱 NEXA TRADES FEECAT (owner, 2026-10-22: "nexa can do 2-3 calls every 5 mins to trade AS feecat … yay or nay"; owner only, HQ › Fee ›
// NEXA's desk). ⚙ Her rules | 🪟 NEXA: with NEXA on, FeeCat buys only coins NEXA said YES to (every guard still applies) and sells what she
// says SELL — paper. The ring counts down to her next desk round (≤ 3 one-line questions), beside it her last 15 min of words, her graded
// record and the calls themselves (the exact numbers she saw on hover).
const C = 2 * Math.PI * 26;
const FRESH = 900;
const ago = t => { const s = Date.now() / 1000 - t; return s < 60 ? `${Math.max(0, Math.round(s))}s` : `${Math.round(s / 60)}m`; };
const pct = v => `${v > 0 ? '+' : ''}${(+v || 0).toFixed(1)}%`;
const TONE = { YES: 'is-yes', HOLD: 'is-hold', NO: 'is-no', SELL: 'is-sell' };

export function deskCounts(desk, now = Date.now() / 1000) {
  const out = { YES: 0, NO: 0, SELL: 0, HOLD: 0 };
  (desk || []).forEach(c => { if (c.word && now - c.at <= FRESH) out[c.word] = (out[c.word] || 0) + 1; });
  return out;
}

// 🐱 NEXA trades AS FeeCat (owner, 2026-10-23): FeeCat's own book under her calls — what she holds now (🪟 = bought on NEXA's YES) and, when a
// YES didn't buy, the guard that stopped it (holders / pool floor never step aside). One 15 s poll of /api/cats/leader, only while NEXA trades.
export function feeBook(lead) {
  const cat = lead?.cat || {}; const scan = lead?.scan || {};
  const held = (cat.positions || []).map(p => ({ sym: p.symbol, ch: +p.currentChange || 0, sol: +p.costSol || 0, nexa: !!p.nexa, pair: p.pairAddress }));
  const stops = [...(scan.safetyRejects || []), ...(scan.brainRejects || [])].slice(-3).reverse();
  return { held, stops, bal: +cat.balanceSol || 0 };
}

// ⚔ THE DUEL (P1 #1, first cut): NEXA's YES hit rate (graded an hour later) vs FeeCat's own closed trades — two bars, the leader glows. Not
// apples to apples yet (a shadow ledger of the same coins is still open), so each side names what it counts.
export function duel(rec, cat) {
  const n = (+cat?.wins || 0) + (+cat?.losses || 0);
  const nx = rec?.n ? { pct: +rec.rightPct || 0, n: rec.n, typical: +rec.typical || 0 } : null;
  const rl = n ? { pct: Math.round(100 * (+cat.wins || 0) / n), n } : null;
  return { nx, rl, lead: nx && rl ? (nx.pct > rl.pct ? 'nexa' : nx.pct < rl.pct ? 'rules' : 'tie') : null };
}

export function CatBrainSwitch({ d, busy, act }) {
  const [, tick] = useState(0);
  const [lead, setLead] = useState(null);
  useEffect(() => { const t = setInterval(() => tick(x => x + 1), 5000); return () => clearInterval(t); }, []);
  const on = !!d?.trade;
  useEffect(() => {
    if (!on) return undefined;
    let alive = true;
    const go = () => { if (!document.hidden) fetch('/api/cats/leader').then(r => (r.ok ? r.json() : null)).then(x => { if (alive && x) setLead(x); }).catch(() => {}); };
    go(); const t = setInterval(go, 15000); return () => { alive = false; clearInterval(t); };
  }, [on]);
  const book = feeBook(lead);
  const dv = duel(d?.record?.favor, lead?.cat);
  const every = d?.deskEvery || 300;
  const since = d?.deskAt ? Date.now() / 1000 - d.deskAt : every;
  const fill = on ? Math.max(0.04, Math.min(1, since / every)) : 0;
  const n = deskCounts(d?.desk);
  const rec = d?.record?.favor || {};
  const calls = (d?.desk || []).slice(-6).reverse();
  const nums = [['YES', n.YES, 'coins she said YES to in the last 15 min — the only ones FeeCat may buy'], ['NO', n.NO, 'coins she passed on'], ['SELL', n.SELL, 'held coins she said to sell']];
  return <article className={`cb-wrap nxd-trade${on ? ' is-nexa' : ''}${on && d?.provider?.on ? ' is-live' : ''}`} data-testid="nexa-trade">
    <header className="cb-top"><span className="eyebrow">🐱 WHO TRADES FEECAT</span>
      <div className="m-seg cb-seg" role="radiogroup" aria-label="Who trades FeeCat">
        <button type="button" role="radio" aria-checked={!on} disabled={busy || !d} onClick={() => on && act({ trade: false })} data-tip="FeeCat trades on her own rule engine (NEXA still advises: skip / bank)">⚙ Her rules</button>
        <button type="button" role="radio" aria-checked={on} disabled={busy || !d} onClick={() => !on && act({ trade: true })} data-testid="nexa-trade-on"
          data-tip={`NEXA trades AS FeeCat on paper: ≤ ${d?.deskCalls || 3} yes / no questions every ${Math.round(every / 60)} min — her YES is the call (chart / memory second opinions step aside, half size on a veto); rug guards — pool floor, holders, discipline — never do. Sells her SELL`}>🪟 NEXA trades</button>
      </div></header>
    <div className="cb-body">
      <svg className="cb-ring" viewBox="0 0 64 64" aria-hidden="true">
        <circle className="cb-track" cx="32" cy="32" r="26" />
        <circle className="cb-arc" cx="32" cy="32" r="26" strokeDasharray={`${(fill * C).toFixed(1)} ${C.toFixed(1)}`} />
        <g className="cb-halo"><circle cx="32" cy="32" r="30" /></g>
        <g className="cb-net">
          <line x1="22" y1="26" x2="32" y2="38" /><line x1="32" y1="38" x2="42" y2="26" /><line x1="22" y1="26" x2="42" y2="26" />
          <circle cx="22" cy="26" r="3" /><circle cx="42" cy="26" r="3" /><circle className="cb-core" cx="32" cy="38" r="4" />
        </g>
      </svg>
      <div className="cb-read">
        <b>{on ? 'NEXA trades FeeCat' : 'FeeCat on her own rules'}</b>
        <small data-tip="The ring fills toward her next desk round">{!on ? 'switch on to hand her the desk · paper' : !d?.provider?.on ? 'NEXA is not connected — FeeCat holds, her stops still run'
          : d?.deskAt ? `last round ${ago(d.deskAt)} ago · next in ${Math.max(0, Math.round((every - since) / 60))}m` : 'first round starting…'}</small>
        <div className="cb-nums">{nums.map(([k, v, tip], i) => <span key={k} className={`cb-num ${TONE[k]}`} style={{ '--i': i }} data-tip={tip}><b className="fl-tick" key={v}>{v}</b><small>{k}</small></span>)}</div>
        {rec.n ? <div className="cb-rec" data-tip={`Her YES / favored coins an hour later: ${rec.rightPct}% rose · typical ${rec.typical > 0 ? '+' : ''}${rec.typical}% (${rec.n} graded)`}>
          <small>YES RIGHT</small><i><em style={{ transform: `scaleX(${Math.min(1, (rec.rightPct || 0) / 100)})` }} /></i><b>{rec.rightPct}%</b>
        </div> : null}
      </div>
    </div>
    {on && (dv.nx || dv.rl) ? <div className={`cb-duel is-${dv.lead || 'none'}`} data-testid="nexa-duel">
      <span className="cb-duel-h">⚔ THE DUEL</span>
      {[['nexa', '🪟 NEXA', dv.nx, dv.nx ? `her YES rose an hour later · ${dv.nx.n} graded · typical ${pct(dv.nx.typical)}` : 'no graded calls yet'],
        ['rules', '⚙ RULES', dv.rl, dv.rl ? `FeeCat's closed trades won · ${dv.rl.n} trades` : 'no closed trades yet']].map(([k, label, v, tip], i) =>
        <span key={k} className={`cb-side is-${k}`} style={{ '--i': i }} data-tip={tip}><small>{label}</small>
          <i><em style={{ transform: `scaleX(${v ? Math.min(1, v.pct / 100) : 0})` }} /></i><b className="fl-tick" key={v?.pct}>{v ? `${v.pct}%` : '—'}</b></span>)}
      <small className="cb-duel-why">{dv.lead === 'nexa' ? 'NEXA leads — real money still waits on a same-coin shadow ledger' : dv.lead === 'rules' ? 'the rules lead — NEXA stays on paper / signed proposals' : 'too early to call'}</small>
    </div> : null}
    {on ? <div className="cb-book" data-testid="nexa-feebook">
      <span className="cb-book-h" data-tip="FeeCat's own paper book — NEXA's YES buys land here, as FeeCat">🐱 FEECAT'S BOOK<small>{book.bal.toFixed(2)} SOL free</small></span>
      {book.held.length ? book.held.map((h, i) => <span key={h.pair} className={`cb-pos ${h.ch >= 0 ? 'is-up' : 'is-dn'}`} style={{ '--i': i }}
        data-tip={`${h.nexa ? 'Bought on NEXA\'s YES' : 'Bought on FeeCat\'s own rules'} · ${h.sol} SOL in (paper)`}>
        {h.nexa ? <i aria-hidden="true">🪟</i> : null}<b>${h.sym}</b><em className="fl-tick" key={h.ch.toFixed(1)}>{pct(h.ch)}</em></span>)
        : <span className="cb-pos is-flat">flat — waiting on a YES that clears the rug guards</span>}
      {book.stops.length ? <span className="cb-stops">{book.stops.map((x, i) => <small key={`${x.symbol}-${i}`} data-tip="The guard that stopped this buy — rug guards never step aside for NEXA">🛡 ${x.symbol}: {x.why}</small>)}</span> : null}
    </div> : null}
    {calls.length ? <ol className="cb-calls">{calls.map((c, i) => <li key={`${c.at}-${c.pair}`} style={{ '--i': i }} data-tip={c.line}>
      <span className={`cb-word ${TONE[c.word] || 'is-none'}`}>{c.word || '—'}</span><b>${c.symbol || c.pair?.slice(0, 5)}</b><em>{c.why || (c.word ? '' : 'no clear word')}</em>
      <small>{c.ms ? `${Math.round(c.ms / 1000)}s · ` : ''}{ago(c.at)}</small></li>)}</ol> : on ? <p className="cb-why">Her desk calls land here — one line of numbers per coin, one word back.</p> : null}
  </article>;
}

// A user's cat: the FEELESS rule engine (NEXA trades only FeeCat herself, from the owner's HQ).
export function EngineLine() {
  return <div className="cb-wrap cb-engine"><span className="eyebrow">DECISION ENGINE</span><b>FEELESS rule engine</b><small>Live DexScreener prices · transparent entry / exit rules</small></div>;
}
