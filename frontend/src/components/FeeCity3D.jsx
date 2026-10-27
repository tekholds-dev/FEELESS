import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Building, Building2, Zap, Flower2, Crown, Swords, Trophy, Radio, Waves, Medal, Siren, Gem, ClipboardList, Dumbbell, Spade, Warehouse, Radar, Activity, Eye, Scale, Cat, Fuel, Newspaper, Landmark, TrendingUp, CandlestickChart, Sun, Moon, Maximize2, Minimize2 } from 'lucide-react';
import { FamilyCity3D, Vitals, vitalsOf } from './FamilyCity3D';
import { MetaCard } from './cards/MetaCard';
import { tokenImageUrls } from './terminal/MarketPrimitives';
import { feePlan, outerPlan, spotOf, PLACES, usd, apyTxt, POOL_KIND } from '../lib/cityPlan';
import { sharedJson } from '../lib/sharedJson';
import '../styles/feeCity3d.css';
import { familiaRoom } from '../lib/familiaRoom';
import { MoneyDesk, providersOf, deskHost, JOB_OF } from './MoneyDesk';

// 🌃 FEE CITY IN REAL 3D (owner, 2026-10-22: "way better design and animations … find free model sites and use the best" · "hella glow, day /
// night" · "expand the city and go to places" · "80 % of the tabs in the cities, easy to find, with a pop-out" · "real Fuse cards in the
// middle of the Fuse Arena"): the capital + its market islands and the outer cities with their pool districts, drawn by three.js with Kenney's
// CC0 kits. A CITY DIRECTORY dock on the map reaches every place (the old tabs) in one tap; district chips fly the camera; ☀ / 🌙 flips the
// city's time of day; ⤢ expands it to the whole window; the real Fuse cards stand over the stadium pitch. No WebGL (or a test) → the CSS city.
export const webglOk = () => {
  if (typeof window === 'undefined' || /jsdom/i.test(window.navigator?.userAgent || '')) return false;
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
};
const lite = () => typeof document !== 'undefined' && document.body.classList.contains('fx-lite');
const still = () => typeof window !== 'undefined' && (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches || document.body.classList.contains('reduced-motion-setting'));
const MODE_KEY = 'feeless.city.mode';
const startMode = () => { try { const m = localStorage.getItem(MODE_KEY); if (m === 'day' || m === 'night') return m; } catch { /* storage blocked */ } return typeof document !== 'undefined' && document.body.classList.contains('theme-day') ? 'day' : 'night'; };
export const PLACE_ICON = { hq: Crown, warroom: Swords, podium: Trophy, wire: Radio, pools: Waves, ranked: Medal, raids: Siren, rewards: Gem, jobs: ClipboardList, gym: Dumbbell, cards: Spade, cartels: Warehouse,
  pumpradar: Radar, runners: Activity, watch: Eye, court: Scale, feecat: Cat, fuel: Fuel, news: Newspaper, feebank: Landmark, brokers: Landmark, trades: TrendingUp, perps: CandlestickChart, tt: Building, sleep: Moon };

// 🏦 the live Solana markets + today's top coins (one shared read a minute, every viewer)
export function useMarkets() {
  const [mk, setMk] = useState(null);
  useEffect(() => { let on = true; const go = () => sharedJson('/api/reputation/familia-markets', { maxAge: 55000 }).then(d => on && d && setMk(d)).catch(() => {});
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 60000); return () => { on = false; clearInterval(t); }; }, []);
  return mk;
}
// ⚔ the Arena's real Fuse cards (the Prime fighters first, then the bred mega cards) as card faces
export function arenaCards(a) {
  const legPair = l => ({ chainId: 'solana', pairAddress: l.pairAddress, baseToken: { address: l.baseAddress || l.mint, symbol: l.symbol }, info: l.logo ? { imageUrl: l.logo } : undefined });
  return [...(a?.fighters || []), ...(a?.mega || [])].filter(c => (c.legs || []).length).slice(0, 3).map((c, i) => {
    const top = [...c.legs].sort((x, y) => (y.weight || 0) - (x.weight || 0))[0] || {};
    return { key: c.id || `c${i}`, kind: 'fuse', title: c.name || c.legs.slice(0, 3).map(l => l.symbol).join(' · '), subtitle: c.legs.slice(0, 3).map(l => `$${l.symbol}`).join(' · '),
      rarity: i === 0 ? 'legendary' : 'epic', design: ['holo', 'aurora', 'ember'][i % 3], glyph: c.emoji || '✦', art: tokenImageUrls(legPair(top)), motion: 'still', holders: c.legs.length, edition: c.kind === 'prime' ? 'PRIME' : 'BRED' };
  });
}
export function useArena(on) {
  const [a, setA] = useState(null);
  useEffect(() => { if (!on) return undefined; let ok = true; sharedJson('/api/reputation/fuses/arena', { maxAge: 120000 }).then(d => ok && setA(d)).catch(() => {}); return () => { ok = false; }; }, [on]);
  return a;
}

