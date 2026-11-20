import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, ReferenceLine, ResponsiveContainer, Tooltip, YAxis } from 'recharts';
import { TeamMark } from './GameRoom';
import { useLogos, logoFor } from '../../lib/teamLogos';
import { boxRef } from '../../lib/boxRef';
import '../../styles/pobDash.css';

// 🎲 THE PoB FOLDER DASHBOARD (Slice 13, owner: "make PoB a sleek dashboard that views everything beautifully when I / a user opens the PoB
// folder: either build their own or see what to have the agent file"). One read (op pob_dash): the games live now, its filings and results,
// P&L without fees (money that reached Kalshi = filled × price; fees live on the receipt, never here), the judges' scores, fresh odds from
// the stash (COMP's reference per game, read every 20 min with no model), and "what to file next", each filed in one tap through the same
// door as File a bid. YOUR SLIP: legs from Kalshi's own list; both minds must back every leg before anything is sent.
const POLL_MS = 30000;
const dashBox = boxRef([640]);   // 📐 its own width (data-w640), no @container
const TABS = [['next', 'Next to file'], ['filings', 'Filings'], ['odds', 'Stash odds'], ['slip', 'Your slip']];
const TAB_KEY = 'feeless.pobDashTab';
const usd = v => (v == null ? '—' : `${v < 0 ? '−' : v > 0 ? '+' : ''}$${Math.abs(v).toFixed(2)}`);
const pct = v => (v == null ? '—' : `${Math.round(v * 100)}%`);
const ago = s => (s == null ? '' : s < 90 ? 'just now' : s < 3600 ? `${Math.round(s / 60)} min ago` : `${Math.round(s / 3600)} h ago`);
const until = iso => { const m = Math.round((Date.parse(iso) - Date.now()) / 60000); return !Number.isFinite(m) ? '' : m <= 0 ? 'starting' : m < 60 ? `in ${m} min` : `in ${Math.floor(m / 60)} h ${m % 60} min`; };
const RESULT = { won: ['Won', 'is-good'], lost: ['Lost', 'is-bad'], live: ['Live bid', 'is-live'], waiting: ['Waiting for your tap', 'is-live'], refused: ['No money moved', 'is-none'], test: ['TEST · never bids', 'is-test'], nobid: ['No real bid', 'is-none'], research: ['Researching', 'is-live'] };
const MODE = { team: 'Team to win', parlay: 'Parlay slip', slip: 'Your slip', board: 'Free chips' };
const readTab = () => { try { return localStorage.getItem(TAB_KEY) || 'next'; } catch { return 'next'; } };

function Meter({ v, tone = '' }) { return <span className={`pdb-meter ${tone}`} aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, v || 0))})` }} /></span>; }

// ⚖ two teams, one bar: each side's win chance on Kalshi, with Polymarket's read as a tick when the stash has it
function Duel({ teams, sport }) {
  const logos = useLogos(sport); const a = teams[0] || {}; const b = teams[1] || {}; const ka = Number(a.kalshi) || 0; const kb = Number(b.kalshi) || 0; const tot = ka + kb || 1;
  return <div className="pdb-duel">
    <span className="pdb-side"><TeamMark t={{ ...a, logo: a.logo || logoFor(logos, a.short) }} size={26} /><b>{a.short}</b><em className="m-num">{pct(a.kalshi)}</em></span>
    <span className="pdb-duel-bar" role="img" aria-label={`Kalshi: ${a.short} ${pct(a.kalshi)}, ${b.short} ${pct(b.kalshi)}`} data-tip={`Kalshi's price for each side${a.poly != null ? ` · Polymarket ${a.short} ${pct(a.poly)}` : ''}`}>
      <u style={{ transform: `scaleX(${ka / tot})` }} />{a.poly != null ? <i style={{ left: `${Math.round(Number(a.poly) * 100)}%` }} /> : null}</span>
    <span className="pdb-side is-r"><em className="m-num">{pct(b.kalshi)}</em><b>{b.short}</b><TeamMark t={{ ...b, logo: b.logo || logoFor(logos, b.short) }} size={26} /></span>
  </div>;
}

