import React, { useEffect, useState } from 'react';
import { fetchLaunchRail } from '../lib/launchRail';
import '../styles/launchLab.css';

// 🧪 LAUNCH LAB (owner, 2026-10-20: "pools and launch need a cool layout with live animated demonstrations of the type of pool / coin being
// created, plus the major configs from the top platforms, plus FEELESS exclusives — in HQ and for users"). Each type plays what really
// happens on-chain (a curve filling to graduation, two piles moving the price, bins shifting, a lock earning fees). Explain-only: the
// signed launchers below it are unchanged. Platform rows are MECHANICS, never quoted fees — those change; FEELESS's own come from its rail.
export const TYPES = [
  { id: 'pump', icon: '💊', name: 'Pump curve', where: 'Pump.fun', demo: 'curve',
    steps: ['A fixed bonding curve sells the coin — every buy lifts the price on a set path', 'The curve fills as SOL comes in', 'Full curve = it graduates to PumpSwap with the liquidity'],
    knobs: ['Name · ticker · picture · socials', 'Optional dev buy at launch', 'Curve + fees are Pump\'s own (not yours to set)'] },
  { id: 'dbc', icon: '🌊', name: 'Dynamic curve', where: 'Meteora DBC · the FEELESS rail', demo: 'dbc',
    steps: ['The launcher picks the curve shape and fees', 'An anti-snipe tax starts high and decays — bots that buy in the first seconds pay most', 'Graduates to a Meteora pool; its liquidity can be locked for good'],
    knobs: ['Curve shape + graduation target', 'Starting anti-snipe tax + how fast it decays', 'Creator share of trading fees', 'Graduated liquidity locked or not'] },
  { id: 'launchlab', icon: '🚀', name: 'LaunchLab curve', where: 'Raydium LaunchLab · LetsBonk', demo: 'curve',
    steps: ['A bonding curve set by the platform (or a partner like LetsBonk)', 'Buys climb the curve', 'Graduates into a Raydium pool'],
    knobs: ['Platform / partner config', 'Creator fee share (partner-set)', 'Name · ticker · picture'] },
  { id: 'amm', icon: '⚖', name: 'Constant-product pool', where: 'Meteora DAMM v2 · Raydium CPMM · PumpSwap', demo: 'amm',
    steps: ['You deposit BOTH sides: tokens and SOL', 'Price = SOL ÷ tokens in the pool — x · y = k', 'Every buy takes tokens out and puts SOL in, so the price rises'],
    knobs: ['Opening price (the ratio you deposit)', 'Swap fee', 'Lock the position or keep control'] },
  { id: 'dlmm', icon: '🎯', name: 'Concentrated bins', where: 'Meteora DLMM', demo: 'dlmm',
    steps: ['Liquidity sits in price bins, not one curve', 'Trades happen in the ACTIVE bin; when it empties the price steps to the next', 'Tight bins = deep at that price, nothing outside it'],
    knobs: ['Bin step (how far each bin is apart)', 'Where your liquidity sits (spot · curve · bid-ask)', 'Base fee + dynamic fee'] },
  { id: 'lock', icon: '🔒', name: 'Locked liquidity', where: 'any pool', demo: 'lock',
    steps: ['The position is locked — nobody can pull the tokens + SOL out', 'It keeps earning swap fees, claimable any time', 'Holders can check it: the rug-proof badge'],
    knobs: ['Lock forever or not at all', 'Who claims the fees'] },
];
export const PLATFORMS = [   // mechanics only (fee numbers change on their side — check their docs)
  { name: 'Pump.fun', curve: 'fixed curve', grad: 'PumpSwap', creator: 'creator rewards (Pump-set)', antiSnipe: '—', lp: 'protocol-held', you: 'name, art, dev buy' },
  { name: 'Raydium LaunchLab', curve: 'platform curve', grad: 'Raydium pool', creator: 'partner-set share', antiSnipe: '—', lp: 'burned / locked per config', you: 'name, art, partner' },
  { name: 'Meteora DBC', curve: 'configurable curve', grad: 'Meteora pool', creator: 'creator + partner split', antiSnipe: 'decaying fee', lp: 'lock optional', you: 'curve, fees, lock' },
  { name: 'FEELESS', curve: 'Meteora DBC', grad: 'Meteora pool', creator: 'your cut of fees', antiSnipe: 'decaying tax', lp: 'locked', you: 'all of it + extras', feeless: true },
];
export const EXCLUSIVES = [
  ['🛡', 'Rug shield from minute one', 'Holder scan, dev / sniper / bundle read and coin verification run on it the moment it trades.'],
  ['💬', 'Its own war room + chat', 'A live chart, trade tape and a chat room open by themselves.'],
  ['🧾', 'One signature, full receipt', 'CA, links, tx and metadata right after you sign — checked for you.'],
  ['🏠', 'House config (HQ)', 'Your own private terms; outsiders pay your toll, 90% back to your claimer.'],
  ['⚛', 'Fuse-ready', 'A coin with a real pool can join Fuse cards and the Arena once it passes the gates.'],
  ['⚡', 'Pump Pulse + callouts', 'Pulses and callouts on every chart that shows it.'],
];

