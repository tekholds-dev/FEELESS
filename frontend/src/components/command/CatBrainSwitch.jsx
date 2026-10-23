import React, { useEffect, useState } from 'react';
import '../../styles/catBrain.css';

// 🪟 WHO TRADES THIS CAT (owner, 2026-10-22: "NEXA trading a cat"): the FEELESS rule engine, or NEXA — the cat then buys only the coins her
// fresh desk read FAVORS (every FeeCat guard still has to pass them) and sells what she names EXIT. Paper only. Her read's freshness is the
// ring (a read older than 30 min is not acted on), her picks / exits / avoids and her graded record sit beside it.
const FRESH_MIN = 30;
const C = 2 * Math.PI * 26;

export function CatBrainSwitch({ cat, act }) {
  const [nexa, setNexa] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let live = true;
    const load = () => fetch('/api/cats/brains').then(r => r.json()).then(d => { if (live) setNexa((d.brains || []).find(b => b.id === 'nexa') || null); }).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    return () => { live = false; clearInterval(t); };
  }, []);
  const on = cat.modelBrain === 'nexa';
  const pick = async v => { if (busy || (v === 'nexa') === on) return; setBusy(true); try { await act('brain', { text: v }); } finally { setBusy(false); } };
  const live = nexa?.state === 'live';
  const fresh = live ? Math.max(0.04, 1 - (nexa.ageMin || 0) / FRESH_MIN) : 0;
  const rec = nexa?.record?.favor || {};
  const nums = [['picks', nexa?.favor, 'coins she favored in her last read — the only ones this cat may buy'], ['exits', nexa?.exit, 'held coins she said to sell'], ['avoid', nexa?.avoid, 'coins she said never to buy']];
  return <div className={`cb-wrap${on ? ' is-nexa' : ''}${live ? ' is-live' : ''}`}>
    <span className="eyebrow">DECISION ENGINE</span>
    <div className="m-seg cb-seg" role="radiogroup" aria-label="Who trades this cat">
      <button type="button" role="radio" aria-checked={!on} disabled={busy} onClick={() => pick('rules')} data-tip="The FEELESS rule engine picks and exits on its own transparent rules">⚙ Rules</button>
      <button type="button" role="radio" aria-checked={on} disabled={busy || cat.isLeader} onClick={() => pick('nexa')} data-tip="NEXA trades this cat on PAPER: only her favored coins (every guard still applies), her exits sold">🪟 NEXA</button>
    </div>
    <div className="cb-body">
      <svg className="cb-ring" viewBox="0 0 64 64" aria-hidden="true">
        <circle className="cb-track" cx="32" cy="32" r="26" />
        <circle className="cb-arc" cx="32" cy="32" r="26" strokeDasharray={`${(fresh * C).toFixed(1)} ${C.toFixed(1)}`} />
        <g className="cb-halo"><circle cx="32" cy="32" r="30" /></g>
        <g className="cb-net">
          <line x1="22" y1="26" x2="32" y2="38" /><line x1="32" y1="38" x2="42" y2="26" /><line x1="22" y1="26" x2="42" y2="26" />
          <circle cx="22" cy="26" r="3" /><circle cx="42" cy="26" r="3" /><circle className="cb-core" cx="32" cy="38" r="4" />
        </g>
      </svg>
      <div className="cb-read">
        <b>{on ? 'NEXA trades this cat' : 'FEELESS rule engine'}</b>
        <small data-tip="Her desk read runs about every 15 min on her own CPU model; a read older than 30 min is not acted on">{live ? `her read · ${nexa.ageMin} min old` : nexa ? 'waiting for her next read' : 'reading NEXA…'}</small>
        <div className="cb-nums">{nums.map(([k, v, tip], i) => <span key={k} className="cb-num" style={{ '--i': i }} data-tip={tip}><b className="fl-tick" key={v ?? '-'}>{v ?? '—'}</b><small>{k}</small></span>)}</div>
        {rec.n ? <div className="cb-rec" data-tip={`Her favored coins an hour later: ${rec.rightPct}% rose · typical ${rec.typical > 0 ? '+' : ''}${rec.typical}% (${rec.n} graded)`}>
          <small>PICKS RIGHT</small><i><em style={{ transform: `scaleX(${Math.min(1, (rec.rightPct || 0) / 100)})` }} /></i><b>{rec.rightPct}%</b>
        </div> : null}
      </div>
    </div>
    {on && nexa?.why ? <p className="cb-why">“{nexa.why}”</p> : null}
  </div>;
}
