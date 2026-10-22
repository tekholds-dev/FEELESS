import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { FeeCity3D, PlacesMenu, useMarkets } from './FeeCity3D';
import { PoolHub, PoolRow, usePools } from './PoolHub';
import { PLACES, usd } from '../lib/cityPlan';
import { openWarRoom } from './WarRoomHost';
import { FamilyHQ } from './FamilyHQ';
import { CityRail, RankBadge, RankLadder } from './FamiliaHud';
import StreetChat from './StreetChat';
import { FamilyFuseBoard } from './FamilyFuseBoard';
import { RaidStage } from './RaidStage';
import { AvenueRoom, AVENUE_LENSES } from './CityAvenue';
import { CityActions, PowerSkyline, SeasonHud, TheWire } from './MobHome';
import { FamiliaOverwatch } from './command/FamiliaOverwatch';
import { Realtor } from './Realtor';
import { useAdmin } from '../lib/adminCall';
import '../styles/familyWorld.css';

// 🗺 THE FAMILIA WORLD (owner, 2026-10-21: "huge like a Sims build — bridges to other parts, seasons, buy blocks near rivals, CPU towns hard to
// raid, CARTELS = the bundlers / snipers / funders from rep, chess moves when you enter a rival city, recruitment challenges, click / drag errands,
// playing cards for hitters and workers, points with real rewards"). Every number is the server's (family_world.py). Points only — the FEECAT
// redeem is a claim the owner pays by hand.
export const STORE_ICON = { pizza: '🍕', gas: '⛽', laundry: '🧺', pharma: '💊', mart: '🏪', lounge: '🍸', docks: '⚓', lab: '🧪', casino: '🎰', bank: '🏦', tower: '🏢', park: '🌳' };
export const WORLD_LENSES = [['map', '🗺 City'], ['ranked', '🎖 Ranked'], ['raids', '⚔ Raids'], ['jobs', '🧰 Errands'], ['rc', '🎖 Challenges'], ['deck', '🃏 Crew deck'], ['shop', '🎁 Rewards'], ['cartels', '🕳 Cartels']];
const SUIT = { hitter: ['♠', 'Hitter'], guard: ['♣', 'Guard'], earner: ['♥', 'Earner'], spy: ['♦', 'Spy'] };
const FACE = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10'];
// pure: a recruit as a playing card — level 1 = Ace … 10 = 10; level 10 hitters are the Kings of the street
export const cardOf = r => ({ suit: (SUIT[r.k] || SUIT.guard)[0], role: (SUIT[r.k] || SUIT.guard)[1], face: r.lvl >= 10 ? 'K' : FACE[Math.max(0, Math.min(9, (r.lvl || 1) - 1))], red: r.k === 'earner' || r.k === 'spy' });
// pure: what a block is to me
export const blockTone = b => (b.mine ? 'mine' : b.kind === 'cpu' ? 'cpu' : b.kind === 'cartel' ? 'cartel' : b.owner ? 'fam' : 'free');
export const mp = n => (n == null ? '—' : Math.round(Number(n)).toLocaleString('en-US'));
export const ago = s => (s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`);
const DRAG = new Set(['pizza', 'laundry', 'pharma', 'lounge', 'docks', 'tower']);
const post = (body) => fetch(apiUrl('/api/reputation/familia-world/act'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || 'Failed'); return j; });

export function useWorld(addr, sess) {
  const [v, setV] = useState(null);
  const load = () => fetch(apiUrl(`/api/reputation/familia-world${addr && sess ? `?address=${addr}&session=${encodeURIComponent(sess)}` : ''}`))
    .then(r => (r.ok ? r.json() : null)).then(x => x && setV(x)).catch(() => {});
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 12000); return () => clearInterval(t); }, [addr, sess]);   // eslint-disable-line react-hooks/exhaustive-deps
  return [v, setV, load];
}

const MARK_GO = { arena: ['/terminal/fuse', '⚔ Build a Fuse card'], launch: ['/terminal/launch', '🚀 Launch a coin'], shield: ['/terminal/reputation', '🛡 Open Rug Shield'] };
function MarkPanel({ k, v }) {
  const m = (v.landmarks || []).find(l => l.key === k); const go = MARK_GO[k];
  return <aside className={`fwd-side m-card t-lm k-${k}`} data-testid="mark-panel"><header><b>{m?.name || k}</b><small>FEE CITY · landmark</small></header><p>{m?.lore}</p>
    {k === 'arena' ? <p className="fwd-rule">Family Fuse rules: cards with the same coin count or one apart (never 4 vs 6) · paper or MP · an MP battle needs {mp(v.rules?.fuseMinMp)} MP in the family bank.</p> : null}
    {k === 'arena' ? <button type="button" className="m-btn m-go" onClick={() => document.getElementById('family-fuse')?.scrollIntoView({ behavior: 'smooth', block: 'start' })} data-tip="The Family Fuse board: live fights, the crowd, your challenge">⚔ Family Fuse board</button> : null}
    {go ? <a className="m-btn" href={go[0]} data-tip="Opens that part of FEELESS">{go[1]}</a> : null}</aside>;
}

// 🏦 a REAL market in Fee City: what it offers, its live numbers, and the action — a DEX pool opens on FEELESS (our engine, your wallet
// signs), everything else opens that market's own app (your wallet signs there; FEELESS never holds funds)
const KIND_WORD = { dex: 'DEX', lend: 'LENDING', perps: 'PERPS', stake: 'LIQUID STAKING', coin: 'TOP COIN' };
function MarketPanel({ k, mk }) {
  const m = (mk?.markets || []).find(x => x.key === k) || (mk?.coins || []).map(c => ({ ...c, kind: 'coin', key: `coin-${c.mint || c.sym}`, name: `$${c.sym || c.symbol || '?'}`, symbol: c.sym || c.symbol })).find(x => x.key === k);
  if (!m) return <aside className="fwd-side m-card t-mk"><b>Market</b><p className="m-dim">Reading the market…</p></aside>;
  const pool = m.pool; const pair = pool?.pair || m.pair || m.pairAddress;
  const meter = Math.max(0.03, Math.min(1, Math.log10(1 + (m.tvl || m.mc || 0)) / 10));
  return <aside className={`fwd-side m-card t-mk k-${m.kind}`} data-testid="market-panel"><header><b>{m.name}</b><small>{KIND_WORD[m.kind] || m.kind} · {ISLAND_OF[m.kind]}</small></header>
    {m.offer ? <p>{m.offer}</p> : null}
    <div className="fwd-mkv"><span><em>{m.kind === 'coin' ? 'MARKET CAP' : 'TVL'}</em><b className="m-num" key={m.tvl || m.mc}>{usd(m.tvl || m.mc)}</b><u><s style={{ transform: `scaleX(${meter})` }} /></u></span>
      {pool ? <><span><em>BUSIEST POOL</em><b>{pool.base}/{pool.quote}{pool.labels?.[0] ? ` · ${pool.labels[0]}` : ''}</b></span><span><em>POOL LIQ</em><b className="m-num">{usd(pool.liq)}</b></span>
        <span><em>24H VOL</em><b className="m-num">{usd(pool.vol)}</b></span><span><em>24H</em><b className={`m-num ${pool.ch >= 0 ? 'm-pos' : 'm-neg'}`}>{pool.ch >= 0 ? '+' : ''}{Number(pool.ch || 0).toFixed(2)}%</b></span></> : null}
      {m.kind === 'coin' && m.ch != null ? <span><em>24H</em><b className={`m-num ${m.ch >= 0 ? 'm-pos' : 'm-neg'}`}>{m.ch >= 0 ? '+' : ''}{Number(m.ch).toFixed(1)}%</b></span> : null}</div>
    <div className="fwd-acts">{pair ? <button type="button" className="m-btn m-go" onClick={() => openWarRoom({ chainId: 'solana', pairAddress: pair, baseToken: { address: m.mint || pool?.baseMint, symbol: pool?.base || m.symbol } })}
      data-tip="Open this pool's war room on FEELESS — chart, tape, swap through our engine; your wallet signs" data-testid="mk-open">📈 Open on FEELESS</button> : null}
      {m.url ? <a className="m-btn" href={m.url} target="_blank" rel="noopener noreferrer" data-tip={`${m.name}'s own app — deposits / borrows happen there and your wallet signs; FEELESS never holds your funds`} data-testid="mk-app">↗ {m.name}</a> : null}</div>
    <small className="m-dim">Live from the chain every minute · the roof light pulses with its volume.</small></aside>;
}
const ISLAND_OF = { dex: 'Market Row', lend: 'Vault District', perps: 'Vault District', stake: 'Vault District', coin: 'New Money' };

