import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Bar, CartesianGrid, Cell, ComposedChart, Line, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import '../../styles/compWatch.css';

// 👁 COMP WATCH (owner 2026-11-15: "nun on comps folder is real and true live animations or data, fix that … the best sources or charts").
// What really moves while nothing trains, read every 10 s from /admin/model-lab/watch (comp_watch.py):
//   · THE BOARD   every coin COMP's internet learner is holding, priced NOW on DexScreener: the move since its snapshot against the ±20% lines
//                 it settles on, a trail of the moves this page has seen, and a countdown to its settle
//   · THE MINDS   every model call the agents made this hour, per minute (Recharts: done vs failed bars + the latency line), and the call tape
//   · SETTLED     the learner's own won / lost / flat record (a Recharts ring) and the rows it just graded itself
// Nothing here is drawn that was not measured: a coin DexScreener did not answer shows "—".
const POLL_MS = 10000;
const TRAIL = 18;
const tok = (name, dflt) => { try { return getComputedStyle(document.body).getPropertyValue(name).trim() || dflt; } catch { return dflt; } };
const mmss = s => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;
const ago = (at, now) => { const s = Math.max(0, Math.round(now - at)); return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.floor(s / 60)}m ago` : `${Math.floor(s / 3600)}h ago`; };
const CALL = { won: 'WON', lost: 'LOST', flat: 'FLAT' };

function Trail({ pts }) {
  if (!pts || pts.length < 2) return <svg className="cw-trail" viewBox="0 0 60 20" aria-hidden="true" />;
  const lo = Math.min(-20, ...pts); const hi = Math.max(20, ...pts); const y = v => 20 - ((v - lo) / (hi - lo || 1)) * 20;
  const d = pts.map((v, i) => `${i ? 'L' : 'M'}${(i / (pts.length - 1)) * 60},${y(v).toFixed(1)}`).join(' ');
  return <svg className="cw-trail" viewBox="0 0 60 20" aria-hidden="true"><line x1="0" x2="60" y1={y(0)} y2={y(0)} className="cw-zero" /><path d={d} className={pts[pts.length - 1] >= 0 ? 'is-up' : 'is-dn'} /></svg>;
}

function Row({ r, i, trail, now, at }) {
  const left = Math.max(0, r.left - (now - at));
  const m = r.move; const w = m == null ? 0 : Math.max(-1, Math.min(1, m / 50));
  return <motion.li layout initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i, 12) * 0.02 }} className={`cw-row is-${r.call || 'wait'}`} data-testid={`cw-coin-${r.pair}`}>
    <span className="cw-sym"><b title={r.symbol}>{r.symbol}</b><small>{r.dex}{r.ageMin != null ? ` · ${r.ageMin}m old at snap` : ''}</small></span>
    <span className="cw-move" data-tip="The move since COMP's snapshot. It settles WON at +20%, LOST at -20% or if the pool is gone">
      <i className="cw-axis" aria-hidden="true"><s className="cw-l" /><s className="cw-r" /><motion.u initial={false} animate={{ scaleX: Math.abs(w) }} transition={{ duration: 0.6 }} className={w >= 0 ? 'is-up' : 'is-dn'} /></i>
      <em className="m-num">{r.gone ? 'pool gone' : m == null ? '—' : `${m > 0 ? '+' : ''}${m.toFixed(1)}%`}</em></span>
    <Trail pts={trail} />
    <span className="cw-left m-num" data-tip="Time until this snapshot settles into a training row">{left ? mmss(left) : 'settling'}</span>
    <i className="cw-call">{r.call ? CALL[r.call] : '…'}</i>
  </motion.li>;
}

export function CompWatch({ call }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [now, setNow] = useState(() => Date.now() / 1000);
  const trails = useRef({}); const callRef = useRef(call); callRef.current = call; const has = !!call; const [c] = useState(() => ({ up: tok('--m-accent', '#19e68c'), bad: tok('--m-danger', '#ff5c7a'), warn: tok('--m-warn', '#f5c451'), dim: tok('--m-dim', '#6b6880') }));
  useEffect(() => {
    if (!has) return undefined; let on = true;
    const load = () => { if (document.hidden) return; callRef.current('/admin/model-lab/watch').then(x => { if (!on) return; (x.board || []).forEach(r => { if (r.move == null) return; const t = trails.current[r.pair] || []; trails.current[r.pair] = [...t, r.move].slice(-TRAIL); }); setD(x); setErr(''); }).catch(e => on && setErr(e.message)); };
    load(); const t = setInterval(load, POLL_MS); const k = setInterval(() => { if (!document.hidden) setNow(Date.now() / 1000); }, 1000);
    return () => { on = false; clearInterval(t); clearInterval(k); };
  }, [has]);
  if (!d || !Array.isArray(d.board)) return <p className="cw-wait" role="status">{err ? `⚠ ${err}` : 'Pricing every coin COMP is holding…'}</p>;
  const mi = d.minds || {}; const tt = d.totals || {}; const fresh = Math.max(0, POLL_MS / 1000 - (now - d.at));
  const ring = [['won', tt.won || 0, c.up], ['lost', tt.lost || 0, c.bad], ['flat', tt.flat || 0, c.dim]].map(([k, v, col]) => ({ k, v, col }));
  const settledTotal = ring.reduce((a, x) => a + x.v, 0);
  return <section className="cw" data-testid="comp-watch" aria-label="COMP watch">
    <header className="cw-h"><span className="cw-dot" aria-hidden="true" /><b>COMP IS WATCHING</b><small>{d.board.length} coins held from DexScreener's live lists · each one becomes a training row an hour after its snapshot</small>
      <em className="m-num" data-testid="cw-fresh">next read {Math.ceil(fresh)}s</em></header>
    {err ? <p className="cw-err" role="alert">⚠ {err} · showing the last read</p> : null}
    <div className="cw-grid">
      <article className="cw-card cw-board"><header><b>THE BOARD</b><span className="cw-lean" data-tip="What COMP would call if every coin settled this second">
        <i className="is-won m-num">{d.lean.won} won</i><i className="is-lost m-num">{d.lean.lost} lost</i><i className="is-flat m-num">{d.lean.flat} flat</i></span></header>
        {d.board.length ? <ol className="cw-rows">{d.board.map((r, i) => <Row key={r.pair} r={r} i={i} trail={trails.current[r.pair]} now={now} at={d.at} />)}</ol> : <p className="cw-wait">Holding nothing right now. The next collect snapshots up to 30 coins.</p>}</article>
      <div className="cw-side">
        <article className="cw-card"><header><b>THE MINDS · {mi.unit === 'hour' ? 'LAST DAY (QUIET HOUR)' : 'LAST HOUR'}</b><small className="m-num">{mi.calls || 0} calls · {mi.fail || 0} failed · ${(mi.usd || 0).toFixed(3)}</small></header>
          <div className="cw-chart" data-testid="cw-minds-chart"><ResponsiveContainer width="100%" height={130}><ComposedChart data={mi.perMin || []} margin={{ top: 6, right: 4, bottom: 0, left: -18 }}>
            <CartesianGrid stroke={c.dim} strokeOpacity={0.18} vertical={false} /><XAxis dataKey="m" tick={{ fontSize: 10, fill: c.dim }} tickFormatter={v => (v === 0 ? 'now' : `${v}${mi.unit === 'hour' ? 'h' : 'm'}`)} interval={mi.unit === 'hour' ? 5 : 14} />
            <YAxis yAxisId="n" allowDecimals={false} tick={{ fontSize: 10, fill: c.dim }} /><YAxis yAxisId="ms" orientation="right" hide />
            <Tooltip contentStyle={{ background: 'var(--m-surface)', border: '1px solid var(--m-line)', fontSize: 12 }} formatter={(v, k) => (k === 'ms' ? [`${(v / 1000).toFixed(1)}s`, 'avg answer'] : [v, k === 'ok' ? 'answered' : 'failed'])} labelFormatter={v => (v === 0 ? `this ${mi.unit === 'hour' ? 'hour' : 'minute'}` : `${-v} ${mi.unit === 'hour' ? 'h' : 'min'} ago`)} />
            <Bar yAxisId="n" dataKey="ok" stackId="a" fill={c.up} isAnimationActive={false} /><Bar yAxisId="n" dataKey="fail" stackId="a" fill={c.bad} isAnimationActive={false} />
            <Line yAxisId="ms" dataKey="ms" stroke={c.warn} dot={false} strokeWidth={1.4} isAnimationActive={false} /></ComposedChart></ResponsiveContainer></div>
          <ul className="cw-tape" data-testid="cw-tape"><AnimatePresence initial={false}>{(mi.tape || []).slice(0, 7).map(t => <motion.li key={`${t.at}-${t.model}`} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className={t.ok ? 'is-ok' : 'is-fail'}>
            <i aria-hidden="true" /><b title={t.model || ''}>{t.model || 'no answer'}</b><small>{t.kind || '—'} · {t.local ? 'local' : 'rented'}</small><em className="m-num">{t.ms ? `${(t.ms / 1000).toFixed(1)}s` : '—'}</em><small className="m-num">{ago(t.at, now)}</small></motion.li>)}</AnimatePresence></ul></article>
        <article className="cw-card cw-settled"><header><b>SETTLED BY ITSELF</b><small className="m-num">{tt.rows ?? 0} rows · {tt.collects ?? 0} passes</small></header>
          <div className="cw-ring" data-testid="cw-ring"><ResponsiveContainer width={112} height={112}><PieChart><Pie data={ring} dataKey="v" nameKey="k" innerRadius={36} outerRadius={52} stroke="none" isAnimationActive={false}>{ring.map(x => <Cell key={x.k} fill={x.col} />)}</Pie></PieChart></ResponsiveContainer>
            <span><b className="m-num">{settledTotal ? Math.round(((tt.won || 0) / Math.max(1, (tt.won || 0) + (tt.lost || 0))) * 100) : 0}%</b><small>won of decided</small></span></div>
          <ul className="cw-legend">{ring.map(x => <li key={x.k} style={{ '--c': x.col }}><i aria-hidden="true" />{x.k}<b className="m-num">{x.v}</b></li>)}</ul>
          <ol className="cw-last">{(d.settled || []).slice(0, 5).map(s => <li key={`${s.at}-${s.title}`} className={`is-${s.outcome}`} title={s.plan}><b>{s.title}</b><i>{s.outcome}</i></li>)}</ol></article>
      </div>
    </div>
  </section>;
}
