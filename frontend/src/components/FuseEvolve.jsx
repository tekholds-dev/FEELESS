import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { FuseCard } from './FuseCard';

// 🧬 Cmd Ctr › Fuse Evolution: pick a strategy + budget, the server breeds baskets of live pools over generations
// (keep the elite, crossover, mutate — backend fuse.evolve) and returns 3 champions with every fitness part shown.
// "Load" drops a champion into the Lab above, where ⚡ Fuse in is still one wallet approval.
const STYLES = [['yield', '💧 Yield hunter'], ['momentum', '🚀 Momentum'], ['steady', '🛡 Steady'], ['degen', '🎲 Degen']];
const BUDGETS = [5, 20, 100];
const GENS = [8, 16, 32];
const SOL = 'So11111111111111111111111111111111111111112';

export function FuseEvolve({ call, onLoad, maxLegs = 10 }) {
  const [style, setStyle] = useState('yield'); const [legs, setLegs] = useState(3); const [gens, setGens] = useState(16); const [budget, setBudget] = useState(5);
  const [solUsd, setSolUsd] = useState(null); const [d, setD] = useState(null); const [shown, setShown] = useState(0); const [busy, setBusy] = useState(false); const [blood, setBlood] = useState(false);
  const timer = useRef(null);
  useEffect(() => { fetch(`https://lite-api.jup.ag/price/v3?ids=${SOL}`).then(r => r.json()).then(x => setSolUsd(Number(x?.[SOL]?.usdPrice) || null)).catch(() => {}); return () => clearInterval(timer.current); }, []);
  const sol = solUsd ? budget / solUsd : null;
  const run = async () => {
    setBusy(true); setD(null); setShown(0); clearInterval(timer.current);
    try {
      const r = await call('/admin/fuses/evolve', { method: 'POST', body: JSON.stringify({ style, legs, generations: gens, population: 32, sol: sol || 0.05, bloodline: blood }) });
      setD(r); let i = 0; timer.current = setInterval(() => { i += 1; setShown(i); if (i >= r.history.length) clearInterval(timer.current); }, Math.max(30, 900 / r.history.length));
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const act = (action, c) => call('/admin/fuses/hq', { method: 'POST', body: JSON.stringify({ action, style, champion: c }) })
    .then(() => { toast.success(action === 'arena' ? 'Entered the arena — settles in 24h' : 'Saved to bloodline'); window.dispatchEvent(new Event('feeless:fuse-hq')); }).catch(e => toast.error(e.message));
  const top = d ? Math.max(1, ...d.history.map(h => h.best)) : 1;
  const done = d && shown >= d.history.length;
  return <section className="m-card fe" data-testid="fuse-evolve">
    <header className="fe-head"><div><span className="m-label">🧬 FUSE EVOLUTION</span><h4>Breed the basket. Keep the strongest.</h4>
      <p className="m-dim">Live pools compete over generations: the fittest survive, cross over and mutate. You pick the strategy and budget; every score is shown.</p></div></header>
    <div className="fe-genes">
      <div className="fe-gene"><small>STRATEGY</small><div className="m-seg" role="radiogroup" aria-label="Strategy">{STYLES.map(([k, l]) => <button type="button" key={k} role="radio" aria-checked={style === k} className={style === k ? 'active' : ''} onClick={() => setStyle(k)}>{l}</button>)}</div></div>
      <div className="fe-gene"><small>POOLS</small><div className="m-seg">{[2, 3, 4, 5, 6, 8, 10].filter(n => n <= maxLegs).map(n => <button type="button" key={n} className={legs === n ? 'active' : ''} onClick={() => setLegs(n)}>{n}</button>)}</div></div>
      <div className="fe-gene"><small>GENERATIONS</small><div className="m-seg">{GENS.map(n => <button type="button" key={n} className={gens === n ? 'active' : ''} onClick={() => setGens(n)}>{n}</button>)}</div></div>
      <div className="fe-gene"><small>BUDGET</small><div className="m-seg">{BUDGETS.map(n => <button type="button" key={n} className={budget === n ? 'active' : ''} onClick={() => setBudget(n)}>${n}</button>)}</div>
        <em className="m-dim">{sol ? `≈ ${sol.toFixed(4)} SOL` : 'SOL price loading…'}</em></div>
    </div>
    <label className="m-toggle fe-blood"><input type="checkbox" checked={blood} onChange={e => setBlood(e.target.checked)} /><span>Breed from bloodline (saved champions seed gen 0)</span></label>
    <button type="button" className="m-btn primary m-go wide" disabled={busy} onClick={run} data-testid="fe-run">{busy ? 'Breeding…' : d ? '🧬 Evolve again (new seed)' : '🧬 Evolve'}</button>
    {d && <>
      <div className="fe-chart" aria-label="Best fitness per generation">{d.history.map((h, i) => <i key={h.gen} className={i < shown ? 'on' : ''} style={{ transform: `scaleY(${i < shown ? Math.max(0.04, h.best / top) : 0.02})` }} title={`Gen ${h.gen}: best ${h.best} · avg ${h.avg}`} />)}</div>
      <div className="fe-meta m-dim"><span>{d.pool} live pools in the gene pool</span><span>{d.evaluated} baskets tested</span><span>gen {Math.min(shown, d.history.length)}/{d.history.length}</span>{d.seeded > 0 && <span>🧬 {d.seeded} bloodline seeds</span>}</div>
      {done && <div className="fe-champs">{d.champions.map((c, i) => <article key={c.pools.join()} className={`fe-champ ${i === 0 ? 'is-top' : ''}`} style={{ animationDelay: `${i * 70}ms` }}>
        <FuseCard c={c} style={d.style || style} rank={i} />
        <div className="fe-acts"><button type="button" className={`m-btn ${i === 0 ? 'primary' : ''}`} onClick={() => onLoad?.(c.legs, sol)} data-testid={`fe-load-${i}`}>Load into Lab →</button>
          <button type="button" className="m-btn" title="Paper $5 for 24h at real prices" onClick={() => act('arena', c)} data-testid={`fe-arena-${i}`}>🏟</button>
          <button type="button" className="m-btn" title="Save to bloodline" onClick={() => act('bloodline', c)}>🧬</button></div>
      </article>)}</div>}
      {done && d.champions[0]?.parts.feeDragPct > 5 && <div className="m-note warn"><b>FEE DRAG</b><span>At ${budget}, network fees eat {d.champions[0].parts.feeDragPct}% of the buy. Fewer pools or a bigger budget keeps more of it working.</span></div>}
      {done && <small className="m-dim">Ranks baskets on live numbers (grade, fee APR, 24h move, depth). Not a promise of profit — memes move fast.</small>}
    </>}
  </section>;
}
