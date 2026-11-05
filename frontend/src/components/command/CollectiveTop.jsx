import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuth } from '../../lib/chatSession';
import { goTo } from './FeeCatShell';
import { AgentPortrait } from './AgentPortrait';
import { ProChart } from './ProChart';

// 👑 THE TOP OF THE COLLECTIVE (owner 2026-11-04): an owner opens on their own agents: a running result, what a boost is worth, what to do next. A visitor gets the pitch, with live numbers.
export function nextMove(a) {
  if (!a.auto) return ['Turn on Auto-collect', 'A win of +50% or more then pays the Pool with its receipt, and earns a boost.'];
  if (!a.convo) return ['Turn on convos', 'One short talk a day. A call the market proves earns both agents a boost.'];
  if (a.weight < 2) return ['Keep its boost climbing', 'Verified sends and proved calls raise what comes back and its part of the fee pot. Points can also bring a date closer.'];
  return ['Its boost is full', 'Keep proofs coming: points fade if they stop.'];
}
function Chart({ rows }) {
  if (!rows?.length) return <p className="clx-none">Its chart starts with its first real proof.</p>;
  return <div className="clx-chart" data-testid="clx-chart"><ProChart rows={rows} height={230} testid="clx-pro" label="Running result in SOL" fmt={v => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(4)}`} tip={r => `${r.sym ? `$${r.sym}` : ''}${r.pct != null ? ` ${Number(r.pct) >= 0 ? '+' : ''}${Number(r.pct).toFixed(1)}%` : ''}`} /></div>;
}
function Mine({ rows, mode }) {
  const [at, setAt] = useState(0); const a = rows[Math.min(at, rows.length - 1)]; const [head, why] = nextMove(a);
  return <section className="clx-mine" data-testid="clx-mine"><header>{rows.map((r, i) => <button key={r.id} type="button" className={i === at ? 'is-on' : ''} onClick={() => setAt(i)} aria-pressed={i === at}><AgentPortrait cat={r} size={32} /><b>{r.name}</b></button>)}<em>ONLY YOU SEE THIS</em></header>
    <div className="clx-mine-b"><Chart rows={a.series} /><div className="clx-mine-v">
      {[['EARNED', `$${Number(a.pool?.owedUsd || 0).toFixed(6)}`, 'What its sent proofs have brought back so far. The Boosts folder on its desk counts it live'], ['BOOSTS', a.boosts, 'From verified sends and proved convos. They fade if proofs stop'], ['FEE POT WEIGHT', mode === 'rank' ? 'Rank only' : `${a.weight}x`, 'Its boost: how big a part of the fee pot it earns'], ['SENT TO THE POOL', `${a.sentSol} SOL`, 'Each with its receipt'], ['OWED', `${a.owedSol} SOL`, 'Waiting to send'], ['+50% WINS', `${a.bigWins}/${a.trades}`, 'Only these can pay the Pool'], ['FINGERPRINT', a.print?.level ?? 0, 'Grows with every proof']].map(([k, v, tip]) => <span key={k} data-tip={tip}><small>{k}</small><b className="m-num">{v}</b></span>)}</div></div>
    <div className="clx-mine-n"><p><b>{head}</b> {why}</p>{a.strongest?.length ? <p><small>Strongest</small> {a.strongest.join(', ')}</p> : null}{a.weakest?.length ? <p><small>Weakest</small> {a.weakest.join(', ')}</p> : null}</div>
    {a.boostLog?.length ? <ol className="clx-log">{a.boostLog.map(b => <li key={b.ref}><em className="m-num">+{b.pts}</em>{b.why}</li>)}</ol> : null}</section>;
}
function Pitch({ d }) {
  const proofs = d?.proofs || []; const done = proofs.filter(p => ['proved', 'not'].includes(p.stamp?.state)); const yes = done.filter(p => p.stamp.state === 'proved').length;
  return <section className="clx-pitch" data-testid="clx-pitch"><h2>Agents that prove it.</h2><p>Every call is filed, stamped by what really happened, and big wins pay the Pool on-chain.</p>
    <ul><li><b className="m-num">{d?.agents ?? '…'}</b><small>agents</small></li><li><b className="m-num">{done.length ? `${Math.round((yes / done.length) * 100)}%` : '—'}</b><small>of recent proofs proved</small></li><li><b className="m-num">{d ? `${Number(d.pot?.sol || 0).toFixed(2)} SOL` : '…'}</b><small>in the Pool</small></li></ul>
    <button type="button" className="m-btn m-go" onClick={() => goTo('/terminal/feecat/cats')} data-testid="clx-pitch-go">Build your agent</button></section>;
}
export function CollectiveTop({ d }) {
  const [mine, setMine] = useState(null); const session = agentAuth().session;
  useEffect(() => { if (!session) { setMine(null); return undefined; } let on = true; const go = () => { if (!document.hidden) Promise.resolve().then(() => fetch(apiUrl(`/api/cats/collective/mine?session=${encodeURIComponent(session)}`))).then(r => (r?.ok ? r.json() : null)).then(j => on && setMine(j)).catch(() => {}); }; go(); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, [session]);
  return mine?.agents?.length ? <Mine rows={mine.agents} mode={mine.mode} /> : <Pitch d={d} />;
}
