import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

// 🧬 Cmd Ctr › Fuse Evolution: pick a strategy + budget, the server breeds baskets of live pools over generations
// (keep the elite, crossover, mutate — backend fuse.evolve) and returns 3 champions with every fitness part shown.
// "Load" drops a champion into the Lab above, where ⚡ Fuse in is still one wallet approval.
const STYLES = [['yield', '💧 Yield hunter'], ['momentum', '🚀 Momentum'], ['steady', '🛡 Steady'], ['degen', '🎲 Degen']];
const BUDGETS = [5, 20, 100];
const GENS = [8, 16, 32];
const usd = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v || 0)}`);
const SOL = 'So11111111111111111111111111111111111111112';

export function FuseEvolve({ call, onLoad, maxLegs = 6 }) {
  const [style, setStyle] = useState('yield'); const [legs, setLegs] = useState(3); const [gens, setGens] = useState(16); const [budget, setBudget] = useState(5);
  const [solUsd, setSolUsd] = useState(null); const [d, setD] = useState(null); const [shown, setShown] = useState(0); const [busy, setBusy] = useState(false);
  const timer = useRef(null);
  useEffect(() => { fetch(`https://lite-api.jup.ag/price/v3?ids=${SOL}`).then(r => r.json()).then(x => setSolUsd(Number(x?.[SOL]?.usdPrice) || null)).catch(() => {}); return () => clearInterval(timer.current); }, []);
  const sol = solUsd ? budget / solUsd : null;
  const run = async () => {
    setBusy(true); setD(null); setShown(0); clearInterval(timer.current);
    try {
      const r = await call('/admin/fuses/evolve', { method: 'POST', body: JSON.stringify({ style, legs, generations: gens, population: 32, sol: sol || 0.05 }) });
      setD(r); let i = 0; timer.current = setInterval(() => { i += 1; setShown(i); if (i >= r.history.length) clearInterval(timer.current); }, Math.max(30, 900 / r.history.length));
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const top = d ? Math.max(1, ...d.history.map(h => h.best)) : 1;
  const done = d && shown >= d.history.length;
  return <section className="m-card fe" data-testid="fuse-evolve">
    <header className="fe-head"><div><span className="m-label">🧬 FUSE EVOLUTION</span><h4>Breed the basket. Keep the strongest.</h4>
      <p className="m-dim">Live pools compete over generations: the fittest survive, cross over and mutate. You pick the strategy and budget; every score is shown.</p></div></header>
    <div className="fe-genes">
      <div className="fe-gene"><small>STRATEGY</small><div className="m-seg" role="radiogroup" aria-label="Strategy">{STYLES.map(([k, l]) => <button type="button" key={k} role="radio" aria-checked={style === k} className={style === k ? 'active' : ''} onClick={() => setStyle(k)}>{l}</button>)}</div></div>
      <div className="fe-gene"><small>POOLS</small><div className="m-seg">{[2, 3, 4, 5, 6].filter(n => n <= maxLegs).map(n => <button type="button" key={n} className={legs === n ? 'active' : ''} onClick={() => setLegs(n)}>{n}</button>)}</div></div>
      <div className="fe-gene"><small>GENERATIONS</small><div className="m-seg">{GENS.map(n => <button type="button" key={n} className={gens === n ? 'active' : ''} onClick={() => setGens(n)}>{n}</button>)}</div></div>
      <div className="fe-gene"><small>BUDGET</small><div className="m-seg">{BUDGETS.map(n => <button type="button" key={n} className={budget === n ? 'active' : ''} onClick={() => setBudget(n)}>${n}</button>)}</div>
        <em className="m-dim">{sol ? `≈ ${sol.toFixed(4)} SOL` : 'SOL price loading…'}</em></div>
    </div>
    <button type="button" className="m-btn primary m-go wide" disabled={busy} onClick={run} data-testid="fe-run">{busy ? 'Breeding…' : d ? '🧬 Evolve again (new seed)' : '🧬 Evolve'}</button>
    {d && <>
      <div className="fe-chart" aria-label="Best fitness per generation">{d.history.map((h, i) => <i key={h.gen} className={i < shown ? 'on' : ''} style={{ transform: `scaleY(${i < shown ? Math.max(0.04, h.best / top) : 0.02})` }} title={`Gen ${h.gen}: best ${h.best} · avg ${h.avg}`} />)}</div>
      <div className="fe-meta m-dim"><span>{d.pool} live pools in the gene pool</span><span>{d.evaluated} baskets tested</span><span>gen {Math.min(shown, d.history.length)}/{d.history.length}</span></div>
      {done && <div className="fe-champs">{d.champions.map((c, i) => <article key={c.pools.join()} className={`fe-champ ${i === 0 ? 'is-top' : ''}`} style={{ animationDelay: `${i * 70}ms` }}>
        <div className="fe-champ-head"><b>{['🥇', '🥈', '🥉'][i]} {c.fitness}</b><span className={`fl-grade g-${c.parts.grade}`}>{c.parts.grade}</span><small className="m-dim">born gen {c.bornGen}</small></div>
        <div className="fe-legs">{c.legs.map(l => <span key={l.pairAddress} className="m-chip">{l.symbol}<small>/{l.quote}</small> <b>{Math.round(l.weight)}%</b></span>)}</div>
        <dl className="m-kv fe-kv"><dt>APR score</dt><dd>{c.parts.aprScore}</dd><dt>24h momentum</dt><dd className={c.parts.momentum24h >= 0 ? 'm-pos' : 'm-neg'}>{c.parts.momentum24h}%</dd><dt>Calm</dt><dd>{c.parts.calm}</dd>
          <dt>Fee drag</dt><dd className={c.parts.feeDragPct > 5 ? 'm-neg' : ''}>{c.parts.feeDragPct}%</dd>{c.parts.impactLegs > 0 && <><dt>Size guard</dt><dd className="m-neg">{c.parts.impactLegs} pool(s) too thin</dd></>}
          <dt>Depth</dt><dd>{usd(c.legs.reduce((a, l) => a + (l.liquidityUsd || 0), 0))}</dd></dl>
        <button type="button" className={`m-btn ${i === 0 ? 'primary' : ''}`} onClick={() => onLoad?.(c.legs, sol)} data-testid={`fe-load-${i}`}>Load into Lab →</button>
      </article>)}</div>}
      {done && d.champions[0]?.parts.feeDragPct > 5 && <div className="m-note warn"><b>FEE DRAG</b><span>At ${budget}, network fees eat {d.champions[0].parts.feeDragPct}% of the buy. Fewer pools or a bigger budget keeps more of it working.</span></div>}
      {done && <small className="m-dim">Ranks baskets on live numbers (grade, fee APR, 24h move, depth). Not a promise of profit — memes move fast.</small>}
    </>}
  </section>;
}
