import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { FamilyCity3D } from './FamilyCity3D';
import { CityChat, CityRail, RankBadge, RankLadder } from './FamiliaHud';
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
    {go ? <a className="m-btn m-go" href={go[0]} data-tip="Opens that part of FEELESS">{go[1]}</a> : null}</aside>;
}

function BlockPanel({ x, v, act, busy, onEnter }) {
  if (x?.lm) return <MarkPanel k={x.lm} v={v} />;
  if (!x) return <aside className="fwd-side m-card"><b>Tap a block</b><p className="m-dim">Gold = yours · violet = families · red = CPU towns (hard) · green = cartels (bundlers, snipers, funders from FEELESS rep). You can raid where you hold a block or one bridge away.</p></aside>;
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
    {tone === 'mine' ? <><p>{x.home ? '🏠 Your home block.' : '🗺 Your turf.'}</p><div className="fwd-acts"><button type="button" className="m-btn m-go" onClick={onEnter} data-testid="blk-enter">Enter the block</button>
      {!x.home ? <button type="button" className="m-btn" disabled={busy} onClick={() => act({ act: 'sell', block: x.id }, 'Turf sold')}>Sell turf</button> : null}</div></> : null}
    {['fam', 'cpu', 'cartel'].includes(tone) && me ? <div className="fwd-acts">
      <button type="button" className="m-btn m-go" disabled={busy || me.reach?.[x.b] === false || !me.hitters?.length} onClick={() => act({ act: 'raid', vs: x.owner }, 'Raid started — make your move')}
        data-tip={me.reach?.[x.b] === false ? 'Out of reach — hold a block in this borough or one bridge away' : !me.hitters?.length ? 'Hire a ready hitter on your block first' : 'A raid is a chess game on their block: your move, their move, 2+ rounds'} data-testid="blk-raid">⚔ Raid · {me.hitters?.length || 0} hitters</button></div> : null}
  </aside>;
}

