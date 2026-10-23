import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Coins, Shield, Crosshair, Briefcase, Eye, ArrowLeft } from 'lucide-react';
import { apiUrl } from '../lib/api';
import { FamilyDeck, deckBody } from './FamilyDeck';
import { FamilyBlock3D, BlockCard, TownPicker } from './FamilyBlock3D';
import { TOWN } from '../lib/cityPlan';
import '../styles/familyBlock.css';
import { familiaDocked, familiaSwap } from './FamiliaTrade';
import { useLpPositions } from '../lib/lpPositions';
import { LpPositionCard } from './LpPositions';
import { dollarsSmall } from '../lib/cityPlan';

// 🏙 THE FAMILY BLOCK (owner, 2026-10-21: "enter your block and build a city — named crypto stores, MP, goons to protect / rob / boost, realistic
// 3D like a game, clickable with vitals, everything explained; the creator wallet gets every unlock"). Drag to spin it 360°. Every number is
// the server's (family_city.py): MP are points only — never bought, sent or cashed out.
export const LOOK = {   // per store: facade, roof, height (px at level 1), shape
  pizza: ['#c8352d', '#f4e3c3', 26, 'shop'], gas: ['#e8e8e8', '#d4202a', 18, 'canopy'], laundry: ['#3a7bd5', '#dfe9f7', 28, 'shop'],
  pharma: ['#e9f6ee', '#1f9d55', 30, 'shop'], mart: ['#13a89e', '#dff7f4', 32, 'shop'], lounge: ['#4b2a7a', '#c08cff', 40, 'club'],
  docks: ['#7a5a3a', '#4a3a2a', 34, 'wide'], lab: ['#d9e7f2', '#7fb8e6', 48, 'glass'], casino: ['#c9a227', '#b3122e', 58, 'club'],
  bank: ['#cfc8b8', '#8a8170', 52, 'classic'], tower: ['#5fa8d3', '#1b3b52', 96, 'glass'], park: ['#2f7d32', '#2f7d32', 0, 'park'],
};
export const heightOf = (b, lvl) => (b === 'park' ? 0 : Math.round(LOOK[b][2] * (0.7 + 0.22 * (lvl || 1))));
const BUILD_SEC = 45;
export function liveStash(v, nowS) {
  if (!v) return 0;
  const add = (v.rate || 0) * Math.max(0, nowS - (v._at ?? nowS)) / 3600;
  return Math.min(v.stashCap || Infinity, Math.floor((v.stash || 0) + add));
}

export function Building({ l, nowS }) {
  const [c1, c2, , shape] = LOOK[l.b] || LOOK.pizza;
  const h = heightOf(l.b, l.lvl);
  const building = nowS - (l.at || 0) < BUILD_SEC;
  if (shape === 'park') return <div className="fbk-park"><i className="fbk-tree t1" /><i className="fbk-tree t2" /><i className="fbk-tree t3" /><i className="fbk-bench" /></div>;
  return <div className={`fbk-b s-${shape} ${building ? 'is-building' : ''}`} style={{ '--h': `${h}px`, '--c1': c1, '--c2': c2 }}>
    <i className="fbk-f fbk-top" /><i className="fbk-f fbk-n" /><i className="fbk-f fbk-e" /><i className="fbk-f fbk-s" /><i className="fbk-f fbk-w" />
    {building ? <><i className="fbk-scaf" /><i className="fbk-crane"><b /></i></> : null}
  </div>;
}

// 🗼 THE DESK'S PICKS hovering over the block (owner: "coin buildings need a coin hovering over them"): the top 3 of the agents' intake list as
// floating coins — tap one to open its war room (chart + Quick trade, the wallet signs). One shared 30 s read (the same as the Trench Towers).
function useIntakeCoins() {   // one 30 s read of the desk's intake for the picks AND the town's TT tower floors
  const [coins, setCoins] = useState(null);
  useEffect(() => { let on = true; const load = () => fetch(apiUrl('/api/reputation/familia/intake')).then(r => (r.ok ? r.json() : null)).then(x => on && x && setCoins(x.coins || [])).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 30000); return () => { on = false; clearInterval(t); }; }, []);
  return coins;
}
function BlockPicks({ coins }) {
  const rows = (coins || []).filter(c => c.pair).slice(0, 3);
  if (!rows.length) return null;
  return <div className="fbk-picks" data-testid="block-picks">{rows.map((c, i) => <button key={c.mint} type="button" className={`fbk-pick ${(c.ch ?? 0) < 0 ? 'dn' : 'up'}`} style={{ '--i': i }}
    onClick={e => { e.stopPropagation(); window.dispatchEvent(new CustomEvent('feeless:war-room', { detail: { chainId: 'solana', pairAddress: c.pair, baseToken: { address: c.mint, symbol: c.sym } } })); }}
    onPointerDown={e => e.stopPropagation()} data-tip={`$${c.sym} · the desk's pick (${c.status || 'intake'}) · 5m ${c.ch == null ? '—' : `${c.ch >= 0 ? '+' : ''}${Number(c.ch).toFixed(1)}%`} — tap to trade it`} data-testid={`block-pick-${i}`}>
    <b>${String(c.sym || '?').slice(0, 7)}</b><small>{c.ch == null ? '—' : `${c.ch >= 0 ? '+' : ''}${Number(c.ch).toFixed(1)}%`}</small></button>)}<em>DESK PICKS</em></div>;
}