function Hero({ t, curve, live, upcoming }) {
  const data = curve.length ? [{ pnl: 0 }, ...curve] : [];
  const rec = t.won + t.lost; const up = t.pnl >= 0;
  return <section className="pdb-hero" data-testid="pdb-hero">
    <div className={`pdb-kpi pdb-pnl m-glass m-live ${up ? 'is-up' : 'is-dn'}`} style={{ '--i': 0 }} data-tip="Settled real Kalshi bids: what they paid minus the money that reached Kalshi. Fees are never in it; they live on each receipt">
      <small className="m-label">P&amp;L · no fees</small><b className={`m-num ${up ? 'm-pos' : 'm-neg'}`} data-testid="pdb-pnl">{usd(t.pnl)}</b>
      <em>{t.real ? `${t.real} real bid${t.real > 1 ? 's' : ''} · $${t.cost.toFixed(2)} in${t.atRisk ? ` · $${t.atRisk.toFixed(2)} live` : ''}` : 'no real bid yet'}</em>
      {data.length ? <div className="pdb-spark"><ResponsiveContainer width="100%" height={46}><AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
        <defs><linearGradient id="pdbFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--m-accent)" stopOpacity={0.45} /><stop offset="100%" stopColor="var(--m-accent)" stopOpacity={0} /></linearGradient></defs>
        <YAxis hide domain={['dataMin', 'dataMax']} /><ReferenceLine y={0} stroke="var(--m-line-hi)" strokeDasharray="3 3" />
        <Tooltip cursor={false} formatter={v => usd(v)} labelFormatter={() => ''} contentStyle={{ background: 'var(--m-surface)', border: '1px solid var(--m-line)', borderRadius: 8, fontSize: 11 }} />
        <Area type="monotone" dataKey="pnl" stroke="var(--m-accent)" strokeWidth={2} fill="url(#pdbFill)" isAnimationActive={false} /></AreaChart></ResponsiveContainer></div> : null}
    </div>
    <div className="pdb-kpi m-glass" style={{ '--i': 1 }} data-tip="Real Kalshi bids that settled: won and lost">
      <small className="m-label">Record</small><b className="m-num" data-testid="pdb-record">{t.won}–{t.lost}</b><Meter v={rec ? t.won / rec : 0} tone="is-good" /><em>{rec ? `${Math.round((t.won / rec) * 100)}% won` : 'nothing settled yet'}</em></div>
    <div className="pdb-kpi m-glass" style={{ '--i': 2 }} data-tip="The Collective's score on each filing it could judge (a judge never scores a proof its own model built)">
      <small className="m-label">Judges</small><b className="m-num" data-testid="pdb-judges">{t.avg == null ? '—' : t.avg}<small>/100</small></b><Meter v={(t.avg || 0) / 100} tone="is-violet" /><em>{t.judged ? `${t.passed} passed of ${t.judged} judged` : 'none judged yet'}</em></div>
    <div className="pdb-kpi m-glass" style={{ '--i': 3 }} data-tip="Games in progress now and games coming up on today's boards">
      <small className="m-label">Tonight</small><b className="m-num" data-testid="pdb-tonight">{live.length}<small> live</small></b><em>{upcoming} coming up · {t.filings} filed</em></div>
  </section>;
}

function LiveStrip({ rows }) {
  if (!rows.length) return null;
  return <ol className="pdb-live" aria-label="Live now" data-testid="pdb-live">{rows.map((g, i) => <li key={g.id} className={`m-glass${g.mine ? ' is-mine' : ''}`} style={{ '--i': i }} data-tip={g.mine ? 'It filed on this game' : 'Live now'}>
    <i className="pdb-dot" aria-hidden="true" />{g.teams.map((t, k) => <span key={k}><b>{t.short}</b><em className="m-num">{t.score ?? ''}</em></span>)}<small>{g.status}</small>{g.mine ? <small className="pdb-mine">YOURS</small> : null}</li>)}</ol>;
}

