import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { Coins, Shield, Crosshair, Briefcase, Eye, RotateCw, Hammer, ArrowLeft } from 'lucide-react';
import { apiUrl } from '../lib/api';
import { FamilyDeck } from './FamilyDeck';
import '../styles/familyBlock.css';

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
function BlockPicks() {
  const [rows, setRows] = useState([]);
  useEffect(() => { let on = true; const load = () => fetch(apiUrl('/api/reputation/familia/intake')).then(r => (r.ok ? r.json() : null)).then(x => on && x && setRows((x.coins || []).filter(c => c.pair).slice(0, 3))).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 30000); return () => { on = false; clearInterval(t); }; }, []);
  if (!rows.length) return null;
  return <div className="fbk-picks" data-testid="block-picks">{rows.map((c, i) => <button key={c.mint} type="button" className={`fbk-pick ${(c.ch ?? 0) < 0 ? 'dn' : 'up'}`} style={{ '--i': i }}
    onClick={e => { e.stopPropagation(); window.dispatchEvent(new CustomEvent('feeless:war-room', { detail: { chainId: 'solana', pairAddress: c.pair, baseToken: { address: c.mint, symbol: c.sym } } })); }}
    onPointerDown={e => e.stopPropagation()} data-tip={`$${c.sym} · the desk's pick (${c.status || 'intake'}) · 5m ${c.ch == null ? '—' : `${c.ch >= 0 ? '+' : ''}${Number(c.ch).toFixed(1)}%`} — tap to trade it`} data-testid={`block-pick-${i}`}>
    <b>${String(c.sym || '?').slice(0, 7)}</b><small>{c.ch == null ? '—' : `${c.ch >= 0 ? '+' : ''}${Number(c.ch).toFixed(1)}%`}</small></button>)}<em>DESK PICKS</em></div>;
}