function PlaceCard({ k, onOpen }) {
  const p = PLACES.find(x => x.key === k); if (!p) return null;
  return <aside className="fwd-side m-card t-place" style={{ '--pc': p.color }} data-testid="place-card"><header><b>{p.name}</b><small>{p.tool ? 'FEELESS AVENUE · live tool' : 'FEE CITY · place'}</small></header><p>{p.sub}</p>
    <div className="fwd-acts"><button type="button" className="m-btn m-go" onClick={() => onOpen(p.lens)} data-tip={p.tool ? 'Pop out the live tool over the city' : 'Walk in — the room pops out over the city'} data-testid="place-enter">Walk in</button>
      {p.page ? <a className="m-btn" href={p.page} data-tip={`${p.name}'s full page`} data-testid="place-page">Full page ↗</a> : null}</div></aside>;
}

// 🏦 a pool building (an outer city's district): the same row as the Pool Hub, big — trade / stake through FEELESS, deposit on its own page,
// set your building to it
function PoolPanel({ k, pools, blocks, onLink }) {
  const r = (pools?.pools || []).find(x => `pool-${x.id}` === k) || Object.values(pools?.cities || {}).flat().find(x => `pool-${x.id}` === k);
  if (!r) return <aside className="fwd-side m-card t-mk"><b>Pool</b><p className="m-dim">Reading the pool…</p></aside>;
  return <aside className="fwd-side m-card t-mk t-pool" data-testid="pool-panel"><header><b>{r.sym}</b><small>{r.proto} · real pool</small></header>
    <ul className="phb-list"><PoolRow r={r} big blocks={blocks} onLink={onLink} /></ul></aside>;
}