// 💡 what to file next: one card per game, each way to file it one tap (the same door as File a bid)
function NextTab({ rows, busy, filing, onFile }) {
  if (!rows.length) return <p className="pdb-none" data-testid="pdb-next-none">Nothing worth filing right now: no game with a Kalshi price starts in the next 36 h, or it already has a filing waiting. It checks again every 30 s.</p>;
  return <ol className="pdb-next" data-testid="pdb-next">{rows.map((n, i) => <li key={n.key} className="pdb-card m-glass" style={{ '--i': i }}>
    <header><small className="m-chip">{String(n.sport).toUpperCase()}</small><small className="pdb-when">{until(n.start)}</small>{n.filed ? <small className="m-chip warn">{n.filed} filed</small> : null}</header>
    <Duel teams={n.teams.map((s, k) => ({ short: s, kalshi: n.kalshi[k], poly: n.poly[k] }))} sport={n.sport} />
    <p className="pdb-why">{n.why}. <small>Market odds, not a promise.</small></p>
    <div className="pdb-go">{n.files.map(f => { const on = filing === f.topic;
      return <button key={f.mode} type="button" className={`m-btn${f.mode === 'team' ? ' m-go' : ''}${on ? ' is-on' : ''}`} disabled={busy || !!filing} onClick={() => onFile(f.topic)}
        data-tip={busy ? 'A PoB is already running: it files once that one is done' : `Files “${f.topic}”: both minds read major sites and call it blind. With your Kalshi key, a bid both back goes out inside your caps; anything else waits for your tap`} data-testid={`pdb-file-${n.key}-${f.mode}`}>
        {on ? 'Filing…' : f.mode === 'team' ? '🎯 File: team to win' : '🧩 File: 3-leg slip'}</button>; })}</div>
  </li>)}</ol>;
}

function FilingsTab({ rows, onOpen }) {
  if (!rows.length) return <p className="pdb-none">No PoB filed yet. Tap a game in Next to file.</p>;
  return <ol className="pdb-rows" data-testid="pdb-rows">{rows.map((r, i) => { const [word, tone] = RESULT[r.result] || ['—', 'is-none']; const j = r.judge || {};
    return <li key={r.id} style={{ '--i': Math.min(i, 12) }}><button type="button" className="pdb-row" onClick={() => onOpen(r.id)} data-tip={r.ticket?.say || r.slip || 'Open its file'} data-testid={`pdb-row-${r.id}`}>
      <em className="m-num pdb-n">#{r.n || '…'}</em>
      <span className="pdb-t"><b>{r.topic}</b><small>{MODE[r.mode]}{r.game?.state === 'in' ? ' · live now' : ''}{r.bids.length ? ` · ${r.bids.map(b => `${b.filled}× ${String(b.side).toUpperCase()} @ ${Number(b.price).toFixed(2)}`).join(', ')}` : ''}</small></span>
      <span className={`pdb-res ${tone}`}>{word}</span>
      <b className={`m-num pdb-p ${r.pnl > 0 ? 'm-pos' : r.pnl < 0 ? 'm-neg' : ''}`}>{r.pnl == null ? '—' : usd(r.pnl)}</b>
      <span className="pdb-j" data-tip={j.state === 'scored' ? `${(j.by || []).join(' + ')}: ${j.score}/100 · ${j.verdict}` : j.why}>{j.state === 'scored' ? <><Meter v={j.score / 100} tone={j.verdict === 'pass' ? 'is-good' : 'is-violet'} /><small className="m-num">{j.score}</small></> : <small>{j.state === 'waiting' ? 'unjudged' : 'no judge'}</small>}</span>
    </button></li>; })}</ol>;
}

