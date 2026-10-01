import { RunnerSettings, EngineSuggest } from './command/FuseAdminSettings';
import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { FuseCard } from './FuseCard';
import { FuseGo } from './FuseGo';
import { TokenAvatar } from './terminal/MarketPrimitives';
import { investigate } from './CaseFile';
import { useLivePrices } from '../lib/livePrices';
import '../styles/runners.css';

// 🏃 FUSE RUNNERS — coins come to it. Every launchpad coin the feed sees is gated (rugs out), scored, laned (scalp / runner
// / hold) with a preset exit ladder; every 15 min a round keeps the best runners and adds newcomers; every round is
// run with $5 at live prices. The Fuse button only lights when the last 24h of rounds actually won. One shared /runners poll (20s).
export const LANES = [['scalp', '🔥', 'SCALP', 'Pre-bond rush'], ['runner', '🏃', 'RUNNERS', '1–48h momentum'], ['hold', '💎', 'HOLD', 'Stayed 2+ rounds']];
const pct = v => `${v >= 0 ? '+' : ''}${Math.abs(v) >= 1000 ? `${(1 + v / 100).toFixed(1)}x` : `${(v || 0).toFixed(1)}%`}`;
const usd = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v || 0)}`);
export const ago = at => { const m = Math.max(1, Math.round((Date.now() / 1000 - at) / 60)); return m < 60 ? `${m}m` : m < 2880 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`; };
const pairOf = r => ({ chainId: 'solana', baseToken: { address: r.mint, symbol: r.symbol }, info: { imageUrl: r.logo } });

export function useRunners() {
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true; const load = () => fetch(apiUrl('/api/reputation/runners')).then(r => r.json()).then(x => alive && x?.live && setD(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 20000); window.addEventListener('feeless:runners', load);
    return () => { alive = false; clearInterval(t); window.removeEventListener('feeless:runners', load); };
  }, []);
  return d;
}

export function Countdown({ at }) {
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, []);
  const s = Math.max(0, Math.round(at - now));
  return <b className="m-num">{String(Math.floor(s / 60)).padStart(2, '0')}:{String(s % 60).padStart(2, '0')}</b>;
}

export function ProofRing({ p, need }) {
  const deg = Math.max(0, Math.min(100, p.winRate)) * 3.6;
  return <div className={`rn-proof ${p.lights ? 'is-lit' : ''}`} data-tip={p.lights ? `Lit: last 24h of rounds averaged ${pct(p.avgPct)}, ${p.winRate}% won.` : `Proving: needs ${need} rounds, a positive average and ≥50% won before the button lights.`}>
    <div className="rn-ring" style={{ '--deg': `${deg}deg` }}><span><b className="m-num">{p.rounds ? pct(p.avgPct) : '—'}</b><small>{p.winRate}% won</small></span></div>
    <div className="rn-proof-txt"><small data-tip="We run $5 through every round at live prices with the lane exits">WE RUN $5 · 24H</small><b>{p.lights ? '🔥 LIT' : p.need ? `PROVING · ${p.need} more rounds` : 'NOT WINNING YET'}</b><em>{p.rounds} rounds · $1 → ${p.per1.toFixed(2)}</em></div>
  </div>;
}

export function CoinRow({ r, live, px }) {
  // px = the shared 10s live price (lib/livePrices) when the poller has this pool; else the server's last read.
  const now = px?.price || r.now || r.price;
  const move = live && r.entry ? (now / r.entry - 1) * 100 : px ? px.h1 : r.chg1h;
  return <div className={`rn-coin lane-${r.lane || 'runner'}`}>
    <span className="rn-logo"><TokenAvatar pair={pairOf(r)} size={30} /></span>
    <span className="rn-name"><b>{r.symbol ? `$${r.symbol}` : `${r.mint.slice(0, 4)}…`}</b><small>{r.stage === 'curve' ? <i className="rn-curve" data-tip={`${r.curve.toFixed(0)}% up the bonding curve — pre-bond`}><i style={{ transform: `scaleX(${Math.min(1, r.curve / 100)})` }} /></i> : <em className="rn-grad" data-tip="Graduated — has its own pool">GRAD</em>}
      {r.streak > 1 && <em className="rn-streak" data-tip={`Stayed in the top for ${r.streak} rounds`}>↻{r.streak}</em>}</small></span>
    <span className="rn-score" data-tip={(r.parts || []).map(p => `${p.part}: +${p.points} (${p.why})`).join('\n')}><i style={{ transform: `scaleX(${Math.min(1, (r.score || 0) / 100)})` }} /><b className="m-num">{Math.round(r.score || 0)}</b></span>
    <span className={`m-num rn-move fl-tick ${(move || 0) >= 0 ? 'm-pos' : 'm-neg'}`} key={(move || 0).toFixed(1)} data-tip={live ? 'Since this round picked it (live)' : 'Last hour (live)'}>{pct(move)}</span>
    <button type="button" className="rn-case" onClick={() => investigate(r.mint)} aria-label="Case file" data-tip="Open the coin's case file">🔎</button>
  </div>;
}

