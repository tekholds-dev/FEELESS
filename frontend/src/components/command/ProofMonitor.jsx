import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';
import { useCountUp } from '../../lib/useCountUp';
import '../../styles/proofMonitor.css';

// 🖥 owner 2026-11-12: "all proofs can be seen in desk monitors, in dynamic ways regardless of proof type — like static we can see a code window and a
// static window". Each kind draws its OWN folder's real data on the monitor: nothing here is sample data, and a missing piece says so.
const DOCS = new Map();   // ws → { code, preview } — one read per page per 2 minutes, shared by every monitor
async function readDoc(work, catId, ws) {
  const hit = DOCS.get(ws); if (hit && Date.now() - hit.at < 120000) return hit;
  const j = await work(catId, { op: 'ws_open', text: ws }); const d = { code: String(j?.doc?.code || ''), preview: j?.doc?.preview || '', at: Date.now() }; DOCS.set(ws, d); return d;
}
export function codeLines(code, n = 90) {
  const body = String(code || '').replace(/\r/g, ''); const at = body.search(/<script[^>]*>/i);   // the page's own script reads better than its <head>
  return (at > 0 ? body.slice(at) : body).split('\n').map(l => l.replace(/\t/g, '  ')).filter(l => l.trim()).slice(0, n);
}