// 💡 a turf block runs on a FUND its upkeep drains by the hour (family_world.UPKEEP_MP): ACTIVE (lit) while funded, SHUT (dark) when dry.
// Any member tops it up from their own points; the Don / Underboss can pay from the family bank.
export const fundPct = h => Math.max(0, Math.min(1, (Number(h) || 0) / (24 * 14)));
export function FundMeter({ x, me, act, busy, upkeep }) {
  const shut = x.state === 'shut'; const day = 24 * upkeep;
  return <div className={`fwd-fund ${shut ? 'is-shut' : ''}`} data-testid="blk-fund">
    <span><em>{shut ? '⏻ SHUT' : '💡 ACTIVE'}</em><b>{shut ? 'dark — fund it to light it' : `${x.fundH ?? 0}h funded`}</b></span>
    <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.02, fundPct(x.fundH))})` }} /></u>
    <div className="fwd-acts"><button type="button" className="m-btn m-go" disabled={busy || (me?.pts ?? 0) < day} onClick={() => act({ act: 'fund', block: x.id, mp: day, source: 'own' }, `${x.id} funded for a day`)}
      data-tip={`+24h from YOUR points (${day} MP; you have ${Math.round(me?.pts || 0)})`} data-testid="blk-fund-own">+24h · {day} MP mine</button>
      {me?.boss ? <button type="button" className="m-btn" disabled={busy || (me?.bank ?? 0) < day * 7} onClick={() => act({ act: 'fund', block: x.id, mp: day * 7, source: 'bank' }, `${x.id} funded for a week`)}
        data-tip={`+7 days from the family bank (${day * 7} MP)`} data-testid="blk-fund-bank">+7d · bank</button> : null}</div>
  </div>;
}

// 🚨 INCOMING (owner, 2026-10-21: "defenders see the incoming raid on THEIR block in the city view"): a raid on your family pins a siren bar over
// the city — who, what's at stake, whose turn, the clock to answer — and one tap opens the raid board and flies to your block.
export function incoming(raids, meId) { return (raids || []).find(r => r.status === 'live' && meId && r.b?.id === meId) || null; }
function RaidAlert({ r, onDefend }) {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, []);
  const left = Math.max(0, Math.round((r.deadline || now) - now));
  return <div className="fwd-alert" role="alert" data-testid="raid-alert"><i className="fwd-siren" aria-hidden="true" />
    <span><b>🚨 [{r.a?.tag}] IS RAIDING YOUR BLOCK</b><small>round {r.round}/{r.rounds} · {r.turn === 'b' ? 'YOUR move' : 'their move'} · stash at risk {mp(r.stash)} MP{r.loot ? ` · ${mp(r.loot)} taken` : ''}</small></span>
    <em data-tip="Time to answer before the round passes">{Math.floor(left / 60)}:{String(left % 60).padStart(2, '0')}</em>
    <button type="button" className="m-btn m-go" onClick={onDefend} data-tip="Open the raid board on your block — guard a lot or strike back" data-testid="raid-defend">🛡 Defend</button></div>;
}

function BlockPanel({ x, v, act, busy, onEnter, mk, onPlace, pools, onLink }) {
  const blocks = v.me ? [v.me.home, ...(v.me.turf || [])].filter(Boolean) : [];
  if (x?.mk && String(x.mk).startsWith('pool-')) return <PoolPanel k={x.mk} pools={pools} blocks={blocks} onLink={onLink} />;
  if (x?.mk) return <MarketPanel k={x.mk} mk={mk} />;
  if (x?.place) return <PlaceCard k={x.place} onOpen={onPlace} />;
  if (x?.lm) return <MarkPanel k={x.lm} v={v} />;
  if (!x) return <aside className="fwd-side m-card"><b>Tap a building</b><p className="m-dim">Gold = yours · violet = families · red = CPU towns (hard) · green = cartels. Across the bridges: MARKET ROW (the DEXes), VAULT DISTRICT (lend · perps · stake) and NEW MONEY (today's top coins) — real markets, live. 📍 Places = the Ladder, the Precinct, the Gym, the Card Room…</p></aside>;
  const me = v.me; const tone = blockTone(x); const price = me?.prices?.[x.id];
  const cpu = (v.cpu || []).find(c => c.id === x.owner); const cart = (v.cartels || []).find(c => c.id === x.owner);
  return <aside className={`fwd-side m-card t-${tone}`} data-testid="block-panel">
    <header><b>{x.owner ? `${x.icon || ''} [${x.tag}] ${x.name}` : `Block ${x.id}`}</b><small>{(v.boroughs || []).find(b => b.key === x.b)?.name}</small></header>
    {cpu ? <p>🤖 CPU town · level {cpu.level} · {cpu.guards} guards · stash {mp(cpu.stash)} MP — they never sleep and answer every move at once.</p> : null}
    {cart ? <p>{cart.icon} cartel of {mp(cart.members)} {cart.role} wallets · {mp(cart.hits)} flagged hits on {mp(cart.coins)} coins · {cart.active7d} active this week. Raids on a cartel pay ×1.5 (justice).</p> : null}
    {tone === 'free' && !me ? <p>{x.b === 'fee' ? 'A premium Fee City plot: production ×2.5, contested from every bridge.' : 'Free turf.'} Join a family and sign in to buy it with MP.</p> : null}
    {tone === 'free' && me ? <><p>Free turf: +4 % production and +1 recruit seat. Turf is reach — raid in this borough and one bridge out.</p>
      <div className="fwd-acts"><button type="button" className="m-btn m-go" disabled={busy || price > me.bank} onClick={() => act({ act: 'buy', block: x.id }, 'Block bought')} data-testid="blk-buy">Buy · {mp(price)} MP</button>
        <button type="button" className="m-btn" disabled={busy} onClick={() => act({ act: 'move', block: x.id }, 'Family moved')} data-tip="Move your home block here (the gas station cuts the fee)" data-testid="blk-move">Move home · {mp(me.moveMp?.[x.b])} MP</button></div></> : null}
    {tone === 'mine' && !x.home ? <FundMeter x={x} me={me} act={act} busy={busy} upkeep={v.rules?.upkeepMp || 10} /> : null}
    {x.launch?.symbol ? <p className="fwd-launch" data-tip="This family's pinned launch — the spire on its home block">🚀 Launch tower · <b>${x.launch.symbol}</b> <a href={`/terminal/coin/solana/${x.launch.mint}`}>chart ↗</a></p> : null}
    {tone === 'mine' ? <><p>{x.home ? '🏠 Your home block.' : '🗺 Your turf.'}</p><div className="fwd-acts"><button type="button" className="m-btn m-go" onClick={onEnter} data-testid="blk-enter">Enter the block</button>
      {!x.home ? <button type="button" className="m-btn" disabled={busy} onClick={() => act({ act: 'sell', block: x.id }, 'Turf sold')}>Sell turf</button> : null}</div></> : null}
    {['fam', 'cpu', 'cartel'].includes(tone) && me ? <div className="fwd-acts">
      <button type="button" className="m-btn m-go" disabled={busy || me.reach?.[x.b] === false || !me.hitters?.length} onClick={() => act({ act: 'raid', vs: x.owner }, 'Raid started — make your move')}
        data-tip={me.reach?.[x.b] === false ? 'Out of reach — hold a block in this borough or one bridge away' : !me.hitters?.length ? 'Hire a ready hitter on your block first' : 'A raid is a chess game on their block: your move, their move, 2+ rounds'} data-testid="blk-raid">⚔ Raid · {me.hitters?.length || 0} hitters</button></div> : null}
  </aside>;
}

function Errand({ e, act, busy }) {
  const [game, setGame] = useState(null); const zone = useRef(null);
  const drag = DRAG.has(e.store);
  const finish = () => { setGame(null); act({ act: 'errand', kind: e.store }, `${e.name} done`); };
  const onDown = ev => { if (!drag) return; ev.currentTarget.setPointerCapture(ev.pointerId); setGame(g => ({ ...g, x: ev.clientX, y: ev.clientY, sx: ev.clientX, sy: ev.clientY })); };
  const onMove = ev => { if (game?.sx != null) setGame(g => ({ ...g, x: ev.clientX, y: ev.clientY })); };
  const onUp = ev => { const z = zone.current?.getBoundingClientRect(); if (z && ev.clientX > z.left && ev.clientX < z.right && ev.clientY > z.top && ev.clientY < z.bottom) finish(); else setGame(g => ({ ...g, sx: null })); };
  const ready = !e.ready && e.lvl > 0;
  return <li className={`fwd-job ${ready ? 'is-ready' : ''}`} data-testid={`job-${e.store}`}>
    <header><i>{STORE_ICON[e.store]}</i><b>{e.name}</b><small>{e.lvl ? (e.ready ? `again in ${ago(e.ready)}` : 'ready') : 'build it first'}</small></header>
    {!game ? <button type="button" className="m-btn" disabled={!ready || busy} onClick={() => setGame({ taps: 0 })} data-tip={e.how} data-testid={`job-go-${e.store}`}>{drag ? '✋ Drag job' : '👆 Tap job'}</button>
      : drag ? <div className="fwd-play">
        <span className="fwd-token" onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} style={game.sx != null ? { transform: `translate(${game.x - game.sx}px, ${game.y - game.sy}px)` } : null} data-testid={`job-token-${e.store}`}>{STORE_ICON[e.store]}</span>
        <span className="fwd-drop" ref={zone}>📍 drop</span><small>{e.how}</small></div>
      : <div className="fwd-play"><button type="button" className="fwd-tapper" style={{ '--n': game.taps }} onClick={() => { const n = game.taps + 1; if (n >= 6) finish(); else setGame({ taps: n }); }} data-testid={`job-tap-${e.store}`}>{STORE_ICON[e.store]} {6 - game.taps}</button><small>{e.how}</small></div>}
  </li>;
}

export function CrewDeck({ crew }) {
  if (!crew?.length) return <p className="m-dim">No recruits yet — hire them on your block or win them in 🎖 Challenges.</p>;
  return <div className="fwd-deck" data-testid="crew-deck">{crew.map((r, i) => { const c = cardOf(r); return <div key={r.id} className={`fwd-card ${c.red ? 'red' : ''} ${r.hurt ? 'is-hurt' : ''} ${r.special ? 'is-special' : ''}`} style={{ '--i': i }}
    data-tip={`${c.role} · level ${r.lvl}${r.next ? ` · ${r.xp}/${r.next} XP` : ''}${r.hurt ? ` · hurt, back in ${Math.ceil(r.hurt / 60)} min` : ''}`}>
    <span className="tl">{c.face}<i>{c.suit}</i></span><b>{c.suit}</b><small>{c.role}</small><span className="br">{c.face}<i>{c.suit}</i></span></div>; })}</div>;
}

// 🏠 the My family TAB = the same Family HQ as the city's pop-out (owner, 2026-10-22: "the page of my family should be meta with vitals and tools —
// strip the text"): its own world read (bank, turf, expansions) + the family's tools
export function FamilyTab({ mine, addr, sess, tools, onEnter, onLeave, onSignIn }) {
  const [v, setV] = useWorld(addr, sess); const [busy, setBusy] = useState(false);
  const act = async (body, ok) => {
    if (!sess) { if (onSignIn) await onSignIn(); else toast.error('Sign in first — one wallet signature, no transaction.'); return; }
    setBusy(true);
    try { const r = await post({ address: addr, session: sess, ...body }); setV(r); toast.success(ok); } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return <section className="fwd-tab m-card" data-testid="family-tab"><FamilyHQ mine={mine} world={v} act={act} busy={busy} onEnter={onEnter} tools={tools} />
    {onLeave ? <button type="button" className="m-btn fhq-leave" disabled={busy} onClick={onLeave} data-testid="crew-leave">Leave the family</button> : null}</section>;
}

// 🚪 inside a place: its room pops out OVER the city (the street stays live behind it) — Esc or ✕ walks back out
const EXTRA_PLACES = { overwatch: { key: 'overwatch', name: '👑 OVERWATCH', sub: 'creator only · every family', color: '#ff8fa3' },
  realtor: { key: 'realtor', name: '🏷 THE REALTOR', sub: 'every plot for sale · by tier', color: '#45e4c8' } };
function PlacePanel({ lens, live, onClose, children }) {
  const p = PLACES.find(x => x.lens === lens) || EXTRA_PLACES[lens];
  useEffect(() => { const esc = e => { if (e.key === 'Escape') onClose(); }; window.addEventListener('keydown', esc); return () => window.removeEventListener('keydown', esc); }, [onClose]);
  return <section className={`fwd-place k-${p?.key || lens}${p?.tool ? ' is-tool' : ''}`} style={{ '--pc': p?.color || '#d4af37' }} role="dialog" aria-label={p?.name || lens} data-testid={`place-panel-${lens}`}>
    <header><i aria-hidden="true" /><span><b>{p?.name || lens}</b><small>{p?.sub}{lens === 'raids' && live ? ` · ${live} live` : ''}</small></span>
      <button type="button" onClick={onClose} aria-label="Walk back out" data-tip="Back to the street (Esc)" data-testid="place-close">✕</button></header>
    <div className="fwd-placebody">{children}</div></section>;
}

export function FamilyWorld({ addr, sess, onEnter, onJoin, onSignIn, rooms = {} }) {
  const [v, setV] = useWorld(addr, sess); const [lens, setLensRaw] = useState(null); const mk = useMarkets(); const pools = usePools(); const [sel, setSelRaw] = useState(null); const [busy, setBusy] = useState(false);   // lens = the place you walked into (null = the street)
  const [city, setCity] = useState('fee'); const [tour, setTour] = useState(false);
  const setSel = x => setSelRaw(s => (x && s && ((x.id && s.id === x.id) || (x.lm && s.lm === x.lm) || (x.mk && s.mk === x.mk) || (x.place && s.place === x.place)) ? null : x));   // tap the picked plot again = zoom back out
  const [crew, setCrew] = useState(null); const { call: adminCall } = useAdmin();
  const setLens = k => { if (!k || k === 'map') { setLensRaw(null); return; } const p = PLACES.find(x => x.lens === k); setLensRaw(k); setCity('fee'); if (p) setSelRaw({ place: p.key }); };
  useEffect(() => { if (!addr || !sess || lens !== 'deck') return; fetch(apiUrl(`/api/reputation/familia-city?address=${addr}&session=${encodeURIComponent(sess)}`)).then(r => (r.ok ? r.json() : null)).then(x => x && setCrew(x.crew || [])).catch(() => {}); }, [lens, addr, sess]);
  const act = async (body, ok) => {
    if (!sess) { if (onSignIn) await onSignIn(); else toast.error('Sign in first — one wallet signature, no transaction.'); return; }
    setBusy(true);
    try { const r = await post({ address: addr, session: sess, ...body }); setV(r); toast.success(r.result?.mp ? `${ok} · +${mp(r.result.mp)} MP` : ok); if (body.act === 'raid') setLensRaw('raids'); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  if (!v) return <div className="fwd-load m-card">Reading the city…</div>;
  // one router for every "go there" on the landing (HUD, loop, action buttons, skyline)
  const go = to => {
    if (to === 'join') { onJoin?.(); return; }
    if (to === 'block') { if (v.me) onEnter(); else onJoin?.(); return; }
    if (to === 'fuse') { setLens(null); setCity('fee'); setTimeout(() => document.getElementById('family-fuse')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60); return; }
    setLens(to); document.querySelector('[data-testid="world-map"]')?.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
  };
  const flyTo = r => { const home = (v.blocks || []).find(b => b.owner === r.id && b.home) || (v.blocks || []).find(b => b.owner === r.id);
    if (!home) return; const c = (v.cities || []).find(x => x.boroughs.includes(home.b)); setLensRaw(null); if (c) setCity(c.key); setSelRaw(home); };
  const me = v.me; const live = (v.raids || []).filter(r => r.status === 'live').length;
  const myBlocks = me ? [me.home, ...(me.turf || [])].filter(Boolean) : [];
  const howBtn = <button type="button" className={tour ? 'active' : ''} onClick={() => setTour(t => !t)} aria-pressed={tour} data-tip="Show how Familia works, pinned on the city" data-testid="city-tour">❓ How it works</button>;
  const link = (block, r) => act({ act: 'link', block, pool: r.id }, `${block} now wears ${r.sym}`);   // 🏠 set your building to a real pool (display only)
  const place = {
    overwatch: v.staff ? <FamiliaOverwatch call={adminCall} /> : null,   // 👑 creator only (the server re-checks the owner signature)
    realtor: <Realtor v={v} act={act} busy={busy} onFly={id => { const b = (v.blocks || []).find(x => x.id === id); if (!b) return; const c = (v.cities || []).find(x => x.boroughs.includes(b.b)); setLensRaw(null); if (c) setCity(c.key); setSelRaw(b); }} />,
    ranked: <RankLadder ranked={v.ranked} mine={me?.id} />,
    raids: <div className="fwd-raids">{(v.raids || []).length ? v.raids.slice().reverse().map(r => <RaidStage key={r.id} r={r} act={act} busy={busy} />)
      : <p className="m-dim">No raids. Tap a rival building in the city — a CPU town if you're brave.</p>}
      <ol className="fwd-wlog">{(v.log || []).map((l, i) => <li key={i}>{l.what}</li>)}</ol></div>,
    jobs: me ? <ul className="fwd-jobs">{me.errands.map(e => <Errand key={e.store} e={e} act={act} busy={busy} />)}</ul> : <p className="m-dim">Join a family to run errands.</p>,
    rc: me ? <ul className="fwd-rc">{me.challenges.map(c => { const cc = cardOf(c.recruit); return <li key={c.key} className={c.done ? 'is-done' : c.ready ? 'is-ready' : ''} data-testid={`rc-${c.key}`}>
      <b>{c.name}</b><small>{c.metric}: {mp(c.have)}/{mp(c.need)}</small><u><s style={{ transform: `scaleX(${Math.min(1, c.have / c.need)})` }} /></u>
      <span className={`fwd-mini ${cc.red ? 'red' : ''}`}>{cc.face}{cc.suit}</span><em>+{mp(c.mp)} MP</em>
      <button type="button" className="m-btn" disabled={!c.ready || busy} onClick={() => act({ act: 'challenge', kind: c.key }, 'Recruit joined')}>{c.done ? '✓ claimed' : 'Claim'}</button></li>; })}</ul> : <p className="m-dim">Join a family to take challenges.</p>,
    deck: <CrewDeck crew={crew} />,
    pools: <PoolHub pools={pools} blocks={myBlocks} onLink={link} />,
    family: typeof rooms.family === 'function' ? rooms.family({ v, act, busy, onEnter, fly: id => { const b = (v.blocks || []).find(x => x.id === id); if (!b) return; const c = (v.cities || []).find(x => x.boroughs.includes(b.b)); setLensRaw(null); if (c) setCity(c.key); setSelRaw(b); } }) : rooms.family || null,
    wars: rooms.wars || null, board: rooms.board || null, feed: rooms.feed || null,
    ...Object.fromEntries(AVENUE_LENSES.map(k => [k, <AvenueRoom lens={k} />])),
    shop: me ? <div className="fwd-shop"><ul>{me.rewards.map(r => <li key={r.key}><b>{r.name}</b><small>{r.what}</small>
      <button type="button" className="m-btn" disabled={busy || r.cost > me.bank} onClick={() => act({ act: 'reward', kind: r.key }, r.name)} data-testid={`rw-${r.key}`}>{mp(r.cost)} MP</button></li>)}</ul>
      <div className="fwd-redeem m-card" data-testid="redeem"><b>🐱 Redeem MP → FEECAT</b><p>{mp(v.rate?.mp)} MP = {mp(v.rate?.feecat)} FEECAT. The Don files the claim; the owner pays it by hand. You have {mp(me.bank)} MP ({Math.min(100, Math.round((me.bank / (v.rate?.mp || 1)) * 100))} % of one).</p>
        <u><s style={{ transform: `scaleX(${Math.min(1, me.bank / (v.rate?.mp || 1))})` }} /></u>
        <button type="button" className="m-btn m-go" disabled={busy || me.bank < (v.rate?.mp || Infinity)} onClick={() => { if (window.confirm('File a FEECAT redeem with your MP?')) act({ act: 'redeem' }, 'Redeem filed'); }}>File redeem</button>
        {me.redeems?.length ? <ol>{me.redeems.map(x => <li key={x.id}>{mp(x.mp)} MP → {mp(x.feecat)} FEECAT · {x.status}</li>)}</ol> : null}</div></div> : <p className="m-dim">Join a family to spend MP.</p>,
    cartels: <div className="fwd-carts">{(v.cartels || []).map(c => <div key={c.id} className={`fwd-cart r-${c.role}`} data-testid={`cartel-${c.id}`}>
      <header><i>{c.icon}</i><b>{c.name}</b><small>[{c.tag}] · level {c.level}</small></header>
      <span><em>WALLETS</em><b>{mp(c.members)}</b></span><span><em>HITS</em><b>{mp(c.hits)}</b></span><span><em>COINS</em><b>{mp(c.coins)}</b></span><span><em>ACTIVE 7D</em><b>{mp(c.active7d)}</b></span>
      <u><s style={{ transform: `scaleX(${Math.min(1, c.level / 10)})` }} /></u></div>)}
      <p className="m-dim">Cartels are the wallets FEELESS's own rep flagged as bundler · sniper · funder, grouped by the coins they hit together. They live in Cartel Docks — raid them for a ×1.5 justice bonus.</p></div>,
  }[lens] || null;
  return <section className="fwd" data-testid="family-world">
    <SeasonHud v={v} onJoin={onJoin} go={to => go(to)} />
    {v.cities ? <CityRail cities={v.cities} city={city} onGo={k => { setSelRaw(null); setLensRaw(null); setCity(k); }} /> : null}
    <div className="fwd-mapwrap"><FeeCity3D v={v} sel={sel} setSel={setSel} city={city} setCity={setCity} markets={mk} pools={pools} onPlace={k => setLensRaw(k)} onGoPlace={p => setLens(p.lens)} active={lens}
        overlay={<>{incoming(v.raids, me?.id) ? <RaidAlert r={incoming(v.raids, me?.id)} onDefend={() => { setLens('raids'); const h = (v.blocks || []).find(b => b.id === me?.home); if (h) setSelRaw(h); }} /> : null}<TheWire log={v.log} /><CityActions v={v} go={go} />{lens ? <PlacePanel lens={lens} live={live} onClose={() => setLensRaw(null)}>{place}</PlacePanel> : null}</>}
        tour={{ on: tour, ctl: <><PlacesMenu onGo={p => setLens(p.lens)} />{howBtn}</>, ctl3: howBtn }} />
      <div className="fwd-col"><BlockPanel x={sel} v={v} act={act} busy={busy} onEnter={onEnter} mk={mk} onPlace={k => setLensRaw(k)} pools={pools} onLink={link} />
        {v.cities ? <StreetChat city={city} name={(v.cities.find(c => c.key === city) || {}).name || 'the city'} addr={addr} sess={sess} /> : null}</div></div>
    {city === 'fee' && v.ffuse ? <FamilyFuseBoard v={v} setV={setV} addr={addr} sess={sess} /> : null}
    <PowerSkyline v={v} onPick={flyTo} onEmpty={() => go(v.me ? 'map' : 'join')} />
  </section>;
}