// 🏙 THE FAMILY BLOCK (owner, 2026-10-22: "my family block supposed to look like the new city design and expanding — me adding buildings for
// markets i wanna use, under construction until i actually buy … not these fake buildings and fake corny drag and drop errands, real errands"):
// the block is the family's REAL market buildings in the same 3D engine as Fee City (FamilyBlock3D · backend/block_markets.py) — built only by a
// real position, errands from that position. The MP points game (stash, recruits, robberies) folds into one panel underneath.
export function errandGo(e, b, nav = path => window.location.assign(path)) {   // every errand runs IN FEELESS (owner: "no redirects")
  if (e.kind === 'switch' && e.swap) {   // ⚖ a better-paying LST: the swap opens with both coins set (you still press Get quote) — INSIDE Familia's dock
    if (familiaDocked()) { familiaSwap(e.swap); return 'swap'; }
    try { sessionStorage.setItem('feeless.swap.pair', JSON.stringify({ input: e.swap.from, output: e.swap.to })); } catch { /* storage blocked */ }
    nav('/terminal/trade'); return 'swap';
  }
  if (e.kind === 'hedge') { window.dispatchEvent(new CustomEvent('feeless:deck', { detail: 'perps' })); return 'deck'; }
  return e.kind === 'range' ? 'range' : 'desk';   // 🎯 the drawn range / 💸 the money desk open in the building's own pop-out
}

// 🎲 the MP street game under the block — the ONLY part that ticks every second (its live stash). It used to tick the whole block page
// (3D wrapper, deck, cards) once a second — one of the "my family town lags" causes (2026-10-23).
function StreetGame({ v, act, busy, can }) {
  const [nowS, setNowS] = useState(() => Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNowS(Date.now() / 1000); }, 1000); return () => clearInterval(t); }, []);
  const stash = liveStash(v, nowS);
  return <details className="fbk-card fbk-mp" data-testid="block-mp"><summary data-tip="The MP points game: the stash your old stores make, recruits, robberies — points only, never money">🎲 Street game · {stash.toLocaleString('en-US')} MP in the stash</summary>
            <button type="button" className="m-btn m-go fbk-collect" disabled={busy || stash < 1} onClick={() => act({ act: 'collect' })} data-testid="block-collect"><Coins size={15} /> Collect {stash.toLocaleString('en-US')} MP</button>
            <p className="fbk-streak" data-tip="Collect every day: +5 % production a day, up to +50 %. Members' verified FEELESS trades this week boost production up to ×3.">🔥 streak {v.streak || 0}d · +{v.streakBonus || 0} % · trading boost ×{v.boost}{v.houseTax != null ? ` · house ${v.houseTax} %` : ''}</p>
            {v.casino ? <button type="button" className="m-btn fbk-dice" disabled={busy || v.bank < 200} onClick={() => act({ act: 'dice', lot: Math.max(10, Math.floor(v.bank * 0.05)) })} data-tip="Once an hour: stake 5 % of the bank, a win pays 1.9× — earned MP only, points only" data-testid="block-dice">🎰 Roll {Math.max(10, Math.floor(v.bank * 0.05)).toLocaleString('en-US')} MP</button> : null}
            <h5>RECRUITS · {(v.crew || []).length}/{v.goonCap}</h5>
            {(v.crew || []).length ? <ul className="fbk-crew">{v.crew.map(r => <li key={r.id} className={r.hurt ? 'is-hurt' : ''} data-tip={r.hurt ? `hurt — back in ${Math.ceil(r.hurt / 60)} min` : r.next ? `level ${r.lvl} · ${r.xp}/${r.next} XP — trains every hour` : 'top level'}>
              <i>{r.icon}</i><b>L{r.lvl}</b><u><s style={{ transform: `scaleX(${r.next ? Math.min(1, r.xp / r.next) : 1})` }} /></u></li>)}</ul> : null}
            <div className="fbk-goons">{(v.goonTypes || []).map(g => { const Ic = g.key === 'guard' ? Shield : g.key === 'hitter' ? Crosshair : g.key === 'spy' ? Eye : Briefcase;
              return <button key={g.key} type="button" disabled={!can || busy || g.cost > v.bank || g.ok === false} onClick={() => act({ act: 'hire', kind: g.key }, `${g.icon} ${g.name} hired`)} data-tip={g.what} data-testid={`hire-${g.key}`}>
                <Ic size={15} /><b>{v.goons[g.key] || 0}</b><small>{g.name}</small><em>{g.cost ? `${g.cost} MP` : 'free'}</em></button>; })}</div>
            {(v.rivals || []).length ? <><h5>🔫 ROB A STASH</h5><ul className="fbk-rivals">{v.rivals.map(r => <li key={r.id}><span><b>[{r.tag}]</b> {r.name}<small>stash {r.stash.toLocaleString('en-US')} · 🛡 {r.guards}</small></span>
              <button type="button" disabled={!can || busy || !(v.goons.hitter > 0) || r.cool > 0} onClick={() => act({ act: 'rob', vs: r.id })} data-tip={`Your hitters vs their guards: ${Math.round(r.odds * 100)} % — a win takes 25 % of their stash; a loss costs a hitter`} data-testid={`rob-${r.tag}`}>
                {r.cool > 0 ? `${Math.ceil(r.cool / 60)}m` : `${Math.round(r.odds * 100)} %`}</button></li>)}</ul></> : null}
            {(v.log || []).length ? <><h5>📜 THE STREET</h5><ol className="fbk-log">{v.log.slice(0, 8).map(([t, w]) => <li key={`${t}-${w}`}>{w}</li>)}</ol></> : null}
          </details>;
}