// 🚪 CLICK-THROUGH (owner P2: "Launch click-through pages — the hero alone isn't the page"): every type, platform row and exclusive is a real
// door — the FEELESS launcher prefilled (Pump.fun or the FEELESS rail, your wallet signs), the platform's own launchpad, the directory below,
// or the FEELESS tool the exclusive is about.
export const DOOR = {
  pump: ['/terminal/launch?setup=feeless&rail=pump', '🚀 Launch a Pump coin here', 'The FEELESS launcher on the Pump.fun rail — you sign, it lands with its war room'],
  dbc: ['/terminal/launch?setup=feeless', '🚀 Launch on the FEELESS rail', 'Meteora DBC with the FEELESS rail: anti-snipe tax, locked liquidity, your fee cut'],
  launchlab: ['https://raydium.io/launchpad/', '↗ Raydium LaunchLab', "Raydium's own launchpad (LetsBonk runs on it) — your wallet signs there"],
  amm: ['#launchpads', '↓ Who makes these pools', 'The launchpad radar below — every rail and what it builds'],
  dlmm: ['#launchpads', '↓ Who makes these pools', 'The launchpad radar below — every rail and what it builds'],
  lock: ['/terminal/launch?setup=feeless', '🔒 Launch with liquidity locked', 'The FEELESS rail locks the graduated liquidity for good'],
};
const PLATFORM_DOOR = { 'Pump.fun': DOOR.pump[0], 'Raydium LaunchLab': DOOR.launchlab[0], 'Meteora DBC': '#launchpads', FEELESS: DOOR.dbc[0] };
const EX_DOOR = { 'Rug shield from minute one': '/terminal/reputation', 'Its own war room + chat': '/terminal/chat', 'One signature, full receipt': '/terminal/launch?setup=feeless',
  'House config (HQ)': '/terminal/hq', 'Fuse-ready': '/terminal/fuse', 'Pump Pulse + callouts': '/terminal/pump' };