export function RunnersPanel({ call }) {
  const d = useRunners();
  const lp = useLivePrices([...(d?.round?.picks || []), ...(d?.live || []).slice(0, call ? 60 : 12)].map(x => x.pairAddress));
  const [budget, setBudget] = useState(5); const [go, setGo] = useState(false); const [override, setOverride] = useState(false); const [showDrop, setShowDrop] = useState(false);
  const picks = useMemo(() => d?.round?.picks || [], [d]);
  const legs = useMemo(() => picks.map(p => ({ chainId: 'solana', pairAddress: p.pairAddress, symbol: p.symbol || `${p.mint.slice(0, 4)}…`, baseAddress: p.mint, logo: p.logo, weight: 100 / picks.length, change24h: p.chg1h, liquidityUsd: p.liq })), [picks]);
  if (!d) return <section className="rn" data-testid="runners"><div className="rn-hero is-ghost" /></section>;
  const lit = d.proof.lights || override;
  const sol = d.solUsd ? budget / d.solUsd : null;
  const force = () => call?.('/admin/runners/round', { method: 'POST' }).then(() => { toast.success('New round dealt'); window.dispatchEvent(new Event('feeless:runners')); }).catch(e => toast.error(e.message));
  return <section className="rn" data-testid="runners">{call && <><EngineSuggest call={call} /><RunnerSettings call={call} /></>}
    <header className="rn-hero">
      <div className="rn-title"><span className="m-label">🏃 FUSE RUNNERS · LIVE</span><h3>Coins come to it.</h3>
        <p>Every Pump.fun coin the feed sees is gated, scored and laned the moment it arrives. Every 15 min a round keeps the best runners and deals in new ones. Each lane has its exit plan baked in.</p></div>
      <ProofRing p={d.proof} need={d.lightMinRounds} />
      <div className="rn-clock" data-tip="Next round: the best runners stay, the rest are replaced"><small>NEXT ROUND</small><Countdown at={d.nextRoundAt} />{call && <button type="button" className="m-btn fl-clear" onClick={force}>Deal now</button>}</div>
    </header>
    <ol className="rn-pipe">{[['📡', 'Arrived', d.seen], ['🛡', 'Passed gates', d.live.length], ['✕', 'Dropped', d.dropped.length], ['🎯', 'In round', picks.length]].map(([i, l, n], k) =>
      <li key={l} style={{ animationDelay: `${k * 60}ms` }} data-tip={l === 'Passed gates' ? d.gates.join(' · ') : undefined}><b>{i}</b><span><em className="m-num">{n}</em><small>{l}</small></span></li>)}</ol>
    <div className="rn-lanes">{LANES.map(([k, ic, name, sub]) => { const rows = picks.filter(p => p.lane === k); return <div key={k} className={`rn-lane lane-${k}`}>
      <header><b>{ic} {name}</b><small>{sub}</small><em data-tip="Preset exits — alerts you at each step for a one-tap sell">{d.exits[k]}</em></header>
      {rows.length ? rows.map(r => <CoinRow key={r.mint} r={r} live px={lp.get(r.pairAddress)} />) : <p className="m-dim rn-empty">{k === 'hold' ? 'A runner lands here after 2 rounds in the top.' : 'Nothing in this lane this round.'}</p>}
    </div>; })}</div>
    {(d.round?.swaps || []).length > 0 && <div className="rn-swaps" data-testid="rn-swaps">{d.round.swaps.slice(-3).reverse().map(s => <span key={s.at}>🔁 auto-swapped <b>${s.out.symbol}</b> → <b>${s.in.symbol}</b><small>{s.why[0]}</small></span>)}</div>}
    {picks.length > 0 && <div className={`rn-fuse ${d.proof.lights ? 'is-lit' : ''}`} key={d.round?.id}>
      <FuseCard c={{ pools: legs.map(l => l.pairAddress), fitness: Math.round(picks.reduce((a, p) => a + p.score, 0) / picks.length), bornGen: d.history.length,
        parts: { grade: d.proof.lights ? 'A' : 'C', aprScore: 0, momentum24h: 0, calm: '—', feeDragPct: sol ? Math.min(100, 0.0001 * picks.length * d.solUsd / budget * 100) : 0, impactLegs: 0 }, legs }} style="degen" rank={0} budget={budget} autoFlip={6000} />
      <div className="rn-fuse-side">
        <span className="m-label">RUNNER FUSE · THIS ROUND</span>
        <p className="m-dim">{picks.length} runners, equal weight. Each is bought by mint (pre-bond on the curve or from its new pool) in one wallet approval; its lane's exit plan goes on your 🎯 limits.</p>
        <div className="m-seg">{[1, 2, 5].map(v => <button type="button" key={v} className={budget === v ? 'active' : ''} onClick={() => setBudget(v)}>${v}</button>)}</div>
        {call && !d.proof.lights && <label className="m-toggle rn-override" data-tip="Admin only: fuse before the $5 run is positive"><input type="checkbox" checked={override} onChange={e => setOverride(e.target.checked)} /><span>Fuse unproven ($5 run: {d.proof.rounds ? pct(d.proof.avgPct) : 'no rounds yet'})</span></label>}
        {!go ? <button type="button" className={`m-btn primary m-go wide rn-go ${lit ? 'is-lit' : ''}`} disabled={!lit || !sol} onClick={() => setGo(true)} data-testid="rn-go">{lit ? `⚡ Fuse runners · $${budget}` : `🔒 Lights up when proven (${d.proof.need ? `${d.proof.need} rounds to go` : 'not winning yet'})`}</button>
          : <FuseGo legs={legs.map(l => ({ ...l, sol: Math.round(sol / legs.length * 1e6) / 1e6 }))} fuse={{ name: 'Runner Fuse' }} onClose={() => setGo(false)} />}
      </div>
    </div>}
    <div className="rn-cols">
      <div className="rn-board"><header><b>📡 Live board</b><small className="m-dim">{d.live.length} passing every gate · best first</small></header>{d.live.slice(0, call ? 60 : 12).map(r => <CoinRow key={r.mint} r={r} px={lp.get(r.pairAddress)} />)}
        {!d.live.length && <><p className="m-dim rn-empty">Nothing passes every gate this minute — watching the busiest arrivals:</p>
          <ul className="rn-drop">{d.dropped.slice(0, 6).map(r => <li key={r.mint}><b>${r.symbol}</b><span>{r.gates.slice(0, 2).join(' · ')}</span></li>)}</ul></>}
        <button type="button" className="rn-drop-toggle" aria-expanded={showDrop} onClick={() => setShowDrop(s => !s)}>{showDrop ? 'Hide' : 'Show'} the {d.dropped.length} dropped (why)</button>
        {showDrop && <ul className="rn-drop">{d.dropped.map(r => <li key={r.mint}><b>${r.symbol}</b><span>{r.gates.slice(0, 2).join(' · ')}{r.gates.length > 2 ? ` +${r.gates.length - 2}` : ''}</span></li>)}</ul>}</div>
      <div className="rn-hist"><header><b>🏟 Last rounds · we run $5</b><small className="m-dim">equal $ · lane exits</small></header>
        {d.history.length ? <ol className="rn-rounds" data-testid="rn-rounds">{d.history.map((h, i) => { const up = h.pct >= 0; const end = 5 * (1 + h.pct / 100);
          return <li key={h.id} className={up ? 'up' : 'down'} style={{ '--i': i }}>
            <span className="rn-r-when m-num">{ago(h.at)}</span>
            <span className="rn-r-coins">{h.symbols.map(s => `$${s}`).join(' · ')}</span>
            <i className="rn-r-bar"><i style={{ transform: `scaleX(${Math.min(1, Math.max(0.04, Math.abs(h.pct) / 60))})` }} /></i>
            <b className={`m-num ${up ? 'm-pos' : 'm-neg'}`}>{pct(h.pct)}</b><small className="m-num">$5 → ${end.toFixed(2)}</small></li>; })}</ol>
          : <p className="m-dim">The first rounds are being dealt.</p>}
        <small className="m-dim">We run $5 through every round at live prices with its lane exits — a track record, not a promise. Pre-bond coins can go to zero in minutes; gates and exits cut that, they don't prevent it.</small></div>
    </div>
  </section>;
}