function RaidBoard({ r, act, busy }) {
  const [pick, setPick] = useState(r.side === 'b' ? 'guard' : 'hit');
  const mySide = r.actions?.hit ? 'a' : 'b'; const myTurn = r.status === 'live' && r.turn === mySide;
  const [left, setLeft] = useState(0);
  useEffect(() => { const f = () => setLeft(Math.max(0, Math.round(r.deadline - Date.now() / 1000))); f(); const t = setInterval(f, 1000); return () => clearInterval(t); }, [r.deadline]);
  const cells = Array.from({ length: 25 }, (_, i) => r.board.find(l => l.lot === i));
  const send = (lot) => act({ act: mySide === 'a' ? 'attack' : 'defend', raid: r.id, kind: pick, lot }, 'Move made');
  return <div className={`fwd-raid m-card ${r.status}`} data-testid={`raid-${r.id}`}>
    <header><b>{r.a.tag} ⚔ {r.b.tag}</b><small>{r.status === 'live' ? `round ${r.round}/${r.rounds} · ${myTurn ? `YOUR MOVE · ${left}s` : `their move · ${left}s`}` : `${r.end} · ${mp(r.paid)} MP`}</small>
      <em>loot {mp(r.loot)} / {mp(Math.floor(r.stash * 0.35))}</em></header>
    <div className="fwd-chess">{cells.map((l, i) => <button key={i} type="button" className={`fwd-sq ${(i + Math.floor(i / 5)) % 2 ? 'dk' : 'lt'} ${l ? 'has' : ''} ${l?.down ? 'is-down' : ''}`}
      disabled={!myTurn || busy || !l || pick === 'retreat' || pick === 'counter' || pick === 'lockdown'} onClick={() => send(i)} data-testid={`sq-${i}`}>
      {l ? <><i>{STORE_ICON[l.b] || '🏬'}</i><small>L{l.lvl}</small><b className={l.def == null ? 'q' : ''}>{l.def == null ? '?' : `🛡${l.def + (l.shield || 0)}`}</b></> : null}</button>)}</div>
    {r.status === 'live' ? <div className="fwd-moves">{Object.entries(r.actions || {}).map(([k, w]) => <button key={k} type="button" className={`m-btn ${pick === k ? 'active' : ''}`} onClick={() => { setPick(k); if (['retreat', 'counter', 'lockdown'].includes(k) && myTurn) act({ act: mySide === 'a' ? 'attack' : 'defend', raid: r.id, kind: k, lot: -1 }, 'Move made'); }}
      disabled={!myTurn || busy} data-tip={w} data-testid={`mv-${k}`}>{k}</button>)}</div> : null}
    <ol className="fwd-log">{(r.moves || []).slice().reverse().map((m, i) => <li key={i} className={`s-${m.side}`}>{m.word}</li>)}</ol>
  </div>;
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

export function FamilyWorld({ addr, sess, onEnter }) {
  const [v, setV] = useWorld(addr, sess); const [lens, setLens] = useState('map'); const [sel, setSelRaw] = useState(null); const [busy, setBusy] = useState(false);
  const [city, setCity] = useState('fee'); const [tour, setTour] = useState(false);
  const setSel = x => setSelRaw(s => (x && s && ((x.id && s.id === x.id) || (x.lm && s.lm === x.lm)) ? null : x));   // tap the picked plot again = zoom back out
  const [crew, setCrew] = useState(null);
  useEffect(() => { if (!addr || !sess || lens !== 'deck') return; fetch(apiUrl(`/api/reputation/familia-city?address=${addr}&session=${encodeURIComponent(sess)}`)).then(r => (r.ok ? r.json() : null)).then(x => x && setCrew(x.crew || [])).catch(() => {}); }, [lens, addr, sess]);
  const act = async (body, ok) => {
    if (!sess) { toast.error('Connect your wallet + open chat once to sign in first.'); return; }
    setBusy(true);
    try { const r = await post({ address: addr, session: sess, ...body }); setV(r); toast.success(r.result?.mp ? `${ok} · +${mp(r.result.mp)} MP` : ok); if (body.act === 'raid') setLens('raids'); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  if (!v) return <div className="fwd-load m-card">Reading the city…</div>;
  const me = v.me; const live = (v.raids || []).filter(r => r.status === 'live').length;
  return <section className="fwd" data-testid="family-world">
    <header className="fwd-top">
      <div><span className="m-label">👑 FEE CITY + 4 CITIES · {v.season?.name}</span><b>{(v.blocks || []).filter(b => b.owner).length}/{(v.blocks || []).length} plots held · {(v.cartels || []).length} cartels · {(v.ranked || []).length} ranked families</b>
        {v.boom ? <small>🔥 today's boom: “{v.boom.word}” → {(v.boroughs || []).find(b => b.key === v.boom.borough)?.name} ×{v.boom.mult}</small> : null}</div>
      {me ? <div className="fwd-me">{me.rank ? <RankBadge rank={me.rank} /> : null}<span><em>BANK</em><b key={me.bank}>{mp(me.bank)}</b></span><span><em>TURF</em><b>{me.turf.length}</b></span><span><em>YOUR PTS</em><b>{mp(me.pts)}</b></span>
        {me.fuse ? <span data-tip="The Fuse wallet's confirmed trades this week (fees apart)"><em>⚛ FUSE 7D</em><b className={me.fuse.realizedUsd >= 0 ? 'm-pos' : 'm-neg'}>{me.fuse.trades} · ${me.fuse.realizedUsd}</b></span> : null}
        {me.shield ? <span><em>🛡 TRUCE</em><b>{ago(me.shield)}</b></span> : null}{me.rush ? <span><em>⚡ RUSH</em><b>{ago(me.rush)}</b></span> : null}</div> : <small className="m-dim">Join a family to hold turf.</small>}
    </header>
    <nav className="fwd-lens" role="tablist">{WORLD_LENSES.map(([k, w]) => <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)} data-testid={`wl-${k}`}>{w}{k === 'raids' && live ? <b>{live}</b> : null}</button>)}</nav>
    {lens === 'map' && <>{v.cities ? <CityRail cities={v.cities} city={city} onGo={k => { setSelRaw(null); setCity(k); }} /> : null}
      <div className="fwd-mapwrap"><FamilyCity3D v={v} sel={sel} setSel={setSel} city={city} setCity={setCity}
        tour={{ on: tour, ctl: <button type="button" className={tour ? 'active' : ''} onClick={() => setTour(t => !t)} aria-pressed={tour} data-tip="Show how Familia works, pinned on the city" data-testid="city-tour">❓ How it works</button> }} />
        <div className="fwd-col"><BlockPanel x={sel} v={v} act={act} busy={busy} onEnter={onEnter} />
          {v.cities ? <CityChat city={city} name={(v.cities.find(c => c.key === city) || {}).name || 'the city'} addr={addr} sess={sess} /> : null}</div></div></>}
    {lens === 'ranked' && <RankLadder ranked={v.ranked} mine={me?.id} />}
    {lens === 'raids' && <div className="fwd-raids">{(v.raids || []).length ? v.raids.slice().reverse().map(r => <RaidBoard key={r.id} r={r} act={act} busy={busy} />)
      : <p className="m-dim">No raids. Pick a rival block on the 🗺 City — a CPU town if you're brave.</p>}
      <ol className="fwd-wlog">{(v.log || []).map((l, i) => <li key={i}>{l.what}</li>)}</ol></div>}
    {lens === 'jobs' && (me ? <ul className="fwd-jobs">{me.errands.map(e => <Errand key={e.store} e={e} act={act} busy={busy} />)}</ul> : <p className="m-dim">Join a family to run errands.</p>)}
    {lens === 'rc' && (me ? <ul className="fwd-rc">{me.challenges.map(c => { const cc = cardOf(c.recruit); return <li key={c.key} className={c.done ? 'is-done' : c.ready ? 'is-ready' : ''} data-testid={`rc-${c.key}`}>
      <b>{c.name}</b><small>{c.metric}: {mp(c.have)}/{mp(c.need)}</small><u><s style={{ transform: `scaleX(${Math.min(1, c.have / c.need)})` }} /></u>
      <span className={`fwd-mini ${cc.red ? 'red' : ''}`}>{cc.face}{cc.suit}</span><em>+{mp(c.mp)} MP</em>
      <button type="button" className="m-btn" disabled={!c.ready || busy} onClick={() => act({ act: 'challenge', kind: c.key }, 'Recruit joined')}>{c.done ? '✓ claimed' : 'Claim'}</button></li>; })}</ul> : <p className="m-dim">Join a family to take challenges.</p>)}
    {lens === 'deck' && <CrewDeck crew={crew} />}
    {lens === 'shop' && (me ? <div className="fwd-shop"><ul>{me.rewards.map(r => <li key={r.key}><b>{r.name}</b><small>{r.what}</small>
      <button type="button" className="m-btn" disabled={busy || r.cost > me.bank} onClick={() => act({ act: 'reward', kind: r.key }, r.name)} data-testid={`rw-${r.key}`}>{mp(r.cost)} MP</button></li>)}</ul>
      <div className="fwd-redeem m-card" data-testid="redeem"><b>🐱 Redeem MP → FEECAT</b><p>{mp(v.rate?.mp)} MP = {mp(v.rate?.feecat)} FEECAT. The Don files the claim; the owner pays it by hand. You have {mp(me.bank)} MP ({Math.min(100, Math.round((me.bank / (v.rate?.mp || 1)) * 100))} % of one).</p>
        <u><s style={{ transform: `scaleX(${Math.min(1, me.bank / (v.rate?.mp || 1))})` }} /></u>
        <button type="button" className="m-btn m-go" disabled={busy || me.bank < (v.rate?.mp || Infinity)} onClick={() => { if (window.confirm('File a FEECAT redeem with your MP?')) act({ act: 'redeem' }, 'Redeem filed'); }}>File redeem</button>
        {me.redeems?.length ? <ol>{me.redeems.map(x => <li key={x.id}>{mp(x.mp)} MP → {mp(x.feecat)} FEECAT · {x.status}</li>)}</ol> : null}</div></div> : <p className="m-dim">Join a family to spend MP.</p>)}
    {lens === 'cartels' && <div className="fwd-carts">{(v.cartels || []).map(c => <div key={c.id} className={`fwd-cart r-${c.role}`} data-testid={`cartel-${c.id}`}>
      <header><i>{c.icon}</i><b>{c.name}</b><small>[{c.tag}] · level {c.level}</small></header>
      <span><em>WALLETS</em><b>{mp(c.members)}</b></span><span><em>HITS</em><b>{mp(c.hits)}</b></span><span><em>COINS</em><b>{mp(c.coins)}</b></span><span><em>ACTIVE 7D</em><b>{mp(c.active7d)}</b></span>
      <u><s style={{ transform: `scaleX(${Math.min(1, c.level / 10)})` }} /></u></div>)}
      <p className="m-dim">Cartels are the wallets FEELESS's own rep flagged as {['bundler', 'sniper', 'funder'].join(' · ')}, grouped by the coins they hit together. They grow with their strikes and rank apart from the families. They live in Cartel Docks — raid them for a ×1.5 justice bonus.</p></div>}
  </section>;
}
