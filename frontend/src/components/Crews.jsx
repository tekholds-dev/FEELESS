import React, { Suspense, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { sharedJson } from '../lib/sharedJson';
import { readChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import { useLivePrice } from '../lib/livePriceHub';
import { price as pxWord } from '../lib/num';
import '../styles/crews.css';
import { FamilyBadge, EMBLEM } from './FamilyBadge';
import { WarRoom, WarStrip, PublicWars, useWars } from './FamilyWars';
import { FamilyBlock } from './FamilyBlock';
import { FamilyWorld } from './FamilyWorld';
import { useRemembered } from '../lib/remember';
import { Crown, Swords, Map as MapIcon, Trophy, Radio } from 'lucide-react';
import '../styles/familyNoir.css';

// 🛡 CREWS (Leaderboard › Crews · Season & ranks): $25 in SOL to the FEELESS fee wallet starts a crew with 5 seats including you; +5 seats cost $5. A crew
// shares no money — everyone signs their own trades. The weekly board ranks what members' VERIFIED FEELESS trades did over 7 days; the top 3 pay season
// points. Owner, 2026-10-19: "a huge ordeal — meta realtime, top 3 crews in the popular tabs, profile, a secure passcode, bounties, discussion boards,
// crew launch, electric border 3D". GET /crews · /crews/price · /crews/mine · POST create · seats · join · leave · act (code · post · bounty · claim ·
// settle · launch). Live: the board re-reads every 20s while the tab is open.
const EcosystemChat = React.lazy(() => import('./EcosystemChat'));
export const PRIZES = [150, 100, 60];
export const MEDAL = ['🥇', '🥈', '🥉'];
export const pctTxt = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v}%`);
export const inviteLink = (origin, path, code) => `${origin}${path}?lens=crews&join=${encodeURIComponent(code)}`;
export const rankNote = r => (r.ranked ? `${r.trades} trades · ${r.wonPct}% won` : r.members < 2 ? 'needs 2+ members to rank' : `${r.trades}/5 trades to rank`);
export const costText = (q, kind) => { const x = q?.[kind]; if (!x) return ''; return q.free ? 'free for FEELESS staff' : `$${x.usd.toFixed(x.usd % 1 ? 2 : 0)}${x.sol ? ` ≈ ${x.sol} SOL` : ''}`; };
export const seatsLine = c => `${c.members.length}/${c.seats} seats`;
// pure: the three crews on the podium — ranked first by week %, else the busiest crews (so the stage is never empty while crews exist)
export const podium = rows => { const r = (rows || []).filter(x => x.ranked); return (r.length ? r : [...(rows || [])].sort((a, b) => b.members - a.members || b.active - a.active)).slice(0, 3); };
// pure: a 0–1 heat for the electric border (activity + result): calm crews hum, hot crews crackle
export const heat = r => Math.max(0, Math.min(1, ((r?.active || 0) / Math.max(1, r?.members || 1)) * 0.5 + Math.min(1, Math.abs(Number(r?.pct) || 0) / 40) * 0.5));
import { InviteInbox, InviteBox } from './FamilyInvites';
import { MobScene } from './MobScene';
import { FamilyHero, FamilyTable, FamilyWire, MemberFile, CardStudio } from './FamilyRoom';
import '../styles/familyInvites.css';
const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Request failed'); return x; });

export function useCrewBoard(every = 20000) {
  const [b, setB] = useState(null);
  useEffect(() => { let on = true; let t = null;
    const go = fresh => sharedJson('/api/reputation/crews', { maxAge: 15000, fresh }).then(d => { if (on) setB(d); }).catch(() => {}).finally(() => { if (on) t = setTimeout(() => go(), document.hidden ? every * 3 : every); });
    go(); return () => { on = false; clearTimeout(t); }; }, [every]);
  return b;
}

// 🃏 the Don's card style (crews.CARD) — literal class names, one per option
export const CARD_STYLE = { noir: 'cd-noir', gold: 'cd-gold', blood: 'cd-blood', neon: 'cd-neon', ice: 'cd-ice', royal: 'cd-royal' };
export const CARD_FX = { smoke: 'cfx2-smoke', embers: 'cfx2-embers', rain: 'cfx2-rain', lightning: 'cfx2-lightning', stars: 'cfx2-stars' };
// ⚡ one crew as a 3D card with an electric border: tilt follows the pointer (transform only), the border's arc turns faster the hotter the crew
export function CrewCard3D({ r, place, small, onOpen }) {
  const el = useRef(null);
  const tilt = e => { const n = el.current; if (!n || small) return; const b = n.getBoundingClientRect(); n.style.setProperty('--rx', `${((e.clientY - b.top) / b.height - 0.5) * -14}deg`); n.style.setProperty('--ry', `${((e.clientX - b.left) / b.width - 0.5) * 16}deg`); };
  const flat = () => { el.current?.style.setProperty('--rx', '0deg'); el.current?.style.setProperty('--ry', '0deg'); };
  const h = heat(r);
  const cd = r.card || {};
  return <button type="button" ref={el} className={`crw-3d ${['', 'p1', 'p2', 'p3', 'p4'][place] || ''} ${small ? 'is-small' : ''} ${h > 0.6 ? 'is-hot' : ''} ${CARD_STYLE[cd.style] || ''}`} style={{ '--heat': h.toFixed(2), '--spin': `${(6 - h * 4.5).toFixed(1)}s` }}
    onPointerMove={tilt} onPointerLeave={flat} onClick={() => onOpen?.(r)} data-testid={`crew-3d-${r.tag}`} aria-label={`${r.name}: ${pctTxt(r.pct)} this week`}>
    <span className="crw-bolt" aria-hidden="true" />
    <span className="crw-face">
      {CARD_FX[cd.fx] ? <span className={`crw-cfx ${CARD_FX[cd.fx]}`} aria-hidden="true"><i /><i /><i /><i /><i /></span> : null}
      <span className="crw-medal">{MEDAL[place - 1] || '🌹'}</span>
      {r.badge ? <FamilyBadge b={r.badge} size={small ? 'sm' : 'md'} chips={!small} /> : null}
      <b className="crw-3tag">{r.tag}</b>
      <span className="crw-3name">{r.name}</span>
      <em className={`crw-3pct ${r.pct == null ? '' : r.pct >= 0 ? 'm-pos' : 'm-neg'}`} key={r.pct}>{pctTxt(r.pct)}</em>
      {cd.line ? <i className="crw-3line">“{cd.line}”</i> : null}
      <span className="crw-3meta">{r.members}/{r.seats} · {r.active} live{r.launch ? ` · 🚀 $${r.launch}` : ''}{r.bounties ? ` · 🎯 ${r.bounties}` : ''}</span>
      {!small && <span className="crw-heat" aria-hidden="true"><i style={{ transform: `scaleX(${Math.max(0.05, h)})` }} /></span>}
    </span>
  </button>;
}

// 🏆 TOP 3 CREWS strip for the popular tabs (globe war room, Home, Leaderboard): self-loading, live, one shared read
export function TopCrews({ title = '🌹 TOP FAMILIES' }) {
  const b = useCrewBoard(); const top = podium(b?.board);
  if (!top.length) return null;
  return <section className="crw-top" data-testid="top-crews"><header><span className="m-label">{title}</span><a href="/terminal/leaderboard?lens=crews">all families →</a></header>
    <div className="crw-top-row">{top.map((r, i) => <CrewCard3D key={r.id} r={r} place={i + 1} small onOpen={() => { window.location.href = '/terminal/leaderboard?lens=crews'; }} />)}</div></section>;
}

// 👤 the crew on a profile (Activity): its card live, the member's own week and points
export function CrewProfile({ address }) {
  const [c, setC] = useState(null); const b = useCrewBoard(30000);
  useEffect(() => { let on = true; if (!address) return undefined; sharedJson(`/api/reputation/crews/of/${address}`, { maxAge: 120000 }).then(d => on && setC(d?.crew || null)).catch(() => {}); return () => { on = false; }; }, [address]);
  if (!c) return null;
  const rows = b?.board || []; const r = rows.find(x => x.id === c.id); const place = r && r.ranked ? rows.filter(x => x.ranked).indexOf(r) + 1 : 0;
  return <section className="crw-prof m-card" data-testid="crew-profile"><header><span className="m-label">🌹 LA FAMILIA</span><small>{place ? `#${place} this week` : 'unranked this week'}</small></header>
    {r ? <CrewCard3D r={r} place={place && place <= 3 ? place : 4} /> : <b>[{c.tag}] {c.name}</b>}</section>;
}