const ext = u => /^https?:/.test(u);
export function Door({ to, children, className = '', tip, testId }) {
  return <a className={className} href={to} data-tip={tip} data-testid={testId} {...(ext(to) ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
    onClick={e => { if (to.startsWith('#')) { e.preventDefault(); document.getElementById(to.slice(1))?.scrollIntoView({ behavior: 'smooth', block: 'start' }); } }}>{children}</a>;
}

function Demo({ kind }) {
  if (kind === 'amm') return <svg className="llb-svg llb-amm" viewBox="0 0 240 130" aria-hidden="true">
    <text x="120" y="16" className="llb-t">x · y = k</text>
    <g className="llb-pile a"><rect x="40" y="30" width="60" height="80" rx="6" /></g><g className="llb-pile b"><rect x="140" y="30" width="60" height="80" rx="6" /></g>
    <text x="70" y="124" className="llb-t">TOKENS</text><text x="170" y="124" className="llb-t">SOL</text>
    <g className="llb-buy"><circle cx="120" cy="70" r="6" /></g><text x="120" y="48" className="llb-t llb-price">price ▲</text></svg>;
  if (kind === 'dlmm') return <svg className="llb-svg" viewBox="0 0 240 130" aria-hidden="true">{Array.from({ length: 11 }, (_, i) => { const h = 18 + 70 * Math.exp(-((i - 5) ** 2) / 8);
    return <rect key={i} className="llb-bin" x={10 + i * 20.5} y={110 - h} width="16" height={h} rx="3" />; })}<g className="llb-active"><rect x="112.5" y="14" width="16" height="96" rx="3" /></g><text x="120" y="126" className="llb-t">active bin steps as it empties</text></svg>;
  if (kind === 'lock') return <svg className="llb-svg" viewBox="0 0 240 130" aria-hidden="true"><g className="llb-shackle"><path d="M100 60V44a20 20 0 0140 0v16" fill="none" strokeWidth="8" /></g><rect className="llb-body" x="88" y="58" width="64" height="52" rx="8" />
    {[0, 1, 2].map(i => <g key={i} className={`llb-coin c${i}`}><circle cx={60 + i * 60} cy="100" r="7" /></g>)}<text x="120" y="126" className="llb-t">locked · still earning fees</text></svg>;
  const dbc = kind === 'dbc';
  return <svg className="llb-svg" viewBox="0 0 240 130" aria-hidden="true">
    <path className="llb-curve" d="M14 112 C 80 108, 150 90, 190 22" /><g className="llb-dot"><circle cx="0" cy="0" r="6" /></g>
    <rect className="llb-track" x="14" y="118" width="212" height="5" rx="2.5" /><g className="llb-fill"><rect x="14" y="118" width="212" height="5" rx="2.5" /></g>
    <g className="llb-grad"><text x="206" y="18" className="llb-t">🎓</text></g>
    {dbc ? <><text x="40" y="22" className="llb-t">anti-snipe tax</text><rect className="llb-track" x="14" y="28" width="90" height="5" rx="2.5" /><g className="llb-tax"><rect x="14" y="28" width="90" height="5" rx="2.5" /></g></> : null}
  </svg>;
}

// 🚀 LAUNCH PAD hero (owner, 2026-10-21: "Launch degen styling never got done"): a drawn rocket on its tower at amber dusk, a T-minus countdown that
// loops, exhaust smoke, and the rocket blasts off every time you pick another launch type (the pad re-keys on the type). Pure CSS / SVG.
export const tMinus = (ms, every = 12000) => Math.max(0, 10 - Math.floor((ms % every) / 1000));
// ⚡ THE LAUNCH HERO (owner 2026-10-26: "a cartoon rocket is kiddy — real, film-grain, electric"): near-black with the Launch green, film grain +
// scanlines, the chosen mechanic's curve as a live electric wire with a spark riding it, the real rail status underneath. transform / opacity only.
const WIRE = { pump: 'M0 150 C150 145 300 120 420 70 S560 12 600 8', dbc: 'M0 150 C120 148 240 130 360 92 S520 30 600 18', launchlab: 'M0 150 L120 132 L240 110 L360 80 L480 46 L600 14',
  amm: 'M0 140 C200 140 260 40 600 30', dlmm: 'M0 150 H120 V118 H240 V86 H360 V60 H480 V34 H600', lock: 'M0 120 H600' };
function LaunchPad({ t, rail }) {
  const d = WIRE[t.id] || WIRE.pump;
  return <div className="llp" key={t.id} data-testid="launch-pad">
    <i className="llp-grain" aria-hidden="true" /><i className="llp-scan" aria-hidden="true" />
    <svg className="llp-wire" viewBox="0 0 600 160" preserveAspectRatio="none" aria-hidden="true"><path d={d} className="llp-glow" /><path d={d} className="llp-line" pathLength="100" /></svg>
    <div className="llp-hud">
      <span className="llp-eyebrow">⚡ LAUNCH · {t.where}</span>
      <b className="llp-count">{t.name}</b>
      <div className="llp-chips"><span className={rail?.ready ? 'ok' : ''}>{rail?.ready ? '● FEELESS rail ready' : '○ FEELESS rail not set up'}</span>
        {rail?.tab?.maxDevBuySol ? <span>dev buy ≤ {rail.tab.maxDevBuySol} SOL</span> : null}{rail?.costs?.pumpSlippagePct != null ? <span>slippage {rail.costs.pumpSlippagePct}%</span> : null}<span>you sign every step</span></div>
    </div>
  </div>;
}

export function LaunchLab({ start = 'pump', hq = false }) {
  const [id, setId] = useState(start); const [rail, setRail] = useState(null);
  useEffect(() => { let on = true; fetchLaunchRail().then(r => on && setRail(r)).catch(() => {}); return () => { on = false; }; }, []);
  const t = TYPES.find(x => x.id === id) || TYPES[0];
  return <section className="llb" data-testid="launch-lab">
    <LaunchPad t={t} rail={rail} />
    <header className="llb-head"><span className="eyebrow">🧪 LAUNCH LAB{hq ? ' · HQ' : ''}</span><h2>See what you're creating before you sign.</h2></header>
    <div className="llb-types" role="tablist">{TYPES.map(x => <button key={x.id} type="button" role="tab" aria-selected={x.id === id} className={x.id === id ? 'is-on' : ''} onClick={() => setId(x.id)} data-testid={`llb-${x.id}`}><b>{x.icon}</b>{x.name}<small>{x.where}</small></button>)}</div>
    <div className="llb-stage" key={t.id}><div className="llb-demo"><Demo kind={t.demo} /></div>
      <div className="llb-how"><h3>{t.icon} {t.name} <small>{t.where}</small></h3><ol>{t.steps.map((s, i) => <li key={s} style={{ '--i': i }}>{s}</li>)}</ol>
        <h4>WHAT YOU SET</h4><ul className="llb-knobs">{t.knobs.map(k => <li key={k}>{k}</li>)}</ul>
        {DOOR[t.id] ? <Door to={DOOR[t.id][0]} className="m-btn m-go llb-door" tip={DOOR[t.id][2]} testId={`llb-door-${t.id}`}>{DOOR[t.id][1]}</Door> : null}</div></div>
    <div className="llb-table" role="table" aria-label="Launch platforms compared"><div className="llb-row is-head" role="row">{['', 'Curve', 'Graduates to', 'Creator earns', 'Anti-snipe', 'Liquidity after', 'You set'].map(h => <span key={h} role="columnheader">{h}</span>)}</div>
      {PLATFORMS.map(p => <div key={p.name} className={`llb-row${p.feeless ? ' is-feeless' : ''}`} role="row"><b><Door to={PLATFORM_DOOR[p.name] || '#launchpads'} className="llb-plink" tip={`Open ${p.name}`} testId={`llb-plat-${p.name.split(' ')[0]}`}>{p.name} ›</Door></b><span>{p.curve}</span><span>{p.grad}</span><span>{p.creator}</span><span>{p.antiSnipe}</span><span>{p.lp}</span><span>{p.you}</span></div>)}</div>
    <p className="llb-note">Fee numbers change on each platform's side — check their docs. FEELESS's rail right now: {rail?.ready ? 'ready' : 'not set up yet'}{rail?.tab?.maxDevBuySol ? ` · dev buy up to ${rail.tab.maxDevBuySol} SOL` : ''}{rail?.costs?.pumpSlippagePct != null ? ` · Pump launch slippage ${rail.costs.pumpSlippagePct}%` : ''}.</p>
    <h4 className="llb-h">⚡ ONLY ON FEELESS</h4><div className="llb-ex">{EXCLUSIVES.filter(e => hq || e[1] !== 'House config (HQ)').map(([i, n, w], k) => <Door key={n} to={EX_DOOR[n] || '#launchpads'} className="llb-exd" tip={`${n} — open it`} testId={`llb-ex-${k}`}><div style={{ '--i': k }}><b>{i}</b><strong>{n}</strong><small>{w}</small><em aria-hidden="true">›</em></div></Door>)}</div>
  </section>;
}
export default LaunchLab;