// pure: a market's / pool's / place's vitals for the stage panel (WHAT · LIVE)
export function marketVitals(m, plan) {
  if (!m) return null;
  if (m.place) { const p = (plan?.places || []).find(x => x.key === m.place) || PLACES.find(x => x.key === m.place);
    return p ? { title: p.name, tone: 'lm', groups: [['PLACE', [['WHAT', p.sub], ['OPEN', 'tap again or use the panel']]]] } : null; }
  const x = (plan?.markets || []).find(k => k.key === m.mk); if (!x) return null; const mm = x.m || {};
  const act = deskAct(x);   // 💸 every money building is ACTIVE (owner, 2026-10-23: "80 % active real money buildings"): its own in-place action
  if (x.pool) return { title: x.name, tone: 'mk', act, groups: [['POOL', [['KIND', POOL_KIND[x.kind] || x.kind], ['PROTOCOL', x.proto]]], ['LIVE', [['TVL', usd(x.tvl), Math.min(1, Math.log10(1 + (x.tvl || 0)) / 10)], ['APY', apyTxt(x.apy)], ...(mm.vol ? [['24H VOL', usd(mm.vol)]] : [])]]] };
  const live = x.kind === 'coin' ? [['MARKET CAP', usd(x.tvl)], ...(x.move != null ? [['24H', `${x.move >= 0 ? '+' : ''}${Number(x.move).toFixed(1)}%`]] : []), ...(mm.vol ? [['24H VOL', usd(mm.vol)]] : [])]
    : [['TVL', usd(x.tvl), Math.min(1, Math.log10(1 + (x.tvl || 0)) / 10)], ...(mm.pool ? [['BUSIEST POOL', `${mm.pool.base}/${mm.pool.quote}${mm.pool.labels?.length ? ` · ${mm.pool.labels[0]}` : ''}`], ['POOL LIQ', usd(mm.pool.liq)], ['POOL 24H VOL', usd(mm.pool.vol)]] : [])];
  return { title: x.name, tone: 'mk', act, groups: [['WHAT', [['KIND', String(x.kind).toUpperCase()], ...(mm.offer ? [['OFFERS', mm.offer]] : [])]], ['LIVE', live], ['ACTIVITY', [['HALO', `turns at ${x.hz}× = its volume`]]]] };
}

// pure: a market building's in-place money action — a pool → its own desk row (stake / lend / LP / trade), a protocol → the desk on its job led by
// its busiest pool, a coin → the swap dock (you press Get quote; your wallet signs). Never a link out.
export function deskAct(x) {
  if (!x) return null; const mm = x.m || {};
  if (x.kind === 'coin') { const to = mm.mint || mm.address; return to ? { word: `⚡ BUY $${x.name} HERE`, swap: { to, title: `${x.name} · BUY IT HERE` } } : null; }
  const job = JOB_OF[x.kind] || 'best';
  const word = { stake: '⚡ STAKE HERE', lend: '⚡ LEND HERE', lp: '⚡ ADD LIQUIDITY HERE', perps: '⚡ TRADE PERPS HERE', rwa: '⚡ EARN HERE', best: '⚡ PUT MONEY IN HERE' }[job] || '⚡ PUT MONEY IN HERE';
  return x.pool ? { word, desk: { job, focus: mm, title: `${String(x.name).toUpperCase()} · ${word.replace('⚡ ', '')}` } }
    : { word, desk: { job, proto: x.proto || x.name, title: `${String(x.name).toUpperCase()} · ${word.replace('⚡ ', '')}` } };
}