function OddsTab({ rows, at }) {
  if (!rows.length) return <p className="pdb-none" data-testid="pdb-odds-none">The stash has no fresh odds yet. COMP reads tonight's games every 20 min (ESPN, Kalshi, Polymarket, with no model); they show here once it has.</p>;
  return <><p className="pdb-src">From the stash · COMP's newest read {ago(at ? Math.round(Date.now() / 1000 - at) : null)} · Kalshi bar, Polymarket tick</p>
    <ol className="pdb-odds" data-testid="pdb-odds">{rows.map((o, i) => <li key={o.id} className="m-glass" style={{ '--i': i }}>
      <header><small className="m-chip">{String(o.sport).toUpperCase()}</small><small className="pdb-when">{until(o.start)}</small>
        {o.line ? <small className="m-num" data-tip="ESPN's line">{o.line}</small> : null}{o.total ? <small className="m-num" data-tip="ESPN's total">o/u {o.total}</small> : null}
        <small className={`m-chip ${o.stale ? 'warn' : 'ok'}`} data-tip={o.stale ? 'Older than 45 min: COMP reads again soon' : 'Read in the last 45 min'}>{o.stale ? `stale · ${ago(o.age)}` : ago(o.age)}</small>
        {o.sources >= 2 ? <small className={`m-chip ${o.agree ? 'ok' : 'bad'}`} data-tip="Do ESPN's line, Kalshi and Polymarket favour the same side?">{o.agree ? `${o.sources} sources agree` : 'sources split'}</small> : null}</header>
      <Duel teams={o.teams} sport={o.sport} /></li>)}</ol></>;
}