export function FamilyBlock({ cid, addr, sess, onBack, mine: myFam = null, tools = null }) {
  const mine = !cid;
  const [v, setV] = useState(null); const [err, setErr] = useState(''); const [sel, setSel] = useState(null); const [busy, setBusy] = useState(false);
  const stageRef = useRef(null); const rzRef = useRef(-40); const [spin, setSpin] = useState(false);
  const setRz = f => { rzRef.current = typeof f === 'function' ? f(rzRef.current) : f; stageRef.current?.style.setProperty('--rz', `${rzRef.current}deg`); }; const [nowS, setNowS] = useState(() => Date.now() / 1000); const [burst, setBurst] = useState(0);
  const drag = useRef(null);
  const load = () => fetch(apiUrl(mine ? `/api/reputation/familia-city?address=${addr}&session=${encodeURIComponent(sess)}` : `/api/reputation/familia-city/${cid}`))
    .then(async r => { const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'The block could not be read.'); setV({ ...b, _at: Date.now() / 1000 }); setErr(''); })
    .catch(e => setErr(e.message));
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000); return () => clearInterval(t); }, [cid, addr, sess]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNowS(Date.now() / 1000); }, 1000); return () => clearInterval(t); }, []);
  useEffect(() => { if (!spin) return undefined; let raf; let last = performance.now(); const go = t => { setRz(z => z + (t - last) * 0.012); last = t; raf = requestAnimationFrame(go); }; raf = requestAnimationFrame(go); return () => cancelAnimationFrame(raf); }, [spin]);   // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (body, ok) => {
    setBusy(true);
    try {
      const r = await fetch(apiUrl('/api/reputation/familia-city/act'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: addr, session: sess, ...body }) });
      const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'Refused.');
      setV({ ...b, _at: Date.now() / 1000 });
      if (b.result?.stake) toast[b.result.win ? 'success' : 'error'](b.result.win ? `🎰 won ${Math.round(b.result.stake * 0.9).toLocaleString('en-US')} MP` : `🎰 lost ${b.result.stake.toLocaleString('en-US')} MP`);
      if (b.result?.collected) { setBurst(x => x + 1); toast.success(`💰 ${b.result.collected.toLocaleString('en-US')} MP collected`); }
      else if (b.result && 'win' in b.result) toast[b.result.win ? 'success' : 'error'](b.result.win ? `🔫 took ${b.result.take.toLocaleString('en-US')} MP` : '☠ the hit failed — one hitter lost');
      else toast.success(ok);
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };
  const moved = useRef(false);
  const down = e => { drag.current = { x: e.clientX, rz: rzRef.current }; moved.current = false; };
  const move = e => { if (!drag.current) return; const dx = e.clientX - drag.current.x; if (Math.abs(dx) > 5) moved.current = true; setRz(drag.current.rz + dx * 0.5); };
  const pick = i => { if (!moved.current) setSel(i); };
  const up = () => { drag.current = null; };
  if (err) return <section className="fbk"><p className="fbk-err">{err}</p>{onBack ? <button type="button" className="m-btn" onClick={onBack}><ArrowLeft size={14} /> Back to the city</button> : null}</section>;
  if (!v) return <section className="fbk"><p className="fbk-wait">Opening the block…</p></section>;
  const lot = sel != null ? v.lots[sel] : null;
  const stash = liveStash(v, nowS);
  const can = mine && v.canBuild;
  return (
    <section className="fbk" data-testid="family-block">
      <header className="fbk-hud">
        {onBack ? <button type="button" className="fbk-back" onClick={onBack}><ArrowLeft size={14} /> City</button> : null}
        <b className="fbk-title">[{v.tag}] {v.name} · BLOCK LVL {v.level}</b>
        <span data-tip="MP in the family bank — what builds, upgrades and goons are paid from"><em>BANK</em><b>{v.bank.toLocaleString('en-US')} MP</b></span>
        <span data-tip={`Made by the stores, waiting to be collected — up to ${v.stashCap.toLocaleString('en-US')} MP (12h). Robbers can hit it; the bank is safe.`}><em>STASH</em><b key={stash}>{stash.toLocaleString('en-US')}</b><i className="fbk-cap"><u style={{ transform: `scaleX(${Math.min(1, stash / Math.max(1, v.stashCap))})` }} /></i></span>
        <span data-tip="MP an hour from every store × level, parks and earners"><em>RATE</em><b>{v.rate}/h</b></span>
        <span data-tip="Members' verified trades this week boost production (×1 to ×2)"><em>BOOST</em><b>×{v.boost}</b></span>
        <span data-tip="Store levels × 10 + goons + bank ÷ 100 — counts toward the family's mob rank"><em>POWER</em><b>{v.power.toLocaleString('en-US')}</b></span>
        {v.staff ? <span className="fbk-staff" data-tip="The creator wallet: every store unlocked, every build free">👑 CREATOR</span> : null}
      </header>
      <div className="fbk-wrap">
        <div className="fbk-left">
        <div className="fbk-stage" ref={stageRef} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerLeave={up} style={{ '--rz': `${rzRef.current}deg` }}>
          <div className="fbk-sky" aria-hidden="true" />
          <div className="fbk-plane">
            <i className="fbk-road" aria-hidden="true" />
            {v.lots.map(l => <button key={l.lot} type="button" className={`fbk-lot ${l.b ? 'has-b' : 'is-empty'} ${l.b === 'park' ? 'is-park' : ''} ${sel === l.lot ? 'is-sel' : ''}`} onClick={() => pick(l.lot)} style={{ '--h': `${l.b ? heightOf(l.b, l.lvl) : 0}px` }}
              aria-label={l.b ? `${l.name} level ${l.lvl}` : `Empty lot ${l.lot + 1}`} data-testid={`lot-${l.lot}`}>
              {l.b ? <><Building l={l} nowS={nowS} /><span className="fbk-sign"><i>{l.icon}</i><small>{'★'.repeat(l.lvl)}</small></span></> : (can ? <span className="fbk-plus">+</span> : null)}
            </button>)}
            {Object.entries(v.goons || {}).flatMap(([k, n]) => Array.from({ length: Math.min(n, 4) }, (_, i) => <i key={`${k}-${i}`} className={`fbk-goon g-${k}`} style={{ '--i': i + (k === 'hitter' ? 4 : k === 'earner' ? 8 : 0) }}><b>{k === 'guard' ? '🛡' : k === 'hitter' ? '🔫' : '💼'}</b></i>))}
          </div>
          <BlockPicks />
          {burst ? <i key={burst} className="fbk-burst" aria-hidden="true">{Array.from({ length: 10 }, (_, i) => <b key={i} style={{ '--i': i }}>🪙</b>)}</i> : null}
          <div className="fbk-ctl"><button type="button" className={spin ? 'active' : ''} onClick={() => setSpin(x => !x)} aria-pressed={spin} data-testid="block-spin"><RotateCw size={14} /> {spin ? 'Stop' : '360°'}</button><small>drag to turn</small></div>
        </div>
        <FamilyDeck mine={myFam && myFam.id === v.id ? myFam : null} tools={myFam && myFam.id === v.id ? tools : null} />
        </div>
        <aside className="fbk-side">
          {lot ? (lot.b ? <div className="fbk-card" data-testid="lot-card">
            <header><i>{lot.icon}</i><div><b>{lot.name}</b><small>LOT {lot.lot + 1} · LEVEL {lot.lvl}/5 {'★'.repeat(lot.lvl)}</small></div></header>
            <p>{lot.what}</p>{lot.func ? <p className="fbk-func">⚙ {lot.func}</p> : null}
            <div className="fbk-kv"><span><em>MAKES</em><b>{lot.mph} MP/h</b></span><span><em>NEXT LEVEL</em><b>{lot.next != null ? `${lot.next.toLocaleString('en-US')} MP` : 'max'}</b></span></div>
            {can && lot.next != null ? <button type="button" className="m-btn m-go" disabled={busy} onClick={() => act({ act: 'upgrade', lot: lot.lot }, `⬆ ${lot.name} upgraded`)} data-testid="lot-upgrade"><Hammer size={14} /> Upgrade · {v.staff ? 'free' : `${lot.next.toLocaleString('en-US')} MP`}</button> : null}
          </div> : <div className="fbk-card" data-testid="lot-build">
            <header><i>🏗</i><div><b>Empty lot {lot.lot + 1}</b><small>{can ? 'pick a store to build' : mine ? 'only the Don or the Underboss builds' : "another family's lot"}</small></div></header>
            {mine ? <ul className="fbk-cat">{(v.catalog || []).map(c => <li key={c.key}><button type="button" disabled={!can || !c.ok || busy || c.cost > v.bank} onClick={() => act({ act: 'build', lot: lot.lot, kind: c.key }, `🏗 ${c.name} going up`)} data-testid={`build-${c.key}`}>
              <i>{c.icon}</i><span><b>{c.name}</b><small>{c.ok ? (c.func || c.what) : `🔒 ${c.need}`}</small></span><em>{c.mph ? `${c.mph}/h` : '+2 %'}<br />{c.cost ? `${c.cost.toLocaleString('en-US')} MP` : 'free'}</em></button></li>)}</ul> : null}
          </div>) : <div className="fbk-card"><header><i>🏙</i><div><b>Tap a lot</b><small>see what it makes · build · upgrade</small></div></header>
            <p>Stores make mob points (MP) every hour into the stash. Collect it into the bank, then build bigger stores. Bigger stores unlock as the family grows, wins wars and makes MP.</p></div>}
          {mine ? <div className="fbk-card">
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
          </div> : null}
        </aside>
      </div>
    </section>
  );
}