function LaunchLive({ l }) {
  const lp = useLivePrice(l?.mint ? { chainId: 'solana', baseToken: { address: l.mint } } : null);
  const first = useRef(null);
  if (!l) return <p className="m-dim crw-hint">No launch pinned. The head pins the coin the family is behind — every member sees it live here.</p>;
  if (lp?.usd && !first.current) first.current = lp.usd;
  const since = lp?.usd && first.current ? (lp.usd / first.current - 1) * 100 : null;
  return <div className="crw-launch" data-testid="crew-launch"><b>🚀 ${l.symbol || l.mint.slice(0, 4)}</b><span key={lp?.usd}>{lp?.usd ? pxWord(lp.usd) : 'reading…'}</span>
    {since != null ? <em className={since >= 0 ? 'm-pos' : 'm-neg'}>{since >= 0 ? '+' : ''}{since.toFixed(2)}% since you opened it</em> : null}
    {l.note && <p>{l.note}</p>}<a href={`/terminal/coin/solana/${l.mint}`}>open chart →</a></div>;
}

export const BADGE_PARTS = [['emblem', '🎴 Emblem'], ['frame', '🖼 Frame'], ['fx', '✨ Effect'], ['colors', '🎨 Colors'], ['motto', '✒ Motto']];
export const COLOR_PAIRS = [['#d4af37', '#111111'], ['#ff4d6d', '#111111'], ['#15d16a', '#ffd36b'], ['#9b5cff', '#6fd3ff'], ['#ffffff', '#ff4d6d'], ['#ff9f45', '#9b5cff']];
// pure: how far a locked option is from unlocking (0–1), or null when the line is a place ('best') / unknown
export function unlockProgress(o, metrics) {
  if (o.ok) return 1;
  if (!o.metric || o.metric === 'best' || !o.min) return null;
  return Math.max(0, Math.min(1, (Number((metrics || {})[o.metric]) || 0) / o.min));
}
export function rollBadge(cat, d) {
  const pick = rows => { const ok = rows.filter(o => o.ok); return ok.length ? ok[Math.floor(Math.random() * ok.length)].key : null; };
  const pair = COLOR_PAIRS[Math.floor(Math.random() * COLOR_PAIRS.length)];
  return { ...d, emblem: pick(cat.parts.emblem) || d.emblem, frame: pick(cat.parts.frame) || d.frame, fx: pick(cat.parts.fx) || d.fx, c1: pair[0], c2: pair[1] };
}
// 🌹 the badge workshop (owner, 2026-10-21: "badge customizing isn't complete"): a turntable preview under a spotlight, one part at a time as
// big live tiles (each tile IS that option on your badge), locked tiles with how far the family is from them, colour pairs + swatches, a roll.
function BadgeBuilder({ mine, owner, addr, sess, q, act, busy }) {
  const [cat, setCat] = useState(null); const [d, setD] = useState(null); const [part, setPart] = useState('emblem');
  useEffect(() => { let on = true; fetch(apiUrl(`/api/reputation/crews/badge/catalog?address=${addr}&session=${encodeURIComponent(sess)}`)).then(r => (r.ok ? r.json() : null))
    .then(x => { if (on && x) { setCat(x); setD(cur => cur || { emblem: x.badge.emblem, frame: x.badge.frame, fx: x.badge.fx, c1: x.badge.c1 || x.colors[0], c2: x.badge.c2 || x.colors[1], motto: x.badge.motto || '' }); } }).catch(() => {});
    return () => { on = false; }; }, [addr, sess, mine?.badge?.v]);   // eslint-disable-line react-hooks/exhaustive-deps
  if (!cat || !d) return <p className="m-dim crw-hint">opening the badge workshop…</p>;
  const prev = { ...d, tag: mine.tag, name: mine.name, ranks: cat.metrics };
  const cost = cat.built && !cat.free ? (costText(q, 'badge') || `$${cat.restyleUsd}`) : 'free';
  const all = Object.values(cat.parts).flat(); const open = all.filter(o => o.ok).length;
  return <div className="fbb fbb2" data-testid="badge-builder">
    <div className="fbb-stage"><i className="fbb-spot" aria-hidden="true" /><div className="fbb-turn"><FamilyBadge b={prev} size="lg" /></div>
      <p className="fbb-open"><b>{open}</b>/{all.length} parts unlocked<span><i style={{ transform: `scaleX(${open / Math.max(1, all.length)})` }} /></span></p>
      <p className="fbb-met">{Object.entries(cat.metrics).map(([k, v]) => <span key={k} data-tip={cat.metricWords[k]}><b>{v ?? '—'}</b><small>{cat.metricWords[k]}</small></span>)}</p>
      {owner ? <div className="fbb-acts"><button type="button" className="m-btn" onClick={() => setD(x => rollBadge(cat, x))} data-testid="fbb-roll">🎲 Roll</button>
        <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => act('/api/reputation/crews/badge', { badge: d }, cat.built ? '🌹 badge restyled' : '🌹 badge forged', cat.built && !cat.free ? 'badge' : undefined)} data-testid="fbb-save">
          {cat.built ? `Restyle · ${cost}` : 'Forge it · free'}</button></div> : <p className="m-dim crw-hint">Only the Don forges the badge — every unlock comes from what the family really did.</p>}
    </div>
    <div className="fbb-parts">
      <nav className="fbb-tabs m-seg" role="tablist">{BADGE_PARTS.map(([k, w]) => <button key={k} type="button" role="tab" aria-selected={part === k} className={part === k ? 'active' : ''} onClick={() => setPart(k)} data-testid={`fbb-tab-${k}`}>{w}</button>)}</nav>
      {cat.parts[part] ? <div className="fbb-tiles">{cat.parts[part].map((o, i) => { const pr = unlockProgress(o, cat.metrics);
        return <button key={o.key} type="button" disabled={!o.ok || !owner} style={{ '--i': i }} className={`fbb-tile ${d[part] === o.key ? 'active' : ''} ${o.ok ? '' : 'is-locked'}`}
          onClick={() => setD(x => ({ ...x, [part]: o.key }))} data-tip={o.ok ? o.label : `🔒 ${o.need}`} data-testid={`fbb-${part}-${o.key}`}>
          <span className="fbb-mini"><FamilyBadge b={{ ...prev, [part]: o.key }} size="sm" /></span><small>{o.label}</small>
          {o.ok ? null : <><i className="fbb-lock">🔒</i>{pr != null ? <span className="fbb-prog"><b style={{ transform: `scaleX(${Math.max(0.04, pr)})` }} /></span> : null}<em>{o.need}</em></>}</button>; })}</div> : null}
      {part === 'colors' ? <div className="fbb-colors">
        <div className="fbb-pairs">{COLOR_PAIRS.map(([a1, a2]) => <button key={a1 + a2} type="button" disabled={!owner} className={d.c1 === a1 && d.c2 === a2 ? 'active' : ''} onClick={() => setD(x => ({ ...x, c1: a1, c2: a2 }))} aria-label={`colours ${a1} and ${a2}`}><i style={{ background: a1 }} /><i style={{ background: a2 }} /></button>)}</div>
        {['c1', 'c2'].map(k => <span key={k} className="fbb-sw"><em>{k === 'c1' ? 'MAIN' : 'TRIM'}</em>{cat.colors.map(c => <button key={c} type="button" disabled={!owner} className={d[k] === c ? 'active' : ''} style={{ background: c }} onClick={() => setD(x => ({ ...x, [k]: c }))} aria-label={`${k} ${c}`} />)}</span>)}</div> : null}
      {part === 'motto' ? <div className="fbb-motto"><input className="m-input" value={d.motto} maxLength={cat.mottoMax} disabled={!owner} placeholder="Famiglia prima di tutto" onChange={e => setD(x => ({ ...x, motto: e.target.value }))} aria-label="Family motto" />
        <small>{d.motto.length}/{cat.mottoMax} · shown under the badge on every card</small></div> : null}
    </div>
  </div>;
}

