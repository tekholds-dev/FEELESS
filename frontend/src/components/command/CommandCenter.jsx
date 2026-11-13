import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';
import { Ic3 } from '../../lib/icon3d';
import '../../styles/commandCenter.css';

// 🛰 SITE-4 · LIVE OPS (the HQ's name never ships in the bundle: the gate checks) (Supreme Intelligence §7: "research, browser activity, PoI evolution, trades, wallets, costs and Colony ... no
// fake activity or decorative telemetry"). One live screen of what every agent is really doing: who is working and on what, which browser
// waits on you, which model answered and what it cost this hour, how the reviewers grade each proof kind, which shared reads are fresh, the
// method kits' state, and the event river. Every number comes from the running service; nothing here is drawn for show. Polls every 15 s
// while visible, all reads in parallel.
const KIND_IC = { Browser: '🌐', PoW: '⛏', PoP: '📉', PoB: '🎲', PoStatic: '💻', PoC: '📣', Research: '🔎', Folder: '📁' };
const BRIEF = { pow: 'PoW', pop: 'PoP', pob: 'PoB', poc: 'PoC', pos: 'PoStatic', poe: 'PoEco' };
const usd = n => `$${Number(n || 0) < 0.01 && n ? Number(n).toFixed(4) : Number(n || 0).toFixed(2)}`;
const ago = at => { if (!at) return '—'; const m = Math.max(0, Math.round((Date.now() / 1000 - at) / 60)); return m < 1 ? 'now' : m < 60 ? `${m}m` : m < 1440 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`; };
function useLive(cat, work) {
  const [d, setD] = useState({ at: 0 });
  useEffect(() => {
    let live = true;
    const go = async () => {
      if (document.hidden) return;
      const [now, eng, brief, feed] = await Promise.all([work(cat.id, { op: 'agents_now' }).catch(() => null), work(cat.id, { op: 'engines' }).catch(() => null),
        fetch(apiUrl('/api/cats/brief/proofs')).then(r => (r.ok ? r.json() : null)).catch(() => null),
        fetch(apiUrl(`/api/cats/${cat.id}/feed?${agentAuthQuery()}`)).then(r => (r.ok ? r.json() : null)).catch(() => null)]);
      if (live) setD({ now, eng, brief, feed, at: Date.now() });
    };
    go(); const t = setInterval(go, 15000); return () => { live = false; clearInterval(t); };
  }, [cat.id, work]);
  return d;
}

// 🛰 THIS DESK (SITE-4): the desk's own money and bills, read every 60 s (the wallet read touches the chain, so it runs slower than the floor).
// Sicario's trades from the Fuse card's wallet: its books (card cash, wallet, gas reserve, outside the card). Every other desk: its own wallet,
// what thinking cost today from its own receipts, and its place in The Pool (sent, earned, owed counting up live). Errors are said, never filled in.
export function deskSums(w, pool, now = Date.now() / 1000) {
  const day = now - 86400; const rc = (w?.modelReceipts || []).filter(r => (r.at || 0) >= day);
  const p = pool?.pool || null;
  return { fuse: !!w?.fuse, sol: w?.fuse ? w?.walletSol : w?.sol, usdc: w?.usdc, card: w?.cardSol, reserve: w?.reserveSol, outside: w?.outsideSol, addr: w?.address,
    bills: rc.reduce((a, r) => a + (Number(r.usd) || 0), 0), calls: rc.length, last: rc[0]?.model || null,
    sent: p?.sentUsd, earned: p?.earnedUsd, owed: p ? (p.owedUsd || 0) + (p.ratePerSecUsd || 0) * Math.max(0, now - (p.at || now)) : null, locked: p?.lockedUsd, rate: p?.ratePerSecUsd };
}
function useDesk(cat, work) {
  const [d, setD] = useState({ at: 0 });
  useEffect(() => {
    let live = true;
    const go = async () => {
      if (document.hidden) return;
      const [w, pool] = await Promise.all([work(cat.id, { op: 'wallet' }).then(x => ({ ok: x }), e => ({ err: String(e?.message || e || 'no read') })),
        work(cat.id, { op: 'pool' }).then(x => ({ ok: x }), e => ({ err: String(e?.message || e || 'no read') }))]);
      if (live) setD({ w, pool, at: Date.now() });
    };
    go(); const t = setInterval(go, 60000); return () => { live = false; clearInterval(t); };
  }, [cat.id, work]);
  return d;
}
function Ticker({ base, rate, at }) {
  const [v, setV] = useState(base);
  useEffect(() => { if (!rate) { setV(base); return undefined; } const t = setInterval(() => setV(base + rate * (Date.now() / 1000 - at)), 1000); return () => clearInterval(t); }, [base, rate, at]);
  return <b className="m-num">${Number(v || 0).toFixed(v >= 1 ? 2 : 5)}</b>;
}
const sol = n => (n == null ? '—' : `${Number(n).toFixed(4)} SOL`);
export function DeskLane({ cat, work }) {
  const d = useDesk(cat, work);
  if (!d.at) return <section className="ccx-card is-desk" data-testid="ccx-desk"><h4><Ic3 e="👛" /> THIS DESK</h4><p className="ccx-none">Reading its wallet and its Pool…</p></section>;
  const s = deskSums(d.w.ok, d.pool.ok);
  return <section className="ccx-card is-desk" data-testid="ccx-desk"><h4><Ic3 e="👛" /> THIS DESK <small>{s.fuse ? 'it trades from the Fuse card wallet' : 'its own wallet, bills and Pool'} · every 60 s</small></h4>
    <div className="ccx-desk">
      <div className="ccx-dbox"><em>{s.fuse ? 'FUSE WALLET' : 'WALLET'}</em>{d.w.err ? <p className="ccx-none" data-testid="ccx-desk-werr">{d.w.err}</p> : <>
        <b className="m-num">{sol(s.sol)}</b>{s.fuse ? <small className="m-num">card {sol(s.card)} · gas {sol(s.reserve)} · outside {sol(s.outside)}</small> : <small className="m-num">${Number(s.usdc || 0).toFixed(2)} USDC</small>}
        {s.addr ? <small className="m-num ccx-addr">{s.addr.slice(0, 4)}…{s.addr.slice(-4)}</small> : null}</>}</div>
      {!s.fuse ? <div className="ccx-dbox"><em>THINKING · 24H</em>{d.w.err ? <p className="ccx-none">—</p> : <><b className="m-num">${s.bills.toFixed(s.bills < 1 ? 4 : 2)}</b><small>{s.calls} paid calls{s.last ? ` · last ${s.last}` : ''}</small></>}</div> : null}
      <div className="ccx-dbox"><em>THE POOL</em>{d.pool.err ? <p className="ccx-none" data-testid="ccx-desk-perr">{d.pool.err}</p> : s.owed == null ? <p className="ccx-none">Not in The Pool yet.</p> : <>
        <Ticker base={s.owed} rate={s.rate} at={Date.now() / 1000} /><small className="m-num">owed · sent ${Number(s.sent || 0).toFixed(2)} · earned ${Number(s.earned || 0).toFixed(2)} · locked ${Number(s.locked || 0).toFixed(2)}</small></>}</div>
    </div></section>;
}
const Kpi = ({ k, v, sub, tone, i }) => <span className={`ccx-kpi${tone ? ` is-${tone}` : ''}`} style={{ '--i': i }}><small>{k}</small><b className="m-num" key={String(v)}>{v}</b>{sub ? <em>{sub}</em> : null}</span>;
export function CommandCenter({ cat, work }) {
  const d = useLive(cat, work); const agents = d.now?.agents || []; const e = d.eng || {}; const routes = e.routes || []; const rv = e.reviewer || {};
  const working = agents.filter(a => a.doing?.length); const waits = agents.flatMap(a => (a.doing || []).filter(x => x.wait).map(x => ({ ...x, agent: a.name })));
  const calls = routes.reduce((a, r) => a + r.calls, 0); const spent = routes.reduce((a, r) => a + (r.usd || 0), 0); const topCalls = Math.max(1, ...routes.map(r => r.calls));
  const reads = e.reads?.kinds || []; const kits = e.methods?.kits || []; const brief = d.brief?.rows || []; const feed = d.feed?.items || d.feed?.rows || [];
  if (!d.at) return <p className="dsk-note" data-testid="ccx-wait">Reading the live service…</p>;
  return <section className="ccx" data-testid="command-center">
    <header className="ccx-h m-live"><span><em>LIVE OPS</em><b>Every agent, every call, every proof, right now</b><small>From the running service, every 15 seconds. Nothing on this screen is drawn for show.</small></span>
      <span className="ccx-tick m-num" key={d.at}><s />{new Date(d.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span></header>
    <div className="ccx-kpis">
      <Kpi i={0} k="WORKING NOW" v={`${working.length}/${agents.length}`} sub="agents" tone={working.length ? 'go' : ''} />
      <Kpi i={1} k="WAITING ON YOU" v={waits.length} sub={waits.length ? 'a browser needs you' : 'nothing'} tone={waits.length ? 'warn' : ''} />
      <Kpi i={2} k="MODEL CALLS · 1H" v={calls} sub={`${routes.length} routes`} />
      <Kpi i={3} k="SPENT · 1H" v={usd(spent)} sub="real bills" />
      <Kpi i={4} k="REVIEWS PASS" v={rv.passPct == null ? '—' : `${rv.passPct}%`} sub={`${rv.graded || 0} graded · ${rv.waiting || 0} due`} tone={rv.passPct >= 60 ? 'go' : rv.passPct != null ? 'warn' : ''} />
      <Kpi i={5} k="FRESH READS" v={reads.length + (e.reads?.topics || 0)} sub={`${reads.reduce((a, r) => a + (r.reused || 0), 0) + (e.reads?.topicReuses || 0)} reuses`} />
    </div>
    <div className="ccx-grid">
      <section className="ccx-card is-floor" data-testid="ccx-floor"><h4><Ic3 e="🖥" /> THE FLOOR <small>what each agent is really doing</small></h4>
        <ul className="ccx-agents">{agents.map((a, i) => <li key={a.id} className={a.doing?.length ? 'is-on' : ''} style={{ '--i': Math.min(i, 12) }}><span className="ccx-who"><s aria-hidden="true" /><b>{a.name}</b>{a.me ? <small>this desk</small> : null}</span>
          {a.doing?.length ? <span className="ccx-doing">{a.doing.map((x, j) => <em key={j} className={x.wait ? 'is-wait' : ''} data-tip={x.wait ? 'Its browser hit something only you can do (a sign-in, a check)' : x.kind}>{KIND_IC[x.kind] || '•'} {x.say}{x.wait ? ' · needs you' : ''}</em>)}</span> : <span className="ccx-idle">idle</span>}</li>)}</ul></section>
      <section className="ccx-card" data-testid="ccx-routes"><h4><Ic3 e="🛰" /> WHO ANSWERED · LAST HOUR <small>route, calls, ok, cost</small></h4>
        {routes.length ? <ul className="ccx-bars">{routes.slice(0, 8).map((r, i) => <li key={r.route} style={{ '--i': i }} data-tip={`${r.calls} calls · ${r.okPct}% ok · avg ${(r.avgMs / 1000).toFixed(1)}s · ${usd(r.usd)}`}><span>{r.route}</span><u><s style={{ transform: `scaleX(${r.calls / topCalls})` }} /></u><b className="m-num">{r.calls}</b><small className={`m-num${r.okPct < 80 ? ' is-bad' : ''}`}>{r.okPct}%</small><small className="m-num">{usd(r.usd)}</small></li>)}</ul> : <p className="ccx-none">No model call in the last hour.</p>}</section>
      <section className="ccx-card" data-testid="ccx-quality"><h4><Ic3 e="🧑‍⚖️" /> EVIDENCE QUALITY <small>The Collective's review average and graded right, per proof kind, this week</small></h4>
        {brief.length ? <ul className="ccx-bars is-q">{brief.map((r, i) => <li key={r.kind} style={{ '--i': i }} data-tip={`${r.filed7} filed this week · ${r.reviews} reviewed${r.passPct != null ? ` (${r.passPct}% passed)` : ''} · graded ${r.right} right / ${r.wrong} wrong`}><span>{BRIEF[r.kind] || r.kind}</span><u><s style={{ transform: `scaleX(${(r.avgScore || 0) / 100})` }} /></u><b className="m-num">{r.avgScore ?? '–'}</b><small className="m-num">{r.rightPct != null ? `${r.rightPct}% right` : 'ungraded'}</small><small className="m-num">{r.filed7} wk</small></li>)}</ul> : <p className="ccx-none">No proof reviewed this week yet.</p>}</section>
      <section className="ccx-card" data-testid="ccx-reads"><h4><Ic3 e="🔎" /> SHARED READS <small>one read, every agent's next proof, while fresh</small></h4>
        {reads.length ? <ul className="ccx-bars is-reads">{reads.map((r, i) => <li key={r.kind} style={{ '--i': i }} data-tip={`${r.sites} sites read · reused ${r.reused}× · fresh for ${r.freshMin} min`}><span>{BRIEF[r.kind] || r.kind}</span><u><s style={{ transform: `scaleX(${Math.max(0, 1 - r.ageMin / Math.max(1, r.freshMin))})` }} /></u><b className="m-num">{r.ageMin}m</b><small className="m-num">{r.reused}× reused</small></li>)}</ul> : <p className="ccx-none">No shared read is fresh right now.</p>}
        <h4 className="ccx-sub"><Ic3 e="🧰" /> METHOD KITS</h4><span className="ccx-kits">{kits.length ? kits.map(k => <em key={k.kit} className={`is-${k.state || 'unmeasured'}`} data-tip={`${k.state || 'unmeasured'}${k.followedWin != null ? ` · ${Math.round(k.followedWin * 100)}% right when followed` : ''}`}>{k.kit}</em>) : <small className="ccx-none">Measured when Missions opens.</small>}</span></section>
      <DeskLane cat={cat} work={work} />
      <section className="ccx-card is-river" data-testid="ccx-river"><h4><Ic3 e="📡" /> EVENT RIVER <small>filed, graded, reviewed, ready, newest first</small></h4>
        {feed.length ? <ol className="ccx-river">{feed.slice(0, 14).map((x, i) => <li key={`${x.at}-${i}`} className={x.tone === 'look' ? 'is-look' : ''} style={{ '--i': Math.min(i, 10) }}><em className="m-num">{ago(x.at)}</em><b>{x.kind || '•'}</b><span>{x.text}</span></li>)}</ol> : <p className="ccx-none">Nothing new on this desk yet.</p>}</section>
    </div></section>;
}
