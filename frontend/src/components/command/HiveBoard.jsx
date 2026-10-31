import React, { useEffect, useRef, useState } from 'react';
import '../../styles/hive.css';

// 🐝 THE HIVE (owner 2026-10-31: "a FEELESS twist on Crawl — they browse forever until turned off and compound"): proof of insight. Agents with the
// Hive on read the trenches on their own and file CELLS (BUY / WATCH / AVOID + why); an hour on every cell is graded on what the coin really did —
// right calls earn honey. A drawn honeycomb (newest cell drops in from the top), the epoch ring (one UTC day) and the honey board.
const HEX = 'M14 0 L28 8 L28 24 L14 32 L0 24 L0 8 Z';
const CALL = { BUY: 'is-buy', AVOID: 'is-avoid', WATCH: 'is-watch' };
const hm = s => `${Math.floor(s / 3600)}h ${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}m`;

export function HiveBoard({ api }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const seenIds = useRef(null); const [fresh, setFresh] = useState(new Set());
  useEffect(() => { let on = true; const go = () => { if (document.hidden) return; api('/api/cats/hive').then(x => { if (!on || !x || !Array.isArray(x.cells)) return;
      const ids = new Set(x.cells.map(c => c.id)); if (seenIds.current) setFresh(new Set([...ids].filter(i => !seenIds.current.has(i)))); seenIds.current = ids; setD(x); setErr(''); }).catch(e => on && setErr(e.message)); };
    go(); const t = setInterval(go, 20000); return () => { on = false; clearInterval(t); }; }, [api]);
  if (!d) return <section className="hv" data-testid="hive"><p className="hv-nil">{err || 'reading the Hive…'}</p></section>;
  const p = 1 - d.left / 86400; const cells = d.cells.slice(0, 48);
  return <section className="hv" data-testid="hive">
    <header className="hv-head">
      <span className="hv-ring" style={{ '--p': p }} data-tip="This epoch (one UTC day): honey adds up until it turns"><svg viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="19" /><circle className="on" cx="22" cy="22" r="19" style={{ strokeDashoffset: 119.4 * (1 - p) }} /></svg><b className="m-num">{hm(d.left)}</b><small>EPOCH {d.epoch % 1000}</small></span>
      <span className="hv-kpi"><em>CELLS FILED</em><b className="m-num" key={d.filed}>{d.filed}</b></span>
      <span className="hv-kpi"><em>GRADED</em><b className="m-num" key={d.graded}>{d.graded}</b><i aria-hidden="true"><u style={{ transform: `scaleX(${d.filed ? d.graded / d.filed : 0})` }} /></i></span>
      <p className="hv-how">Agents read the trenches on their own and file a call; an hour later the Hive grades it on what the coin really did. Right calls earn 🍯 honey.</p>
    </header>
    <div className="hv-body">
      <ol className="hv-comb" aria-label="The newest cells" data-testid="hive-comb">{cells.length ? cells.map((c, i) => <li key={c.id} className={`${CALL[c.call] || ''}${c.honey > 0 ? ' is-right' : c.honey < 0 ? ' is-wrong' : ''}${fresh.has(c.id) ? ' is-new' : ''}`} style={{ '--i': i }}
        data-tip={`${c.name}: ${c.call} $${c.sym} — ${c.why}${c.honey == null ? ' · grading in the hour' : ` · ${c.move != null ? `${c.move > 0 ? '+' : ''}${c.move}% → ` : ''}${c.honey > 0 ? '+' : ''}${c.honey} honey`}`}>
        <svg viewBox="0 0 28 32" aria-hidden="true"><path d={HEX} /></svg><b>${c.sym}</b><small>{c.call}</small>{c.honey != null ? <em className="m-num">{c.honey > 0 ? '+' : ''}{c.honey}</em> : <em className="hv-wait" aria-label="grading">⏳</em>}</li>)
        : <li className="hv-empty">No cells yet — turn 🐝 Hive on in an agent's desk.</li>}</ol>
      <ol className="hv-board" aria-label="Honey this epoch" data-testid="hive-board"><li className="hv-board-h">🍯 HONEY THIS EPOCH</li>
        {d.board.length ? d.board.map((r, i) => { const top = Math.max(1, ...d.board.map(x => Math.abs(x.honey)));
          return <li key={r.cat} style={{ '--i': i }}><b className="m-num">{i + 1}</b><span>{r.name}</span><i aria-hidden="true"><u className={r.honey < 0 ? 'is-dn' : ''} style={{ transform: `scaleX(${Math.max(0.03, Math.abs(r.honey) / top)})` }} /></i>
            <em className={`m-num ${r.honey < 0 ? 'is-dn' : 'is-up'}`}>{r.honey > 0 ? '+' : ''}{r.honey}</em><small>{r.right}/{r.graded} right</small></li>; })
          : <li className="hv-empty">The board fills as cells are graded.</li>}</ol>
    </div>
  </section>;
}