// 🧾 his own slip: a game, then legs from Kalshi's own list, then the minds check it with every guard on
function SlipTab({ games, catId, work, busy, onFiled }) {
  const [g, setG] = useState(''); const [menu, setMenu] = useState(null); const [err, setErr] = useState(''); const [legs, setLegs] = useState([]); const [sending, setSending] = useState(false);
  const game = games.find(x => x.key === g);
  const load = useCallback(topic => { setMenu(null); setErr(''); setLegs([]); work(catId, { op: 'pob_menu', text: topic }).then(setMenu).catch(e => setErr(e.message)); }, [catId, work]);
  useEffect(() => { if (game) load(game.topic); }, [g]);   // eslint-disable-line react-hooks/exhaustive-deps
  const pick = (m, side) => setLegs(x => { const rest = x.filter(l => l.ticker !== m.ticker && !(m.kind === 'team' && l.kind === 'team')); const was = x.find(l => l.ticker === m.ticker);   // one winner per game: a team-to-win leg replaces the other (the server refuses both)
    return was && was.side === side ? rest : [...rest, { ticker: m.ticker, side, kind: m.kind, title: side === 'yes' ? m.over : m.under, px: side === 'yes' ? m.yes : m.no }].slice(-(menu?.max || 4)); });
  const fair = legs.length ? legs.reduce((a, l) => a * (Number(l.px) || 0), 1) : null;
  const max = menu?.max || 4; const min = menu?.min || 2;
  const send = () => { setSending(true); setErr(''); work(catId, { op: 'pob', text: game.topic, tools: { slip: legs.map(({ ticker, side, title }) => ({ ticker, side, title })) } })
    .then(j => { onFiled(j.topic || game.topic); setLegs([]); }).catch(e => setErr(e.message)).finally(() => setSending(false)); };
  return <div className="pdb-slip" data-testid="pdb-slip">
    <label className="m-field"><span>Game</span><select className="m-input" value={g} onChange={e => setG(e.target.value)} data-testid="pdb-slip-game"><option value="">Pick a game coming up…</option>{games.map(x => <option key={x.key} value={x.key}>{x.label} · {until(x.start)}</option>)}</select></label>
    {!g ? <p className="pdb-none">Pick a game: its legs come from Kalshi's own list, the same list the minds see.</p> : !menu && !err ? <p className="pdb-none">Reading Kalshi's legs for {game?.label}…</p> : null}
    {menu && !menu.legs.length ? <p className="pdb-none">Kalshi lists no slip legs for this game right now.</p> : null}
    {menu?.legs?.length ? <ol className="pdb-legs" data-testid="pdb-legs">{menu.legs.map((m, i) => { const on = legs.find(l => l.ticker === m.ticker);
      return <li key={m.ticker} className={on ? 'is-on' : ''} style={{ '--i': Math.min(i, 14) }}><span><b>{m.kind === 'player' ? m.over.replace(/ OVER .*/, '') : m.over}</b><small>{m.kind === 'player' ? `${m.stat} · line ${m.line}` : m.kind === 'line' ? 'spread / total' : 'team to win'}</small></span>
        <span className="m-seg" role="group" aria-label={`${m.over} side`}>{[['yes', m.kind === 'player' ? 'Over' : 'Yes', m.yes], ['no', m.kind === 'player' ? 'Under' : 'No', m.no]].map(([s, l, px]) => <button key={s} type="button" className={on?.side === s ? 'active' : ''} aria-pressed={on?.side === s} disabled={px == null || (!on && legs.length >= max)} onClick={() => pick(m, s)} data-tip={`${s === 'yes' ? m.over : m.under} · Kalshi asks ${px ?? '—'}`} data-testid={`pdb-leg-${i}-${s}`}>{l} <em className="m-num">{px != null ? Number(px).toFixed(2) : '—'}</em></button>)}</span></li>; })}</ol> : null}
    <section className="pdb-ticket m-glass" data-testid="pdb-ticket"><header><b>🧾 Your slip · {legs.length}/{max} legs</b>{fair != null ? <em className="m-num" data-tip="The legs' own prices multiplied: what the slip is worth if the legs were independent. Market odds, not a promise">≈ {fair.toFixed(3)} · {(1 / (fair || 1)).toFixed(1)}×</em> : null}</header>
      {legs.length ? <ol>{legs.map(l => <li key={l.ticker}><span>{l.title}</span><button type="button" className="m-btn" onClick={() => setLegs(x => x.filter(y => y.ticker !== l.ticker))} aria-label={`Remove ${l.title}`} data-tip="Take this leg off">✕</button></li>)}</ol> : <p className="pdb-none">Tap Over / Under on {min} to {max} legs.</p>}
      <ul className="pdb-checks" aria-label="What it goes through"><li>Both minds read major sites and must back every leg, a player leg with its own number and evidence</li><li>Only legs Kalshi lists open; no leg that repeats another</li><li>Your caps, balance and floor are checked again, and Kalshi is read back</li><li>Not backed whole? Nothing is sent, and its file says which leg and why</li></ul>
      <button type="button" className="m-btn m-go" disabled={busy || sending || legs.length < min} onClick={send} data-tip={busy ? 'A PoB is already running: send it once that one is done' : `Paid model calls. Both minds check your ${legs.length} legs; a slip both back goes out inside your caps (any other waits for your tap)`} data-testid="pdb-slip-send">{sending ? 'Sending…' : 'Have the minds check it'}</button>
    </section>
    {err ? <p className="dsk-note" role="alert">{err}</p> : null}
  </div>;
}