const TABS = [['card', '🃏 Card'], ['invite', '✉ Invite'], ['badge', '🌹 Badge'], ['board', '💬 Board'], ['bounty', '🎯 Bounties'], ['launch', '🚀 Launch'], ['members', '➕ Seats'], ['code', '🔐 Code']];

function CrewHQ({ mine, owner, addr, sess, busy, setBusy, setMine, act, q, rows, inv, reload }) {
  const [tab, setTab] = useState(mine.badge?.set ? 'board' : 'badge'); const [txt, setTxt] = useState(''); const [rew, setRew] = useState(50); const [mint, setMint] = useState(''); const [sym, setSym] = useState(''); const [code, setCode] = useState(''); const [plain, setPlain] = useState('');
  const doAct = async (a, body, ok) => { setBusy(a); try { const r = await post('/api/reputation/crews/act', { address: addr, session: sess, act: a, ...body }); if (r.crew) setMine(r.crew); if (r.plainCode) setPlain(r.plainCode); toast.success(ok); setTxt(''); } catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const posts = mine.posts || []; const roots = posts.filter(p => !p.parent).slice().reverse(); const kids = id => posts.filter(p => p.parent === id);
  const link = mine.code ? inviteLink(window.location.origin, window.location.pathname, mine.code) : null;
  return <>
    <nav className="crw-tabs m-seg" role="tablist">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`crew-tab-${k}`}>{l}{k === 'bounty' && mine.bountiesOpen ? <b>{mine.bountiesOpen}</b> : null}</button>)}</nav>
    <div className="crw-pane" key={tab}>
      {tab === 'card' && <CardStudio mine={mine} owner={owner} addr={addr} sess={sess} onChanged={c => c && setMine(c)} preview={d => { const r = rows.find(x => x.id === mine.id) || { id: mine.id, name: mine.name, tag: mine.tag, members: mine.members.length, seats: mine.seats, active: mine.vitals?.active || 0, pct: null, badge: mine.badge }; return <CrewCard3D r={{ ...r, card: d }} place={1} />; }} />}
      {tab === 'badge' && <BadgeBuilder mine={mine} owner={owner} addr={addr} sess={sess} q={q} act={act} busy={busy} />}
      {tab === 'board' && <>
        <form className="crw-row" onSubmit={e => { e.preventDefault(); doAct('post', { text: txt }, '💬 posted'); }}><input className="m-input" placeholder="Talk to the family…" value={txt} maxLength={500} onChange={e => setTxt(e.target.value)} aria-label="Post" /><button type="submit" className="m-btn primary" disabled={!txt.trim() || !!busy}>Post</button></form>
        {!roots.length && <p className="m-dim crw-hint">The board is quiet. Drop a play, a lesson or a call — members only.</p>}
        <ul className="crw-posts">{roots.map((p, i) => <li key={p.id} style={{ '--i': i }}><b>{p.name}</b><small>{new Date(p.at * 1000).toLocaleString()}</small><p>{p.text}</p>
          {kids(p.id).map(k => <div key={k.id} className="crw-reply"><b>{k.name}</b> {k.text}</div>)}
          <button type="button" className="crw-rbtn" onClick={() => { const t = window.prompt('Reply:'); if (t) doAct('post', { text: t, parent: p.id }, '↩ replied'); }}>↩ reply</button></li>)}</ul>
        <details className="crw-room"><summary>⚡ Live family room</summary><Suspense fallback={<small className="m-dim">Opening the room…</small>}><div className="crw-chat"><EcosystemChat compact room={mine.room} ecosystem={{ id: `crew-${mine.id}`, name: mine.name }} /></div></Suspense></details>
      </>}
      {tab === 'bounty' && <>
        {owner && <form className="crw-row" onSubmit={e => { e.preventDefault(); doAct('bounty', { text: txt, reward: Number(rew) }, '🎯 bounty posted'); }}><input className="m-input" placeholder="Task (e.g. find a germ entry under $50K)" value={txt} maxLength={120} onChange={e => setTxt(e.target.value)} aria-label="Bounty task" />
          <input className="m-input crw-tag" value={rew} onChange={e => setRew(e.target.value.replace(/\D/g, ''))} aria-label="Reward points" /><button type="submit" className="m-btn primary" disabled={!txt.trim() || !!busy}>Post · {rew || 0} pts</button></form>}
        <p className="m-dim crw-hint">Bounties pay family points, never money.</p>
        <ul className="crw-bounties">{(mine.bounties || []).slice().reverse().map(b => <li key={b.id} className={`is-${b.state}`}><b>🎯 {b.title}</b><em>{b.reward} pts</em><small>{b.state === 'open' ? 'open' : b.state === 'claimed' ? `claimed by ${b.byName}: ${b.proof}` : `paid to ${b.byName}`}</small>
          {b.state === 'open' && <button type="button" className="m-btn" disabled={!!busy} onClick={() => { const pr = window.prompt('Proof (a tx, a link, a line):'); if (pr) doAct('claim', { id: b.id, text: pr }, '🙋 claimed'); }}>Claim</button>}
          {b.state === 'claimed' && owner && <><button type="button" className="m-btn primary" onClick={() => doAct('settle', { id: b.id, pay: true }, '✅ paid')}>Pay</button><button type="button" className="m-btn" onClick={() => doAct('settle', { id: b.id, pay: false }, '↺ reopened')}>Reopen</button></>}</li>)}</ul>
      </>}
      {tab === 'launch' && <><LaunchLive l={mine.launch} />
        {owner && <form className="crw-row" onSubmit={e => { e.preventDefault(); doAct('launch', { mint: mint.trim(), symbol: sym, text: txt }, mint ? '🚀 launch pinned' : 'launch cleared'); }}><input className="m-input" placeholder="Coin CA (empty = clear)" value={mint} onChange={e => setMint(e.target.value)} aria-label="Launch mint" /><input className="m-input crw-tag" placeholder="SYM" value={sym} maxLength={16} onChange={e => setSym(e.target.value.toUpperCase())} aria-label="Symbol" /><input className="m-input" placeholder="Why we're behind it" value={txt} maxLength={160} onChange={e => setTxt(e.target.value)} aria-label="Launch note" /><button type="submit" className="m-btn primary" disabled={!!busy}>Pin</button></form>}</>}
      {tab === 'invite' && <InviteBox addr={addr} sess={sess} sent={inv?.sent} canAdd={inv?.canAdd} onDone={reload} />}
      {tab === 'members' && <div className="crw-seats"><p className="m-dim crw-hint">{seatsLine(mine)} — everyone sits at the table above.</p>
        {owner ? <button type="button" className="m-btn primary" disabled={!!busy} onClick={() => act('/api/reputation/crews/seats', {}, `➕ +${mine.packSeats} seats`, 'seats')} data-testid="crew-seats">{`➕ +${mine.packSeats} seats · ${costText(q, 'seats') || `$${mine.packUsd}`}`}</button> : <p className="m-dim crw-hint">Only the Don adds seats.</p>}</div>}
      {tab === 'code' && <>
        {plain && <div className="crw-plain" data-testid="crew-plain"><b>🔐 {plain}</b><small>shown ONCE — it is stored encrypted (salted hash). Copy it now.</small><button type="button" className="m-btn" onClick={() => navigator.clipboard?.writeText(inviteLink(window.location.origin, window.location.pathname, plain))}>⧉ Copy invite</button></div>}
        {link ? <div className="crw-invite"><code>{link}</code><button type="button" className="m-btn" onClick={() => navigator.clipboard?.writeText(link).then(() => toast.success('Invite link copied'))} data-testid="crew-copy">⧉ Copy invite</button></div>
          : <p className="m-dim crw-hint">{mine.codeSet ? `🔐 secure passcode set (…${mine.codeTail || ''}). Members join with it; it is never shown again.` : ''}</p>}
        {owner && <form className="crw-row" onSubmit={e => { e.preventDefault(); doAct('code', { code: code.trim() }, '🔐 code set'); setCode(''); }}><input className="m-input" placeholder="Your own code (6–24) — or leave empty to generate" value={code} maxLength={24} onChange={e => setCode(e.target.value)} aria-label="Crew code" /><button type="submit" className="m-btn primary" disabled={!!busy} data-testid="crew-code">{code.trim() ? 'Set code' : '🎲 Generate secure passcode'}</button></form>}
      </>}
    </div>
  </>;
}

