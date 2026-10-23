import React, { Suspense, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { sharedJson } from '../lib/sharedJson';
import { readChatSession, getChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import { useLivePrice } from '../lib/livePriceHub';
import { price as pxWord } from '../lib/num';
import '../styles/crews.css';
import { FamilyBadge } from './FamilyBadge';
import { PRIZES, MEDAL, pctTxt, inviteLink, rankNote, costText, seatsLine, podium, heat, CARD_STYLE, CARD_FX, evAgo, useCrewBoard, CrewCard3D, TopCrews, CrewProfile, CrewChip } from './CrewCard';
export { PRIZES, MEDAL, pctTxt, inviteLink, rankNote, costText, seatsLine, podium, heat, CARD_STYLE, CARD_FX, evAgo, useCrewBoard, CrewCard3D, TopCrews, CrewProfile, CrewChip };
import { CrestForge } from './CrestForge';
import { FamilyCardArt } from './FamilyCardArt';
import { useGlide } from '../lib/useGlide';
export { useGlide };
import { WarRoom, WarStrip, PublicWars, useWars } from './FamilyWars';
import { FamilyBlock } from './FamilyBlock';
import { FamilyWorld, FamilyTab } from './FamilyWorld';
import { FamilyHQ } from './FamilyHQ';
import { useRemembered } from '../lib/remember';
import { Crown, Swords, Map as MapIcon, Trophy, Radio } from 'lucide-react';
import '../styles/familyNoir.css';
import '../styles/familiaBackdrop.css';
import '../styles/familyWire.css';   // the Podium's own rules live there (it must never render bare without the page backdrop)

// 🛡 CREWS (Leaderboard › Crews · Season & ranks): $25 in SOL to the FEELESS fee wallet starts a crew with 5 seats including you; +5 seats cost $5. A crew
// shares no money — everyone signs their own trades. The weekly board ranks what members' VERIFIED FEELESS trades did over 7 days; the top 3 pay season
// points. Owner, 2026-10-19: "a huge ordeal — meta realtime, top 3 crews in the popular tabs, profile, a secure passcode, bounties, discussion boards,
// crew launch, electric border 3D". GET /crews · /crews/price · /crews/mine · POST create · seats · join · leave · act (code · post · bounty · claim ·
// settle · launch). Live: the board re-reads every 20s while the tab is open.
const EcosystemChat = React.lazy(() => import('./EcosystemChat'));
// pure: the three crews on the podium — ranked first by week %, else the busiest crews (so the stage is never empty while crews exist)
// pure: a 0–1 heat for the electric border (activity + result): calm crews hum, hot crews crackle
import { InviteInbox, InviteBox } from './FamilyInvites';
import { MobScene } from './MobScene';
import { FamilyTable, FamilyWire, MemberFile, CardStudio } from './FamilyRoom';
import '../styles/familyInvites.css';
import { FamiliaTradeDock } from './FamiliaTrade';
const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Request failed'); return x; });


// 🃏 the Don's card style (crews.CARD) — literal class names, one per option
// ⚡ THE FAMILY CARD (owner, 2026-10-22 redo: "a drawn trading card"): crest header over a drawn scene per style (FamilyCardArt), the name in
// Playfair, the live vitals ON the card (week % that glides to its number, seats filled, rank plate), the Don's tagline, a calm live effect.
// Tilt follows the pointer (transform only); the electric border's arc turns faster the hotter the family is.

// 🏆 TOP 3 CREWS strip for the popular tabs (globe war room, Home, Leaderboard): self-loading, live, one shared read

// 👤 the crew on a profile (Activity): its card live, the member's own week and points

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

export const TABS = [['card', '🃏 Card'], ['invite', '✉ Invite'], ['badge', '🌹 Badge'], ['board', '💬 Board'], ['bounty', '🎯 Bounties'], ['launch', '🚀 Launch'], ['members', '➕ Seats'], ['code', '🔐 Code']];

function CrewHQ({ mine, owner, addr, sess, busy, setBusy, setMine, act, q, rows, inv, reload, tab: tabP, setTab: setTabP }) {
  const [tabS, setTabS] = useState(mine.badge?.set ? 'board' : 'badge'); const tab = tabP || tabS; const setTab = setTabP || setTabS;   // controlled by the Family HQ's tool rail when it is given const [txt, setTxt] = useState(''); const [rew, setRew] = useState(50); const [mint, setMint] = useState(''); const [sym, setSym] = useState(''); const [code, setCode] = useState(''); const [plain, setPlain] = useState('');
  const doAct = async (a, body, ok) => { setBusy(a); try { const r = await post('/api/reputation/crews/act', { address: addr, session: sess, act: a, ...body }); if (r.crew) setMine(r.crew); if (r.plainCode) setPlain(r.plainCode); toast.success(ok); setTxt(''); } catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const posts = mine.posts || []; const roots = posts.filter(p => !p.parent).slice().reverse(); const kids = id => posts.filter(p => p.parent === id);
  const link = mine.code ? inviteLink(window.location.origin, window.location.pathname, mine.code) : null;
  return <>
    {tabP ? null : <nav className="crw-tabs m-seg" role="tablist">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`crew-tab-${k}`}>{l}{k === 'bounty' && mine.bountiesOpen ? <b>{mine.bountiesOpen}</b> : null}</button>)}</nav>}
    <div className="crw-pane" key={tab}>
      {tab === 'card' && <CardStudio mine={mine} owner={owner} addr={addr} sess={sess} onChanged={c => c && setMine(c)} preview={d => { const r = rows.find(x => x.id === mine.id) || { id: mine.id, name: mine.name, tag: mine.tag, members: mine.members.length, seats: mine.seats, active: mine.vitals?.active || 0, pct: null, badge: mine.badge }; return <CrewCard3D r={{ ...r, card: d }} place={1} />; }} />}
      {tab === 'badge' && <CrestForge mine={mine} owner={owner} addr={addr} sess={sess} costWord={costText(q, 'badge')} act={act} busy={busy} />}
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
// 📡 THE WIRE (Live tab, 2026-10-22 redo): a drawn radar — the arm sweeps, every family event of the week is a blip (closer to the centre =
// newer, its angle = what kind of event) — the week's counters glide to their numbers, and the teletype under it wears each family's crest.
const EV_ORDER = ['founded', 'joined', 'badge', 'bounty', 'claimed', 'paid', 'launch', 'crown'];
const EV_COLOR = { founded: '#ff4d6d', joined: '#45e486', badge: '#d4af37', bounty: '#ff9f45', claimed: '#6fd3ff', paid: '#ffd36b', launch: '#9b5cff', crown: '#fff1c4' };
// pure: where an event sits on the radar (newer = nearer the middle; the kind picks the slice)
export function blipAt(e, now) {
  const k = Math.max(0, EV_ORDER.indexOf(e.kind)); const age = Math.max(0, now - (e.at || now));
  const r = 18 + Math.min(1, age / (7 * 86400)) * 70; const a = ((k + 0.5) / EV_ORDER.length) * Math.PI * 2 + ((String(e.id).length * 37) % 20 - 10) / 60;
  return { x: +(100 + r * Math.cos(a)).toFixed(1), y: +(100 + r * Math.sin(a)).toFixed(1), fresh: age < 3600 };
}
function Glide({ n }) { const v = useGlide(n == null ? null : Number(n), 900); return v == null ? '—' : Math.round(v).toLocaleString('en-US'); }
export function FamilyPulse({ rows }) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; const load = () => sharedJson('/api/reputation/crews/live', { maxAge: 15000 }).then(x => on && x && setD(x)).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000); return () => { on = false; clearInterval(t); }; }, []);
  const v = d?.vitals || {}; const ev = d?.events || []; const now = Date.now() / 1000;
  const crest = Object.fromEntries((rows || []).filter(r => r.badge).map(r => [r.tag, r.badge]));
  const tiles = [['FAMILIES', v.families], ['MEMBERS', v.members], ['JOINED 7D', v.joinedWeek], ['OPEN BOUNTIES', v.openBounties], ['PTS PAID 7D', v.ptsWeek], ['LAUNCHES', v.launches]];
  return <section className="crw-pulse fwi" data-testid="family-pulse">
    <header><span className="crw-live"><i />LIVE</span><b>THE WIRE · WHAT THE FAMILIES ARE DOING</b></header>
    <div className="fwi-top">
      <svg className="fwi-radar" viewBox="0 0 200 200" role="img" aria-label={`${ev.length} family events this week on the radar`}>
        <circle cx="100" cy="100" r="92" className="ring o" /><circle cx="100" cy="100" r="62" className="ring" /><circle cx="100" cy="100" r="32" className="ring" />
        <path d="M100,8 V192 M8,100 H192" className="cross" />
        <g className="fwi-sweep"><path d="M100,100 L100,8 A92,92 0 0 1 165,35 Z" /></g>
        {ev.slice(0, 24).map(e => { const p = blipAt(e, now); return <g key={`${e.kind}-${e.id}-${e.at}`} className={`fwi-blip ${p.fresh ? 'is-fresh' : ''}`} style={{ '--bc': EV_COLOR[e.kind] || '#45e486' }}>
          <circle cx={p.x} cy={p.y} r="7" className="halo" /><circle cx={p.x} cy={p.y} r="3" className="dot" /><title>[{e.fam}] {e.text}</title></g>; })}
        <circle cx="100" cy="100" r="3" className="core" />
      </svg>
      <div className="fwi-vit">{tiles.map(([k, n], i) => <span key={k} style={{ '--i': i }}><em>{k}</em><b><Glide n={n} /></b></span>)}</div>
    </div>
    {ev.length ? <ol className="fwi-feed" data-testid="family-feed">{ev.slice(0, 12).map((e, i) => <li key={`${e.kind}-${e.id}-${e.at}`} className={`k-${e.kind} ${now - e.at < 3600 ? 'is-fresh' : ''}`} style={{ '--i': i, '--bc': EV_COLOR[e.kind] || '#45e486' }}>
      <span className="fwi-crest">{crest[e.fam] ? <FamilyBadge b={{ ...crest[e.fam], tag: e.fam }} size="sm" px={26} /> : <i>{EV_ICON[e.kind] || '•'}</i>}</span>
      <b>[{e.fam}]</b><span className="fwi-txt"><u>{EV_ICON[e.kind] || '•'}</u>{e.text}</span><small>{evAgo(e.at)}</small></li>)}</ol>
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
  const { wallet, provider, signMessage } = useWallet() || {}; const addr = wallet?.address || '';
  // 🔑 sign in RIGHT HERE (one signature, no transaction) — Familia used to read the chat session only, so a wallet that never opened chat in
  // this browser (or whose session expired) saw the city as a stranger: "not signed in", no family, no expand (owner, 2026-10-22)
  const [sess, setSess] = useState(() => (addr ? readChatSession(addr) : ''));
  useEffect(() => { setSess(addr ? readChatSession(addr) : ''); }, [addr]);
  const signIn = async () => { if (!addr) { toast.error('Connect your wallet first.'); return ''; }
    try { const t = await getChatSession(addr, signMessage); setSess(t); return t; } catch (e) { toast.error(e.code === 4001 ? 'Declined in wallet.' : e.message); return ''; } };
  const board = useCrewBoard(); const warsD = useWars(); const [tab, setTab] = useRemembered('feeless.fam.tab', 'home'); const [file, setFile] = useState(null); const [block, setBlock] = useState(undefined);
  const liveWars = (warsD?.wars || []).filter(w => w.state === 'live').length;
  const [mine, setMine] = useState(undefined); const [fams, setFams] = useState([]); const [inv, setInv] = useState(null); const [busy, setBusy] = useState(''); const [q, setQ] = useState(null);
  const [name, setName] = useState(''); const [tag, setTag] = useState(''); const [code, setCode] = useState(() => { try { return new URLSearchParams(window.location.search).get('join') || ''; } catch { return ''; } });
  const loadMine = () => { if (!addr || !sess) { setMine(null); return Promise.resolve(); } return fetch(apiUrl(`/api/reputation/crews/mine?address=${addr}&session=${encodeURIComponent(sess)}`)).then(r => (r.ok ? r.json() : { crew: null })).then(d => { setMine(d.crew || null); setFams(d.families || []); setInv({ invites: d.invites || [], sent: d.sent || [], canAdd: !!d.canAdd }); }).catch(() => setMine(null)); };
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
    if (!sess) { await signIn(); return; }
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
  const joinNode = <>
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
  </>;
  const boardNode = <>
    <div className="crw-board m-card">
      <header><span className="m-label">🏆 WEEKLY FAMILY BOARD</span><small data-tip={board?.rule}>{board ? `${board.total} famil${board.total === 1 ? 'y' : 'ies'} · verified trades, last 7 days` : ''}</small></header>
      <p className="crw-prize" data-testid="crew-prizes">The top 3 families pay every member season points each week: <b>🥇 +{PRIZES[0]}</b> · <b>🥈 +{PRIZES[1]}</b> · <b>🥉 +{PRIZES[2]}</b></p>
      {board && !rows.length && <p className="crw-hint m-dim">No families yet. Start one, fill your seats and trade — the board ranks verified results.</p>}
      <Podium rows={rows.filter(r => r.ranked).slice(0, 3)} />
      <ol>{rows.map((r, i) => <li key={r.id} className={r.ranked ? '' : 'is-off'} style={{ '--i': i }} data-testid={`crew-row-${r.tag}`}>
        <b className={`crw-rank ${r.ranked && i < 3 ? `fcc-rank is-p${i + 1}` : ''}`}>{r.ranked ? i + 1 : '·'}</b>{r.badge ? <FamilyBadge b={r.badge} size="sm" px={32} /> : <span className="crw-tagc">{r.tag}</span>}<span className="crw-rname">{r.name}{r.launch ? <i> 🚀 ${r.launch}</i> : null}</span>
        <small>{r.members}/{r.seats} seats · {r.active} active</small><em className={`m-num ${r.pct == null ? '' : r.pct >= 0 ? 'm-pos' : 'm-neg'}`} key={r.pct}>{pctTxt(r.pct)}</em><small className="crw-note">{rankNote(r)}</small>
        <span className="crw-bar" aria-hidden="true"><i style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, Math.abs(Number(r.pct) || 0) / 50))})` }} className={r.pct >= 0 ? 'up' : 'dn'} /></span></li>)}</ol>
      <small className="m-dim crw-rule">{board?.rule}</small>
    </div>
    <details className="crw-room crw-boardroom" open><summary data-tip="One room for every family on the board — trash talk, call-outs, congrats">💬 The board room <small>every family, one table</small></summary>
      <Suspense fallback={<small className="m-dim">Opening the room…</small>}><div className="crw-chat"><EcosystemChat compact room="familia-board" ecosystem={{ id: 'familia-board', name: 'Familia · The board room' }} /></div></Suspense></details>
  </>;
  // 🏙 the Familia tabs as places IN the city (owner, 2026-10-22: "80 % of these tabs in the cities, easy to find, with a pop-out"): the city's
  // directory opens these rooms over the map — your Family HQ (vitals + tools), the War Room, the Podium, the Wire
  const hqTools = (tool, setTool) => (tool === 'table' ? <FamilyTable mine={mine} owner={owner} addr={addr} sess={sess} onChanged={c => c && setMine(c)} onOpen={setFile} />
    : tool === 'wire' ? <FamilyWire mine={mine} />
      : <div className="crw-mine m-card"><CrewHQ mine={mine} owner={owner} addr={addr} sess={sess} busy={busy} setBusy={setBusy} setMine={setMine} act={act} q={q} rows={rows} inv={inv} reload={loadMine} tab={tool} setTab={setTool} /></div>);
  const rooms = {
    family: ctx => (mine ? <FamilyHQ mine={mine} world={ctx.v} act={ctx.act} busy={ctx.busy} onEnter={ctx.onEnter} onFly={ctx.fly} tools={hqTools} /> : joinNode),
    wars: <><WarStrip />{mine ? <div className="crw-mine m-card"><WarRoom mine={mine} owner={owner} rows={rows} busy={busy} act={warAct} /></div> : <PublicWars />}</>,
    board: boardNode, feed: <FamilyPulse rows={rows} />,
  };
  return <section className="crw crw-noir" data-testid="crews">
    {famTab === 'family' ? <MobScene heat={(mine?.vitals?.heat ?? 30) / 100} sign={mine ? mine.tag : 'FAMIGLIA'} /> : null}   {/* the family's own street sign; every other tab's scene is the page backdrop */}
    <nav className="fam-tabs" role="tablist" aria-label="La Familia">{FAM_TABS.map(([k, label, Icon]) => <button key={k} type="button" role="tab" aria-selected={famTab === k} className={famTab === k ? 'active' : ''}
      onClick={() => setTab(k)} data-testid={`fam-tab-${k}`}><Icon size={14} aria-hidden="true" /><span>{k === 'family' && mine ? mine.tag : label}</span>{k === 'wars' && liveWars ? <b>{liveWars}</b> : null}</button>)}</nav>
    {fams.length > 1 ? <div className="fam-switch m-seg" role="tablist" aria-label="Your families" data-testid="fam-switch">{fams.map(f => <button key={f.id} type="button" role="tab" aria-selected={f.active} className={f.active ? 'active' : ''} disabled={f.active || !!busy}
      onClick={async () => { setBusy('switch'); try { await post('/api/reputation/crews/switch', { address: addr, session: sess, cid: f.id }); await loadMine(); sharedJson.freshAt = Date.now(); toast.success(`[${f.tag}] is your active family`); } catch (e) { toast.error(e.message); } finally { setBusy(''); } }}
      data-tip={f.active ? 'The family every Familia page shows now' : `Switch to [${f.tag}] ${f.name}`} data-testid={`fam-switch-${f.tag}`}>[{f.tag}] {f.name}</button>)}</div> : null}
    <InviteInbox invites={inv?.invites} inFamily={!!mine} addr={addr} sess={sess} onDone={loadMine} />
    {addr && !sess ? <div className="m-note" role="status" data-testid="fam-signin"><b>🔑 You're connected but not signed in</b> — your family, turf and ＋expand show once you sign.
      <button type="button" className="m-btn m-go" onClick={signIn} data-tip="One wallet signature — no transaction, no fee. Proves this wallet is yours." data-testid="fam-signin-go">🔑 Sign in · 1 signature</button></div> : null}
    {famTab === 'home' && (block === undefined ? <><FamilyWorld addr={addr} sess={sess} onSignIn={signIn} onEnter={() => setBlock(null)} onJoin={() => setTab('family')} rooms={rooms} />
    </> : <FamilyBlock cid={block} addr={addr} sess={sess} onBack={() => setBlock(undefined)} mine={mine} tools={hqTools} />)}
    {famTab === 'family' && (mine ? <>
      <FamilyTab mine={mine} addr={addr} sess={sess} onSignIn={signIn} tools={hqTools} onEnter={() => { setTab('home'); setBlock(null); }} onLeave={() => { if (window.confirm(`Leave ${mine.name}?`)) act('/api/reputation/crews/leave', {}, 'Left the family'); }} />
    </> : <>
      <header className="fnr-title"><span>🌹 LA FAMILIA</span><b>Famiglia prima di tutto.</b><small>Families rise on verified trades, settle scores in battle trenches, and wear what they earned.</small></header>
    {joinNode}
    </>)}
    {famTab === 'wars' && <><WarStrip />{mine ? <div className="crw-mine m-card"><WarRoom mine={mine} owner={owner} rows={rows} busy={busy} act={warAct} /></div> : <PublicWars />}</>}
    {famTab === 'board' && <>
    {boardNode}
    </>}
    {famTab === 'feed' && <FamilyPulse rows={rows} />}
    {file && mine ? <MemberFile m={file} mine={mine} onClose={() => setFile(null)} /> : null}
    <FamiliaTradeDock />
  </section>;
}

// 🌹 the family badge beside a name (profile header): the family the wallet is in — nothing if none