// 🧾 his own slip on its PoB reading: every leg, which mind backed it on his side, and whether it went out (the record's userSlip)
export function SlipVerdict({ v, sent = false }) {
  if (!v || !(v.legs || []).length) return null;
  const ok = !!v.whole;
  return <section className={`pdb-verdict m-glass ${ok ? 'is-ok' : 'is-no'}`} data-testid="pdb-verdict">
    <header><b>🧾 Your slip · {v.legs.length} legs</b><em className="m-num">{ok ? (sent ? 'both minds backed it · sent' : 'both minds backed it') : 'not sent'}</em></header>
    <ol>{v.legs.map(l => <li key={l.ticker} className={l.ok ? 'is-ok' : 'is-no'}><span>{l.title || l.ticker}{l.gone ? <small> · Kalshi no longer lists it open</small> : null}</span>
      <span className="pdb-verdict-minds">{(l.minds || []).map(m => <i key={m.name} className={m.backs ? 'is-ok' : 'is-no'} data-tip={m.backs ? `${m.name} backs it at ${m.conf}%` : m.side && m.side !== l.side ? `${m.name} took the other side` : `${m.name} did not back it`}>{m.backs ? '✓' : '✕'} {m.name}</i>)}</span></li>)}</ol>
    {v.say && !ok ? <p>{v.say}</p> : null}
  </section>;
}
export function PobDash({ catId, work, busy = false, onOpen, onFiled }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [tab, setTab] = useState(readTab); const [filing, setFiling] = useState('');
  const load = useCallback(() => work(catId, { op: 'pob_dash' }).then(j => { if (j && j.totals) { setD({ next: [], rows: [], odds: [], live: [], curve: [], ...j }); setErr(''); } }).catch(e => setErr(e.message)), [catId, work]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, POLL_MS); return () => clearInterval(t); }, [load]);
  useEffect(() => { if (!busy) setFiling(''); }, [busy]);
  const go = k => { setTab(k); try { localStorage.setItem(TAB_KEY, k); } catch { /* private window */ } };
  const file = topic => { setFiling(topic); setErr(''); work(catId, { op: 'pob', text: topic }).then(() => { onFiled?.(topic); load(); }).catch(e => { setFiling(''); setErr(e.message); }); };
  const games = useMemo(() => { const seen = new Set(); const slipSport = s => ['nba', 'nfl', 'nhl', 'mlb'].includes(s); return [...(d?.next || []).map(n => ({ key: n.key, label: n.teams.join(' vs '), start: n.start, topic: `${n.teams.join(' vs ')} parlay slip 3 legs`, sport: n.sport })),
    ...(d?.odds || []).map(o => ({ key: o.id, label: o.teams.map(t => t.short).join(' vs '), start: o.start, topic: `${o.teams.map(t => t.short).join(' vs ')} parlay slip 3 legs`, sport: o.sport }))].filter(x => slipSport(x.sport) && !seen.has(x.key) && seen.add(x.key)); }, [d]);   // a slip needs player / spread / total legs: the four big leagues
  if (!d) return <section className="pdb m-glass" data-testid="pdb"><p className="pdb-none">{err || 'Reading its filings, the stash odds and tonight’s games…'}</p></section>;
  const counts = { next: d.next.length, filings: d.rows.length, odds: d.odds.length, slip: null };
  return <section ref={dashBox} className="pdb" data-testid="pdb">
    <Hero t={d.totals} curve={d.curve} live={d.live} upcoming={d.upcoming} />
    <LiveStrip rows={d.live} />
    <div className="m-seg pdb-tabs" role="tablist" aria-label="PoB dashboard">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => go(k)} data-testid={`pdb-tab-${k}`}>{l}{counts[k] ? <em className="m-num"> {counts[k]}</em> : null}</button>)}</div>
    <div key={tab} className="pdb-pane" role="tabpanel">
      {tab === 'next' ? <NextTab rows={d.next} busy={busy} filing={filing} onFile={file} /> : tab === 'filings' ? <FilingsTab rows={d.rows} onOpen={onOpen} />
        : tab === 'odds' ? <OddsTab rows={d.odds} at={d.oddsAt} /> : <SlipTab games={games} catId={catId} work={work} busy={busy} onFiled={t => { setFiling(t); onFiled?.(t); load(); }} />}
    </div>
    {filing ? <p className="pdb-filed m-glass" role="status" data-testid="pdb-filed"><i aria-hidden="true" />Filed {filing}. Both minds are reading in their own windows; it lands in Filings when they are done.</p> : null}
    {err ? <p className="dsk-note" role="alert">{err}</p> : null}
  </section>;
}