// 🔴 LA FAMILIA LIVE (owner, 2026-10-19: "more live animations, meta tools, vitals and social events"): every family's public moves as a
// running feed + the live numbers (GET /crews/live: founded · joined · badge forged · bounty posted / claimed / paid · launch · crowned).
const EV_ICON = { founded: '🌹', joined: '🤝', badge: '🛡', bounty: '🎯', claimed: '✋', paid: '💰', launch: '🚀', crown: '👑' };
export const evAgo = t => { const s = Date.now() / 1000 - t; return s < 60 ? 'now' : s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };
export function FamilyPulse() {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; const load = () => sharedJson('/api/reputation/crews/live', { maxAge: 15000 }).then(x => on && x && setD(x)).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000); return () => { on = false; clearInterval(t); }; }, []);
  const v = d?.vitals || {}; const ev = d?.events || [];
  const tiles = [['FAMILIES', v.families], ['MEMBERS', v.members], ['JOINED 7D', v.joinedWeek], ['OPEN BOUNTIES', v.openBounties], ['PTS PAID 7D', v.ptsWeek], ['LAUNCHES', v.launches]];
  return <section className="crw-pulse m-card" data-testid="family-pulse">
    <header><span className="crw-live"><i />LIVE</span><b>LA FAMILIA · WHAT THE FAMILIES ARE DOING</b></header>
    <div className="crw-vit">{tiles.map(([k, n], i) => <span key={k} style={{ '--i': i }}><em>{k}</em><b key={n}>{n == null ? '—' : Number(n).toLocaleString('en-US')}</b></span>)}</div>
    {ev.length ? <ol className="crw-feed" data-testid="family-feed">{ev.slice(0, 12).map((e, i) => <li key={`${e.kind}-${e.id}-${e.at}`} className={`k-${e.kind}`} style={{ '--i': i }}>
      <i>{EV_ICON[e.kind] || '•'}</i><b>[{e.fam}]</b><span>{e.text}</span><small>{evAgo(e.at)}</small></li>)}</ol>
      : <p className="crw-empty">{d ? 'Quiet this week — found a family, post a bounty, pin a launch.' : 'Reading the families…'}</p>}
  </section>;
}