export function FamilyBlock({ cid, addr, sess, onBack, mine: myFam = null, tools = null, demo = null, lpOwner = null }) {   // lpOwner: the /dev/block preview only
  const mine = !cid;
  const [v, setV] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const [bl, setBl] = useState(null); const [bsel, setBsel] = useState(null); const coins = useIntakeCoins();
  const lp = useLpPositions(lpOwner || (mine ? addr : null));   // 🏗 your LP positions stand on your block as live towers
  const lpSel = bsel?.lp ? (lp || []).find(p => p.id === bsel.lp) : null;
  const room = bsel?.town && TOWN[bsel.town] ? bsel.town : null;   // 🏘 a town building you walked into: its real tool pops out over the block
  useEffect(() => { if (!bsel) return undefined; const esc = e => { if (e.key === 'Escape') setBsel(null); }; window.addEventListener('keydown', esc); return () => window.removeEventListener('keydown', esc); }, [bsel]);
  const load = () => fetch(apiUrl(mine ? `/api/reputation/familia-city?address=${addr}&session=${encodeURIComponent(sess)}` : `/api/reputation/familia-city/${cid}`))
    .then(async r => { const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'The block could not be read.'); setV({ ...b, _at: Date.now() / 1000 }); setErr(''); })
    .catch(e => setErr(e.message));
  const loadBl = () => fetch(apiUrl(mine ? `/api/reputation/familia-block?address=${addr}&session=${encodeURIComponent(sess)}` : `/api/reputation/familia-block/${cid}`))
    .then(r => (r.ok ? r.json() : null)).then(b => { if (b) setBl(demo && !b.town ? { ...b, ...demo } : b); }).catch(() => {});   // demo = the dev harness only
  useEffect(() => { load(); loadBl(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000); const u = setInterval(() => { if (!document.hidden) loadBl(); }, 60000);
    return () => { clearInterval(t); clearInterval(u); }; }, [cid, addr, sess]);   // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (body, ok) => {
    setBusy(true);
    try {
      const r = await fetch(apiUrl('/api/reputation/familia-city/act'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: addr, session: sess, ...body }) });
      const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'Refused.');
      setV({ ...b, _at: Date.now() / 1000 });
      if (b.result?.stake) toast[b.result.win ? 'success' : 'error'](b.result.win ? `🎰 won ${Math.round(b.result.stake * 0.9).toLocaleString('en-US')} MP` : `🎰 lost ${b.result.stake.toLocaleString('en-US')} MP`);
      if (b.result?.collected) toast.success(`💰 ${b.result.collected.toLocaleString('en-US')} MP collected`);
      else if (b.result && 'win' in b.result) toast[b.result.win ? 'success' : 'error'](b.result.win ? `🔫 took ${b.result.take.toLocaleString('en-US')} MP` : '☠ the hit failed — one hitter lost');
      else if (ok) toast.success(ok);
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };
  const blAct = async (what, key) => {
    setBusy(true);
    try {
      const r = await fetch(apiUrl('/api/reputation/familia-block/act'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: addr, session: sess, act: what, key }) });
      const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'Refused.');
      setBl(b); setBsel(what === 'add' ? { blk: key } : what === 'tadd' ? { town: key } : null);
      toast.success({ add: '🏗 on the block — it builds itself when you open a real position there', tadd: `🏘 ${TOWN[key]?.name || key} stands in your town — walk in`, tdel: `${TOWN[key]?.name || key} taken down` }[what] || 'Building removed');
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };
  if (err) return <section className="fbk"><p className="fbk-err">{err}</p>{onBack ? <button type="button" className="m-btn" onClick={onBack}><ArrowLeft size={14} /> Back to the city</button> : null}</section>;
  if (!v) return <section className="fbk"><p className="fbk-wait">Opening the block…</p></section>;
  const can = mine && v.canBuild;
  const errands = (bl?.buildings || []).reduce((n, b) => n + (b.state === 'built' ? (b.errands || []).length : 0), 0);
  return (
    <section className="fbk" data-testid="family-block">
      <header className="fbk-hud">
        {onBack ? <button type="button" className="fbk-back" onClick={onBack}><ArrowLeft size={14} /> City</button> : null}
        <b className="fbk-title">[{v.tag}] {v.name} · THE BLOCK</b>
        <span data-tip="Market buildings standing on a real position / all buildings on the block"><em>BUILT</em><b key={bl?.built}>{bl ? `${bl.built}/${(bl.buildings || []).length}` : '—'}</b>
          <i className="fbk-cap"><u style={{ transform: `scaleX(${bl && (bl.buildings || []).length ? bl.built / bl.buildings.length : 0})` }} /></i></span>
        {mine ? <span data-tip="What the family's wallets hold in the block's markets right now (live prices)"><em>IN MARKETS</em><b key={bl?.total}>{bl?.total ? `$${Math.round(bl.total).toLocaleString('en-US')}` : '$0'}</b></span> : null}
        {mine ? <span data-tip="Real-money errands waiting on your built buildings"><em>ERRANDS</em><b>{errands}</b></span> : null}
        {(mine || lpOwner) && (lp || []).length ? <span className="fbk-lp" data-tip="Your LP positions on this block: worth now · fees earned and not claimed yet" data-testid="block-lp-hud"><em>IN POOLS</em><b key={lp.length}>{dollarsSmall(lp.reduce((a, p) => a + (p.valueUsd || 0), 0))}</b><small>+{dollarsSmall(lp.reduce((a, p) => a + (p.feeUsd || 0), 0))} fees</small></span> : null}
        <span data-tip="Mob points in the family bank (points only — the street game below)"><em>BANK</em><b>{v.bank.toLocaleString('en-US')} MP</b></span>
        {v.staff ? <span className="fbk-staff" data-tip="The creator wallet: every unlock">👑 CREATOR</span> : null}
      </header>
      <div className="fbk-wrap">
        <div className="fbk-left">
          <div className="fbk-stage3">{bl ? <FamilyBlock3D bl={bl} sel={bsel} onPick={setBsel} coins={coins} onClosePop={() => setBsel(null)}
            lp={lp} pop={lpSel ? <LpPositionCard p={lpSel} /> : bsel?.blk || bsel?.open != null ? <BlockCard bl={bl} sel={bsel} busy={busy} mine={mine} onAct={blAct} onErrand={(e, b) => errandGo(e, b)} /> : null} /> : <p className="fbk-wait">Surveying the block…</p>}{lpSel || bsel?.blk || bsel?.open != null ? null : <BlockPicks coins={coins} />}
            {room ? <section className="ftr" style={{ '--tc': TOWN[room].color }} role="dialog" aria-label={TOWN[room].name} data-testid={`town-room-${room}`}>
              <header><i aria-hidden="true" /><span><b>{TOWN[room].name}</b><small>{TOWN[room].sub}</small></span>
                <button type="button" onClick={() => setBsel(null)} aria-label="Walk back out" data-tip="Back to the block (Esc)" data-testid="town-room-close">✕</button></header>
              <div className="ftr-body"><React.Suspense fallback={<p className="m-dim">Opening {TOWN[room].name}…</p>}>{deckBody(room, myFam && myFam.id === v.id ? myFam : null, tools)}</React.Suspense></div></section> : null}</div>
          <FamilyDeck mine={myFam && myFam.id === v.id ? myFam : null} tools={myFam && myFam.id === v.id ? tools : null} town={bl?.town || null} />
        </div>
        <aside className="fbk-side">
          <div className="fbk-card"><TownPicker bl={bl} busy={busy} mine={mine} onAct={blAct} open={room} onOpen={k => setBsel({ town: k })} /></div>
          {room ? null : <div className="fbk-card"><BlockCard bl={bl} sel={null} busy={busy} mine={mine} onAct={blAct} onErrand={(e, b) => errandGo(e, b)} /></div>}
          {mine ? <StreetGame v={v} act={act} busy={busy} can={can} /> : null}
        </aside>
      </div>
    </section>
  );
}