function PsMon({ f, catId, work, view }) {
  const [doc, setDoc] = useState(null); const [err, setErr] = useState('');
  useEffect(() => { let on = true; if (!f?.ws || !work) return undefined; readDoc(work, catId, f.ws).then(d => on && setDoc(d)).catch(() => on && setErr('Its page could not be read right now.')); return () => { on = false; }; }, [f?.ws, catId, work]);
  const lines = codeLines(doc?.code);
  return <div className={`pmn-ps${view ? ' is-' + view : ''}`}>
    <div className="pmn-code" aria-label="Its code"><span className="pmn-bar"><i /><i /><i /><b>index.html</b></span>
      {lines.length ? <ol style={{ '--n': lines.length }}>{[...lines, ...lines].map((l, i) => <li key={i}>{l}</li>)}</ol> : <p className="pmn-none">{err || (doc ? 'No code filed yet.' : 'Reading its code…')}</p>}</div>
    <div className="pmn-page" aria-label="Its page"><span className="pmn-bar"><i /><i /><i /><b>{String(f?.topic || 'page').slice(0, 28)}</b></span>
      {doc?.preview ? <iframe title="Its page" sandbox="allow-scripts" srcDoc={doc.preview} tabIndex={-1} /> : <p className="pmn-none">{err || (doc ? 'No page built yet.' : 'Opening its page…')}</p>}</div>
  </div>;
}
function PowMon({ f }) {
  const pct = Number(f?.pnlPct); const has = Number.isFinite(pct); const shown = useCountUp(has ? Math.round(pct * 100) : 0) / 100;
  const coins = (f?.coins || []).slice(0, 4);
  return <div className="pmn-pow"><b className="pmn-sym">${String(f?.sym || coins[0]?.sym || '…').slice(0, 12)}</b>
    <span className={`pmn-pnl m-num ${!has ? '' : pct >= 0 ? 'is-up' : 'is-dn'}`}>{has ? `${shown >= 0 ? '+' : ''}${shown.toFixed(2)}%` : 'no trade yet'}</span>
    {has ? <span className="pmn-meter" aria-hidden="true"><u style={{ transform: `scaleX(${Math.min(1, Math.abs(pct) / 50)})` }} className={pct >= 0 ? 'is-up' : 'is-dn'} /></span> : null}
    <small>{f?.minds || 1} mind{(f?.minds || 1) > 1 ? 's' : ''} · {String(f?.phase || 'filed')}{Number.isFinite(Number(f?.pnlSol)) ? ` · ${Number(f.pnlSol) >= 0 ? '+' : ''}${Number(f.pnlSol).toFixed(4)} SOL` : ''}</small>
    {coins.length > 1 ? <ul className="pmn-coins">{coins.map(c => <li key={c.mint || c.sym} className={Number(c.ch) >= 0 ? 'is-up' : 'is-dn'}>${String(c.sym || '').slice(0, 10)}<em>{Number.isFinite(Number(c.ch)) ? `${Number(c.ch) >= 0 ? '+' : ''}${Number(c.ch).toFixed(0)}%` : ''}</em></li>)}</ul> : null}</div>;
}
// 🎲 owner 2026-11-17 ("hoping main desk monitors dynamically show something when I open this proof file there"): a PoB's monitor is its game,
// live: the score (ESPN, through our own /api/cats/tools/game, one shared read per game per 30 s while it plays), each slip it put on Kalshi (in,
// worth now, P&L: fees never in it, CLAUDE.md §1), each mind's pick, and the sites it really read. Watching only: nothing here sends an order.
const GAMES = new Map();   // game id → { at, d, p }
export function readGame(g) {
  const hit = GAMES.get(g.id); if (hit && (hit.p || Date.now() - hit.at < 30000)) return hit.p || Promise.resolve(hit.d);
  const p = fetch(apiUrl(`/api/cats/tools/game/${g.sport}/${g.id}`)).then(r => (r.ok ? r.json() : null)).catch(() => null)
    .then(d => { GAMES.set(g.id, { at: Date.now(), d }); return d; });
  GAMES.set(g.id, { at: Date.now(), d: hit?.d || null, p }); return p;
}
export function pobSlip(k) {   // the ticket → what the monitor says about it. Pure.
  if (!k) return null;
  const filled = Number(k.filled ?? (k.status === 'filled' ? k.count : 0)) || 0; const placed = !!k.orderId && filled > 0;
  const cost = k.usd != null ? Number(k.usd) : filled * Number(k.price || 0);
  const now = k.outcome === 'won' ? filled : k.outcome === 'lost' ? 0 : k.livePx != null && placed ? filled * Number(k.livePx) : null;
  return { title: k.kind === 'parlay' ? `🧩 ${(k.legs || []).length}-leg parlay` : `${String(k.side || '').toUpperCase()} ${k.title || k.ticker || ''}`.trim(), placed, cost, now,
    pnl: now == null ? null : Math.round((now - cost) * 100) / 100, say: placed ? null : k.status === 'waiting' ? 'waiting for your tap' : k.offer ? 'its pick, your tap' : String(k.status || 'no bid') };
}
const money = v => `${v < 0 ? '−' : ''}$${Math.abs(Number(v) || 0).toFixed(2)}`;
function PobMon({ f, also = [] }) {
  const g = (f?.games || [])[0]; const [d, setD] = useState(null);
  useEffect(() => {
    if (!g?.id || !g?.sport) return undefined; let on = true; const go = () => { if (!document.hidden) readGame(g).then(x => on && x && setD(x)); };
    go(); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); };
  }, [g?.id, g?.sport]);   // eslint-disable-line react-hooks/exhaustive-deps
  const read = [...new Set(Object.values(f?.browsed || {}).flatMap(b => (b && b.sites) || []))]; const sites = [...new Set([...read, ...(f?.sites || [])])].slice(0, 6);
  const calls = f?.calls || []; const slips = [f, ...also].map(x => pobSlip(x?.kalshi)).filter(Boolean); const [ta, tb] = d?.teams || [];
  const live = d?.state === 'in';
  return <div className="pmn-pob" data-testid="pmn-pob"><b className="pmn-topic">{String(f?.topic || 'Bids').slice(0, 60)}</b>
    {d && ta && tb ? <span className={`pmn-score${live ? ' is-live' : ''}`} data-testid="pmn-score"><b className="m-num">{ta.abbr} {ta.score ?? 0} – {tb.score ?? 0} {tb.abbr}</b><small>{live ? '● ' : ''}{d.status || ''}</small></span> : g ? <small>{g.status || g.label || ''}</small> : null}
    {slips.length ? <ul className="pmn-slips" data-testid="pmn-slips">{slips.map((s, i) => <li key={i} className={s.pnl > 0 ? 'is-up' : s.pnl < 0 ? 'is-dn' : ''}><span>{s.title}</span>{s.placed
      ? <em className="m-num">{money(s.cost)} in{s.now != null ? ` · ${money(s.now)} now · ${s.pnl >= 0 ? '+' : ''}${money(s.pnl)}` : ''}</em> : <em>{s.say}</em>}</li>)}</ul> : null}
    {calls.length ? <ul className="pmn-minds">{calls.map(c => { const top = (c.picks || [])[0]; return <li key={c.mind}><b>{c.name || `Mind ${'AB'[c.mind] || ''}`}</b>{top ? <span>{top.pick} <em className="m-num">{top.confidence}%</em></span> : <span>passed</span>}</li>; })}</ul> : null}
    <ul className="pmn-sites">{sites.map((s, i) => <li key={s} style={{ '--i': i }} className={read.includes(s) ? 'is-read' : ''}>{s}</li>)}</ul>
    {!calls.length ? <small className="is-dn">{f?.noTrade ? 'No call: nothing was read, so nothing staked' : 'Reading the games'}</small> : null}</div>;
}
function PocMon({ f, catId }) {
  // 🎬 its OWN made media first (owner 2026-11-12: Bishop's image never reached a monitor), then its snapshot, then the idea itself — never a bare "nothing"
  const made = (f?.media || []).find(x => x.url); const shot = (f?.shots || []).find(x => x.file); const found = (shot?.found || []).slice(0, 5);
  const idea = String((f?.calls || []).find(c => c.post)?.post || '').slice(0, 180);
  return <div className="pmn-poc">{made ? (made.kind === 'video'
    ? <video src={apiUrl(made.url)} muted loop autoPlay playsInline preload="metadata" data-testid="pmn-poc-video" />
    : <img src={apiUrl(made.url)} alt={made.prompt || 'What it made'} loading="lazy" data-testid="pmn-poc-media" />)
    : shot ? <img src={apiUrl(`/api/cats/${catId}/powshot/${String(f.id).replace(/[^a-z0-9]/gi, '').toLowerCase()}/${shot.file}?${agentAuthQuery()}`)} alt={`What it read on ${shot.site}`} loading="lazy" />
      : idea ? <blockquote className="pmn-idea" data-testid="pmn-poc-idea">{idea}</blockquote> : <p className="pmn-none">No snapshot filed.</p>}
    <span className="pmn-poc-say"><b>{String(f?.topic || 'PoC').slice(0, 50)}</b>{made ? <small className="pmn-made">{made.kind === 'video' ? '🎬' : '🖼'} {made.label || 'made here'}</small> : null}{found.length ? <span className="pmn-words">{found.map(w => <em key={w}>{w}</em>)}</span> : null}</span></div>;
}
function PoeMon({ f }) {
  const months = (f?.months || []).slice(-6); const top = Math.max(1, ...months.flatMap(m => [Number(m.income) || 0, Number(m.costs) || 0]));
  const usd = v => `$${Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(1)}K` : Math.round(v)}`;
  return <div className="pmn-poe"><b className="pmn-topic">{String(f?.topic || 'Its books').slice(0, 40)}</b>
    <div className="pmn-bars">{months.map((m, i) => <span key={m.month} style={{ '--i': i }} data-tip={`${m.month}: in ${usd(m.income)}, out ${usd(m.costs)}`}><u className="is-in" style={{ transform: `scaleY(${(Number(m.income) || 0) / top})` }} /><u className="is-out" style={{ transform: `scaleY(${(Number(m.costs) || 0) / top})` }} /><small>{String(m.month).slice(5)}</small></span>)}</div>
    <small>Net <b className={Number(f?.net) >= 0 ? 'is-up' : 'is-dn'}>{usd(Number(f?.net) || 0)}</b> · margin {Number.isFinite(Number(f?.margin)) ? `${Number(f.margin).toFixed(1)}%` : '—'}</small></div>;
}
const BODY = { ps: PsMon, pow: PowMon, pob: PobMon, poc: PocMon, poe: PoeMon };
export function ProofMonitorBody({ p, catId, work }) {
  const B = BODY[p?.k]; return B && p?.f ? <B f={p.f} also={p.also} catId={catId} work={work} view={p.view} /> : null;
}