// 🏆 THE PODIUM (Board tab): the week's top three families on drawn plinths — #1 in the middle, tallest, crowned; each plinth wears the family's
// badge, its verified % (bar = the move) and its season-points prize. Ranks 4+ stay in the list under it.
export function Podium({ rows }) {
  const order = [1, 0, 2].map((k, i) => ({ r: (rows || [])[k] || null, place: [2, 1, 3][i] }));   // an empty plinth waits for a family that ranks
  return <div className="fpd" data-testid="crew-podium">{order.map(({ r, place }, i) => (!r ? <div key={`open-${place}`} className={`fpd-step p${place} is-open`} style={{ '--i': i }} data-tip="Open — a family with 2+ members and 5 closed trades this week takes it">
    <div className="fpd-who"><span className="fpd-ghost" aria-hidden="true" /><b>OPEN</b><small>rank to claim</small></div><div className="fpd-plinth"><strong>{place}</strong><small>+{PRIZES[place - 1]} pts</small></div></div>
    : <div key={r.id} className={`fpd-step p${place}`} style={{ '--i': i }} data-tip={rankNote(r)}>
    <div className="fpd-who">{place === 1 ? <i className="fpd-crown" aria-hidden="true" /> : null}{r.badge ? <FamilyBadge b={r.badge} size="md" /> : <span className="crw-tagc">{r.tag}</span>}
      <b>{r.name}</b><em className={`m-num ${r.pct == null ? '' : r.pct >= 0 ? 'm-pos' : 'm-neg'}`} key={r.pct}>{pctTxt(r.pct)}</em>
      <u><s style={{ transform: `scaleX(${Math.max(0.04, Math.min(1, Math.abs(Number(r.pct) || 0) / 50))})` }} className={r.pct >= 0 ? 'up' : 'dn'} /></u></div>
    <div className="fpd-plinth"><strong>{place}</strong><small>+{PRIZES[place - 1]} pts</small></div></div>))}</div>;
}