// 📍 every place in Fee City (the old lens tabs) as one signpost menu — used by the CSS fallback city's controls
export function PlacesMenu({ onGo }) {
  const [open, setOpen] = useState(false); const ref = useRef(null);
  useEffect(() => { if (!open) return undefined; const out = e => { if (!ref.current?.contains(e.target)) setOpen(false); }; const esc = e => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', out); document.addEventListener('keydown', esc); return () => { document.removeEventListener('pointerdown', out); document.removeEventListener('keydown', esc); }; }, [open]);
  return <span className="fc3-places" ref={ref}><button type="button" className={open ? 'active' : ''} onClick={() => setOpen(o => !o)} aria-expanded={open} data-tip="Every place in Fee City — fly there and walk in" data-testid="city-places">📍 Places</button>
    {open ? <ul className="fc3-menu" role="menu">{PLACES.map((p, i) => <li key={p.key} style={{ '--i': i, '--pc': p.color }}><button type="button" role="menuitem" onClick={() => { setOpen(false); onGo(p); }} data-testid={`place-${p.key}`}>
      <b>{p.name}</b><small>{p.sub}</small></button></li>)}</ul> : null}</span>;
}

// 🧭 the CITY DIRECTORY (owner, 2026-10-23: "the majority of the directory doesn't help users get straight into rapid compound and growth"):
// it LEADS with the money — ⚡ START COMPOUNDING (the best in-place yields, live) and the buildings that grow it — then the family, then the tools.
// Every place is still one tap away; the crest forge has its own door.
export const DIR_GROUPS = [['💸 GROW YOUR MONEY', ['sleep', 'pools', 'mymoney', 'brokers', 'trades', 'feebank', 'perps', 'tt', 'pumpradar', 'runners']],
  ['🌹 THE FAMILY', ['race', 'hq', 'warroom', 'raids', 'cartels', 'podium', 'ranked', 'rewards', 'wire', 'jobs', 'gym', 'cards']], ['🛠 TOOLS', ['court', 'watch', 'feecat', 'fuel', 'news']]];
// pure: the live line a money place wears in the directory (the Pool Hub's best numbers)
export function dirLive(key, pools) {
  const rs = (pools?.pools || []).filter(r => Number(r.apy) > 0); const top = k => rs.filter(r => k.includes(r.kind)).reduce((m, r) => Math.max(m, r.apy), 0);
  if (key === 'sleep') { const v = top(['stake', 'lend']); return v ? `up to ${apyTxt(Math.min(v, 40))} while you sleep` : null; }
  if (key === 'pools') { const v = rs.length; return v ? `${v} paying pools live` : null; }
  return null;
}
function Directory({ onGo, open, setOpen, active, pools, onDesk, desk }) {
  const best = providersOf('best', pools?.pools)[0]; const [more, setMore] = useState(false);   // owner: "no fluff — only real ways to make money": the rest of the city folds away
  let n = 0;
  return <nav className={`fc3-dir ${open ? 'is-open' : ''}`} aria-label="City directory" data-testid="city-directory">
    <button type="button" className="fc3-dirtoggle" onClick={() => setOpen(o => !o)} aria-expanded={open} data-tip="Every place in the city — money first" data-testid="city-dir-toggle"><Building2 size={15} aria-hidden="true" /><span>DIRECTORY</span></button>
    <ul>
      <li className="fc3-dirgo" style={{ '--i': 0, '--pc': '#45e486' }}><button type="button" className={desk && !desk.focus ? 'active' : ''} onClick={onDesk} aria-pressed={!!desk && !desk.focus} data-testid="dir-compound"
        data-tip="The best yields you can start right here, live — pick one, pick your amount, watch it compound; your wallet signs"><Zap size={16} aria-hidden="true" /><span><b>START COMPOUNDING</b><small>{best ? `${best.sym} · ${apyTxt(best.apy)} · in place` : 'the best live yields, in place'}</small></span></button></li>
      {DIR_GROUPS.map(([word, keys], gi) => (gi && !more ? null : <React.Fragment key={word}><li className="fc3-dirh" aria-hidden="true">{word}</li>
        {keys.map(k => PLACES.find(x => x.key === k)).filter(Boolean).map(p => { n += 1; const Icon = PLACE_ICON[p.key] || Building2; const host = p.in ? PLACES.find(x => x.key === p.in) : null; const live = dirLive(p.key, pools);
          return <li key={p.key} className={`${host ? 'is-room' : ''} ${p.money ? 'is-money' : ''}`} style={{ '--i': n, '--pc': p.color }}>
            <button type="button" className={active === p.lens ? 'active' : ''} onClick={() => onGo(p)} data-tip={`${p.name} — ${p.sub}${host ? ` · a room inside ${host.name}` : ''}`} data-testid={`dir-${p.key}`}><Icon size={16} aria-hidden="true" />
              <span><b>{p.name}</b><small>{live || (host ? `↳ in ${host.name.replace(/^(THE|YOUR) /, '')}` : p.sub)}</small></span></button></li>; })}
        {word.includes('FAMILY') ? <li style={{ '--i': n + 1, '--pc': '#ff8fa3' }}><button type="button" onClick={() => { try { sessionStorage.setItem('feeless.hq.tool', 'badge'); } catch { /* storage blocked */ } window.dispatchEvent(new CustomEvent('feeless:hq-tool', { detail: 'badge' })); onGo(PLACES.find(x => x.key === 'hq')); }}
          data-tip="Design your family's crest — shape, charge, colours, motto — and save it; every family sees it" data-testid="dir-crest"><Flower2 size={16} aria-hidden="true" /><span><b>FORGE YOUR CREST</b><small>design the badge · save it</small></span></button></li> : null}
      </React.Fragment>))}
      <li className="fc3-dirmore"><button type="button" onClick={() => setMore(m => !m)} aria-expanded={more} data-tip={more ? 'Fold the family + tool places away' : 'The family places (HQ, wars, podium…) and the tools'} data-testid="dir-more"><span><b>{more ? '− LESS' : '＋ THE REST OF THE CITY'}</b><small>{more ? 'money only' : 'family · wars · tools'}</small></span></button></li>
    </ul>
  </nav>;
}

// 🧭 the district chips: every district, then ONE chip for the family keys (it flies to yours) — six key chips would bury the money districts
export const chipsOf = plan => { const isl = plan?.islands || []; const keys = isl.filter(i => i.key_);
  return [...isl.filter(i => !i.key_), ...(keys.length ? [{ key: 'keys', name: 'THE FAMILY KEYS', sub: `${keys.length} islands · 4 plots each · yours first`, color: '#d4af37' }] : [])]; };

export function FeeCity3D({ v, sel, setSel, city, setCity, tour, overlay, onPlace, onGoPlace, active, markets, pools }) {
  const [gl] = useState(webglOk);
  const host = useRef(null); const eng = useRef(null); const stage = useRef(null); const cardEls = useRef({});
  const [ready, setReady] = useState(false); const [tip, setTip] = useState(null); const [spin, setSpin] = useState(false);
  const [mode, setMode] = useState(startMode); const [full, setFull] = useState(false); const [desk, setDesk] = useState(false); const [dir, setDir] = useState(() => typeof window === 'undefined' || window.innerWidth > 900);
  useEffect(() => { if (active) setDir(false); }, [active]);   // walking into a room folds the directory away (it covered the room's left edge)
  const isFee = city === 'fee' || !v.cities?.length;
  const plan = useMemo(() => (isFee ? feePlan(v, markets, pools) : outerPlan(v, city, pools)), [v, markets, city, isFee, pools]);
  const live = useMemo(() => ({ raided: new Set((v.raids || []).filter(r => r.status === 'live').map(r => r.b?.id).filter(Boolean)),
    fight: (v.ffuse?.fights || []).find(f => f.status === 'live') || null, marks: Object.fromEntries((v.landmarks || []).map(m => [m.key, m.live || {}])) }), [v]);
  const arena = useArena(gl && isFee); const cards = useMemo(() => arenaCards(arena), [arena]);
  const pickRef = useRef(null);
  pickRef.current = pk => {
    if (pk?.gate) { setSel(null); setCity(pk.gate); return; }
    if (pk?.place) { const p = PLACES.find(x => x.key === pk.place) || (plan?.places || []).find(x => x.key === pk.place); setSel(pk); if (p) onPlace?.(p.lens); return; }
    setSel(pk);
  };
  useEffect(() => {   // mount the engine once (WebGL only)
    if (!gl || !host.current) return undefined; let alive = true;
    import('../lib/cityEngine').then(async m => { if (!alive) return; await m.preload();
      if (!alive || !host.current) return;
      eng.current = m.createCity(host.current, { onPick: pk => pickRef.current(pk), onHover: setTip, lite: lite(), still: still(), day: startMode() === 'day',
        onAnchors: pos => { Object.entries(pos).forEach(([id, p]) => { const el = cardEls.current[id]; if (!el) return;   // DOM writes only — React never re-renders per frame
          el.style.transform = `translate(${Math.round(p.x)}px, ${Math.round(p.y)}px) translate(-50%, -100%) scale(${p.s.toFixed(3)})`; el.style.opacity = p.vis ? '1' : '0'; el.style.visibility = p.vis ? 'visible' : 'hidden'; }); } });
      setReady(true); });
    return () => { alive = false; eng.current?.dispose(); eng.current = null; };
  }, [gl]);
  useEffect(() => { if (!ready || !eng.current || !plan) return; eng.current.setPlan(plan, live).then(first => { if (first && sel) eng.current?.flyTo(spotOf(plan, sel)); }); }, [ready, plan, live]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!ready || !eng.current || !plan) return; const s = spotOf(plan, sel); eng.current.flyTo(s, sel?.place === 'tt' ? 46 : sel?.mk || sel?.place ? 26 : sel?.lm ? 22 : 19); }, [ready, sel?.id, sel?.lm, sel?.mk, sel?.place, plan?.kind, plan?.key]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { eng.current?.spin(spin); }, [spin, ready]);
  useEffect(() => { eng.current?.setMode(mode); try { localStorage.setItem(MODE_KEY, mode); } catch { /* storage blocked */ } }, [mode, ready]);
  useEffect(() => {   // the real Fuse cards stand over the pitch: three anchors above the stadium (Fee City only)
    if (!ready || !eng.current) return;
    const ar = isFee ? plan?.marks.find(m => m.key === 'arena') : null;
    if (!ar || !cards.length) { eng.current.setAnchors([]); return; }
    const c = { x: ar.rect.x + ar.rect.w / 2, z: ar.rect.z + ar.rect.d / 2 }; const off = [0, -1, 1];
    eng.current.setAnchors(cards.map((k, i) => ({ id: k.key, x: c.x + off[i] * ar.rect.w * 0.24, y: i === 0 ? 3.2 : 2.4, z: c.z })));
  }, [ready, cards, plan, isFee]);
  useEffect(() => { deskHost(1); const open = e => setDesk(e.detail || true); window.addEventListener('feeless:desk', open); return () => { deskHost(-1); window.removeEventListener('feeless:desk', open); }; }, []);   // 💸 side panels open the desk HERE, big
  useEffect(() => { if (!desk) return undefined; const esc = e => { if (e.key === 'Escape') setDesk(false); }; window.addEventListener('keydown', esc); return () => window.removeEventListener('keydown', esc); }, [desk]);
  useEffect(() => {   // ⤢ expanded: the city takes the window; Esc brings it back
    if (!full) return undefined; const esc = e => { if (e.key === 'Escape') setFull(false); };
    document.body.classList.add('fc3-lock'); window.addEventListener('keydown', esc); const t = setTimeout(() => eng.current?.resize(), 60);
    return () => { document.body.classList.remove('fc3-lock'); window.removeEventListener('keydown', esc); clearTimeout(t); setTimeout(() => eng.current?.resize(), 60); };
  }, [full]);

  if (!gl) return <FamilyCity3D v={v} sel={sel} setSel={setSel} city={city} setCity={setCity} tour={tour} overlay={overlay} />;
  const vit = sel?.place ? null : sel?.mk ? marketVitals(sel, plan) : vitalsOf(sel, v);   // a place's own room pops out instead
  const goIsland = k => { setSel(null); eng.current?.flyTo(spotOf(plan, { isl: k })); };
  return <div className={`fc3 is-${mode} ${ready ? 'is-ready' : ''} ${full ? 'is-full' : ''}`} ref={stage} data-testid="world-map">
    <div className="fc3-host" ref={host} aria-label={isFee ? 'Fee City in 3D — drag to turn, scroll to zoom, tap a building' : `${plan?.name || 'The city'} in 3D`} role="img" />
    {!ready ? <div className="fc3-load" aria-live="polite"><i className="fc3-sky" /><span className="fc3-skyline">{Array.from({ length: 14 }, (_, i) => <b key={i} style={{ '--i': i, '--h': `${30 + ((i * 37) % 60)}px` }} />)}</span><small>drawing the city…</small></div> : null}
    {ready && cards.length ? <div className="fc3-cards" aria-label="Fuse cards in the arena">{cards.map(k => <a key={k.key} href="/terminal/fuse" onClick={e => familiaRoom('fuse', e)} className="fc3-card" ref={el => { cardEls.current[k.key] = el; }} data-tip={`${k.title} — open the Fuse Arena`} data-testid={`arena-card-${k.key}`}>
      <MetaCard card={k} size="sm" /></a>)}</div> : null}
    {tip ? <span className="fc3-tip" style={{ transform: `translate(${tip.x + 14}px, ${tip.y + 12}px)` }}>{tip.label}</span> : null}
    <nav className="fc3-isl" aria-label="Districts" data-testid="city-districts">{chipsOf(plan).map((i, k) => <button key={i.key} type="button" style={{ '--i': k, '--dc': i.color || '#d4af37' }} onClick={() => goIsland(i.key)} data-tip={`Fly to ${i.name}${i.sub ? ` — ${i.sub}` : ''}`} data-testid={`isl-${i.key}`}>{i.name}</button>)}</nav>
    {isFee ? <Directory onGo={p => { setDesk(false); onGoPlace?.(p); }} open={dir} setOpen={setDir} active={active} pools={pools} desk={desk} onDesk={() => setDesk(d => !d)} /> : null}
    {desk ? <aside className="fc3-desk" role="dialog" aria-label="Start compounding" data-testid="city-desk"><button type="button" className="fc3-deskx" onClick={() => setDesk(false)} aria-label="Close" data-tip="Close (Esc)">✕</button>
      <MoneyDesk key={desk.focus?.id || desk.title || 'best'} job={desk.job || 'best'} focus={desk.focus || null} proto={desk.proto || null} rows={pools?.pools} title={desk.title || 'START COMPOUNDING'} /></aside> : null}
    <Vitals vit={vit} onClose={() => setSel(sel)} />
    {overlay}
    <div className="fcy-ctl fc3-ctl">
      <button type="button" className={spin ? 'active' : ''} onClick={() => setSpin(s => !s)} aria-pressed={spin} data-tip="Slowly turn the whole city" data-testid="city-spin">{spin ? '⏸ Stop' : '⟲ 360°'}</button>
      <button type="button" onClick={() => eng.current?.zoom(1.25)} data-tip="Zoom in" aria-label="Zoom in">＋</button>
      <button type="button" onClick={() => eng.current?.zoom(0.8)} data-tip="Zoom out" aria-label="Zoom out">－</button>
      <button type="button" onClick={() => { setSel(null); eng.current?.frameAll(); }} data-tip="See the whole city" aria-label="Whole city" data-testid="city-home">⌂</button>
      <button type="button" onClick={() => setMode(m => (m === 'day' ? 'night' : 'day'))} aria-pressed={mode === 'day'} data-tip={mode === 'day' ? 'Night: neon + lit windows' : 'Day: sun, blue sky'} data-testid="city-mode" aria-label="Day or night">{mode === 'day' ? <Moon size={14} /> : <Sun size={14} />}</button>
      <button type="button" className={full ? 'active' : ''} onClick={() => setFull(f => !f)} aria-pressed={full} data-tip={full ? 'Back to the page (Esc)' : 'Expand the city to the whole window'} data-testid="city-full" aria-label="Expand">{full ? <Minimize2 size={14} /> : <Maximize2 size={14} />}</button>
      {tour.ctl3 ?? tour.ctl}
      <small>drag to turn · right-drag to pan · scroll to zoom · tap a building</small></div>
    <ul className="fcy-key fc3-key"><li className="t-mine">yours</li><li className="t-family">families</li><li className="t-cpu">CPU towns</li><li className="t-cartel">cartels</li><li className="t-mk">markets · pools</li>{isFee ? <li className="t-place">places</li> : null}</ul>
  </div>;
}