// 🌹 the MOB & Rewards › Familia tabs (owner, 2026-10-21: "a landing page, all unique tabs for it")
export const FAM_TABS = [['home', 'Fee City', MapIcon], ['family', 'My family', Crown], ['wars', 'Wars', Swords], ['board', 'Board', Trophy], ['feed', 'Live', Radio]];   // 👑 the city IS the landing (owner, 2026-10-21)
export function Crews({ onScene }) {
  const { wallet, provider } = useWallet() || {}; const addr = wallet?.address || ''; const sess = addr ? readChatSession(addr) : '';
  const board = useCrewBoard(); const warsD = useWars(); const [tab, setTab] = useRemembered('feeless.fam.tab', 'home'); const [file, setFile] = useState(null); const [block, setBlock] = useState(undefined);
  const liveWars = (warsD?.wars || []).filter(w => w.state === 'live').length;
  const [mine, setMine] = useState(undefined); const [inv, setInv] = useState(null); const [busy, setBusy] = useState(''); const [q, setQ] = useState(null);
  const [name, setName] = useState(''); const [tag, setTag] = useState(''); const [code, setCode] = useState(() => { try { return new URLSearchParams(window.location.search).get('join') || ''; } catch { return ''; } });
  const loadMine = () => { if (!addr || !sess) { setMine(null); return Promise.resolve(); } return fetch(apiUrl(`/api/reputation/crews/mine?address=${addr}&session=${encodeURIComponent(sess)}`)).then(r => (r.ok ? r.json() : { crew: null })).then(d => { setMine(d.crew || null); setInv({ invites: d.invites || [], sent: d.sent || [], canAdd: !!d.canAdd }); }).catch(() => setMine(null)); };
  useEffect(() => { loadMine(); const t = setInterval(() => { if (!document.hidden) loadMine(); }, 20000); return () => clearInterval(t); }, [addr, sess]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setTimeout(() => fetch(apiUrl(`/api/reputation/crews/price?address=${addr}&name=${encodeURIComponent(name)}&tag=${encodeURIComponent(tag)}`)).then(r => (r.ok ? r.json() : null)).then(setQ).catch(() => {}), 300); return () => clearTimeout(t); }, [addr, name, tag, mine?.id]);
  const pay = async (kind) => {   // one SOL transfer YOU sign to the fee wallet → its signature goes with the request
    if (q?.free) return '';
    if (!q?.payTo || !q?.[kind]?.sol) throw new Error('The fee wallet or the SOL price is not available right now — try again in a minute.');
    const { batchSend } = await import('../lib/batchSend');
    const [sig] = await batchSend({ provider, owner: addr, recipients: [{ address: q.payTo, amount: Number(q[kind].sol.toFixed(9)) }], kind: `crew-${kind}` });
    return sig;
  };
  const act = async (path, body, ok, kind) => {
    if (!sess) { toast.error('Connect your wallet + open chat once to sign in first.'); return; }
    setBusy(path);
    try {
      const signature = kind ? await pay(kind) : undefined;
      const r = await post(path, { address: addr, session: sess, ...body, ...(kind ? { signature } : {}) }); toast.success(ok);
      setMine(r.crew || null); sharedJson.freshAt = Date.now();
    } catch (e) { toast.error(e.message); } finally { setBusy(''); }
  };
  const rows = board?.board || []; const owner = mine?.members?.find(m => m.owner)?.address === addr;
  const famTab = FAM_TABS.some(([k]) => k === tab) ? tab : 'home';
  useEffect(() => { onScene?.(famTab); }, [famTab, onScene]);   // 🎬 the page behind takes this tab's scene
  const warAct = (a, body, ok) => act('/api/reputation/crews/act', { act: a, ...body }, ok);
  return <section className="crw crw-noir" data-testid="crews">
    {famTab === 'family' ? <MobScene heat={(mine?.vitals?.heat ?? 30) / 100} sign={mine ? mine.tag : 'FAMIGLIA'} /> : null}   {/* the family's own street sign; every other tab's scene is the page backdrop */}
    <nav className="fam-tabs" role="tablist" aria-label="La Familia">{FAM_TABS.map(([k, label, Icon]) => <button key={k} type="button" role="tab" aria-selected={famTab === k} className={famTab === k ? 'active' : ''}
      onClick={() => setTab(k)} data-testid={`fam-tab-${k}`}><Icon size={14} aria-hidden="true" /><span>{k === 'family' && mine ? mine.tag : label}</span>{k === 'wars' && liveWars ? <b>{liveWars}</b> : null}</button>)}</nav>
    <InviteInbox invites={inv?.invites} inFamily={!!mine} addr={addr} sess={sess} onDone={loadMine} />
    {famTab === 'home' && (block === undefined ? <><FamilyWorld addr={addr} sess={sess} onEnter={() => setBlock(null)} onJoin={() => setTab('family')} />
    </> : <FamilyBlock cid={block} addr={addr} sess={sess} onBack={() => setBlock(undefined)} />)}
    {famTab === 'family' && (mine ? <>
      <FamilyHero mine={mine} busy={busy} onLeave={() => { if (window.confirm(`Leave ${mine.name}?`)) act('/api/reputation/crews/leave', {}, 'Left the family'); }} />
      <div className="frm-room"><FamilyTable mine={mine} owner={owner} addr={addr} sess={sess} onChanged={c => c && setMine(c)} onOpen={setFile} /><FamilyWire mine={mine} /></div>
      <div className="crw-mine m-card"><CrewHQ mine={mine} owner={owner} addr={addr} sess={sess} busy={busy} setBusy={setBusy} setMine={setMine} act={act} q={q} rows={rows} inv={inv} reload={loadMine} /></div>
    </> : <>
      <header className="fnr-title"><span>🌹 LA FAMILIA</span><b>Famiglia prima di tutto.</b><small>Families rise on verified trades, settle scores in battle trenches, and wear what they earned.</small></header>
    <div className="crw-mine m-card m-live">
      <>
        <header><span className="m-label">🌹 START A FAMILY OR JOIN ONE</span><small>{q ? `${costText(q, 'create')} · ${q.baseSeats} seats incl. you · +${q.packSeats} seats ${costText(q, 'seats')}` : '5 seats incl. you'} · a family shares no money</small></header>
        {mine === undefined ? <small className="m-dim">Loading…</small> : !sess ? <p className="crw-hint m-dim">Connect your wallet and open chat once to start or join a family.</p> : <div className="crw-forms">
          <form onSubmit={e => { e.preventDefault(); act('/api/reputation/crews/create', { name, tag }, 'Familia started — build your badge in 🌹 Badge', 'create'); }} data-testid="crew-create-form">
            <input className="m-input" placeholder="Family name" value={name} maxLength={20} onChange={e => setName(e.target.value)} aria-label="Family name" />
            <input className="m-input crw-tag" placeholder="TAG" value={tag} maxLength={4} onChange={e => setTag(e.target.value.toUpperCase())} aria-label="Family tag" />
            <button type="submit" className="m-btn primary" disabled={!!busy || name.trim().length < 3 || tag.length < 2 || (q && q.ok === false)} data-tip="One SOL transfer you sign to the FEELESS fee wallet, checked on-chain. If anything fails after you pay, send the same payment again — it is kept.">{busy.endsWith('/create') ? 'Paying…' : `Start a family · ${costText(q, 'create') || '$25'}`}</button>
            {q?.ok === false && (name || tag) && <small className="crw-why" data-testid="crew-why">{q.why}</small>}</form>
          <form onSubmit={e => { e.preventDefault(); act('/api/reputation/crews/join', { code }, 'Welcome to the family'); }} data-testid="crew-join-form">
            <input className="m-input" placeholder="Invite code or passcode (free to join)" value={code} maxLength={32} onChange={e => setCode(e.target.value)} aria-label="Invite code" />
            <button type="submit" className="m-btn" disabled={!!busy || !code.trim()}>Join</button></form></div>}
      </>
    </div>
    </>)}
    {famTab === 'wars' && <><WarStrip />{mine ? <div className="crw-mine m-card"><WarRoom mine={mine} owner={owner} rows={rows} busy={busy} act={warAct} /></div> : <PublicWars />}</>}
    {famTab === 'board' && <>
    <div className="crw-board m-card">
      <header><span className="m-label">🏆 WEEKLY FAMILY BOARD</span><small data-tip={board?.rule}>{board ? `${board.total} famil${board.total === 1 ? 'y' : 'ies'} · verified trades, last 7 days` : ''}</small></header>
      <p className="crw-prize" data-testid="crew-prizes">The top 3 families pay every member season points each week: <b>🥇 +{PRIZES[0]}</b> · <b>🥈 +{PRIZES[1]}</b> · <b>🥉 +{PRIZES[2]}</b></p>
      {board && !rows.length && <p className="crw-hint m-dim">No families yet. Start one, fill your seats and trade — the board ranks verified results.</p>}
      <Podium rows={rows.filter(r => r.ranked).slice(0, 3)} />
      <ol>{rows.map((r, i) => <li key={r.id} className={r.ranked ? '' : 'is-off'} style={{ '--i': i }} data-testid={`crew-row-${r.tag}`}>
        <b className="crw-rank">{r.ranked ? i + 1 : '·'}</b>{r.badge ? <FamilyBadge b={r.badge} size="sm" /> : <span className="crw-tagc">{r.tag}</span>}<span className="crw-rname">{r.name}{r.launch ? <i> 🚀 ${r.launch}</i> : null}</span>
        <small>{r.members}/{r.seats} seats · {r.active} active</small><em className={`m-num ${r.pct == null ? '' : r.pct >= 0 ? 'm-pos' : 'm-neg'}`} key={r.pct}>{pctTxt(r.pct)}</em><small className="crw-note">{rankNote(r)}</small>
        <span className="crw-bar" aria-hidden="true"><i style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, Math.abs(Number(r.pct) || 0) / 50))})` }} className={r.pct >= 0 ? 'up' : 'dn'} /></span></li>)}</ol>
      <small className="m-dim crw-rule">{board?.rule}</small>
    </div>
    </>}
    {famTab === 'feed' && <FamilyPulse />}
    {file && mine ? <MemberFile m={file} mine={mine} onClose={() => setFile(null)} /> : null}
  </section>;
}

// 🌹 the family badge beside a name (profile header): the family the wallet is in — nothing if none
export function CrewChip({ address }) {
  const [c, setC] = useState(null);
  useEffect(() => { let alive = true; if (!address) return undefined; sharedJson(`/api/reputation/crews/of/${address}`, { maxAge: 120000 }).then(d => alive && setC(d?.crew || null)).catch(() => {}); return () => { alive = false; }; }, [address]);
  return c ? <a className="m-chip crw-chip" href="/terminal/leaderboard?lens=crews" data-tip={`La Familia: ${c.name}${c.badge?.motto ? ` — “${c.badge.motto}”` : ''}`} data-testid="crew-chip">{c.badge ? <FamilyBadge b={c.badge} size="sm" /> : '🌹'} {c.tag}</a> : null;
}
