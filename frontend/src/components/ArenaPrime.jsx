import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useAdmin } from '../lib/adminCall';
import { LiveFuseCard, revalue } from './FuseCard';
import { useLivePrices } from '../lib/livePrices';
import { openWarRoom } from './WarRoomHost';
import { CardEarnings } from './CardEarnings';
import { ShareGifButton } from './ShareGif';
import { tokenImageUrls } from './terminal/MarketPrimitives';
import { RoundBell, TrailSummary, CycleBuilder, usd, usdK, pct, txUrl } from './FuseMoney';
import { StrategyPicks, stratPatch } from './StrategyPicks';

// ⭐ ARENA PRIME: FEELESS's own top-tier cards, FULLY AUTO on paper — auto TP/SL, auto-compound, 2 coins rotate every 6h. Different
// from creator picks: these are the public proof the automation works before any trader's config goes auto. "Buy now" loads the
// card into the Lab (traders: up to 3 pools + 3 runners; you approve one wallet transaction).
const CYCLE_PICKS = [['off', 'Off', "Keep the tier's own shape every round"], ['trench', '🗑 Trench', '1 major + 1 pool + up to 1–2 FRESH trench breakouts (≤6h old, broke $20K, ≥400 holders, 250+ trades/h, clean creator, mint + freeze revoked) — high risk, the rest are normal runners'], ['classic', '⚓→🔥', 'anchor (3 majors + 1 new major) → degen (1 major + 3 runners) → anchor → mixed (2 majors + new major + runner)'],
  ['adaptive', '🧠 Adaptive', 'A −3% round rests in anchor (3 majors + 1 new major), a +5% round goes degen, anything else = mixed'], ['safe', '⚓⇄⚖', 'anchor (3 majors + 1 new major) ⇄ mixed (2 majors + new major + runner)'], ['press', '🔥⇄⚖', 'degen (1 major + 3 runners) ⇄ mixed (2 majors + new major + runner)'],
  ['rescue', '🛟', '🛡 safest (3 majors + 1 new major) ⇄ ⚖ breakeven (1 high-volume pool + 3 high-volume runners)'], ['auto', '🤖 Auto', 'Engine picks each round: deep red → breakeven · red → safest · +5% → degen · flat → mixed']];
const LEG_MODES = ['', 'replace', 'park', 'hold'];   // '' = follow the card
const LEG_WORD = { '': '🃏 card', replace: '⇄ replace', park: '🅿 park', hold: '❄ hold' };
const KIND = { rescue: '🛟 Rescue cycle', fix: '🔧 Config fixed', streak: '📈 Streak', 'ride-end': '🏇 Ride over', 'instant-swap': '⚡ Instant loss swap', rug: '🚨 Rug shield', payout: '💸 Paid to wallet', tp: '💰 Auto TP', sl: '🛑 Auto stop', rotate: '⇄ Rotate', compound: '♻ Compound', deal: '🃏 Dealt', floor: '🛡 Floor', park: '🅿 Parked', rebuy: '↩ Bought back', phase: '🔄 Phase', topup: '💵 Top-up', defund: '↩ Back to paper', run: '🏁 Run closed', ride: '🏇 Riding' };
// Tier FX: 💎 Diamond = frost aura + prism ring + glints · 🥇 Gold = gold dust + shine sweep · 🔥 Blaze = fire + embers.
// They burn brighter (is-hot) when the card is up ≥ +10%. Transform/opacity only; frozen under fx-lite / reduced motion.
// Each tier is its OWN MetaCard build: design pattern, rarity frame, colours and aura — recognisable at a glance (and in lite mode).
export const TIER = {
  diamond: { aura: 'frost', name: 'DIAMOND', look: { design: 'prism', rarity: 'legendary', accent: '#9fe3ff', accent2: '#e4d4ff' } },
  gold: { aura: 'gold', name: 'GOLD', look: { design: 'obsidian', rarity: 'epic', accent: '#ffd56a', accent2: '#ff9a4d' } },
  blaze: { aura: 'fire', name: 'BLAZE', look: { design: 'ember', rarity: 'epic', accent: '#ff7a2f', accent2: '#ff3d5a' } },
  next: { aura: 'lightning', name: 'NEXT LEVEL', look: { design: 'plasma', rarity: 'mythic', accent: '#c58bff', accent2: '#3cdcff' } },
  ever: { aura: 'aurora', name: 'EVERLASTING', look: { design: 'nebula', rarity: 'legendary', accent: '#15d16a', accent2: '#6ad7ff' } },
};
// HQ ⚡ meta config: the settings the Arena proof backs today (hourly rotation of 1 coin, −15% floor, compound on, park & rebuy).
export const PRIME_META = { rotateHours: 1, rotateCount: 1, floorPct: 15, compound: true, slMode: 'park' };
// realizedUsd = what the card PAID OUT (walletUsd) — never the gross take-profits (those mostly compounded back in and are still held)
// 🧮 Where the all-time result comes from: the coins on the card now (now − what they cost) vs everything already sold this card's life
// (realized on coins that left + fees the card paid). The two always add up to ALL-TIME = now − put in.
export const allTime = (c, funded) => (c.math?.pnlUsd != null && c.cardFeesUsd != null ? c.math.pnlUsd : (c.valueUsd || 0) + (c.cardFeesUsd || 0) - (funded || 0));   // fees never count in P&L
export const whereDown = (c, funded) => { const legs = (c.legs || []).filter(l => (l.costUsd || 0) > 0);   // coins only — cash is proceeds of what was sold
  const held = legs.reduce((a, l) => a + ((l.usd || 0) - (l.costUsd || 0)), 0); const all = allTime(c, funded);
  return { held: Math.round(held * 100) / 100, sold: Math.round((all - held) * 100) / 100, all: Math.round(all * 100) / 100 }; };
export const primeRow = c => { const funded = c.real ? (c.realBook?.fundedUsd || c.fundedUsd || c.startUsd) : c.startUsd; const paid = c.walletUsd || 0; const total = c.valueUsd || 0; return ({ id: c.id, name: c.label, closed: false, costUsd: funded, valueUsd: total, realizedUsd: paid,
  // Real card face always uses TOTAL FUNDED principal. Run baseline stays separate in the header as THIS RUN FROM.
  // Equation: PUT IN -> IN CARD + PAID OUT NOW = TOTAL EQUITY; all-time P/L = TOTAL EQUITY - PUT IN.
  baseUsd: funded, extraUsd: (c.cash || 0) + (c.rentUsd || 0) + (c.parked || []).reduce((a, p) => a + (p.usd || 0), 0) + paid,
  // 🔒 the card face shows the SAME number as ALL-TIME beside it: the price result, fees apart (it read −$1.88 next to −$1.60)
  pnlUsd: c.real ? allTime(c, funded) : total - funded, pnlPct: funded > 0 ? (c.real ? allTime(c, funded) / funded * 100 : (total / funded - 1) * 100) : 0,
  legs: c.legs.map(l => ({ pairAddress: l.pairAddress, symbol: l.symbol, role: l.role, mint: l.mint, usd: l.costUsd, tokens: l.units, valueUsd: l.usd,
    pnlUsd: l.usd - l.costUsd, pnlPct: l.costUsd ? (l.usd / l.costUsd - 1) * 100 : 0, priced: true, priceNow: l.now, stars: l.stars, liq: l.liq, buying: l.buying || (c.real && !(l.usd > 0)) })) }); };
export const arenaRow = (c, live) => c.real ? primeRow(c) : revalue(primeRow(c), live);

export function usePrime(ms = 60000) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; const load = first => (first || !document.hidden) && fetch(apiUrl('/api/reputation/fuses/prime')).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(true); const t = setInterval(() => load(false), ms); const now = () => load(true); window.addEventListener('feeless:prime', now);
    return () => { alive = false; clearInterval(t); window.removeEventListener('feeless:prime', now); }; }, [ms]);
  return d;
}

export function ArenaPrime({ onLoad }) {
  const d = usePrime();
  const [open, setOpen] = useState(null);
  // REAL-TIME %: every card re-valued with the shared 10s live prices (server numbers back it every 60s)
  const live = useLivePrices((d?.cards || []).flatMap(c => c.legs.map(l => l.pairAddress)));
  if (!d?.cards?.length) return null;
  return <section className="prime" data-testid="arena-prime">
    <header className="prime-head m-card m-live"><span className="m-label">⭐ ARENA PRIME · FULLY AUTO · {d.cards.some(c => c.real) ? `${d.cards.filter(c => c.real).length} ON REAL MONEY · THE REST PAPER AT TRUE FILLS` : `PAPER AT TRUE FILLS · $${d.cfg.sizeUsd} EACH`}</span>
      <h3>Top-tier cards. Every automation on.</h3>
      <p className="m-dim">Only 3–5★ coins: eligible major anchors (SOL / JitoSOL / cbBTC — the basket advances on configured re-shapes) + deep pools + gated runners. Auto TP / SL per coin · {d.cfg.compound ? 'gains auto-compound into the other coins' : 'gains kept as cash'} · the {d.cfg.rotateCount} weakest rotate every {d.cfg.rotateHours < 1 ? `${Math.round(d.cfg.rotateHours * 60)} min` : `${d.cfg.rotateHours}h`} (a floored card is re-dealt at once) · 🛡 card floor at −{d.cfg.floorPct}% (everything into the anchor). {d.cards.some(c => c.real) ? ' 💵 REAL cards trade from the FEELESS Fuse wallet — every swap has its transaction below the card.' : ' Paper fills at the price a wallet would really get (pool impact both ways).'} Fees tracked apart, never in P&L.</p>
      {d.paperMatch?.n > 0 && <span className="m-chip ok" data-tip="Every ~5 min the coins on these cards are priced the way paper fills them AND with a real Jupiter quote for the same $. + = real gives more coins than paper." data-testid="paper-match">📏 Paper vs real quotes: avg {d.paperMatch.avgDevPct >= 0 ? '+' : ''}{d.paperMatch.avgDevPct}% · {d.paperMatch.within2Pct}% within 2% · {d.paperMatch.n} checks</span>}
      {d.weather && <span className={`m-chip ${d.weather.level === 'clear' ? 'ok' : 'warn'}`} data-testid="prime-weather" data-tip={`Runner weather for REAL money, measured by the engine's own sim cards on real recorded prices${d.weather.avgPct != null ? ` (${d.weather.avgPct >= 0 ? '+' : ''}${d.weather.avgPct}% over ${d.weather.n} sims)` : ''}. Clear = every gated runner · Rain = only strong runners in deep pools · Storm = no runners, new majors only. Paper keeps trading everything.`}>{WEATHER[d.weather.level] || WEATHER.clear}</span>}
      {d.realGuard?.length > 0 && <span className="m-chip ok" data-testid="prime-guard" data-tip={`Real-money guard is holding these floors over the saved config: ${d.realGuard.join(' · ')}. A real round trip costs about 2%, so real coins are never flipped on small dips.`}>🛡 Real guard on · {d.realGuard.length}</span>}</header>
    <div className="prime-row">{d.cards.map(c0 => { const rv = arenaRow(c0, live); const c = { ...c0, pnlPct: rv.pnlPct, valueUsd: rv.valueUsd }; const putIn = c.real ? (c.realBook?.fundedUsd || c.fundedUsd || c.startUsd) : (c.math?.putIn || c.startUsd); /* paper: everything ever put in, never a restart's lower start */ const t = TIER[c.tier] || TIER.gold; return <article key={c.id} className={`prime-card t-${c.tpl} tier-${c.tier || 'gold'} ${c.pnlPct >= 10 ? 'is-hot' : ''}`} data-testid={`prime-${c.tpl}`}>
      <span className="prime-tier" aria-hidden="true"><i className="pt-ring" /><i className="pt-sweep" />{Array.from({ length: 6 }, (_, i) => <i key={i} className="pt-spark" style={{ '--i': i }} />)}</span>
      <b className="prime-badge">{t.name}</b><span className={`prime-real ${c.real ? 'is-real' : 'is-paper'}`} data-tip={c.real ? `Real money from the FEELESS Fuse wallet since ${new Date((c.realSince || 0) * 1000).toLocaleDateString()} — every swap is on-chain` : 'Paper at true fills — same engine, same entries, no money'} data-testid={`prime-real-${c.tpl}`}>{c.real ? '💵 REAL MONEY' : '📄 PAPER'}</span>{d.roundWinner?.id === c.id && <span className="prime-crown" data-testid={`prime-crown-${c.tpl}`} data-tip="Best card of the last round">🏆 ROUND WINNER</span>}{c.why && <small className="prime-why">{c.why}</small>}
      {c.cycle && <span className="prime-phase" data-tip="This tier cycles every round: anchor (rest in majors) → degen (runners strike) → anchor → mixed (half and half). One continuous run.">🔄 {(c.phase || 'start').toUpperCase()} ROUND · next {c.cycle[(c.rounds || 0) % c.cycle.length]}</span>}
      <LiveFuseCard r={primeRow(c)} aura={t.aura} look={t.look} label={c.real ? '💵 REAL · FUSE WALLET' : '📄 PAPER · TRUE FILLS'} serverOnly={!!c.real} />
      <ul className="prime-legs">{c.legs.map(l => ({ ...l, pnlPct: l.pnlPct ?? (l.costUsd ? (l.usd / l.costUsd - 1) * 100 : 0) })).map(l => <li key={l.pairAddress}><b role="button" tabIndex={0} className="pl-open" data-tip="Open its chart — trade this coin on its own" onClick={() => openWarRoom({ chainId: 'solana', pairAddress: l.pairAddress, baseToken: { address: l.mint, symbol: l.symbol } })}>${l.symbol}</b>{l.division && DIVISION[l.division] && l.role !== 'anchor' && <small className="pl-div" data-tip="The Gauntlet division this coin came in from">{DIVISION[l.division]}</small>}<small className={`pl-${l.role}`} data-tip={l.ride ? 'Riding: frozen through rounds until it falls 30% from its high' : undefined}>{l.ride ? '🏇 riding' : l.role === 'anchor' ? '⚓ anchor' : l.role}</small><i data-tip={`${l.stars || 3}★ — ${l.role === 'anchor' ? 'eligible major; protected from stops and advanced on configured re-shapes' : l.role === 'pool' ? 'depth + volume' : 'runner score'}`}>{'★'.repeat(l.stars || 3)}</i>
        <em key={l.pnlPct.toFixed(1)} className={`m-num fl-tick ${l.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{l.pnlPct >= 0 ? '+' : ''}{l.pnlPct.toFixed(1)}%</em></li>)}</ul>
      {c.parked?.length > 0 && <ul className="prime-parked">{c.parked.map(p => <li key={p.pairAddress} data-tip="Stopped out and sold to SOL — the slot is kept; it's bought back when price returns to its entry with momentum">🅿 ${p.symbol} <b className="m-num">${p.usd.toFixed(2)}</b> parked · back at ${Number(p.backAt).toPrecision(3)}</li>)}</ul>}
      <div className="prime-stats"><span data-tip={`Profit = now ${usd(c.valueUsd)} − put in ${usd(putIn)} (fees apart)`}><small>PROFIT</small><b key={c.pnlPct.toFixed(1)} className={`m-num fl-tick ${c.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{usdK(c.valueUsd - putIn)}</b><small className={`ps-pct ${c.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(c.pnlPct)}</small></span>
            <span data-tip="Confirmed SOL already segregated from the card and unavailable to future buys"><small>PAID OUT</small><b className="m-num m-pos">{usdK(c.walletUsd)}</b>{c.pendingPayoutUsd > 0 && <small className="m-dim"> · {usd(c.pendingPayoutUsd)} settling</small>}</span>
        {c.floored ? <span data-tip="Floored: everything moved into the anchor; the card is re-dealt with fresh 3★+ coins (Arena picks first) on the next tick — a new run"><small>FLOORED</small><b className="m-num">re-dealing…</b></span>
        : <RoundBell at={c.nextRoundAt || c.lastRotateAt + d.cfg.rotateHours * 3600} sec={c.bellSec || 10} rest={!!c.resting} label={`ROUND ${(c.rounds || 0) + 2}`} />}</div>
      {/* everything else is one tap away — a tier card fits on screen without scrolling */}
      <details className="prime-more" data-testid={`prime-more-${c.tpl}`}><summary>More · rounds, config, record{c.realBook ? ', real book' : ''}</summary>
      <div className="prime-round" data-tip={`One round = one rotation (every ${d.cfg.rotateHours < 1 ? `${Math.round(d.cfg.rotateHours * 60)} min` : `${d.cfg.rotateHours}h`}). The best card each round is crowned.`}>
        <span><small>ROUND</small><b className="m-num">{(c.rounds || 0) + 1}</b></span>
        <span><small>THIS ROUND</small><b key={(c.roundPct || 0).toFixed(1)} className={`m-num fl-tick ${(c.roundPct || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{(c.roundPct || 0) >= 0 ? '+' : ''}{(c.roundPct || 0).toFixed(1)}%</b></span>
        <span><small>ROUNDS WON</small><b className="m-num">{c.roundWins || 0}</b></span></div>
      <div className="prime-rec" data-testid={`prime-rec-${c.tpl}`}><span data-tip="Of the last logged days (max 10), how many the card was up ≥ +10% over 24h. The goal is 8/10 — the Arena shows the truth, never a promise.">
        <small>GOOD DAYS (+10%)</small><b className="m-num">{c.loggedDays ? `${c.goodDays}/${c.loggedDays}` : '—'}</b></span>
        <span data-tip={`Lowest this run has been. The floor moves everything into the anchor at −${d.cfg.floorPct}%, so −25% is never reached short of a price gap.`}><small>WORST</small><b className={`m-num ${(c.lowPct || 0) < 0 ? 'm-neg' : ''}`}>{(c.lowPct || 0).toFixed(1)}%</b></span>
        {c.floored && <span className="prime-floored" data-tip="Floored: holding the anchor until tomorrow's fresh deal">🛡 FLOORED</span>}</div>
      {c.cfgView && <div className="prime-cfgv" data-tip="This card's live config (changes show here at once)">{[`⏱ ${c.cfgView.clockMin}m`, `⚡ instant −${c.cfgView.instantSwapPct || 0}%`, `⏳ round patience ${c.cfgView.confirm}×`, `🔒 round hold ${c.cfgView.holdMin}m`, `❄ +${c.cfgView.rideAt || 0}% → ⇄ −${c.cfgView.rideTrail || 0}% peak`, `🔄 ${c.cfgView.cycle || 'off'}${c.cycleFix ? ` · fix ${c.cycleFix}` : ''}`, `🧩 /${c.cfgView.reshape}`, `🛑 ${c.cfgView.slMode}`, c.cfgView.locked ? '🔐 locked' : null, c.phase ? `▸ ${c.phase}` : null].filter(Boolean).map(t => <span key={t} className="m-chip">{t}</span>)}</div>}
      {c.realBook && <div className="prime-money" data-testid={`prime-book-${c.tpl}`}><span className="m-label">💵 REAL BOOK · FUNDED {usd(c.realBook.fundedUsd)} · {c.realBook.swaps} SWAPS · NETWORK FEES {usd(c.realBook.feesUsd)}</span>
        <ul className="prime-txs">{c.realBook.orders.slice(0, 5).map((o, i) => <li key={i}><b>{o.side === 'topup' ? '💵' : o.side === 'buy' ? '🟢' : '🔴'}</b><span>{o.side === 'topup' ? 'top-up' : `${o.side} $${o.symbol}`}</span>
          <em className="m-num">{usd(o.usd)}</em>{o.sig ? <a href={txUrl(o.sig)} target="_blank" rel="noreferrer" data-tip="Open the transaction">tx ↗</a> : <i />}</li>)}</ul></div>}
      <CardRecord tpl={c.tpl} />
      </details>
      <div className="prime-acts"><button type="button" className="m-btn" onClick={() => setOpen(open === c.id ? null : c.id)} data-testid={`prime-earn-${c.tpl}`}>🪟 Open card · profit trail</button>
        <button type="button" className="m-btn primary m-go" onClick={() => { onLoad?.(c.legs.map(l => ({ chainId: 'solana', pairAddress: l.pairAddress, symbol: l.symbol, baseAddress: l.mint, runner: l.role === 'runner', role: l.role }))); toast.success(`${c.label} loaded into the Lab — you approve the buy`); }} data-testid={`prime-buy-${c.tpl}`}>⚡ Buy now</button></div>
      {open === c.id && <CardEarnings title={c.label} events={(c.audit || c.events).map(e => ({ ...e, label: e.kind === 'tp' ? ({ ride: '🚀 Ride · house money', bank: '🏦 Banked 75%' }[e.mode] || KIND.tp) : KIND[e.kind] || e.kind }))} taken={c.walletUsd || 0} compounded={c.compoundedUsd}
        book={{ putIn: putIn || 0, held: Math.max(0, (c.valueUsd || 0) - (c.walletUsd || 0)), taken: c.walletUsd || 0, fees: c.feesUsd, rounds: c.rounds }} fees={c.feesUsd} onClose={() => setOpen(null)} paper={!c.real}
        extra={<TrailSummary events={c.audit || c.events} legs={c.legs} />}
        legs={c.legs.map(l => ({ ...l, ...(p => (p > 0 && l.entry ? { now: p, pnlPct: (p / l.entry - 1) * 100, usdNow: l.units * p } : { usdNow: l.usd }))(live.get?.(l.pairAddress)?.price), rundown: l.role === 'anchor' ? 'Protected from stops; the eligible-major basket advances on configured re-shapes, and the floor moves everything here' : `TP +${c.tp}% (momentum decides ride / gain / bank) · stop −${c.sl}% (cut at −${c.sl / 2}% if fading) · rotates when weakest` }))} autos={c.events.filter(e => Date.now() / 1000 - e.at < 86400 && e.kind !== 'deal').map(e => ({ at: e.at, text: `${KIND[e.kind] || e.kind} ${e.symbol ? `$${e.symbol} ` : ''}— ${e.why || ''}`, url: '#' }))} />}
    </article>; })}</div>
  </section>;
}

// HQ › ⚔ Arena: Prime controls — on/off, size, rotation (hours + coins), compound, deal fresh cards.
const PCTL_TABS = [['cards', '🃏 Cards', 'Each paper tier card: its coins (⇄ replace · ❄ freeze · stop mode), cycle, payout, re-deal, lock'],
  ['rules', '⏱ Rounds & safety', 'Clock, rotation, patience, hold, re-shape, rounds per run, floor, rescue, stops, compound, size']];
export function PrimeControls({ call }) {
  const d = usePrime(30000);
  const [cfg, setCfg] = useState(null);
  useEffect(() => { if (d?.cfg && !cfg) setCfg(d.cfg); }, [d, cfg]);
  const [mins, setMins] = useState('');
  const [tab, setTab] = useState('cards');
  useEffect(() => { if (cfg) setMins(String(Math.round(cfg.rotateHours * 60))); }, [cfg]);
  if (!cfg) return null;
  const save = (patch, reset = false) => call('/admin/arena/prime', { method: 'POST', body: JSON.stringify({ cfg: patch, reset }) })
    .then(r => { setCfg(r.cfg); toast.success(reset ? 'Fresh Prime cards dealt' : 'Prime config saved'); }).catch(e => toast.error(e.message));
  // HQ ⇄ one coin / 🃏 one tier — paper cards only, audited server-side.
  const act = (body, msg) => call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(body) }).then(() => { toast.success(msg); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message));
  const seg = (k, vals, fmt) => <div className="m-seg">{vals.map(v => <button key={v} type="button" className={cfg[k] === v ? 'active' : ''} onClick={() => save({ [k]: v })}>{fmt(v)}</button>)}</div>;
  const cyc = cfg.cycles || {};
  const paper = (d?.cards || []).filter(c => !c.real);   // 💵 the real card has its own Edit Fuse — this panel tunes PAPER tier cards only
  return <section className="m-card fops pctl" data-testid="prime-controls"><div className="m-row"><span className="m-label">⭐ ARENA PRIME · PAPER TIER CARDS</span>
    <label className="m-toggle"><input type="checkbox" checked={cfg.on} onChange={e => save({ on: e.target.checked })} /><span>{cfg.on ? 'Running' : 'Off'}</span></label>
    <small className="m-dim">{paper.length} paper cards · {paper.map(c => `${c.label} ${c.pnlPct >= 0 ? '+' : ''}${(c.pnlPct || 0).toFixed(1)}%`).join(' · ') || 'dealing…'}</small></div>
    <div className="m-seg pctl-tabs" role="tablist" aria-label="Prime settings">{PCTL_TABS.map(([k, l, tip]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} data-tip={tip} onClick={() => setTab(k)} data-testid={`pctl-${k}`}>{l}</button>)}</div>
    <div className="pctl-pane" hidden={tab !== 'cards'}>
      <div className="prime-edit pctl-cards">{paper.map(c => <div key={c.id} className="m-row"><b>{c.label}</b>
      {c.legs.map(l => { const next = LEG_MODES[(LEG_MODES.indexOf(l.slMode || '') + 1) % LEG_MODES.length];
        return <span key={l.pairAddress} className={`prime-leg ${l.frozen ? 'is-frozen' : ''}`}>
        <button type="button" className="m-btn" disabled={l.frozen} data-tip={`Replace $${l.symbol} with the best 3★+ ${l.role} not on the card (same $)`} onClick={() => act({ replace: { tpl: c.tpl, pairAddress: l.pairAddress } }, `$${l.symbol} replaced`)} data-testid={`prime-swap-${c.tpl}-${l.pairAddress}`}>⇄ ${l.symbol}</button>
        <button type="button" className={`m-btn ${l.frozen ? 'is-on' : ''}`} aria-pressed={l.frozen} data-tip={l.frozen ? 'Frozen: never rotated or stopped (the floor still protects). Tap to unfreeze.' : 'Freeze: the engine never rotates or stops this coin'} onClick={() => act({ leg: { tpl: c.tpl, pairAddress: l.pairAddress, frozen: !l.frozen } }, l.frozen ? `$${l.symbol} back under the engine` : `❄ $${l.symbol} frozen`)} data-testid={`prime-frz-${c.tpl}-${l.pairAddress}`}>❄</button>
        <button type="button" className="m-btn" data-tip={`At this coin's stop: ${LEG_WORD[l.slMode || '']} — tap for ${LEG_WORD[next]}`} onClick={() => act({ leg: { tpl: c.tpl, pairAddress: l.pairAddress, slMode: next } }, `$${l.symbol} stop: ${LEG_WORD[next]}`)} data-testid={`prime-mode-${c.tpl}-${l.pairAddress}`}>{LEG_WORD[l.slMode || ''].split(' ')[0]}</button></span>; })}
      <button type="button" className="m-btn" onClick={() => act({ redeal: c.tpl }, `${c.label} re-dealt`)} data-testid={`prime-redeal-${c.tpl}`}>🃏 Re-deal</button>
      <button type="button" className={`m-btn ${d?.locks?.[c.tpl] ? 'is-on' : ''}`} aria-pressed={!!d?.locks?.[c.tpl]} onClick={() => act({ lock: c.tpl, on: !d?.locks?.[c.tpl] }, d?.locks?.[c.tpl] ? `${c.label} follows the shared config again` : `🔒 ${c.label} config locked as it is now`)}
        data-tip="Lock this tier's FULL config as it is now (clock, cycle, payout, stops, floor…) — tunes, meta config and the engine never change it" data-testid={`prime-lock-${c.tpl}`}>{d?.locks?.[c.tpl] ? '🔒 Locked' : '🔓 Lock config'}</button>
      <CardEditor c={c} cfg={c.cfgEff || d.cfg} locked={!!d?.locks?.[c.tpl]} real={false} call={call} suggest={d.suggest} /></div>)}</div>
    <div className="prime-cycles" data-testid="prime-cycles"><span className="m-label" data-tip="What each tier deals into every round (same run, P&L continues)">🔄 ROUND CYCLES</span>
      {paper.map(c => <div key={c.tpl} className="m-row"><b>{c.label}</b><span className="m-seg" role="group">{CYCLE_PICKS.map(([m, l, tip]) =>
        <button key={m} type="button" className={(cyc[c.tpl] || 'off') === m ? 'active' : ''} data-tip={tip} onClick={() => save({ cycles: { ...cyc, [c.tpl]: m } })} data-testid={`cycle-${c.tpl}-${m}`}>{l}</button>)}</span>
        <CycleBuilder value={cyc[c.tpl]} onChange={v => save({ cycles: { ...cyc, [c.tpl]: v } })} />
        <span className="m-seg" role="group" data-tip="Share of every profit take paid straight to the owner's wallet — the rest compounds">{[0, 25, 50, 75, 100].map(v =>
          <button key={v} type="button" className={(cfg.payouts || {})[c.tpl] === v ? 'active' : ''} onClick={() => save({ payouts: { ...(cfg.payouts || {}), [c.tpl]: v } })} data-testid={`payout-${c.tpl}-${v}`}>💸{v}%</button>)}</span></div>)}
      <div className="m-row"><b>Compound style</b><span className="m-seg" role="group">{[['smart', '🧲 Smart', 'Gains go to the strongest coins (momentum-weighted), never into fading ones'], ['even', '⚖ Even', 'Gains split evenly across the other coins']].map(([v, l, tip]) =>
        <button key={v} type="button" data-tip={tip} className={(cfg.compoundStyle || 'smart') === v ? 'active' : ''} onClick={() => save({ compoundStyle: v })}>{l}</button>)}</span></div></div>
    </div>
    <div className="pctl-pane" hidden={tab !== 'rules'}><div className="prime-ctl"><span>Size</span>{seg('sizeUsd', [20, 100, 500], v => `$${v}`)}<span data-tip="One clock for every swap: the weakest coins rotate out AND floored cards re-deal — replacements come from the Arena first (battle / stage cards, this round's runners, lit cards), then any 3★+ coin">Rotate every</span>{seg('rotateHours', [5 / 60, 0.25, 0.5, 1], v => (v < 1 ? `${v * 60}m` : `${v}h`))}
      <label className="prime-min" data-tip="Any interval: 15 min – 48 h. The weakest non-anchor coins rotate out on this clock."><input className="m-input m-num" inputMode="numeric" value={mins} onChange={e => setMins(e.target.value.replace(/[^0-9]/g, ''))}
        onBlur={() => Number(mins) >= 15 && Number(mins) !== Math.round(cfg.rotateHours * 60) && save({ rotateHours: Math.min(48, Number(mins) / 60) })} onKeyDown={e => e.key === 'Enter' && e.currentTarget.blur()} data-testid="prime-rotate-min" /><span>min</span></label>{null}
      <span>Coins per rotation</span>{seg('rotateCount', [1, 2, 3], v => `${v}`)}
      <p className="prime-own" data-testid="prime-own-note">🃏 Patience, hold, swap-only-below, freeze, peak trail, TP and stop are EACH CARD'S OWN — set them per card in 🃏 Cards › ⚙ Edit Fuse (no two cards share them).</p>
      <label className="m-toggle" data-tip="🔧 The engine fixes itself from the sim brain: runner weather (strict runners when they're bleeding) + its rotation pick. Never touches your clock."><input type="checkbox" checked={cfg.autoBrain !== false} onChange={e => save({ autoBrain: e.target.checked })} data-testid="prime-autobrain" /><span>🔧 Engine self-fix {cfg.strictRunners ? '· 🌧 strict runners ON' : ''}</span></label>
      <span data-tip="🛟 When a card falls this far under what it started with, it switches to the rescue cycle (safest run ⇄ breakeven runners)">Rescue at</span>{seg('rescuePct', [30, 40, 50, 60], v => `−${v}%`)}
      <span data-tip="How often a cycling card re-shapes. Every re-shape sells + re-buys coins — every 6 rounds on 5-min rounds = every 30 min">Re-shape every</span>{seg('cycleEvery', [1, 3, 6, 12], v => `${v} rnd`)}
      <span data-tip="Rounds per run: when they're done the run closes on the record (its %) and the next run starts from there. ∞ = one endless run. Every round opens with a 10s countdown.">Rounds per run</span>{seg('roundsPerRun', [0, 5, 10, 20, 50], v => (v ? `${v}` : '∞'))}
      <span data-tip="Card-level floor: at this loss every pool + runner moves into the anchor, then the card is re-dealt as a new run">Floor</span>{seg('floorPct', [10, 15, 20, 25], v => `−${v}%`)}
      <label className="m-toggle"><input type="checkbox" checked={cfg.compound} onChange={e => save({ compound: e.target.checked })} /><span>Auto-compound gains</span></label>
      <label className="m-toggle" data-tip="A coin that ran +50% is sold before it gives it all back (≤ +5% left) — winners never turn into losers"><input type="checkbox" checked={cfg.trail !== false} onChange={e => save({ trail: e.target.checked })} data-testid="prime-trail" /><span>🔒 Lock +50% runs</span></label>
      <span data-tip="What a stop does: ⇄ swap the coin for the best gated one · 🅿 sell to SOL, keep the slot, buy back at entry with momentum · ❄ never sell on a stop (the floor still protects)">On stop</span>{seg('slMode', ['replace', 'park', 'hold'], v => ({ replace: '⇄ Replace', park: '🅿 Park & rebuy', hold: '❄ Hold' }[v]))}</div>
    
    </div>
    <div className="pctl-pane pctl-foot"><div className="m-row"><button type="button" className="m-btn primary m-go" onClick={() => save(PRIME_META)} data-testid="prime-meta" data-tip="Hourly rotation of 1 coin · −15% floor · compound on · park & rebuy on stops">⚡ Apply meta config</button>
      <small className="m-dim">the config the Arena proof backs right now — tweak anything after</small></div>
    <div className="m-row"><button type="button" className="m-btn" onClick={() => save({}, true)} data-testid="prime-reset">🃏 Deal fresh Prime cards</button>
      <small className="m-dim">{paper.map(c => `${c.label} ${c.pnlPct >= 0 ? '+' : ''}${c.pnlPct.toFixed(1)}%`).join(' · ') || 'dealing…'}</small></div></div></section>;
}

// ⭐ Profile showcase: FEELESS's tier cards (real or paper, live), each with its profit, rounds won and a tap to the Arena —
// shown beside the wallet's own Fuse cards so every profile shows what the top cards are doing.
export function PrimeShowcase() {
  const d = usePrime(60000);
  if (!d?.cards?.length) return null;
  const go = () => { window.location.href = '/terminal/fuse?tab=arena'; };
  return <section className="m-card wp-prime" data-testid="prime-showcase"><span className="m-label">⭐ FEELESS TIER CARDS · LIVE{d.cards.some(c => c.real) ? ' · 💵 REAL MONEY ON' : ''}</span>
    <div className="wp-prime-row">{[...d.cards].sort((a, b) => b.pnlPct - a.pnlPct).map(c => <button key={c.id} type="button" className="wp-prime-card" onClick={go} data-tip={c.why} data-testid={`wp-prime-${c.tpl}`}>
      <small>{(TIER[c.tier] || TIER.gold).name} · {c.real ? '💵 REAL' : '📄 PAPER'}</small><b>{c.label}</b>
      <em className={`m-num ${c.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{c.pnlPct >= 0 ? '+' : ''}{c.pnlPct.toFixed(1)}%</em>
      <small>{usd(c.valueUsd - c.startUsd)} profit · 🏆 {c.roundWins || 0} rounds won · {c.legs.length} coins</small></button>)}</div></section>;
}

// 💵 Creator / HQ wallets: FEELESS's REAL-money tier cards right in Fuse › My cards — live card, real book, every swap with its tx.

// ⚙ Edit a REAL tier card's configs in place (owner). Engine settings save to the tier engine; a locked tier is re-locked with them.
const EDIT = [
  ['rotateHours', '⏱ Round clock', [[0.08, '5m'], [0.25, '15m'], [0.5, '30m'], [1, '1h'], [2, '2h']], 'How long each round lasts'],
  ['instantSwapPct', '⚡ Instant swap at', [[0, 'off'], [5, '−5%'], [10, '−10%'], [15, '−15%'], [20, '−20%']], 'Immediate live-loss trigger. Once the coin reaches this loss, it exits now — no round, patience or minimum-hold wait.'],
  ['rotateConfirm', '⏳ Round patience', [[1, '1'], [2, '2'], [3, '3'], [4, '4']], 'Only for scheduled round rotation. It does NOT delay the instant-loss trigger. OFF = a coin can be rotated out on the very next round (most churn — your choice).'],
  ['rotateMinDrop', '📉 Round swap only below', [[0, 'any'], [5, '−5%'], [10, '−10%'], [15, '−15%'], [20, '−20%']], 'For scheduled round rotation, require the coin to be this far below its entry.'],
  ['minHoldMins', '🔒 Round min hold', [[0, 'off'], [10, '10m'], [15, '15m'], [30, '30m'], [60, '1h'], [120, '2h']], 'Only for scheduled round rotation. It does NOT delay the instant-loss trigger. OFF = a coin can be rotated out on the very next round (most churn — your choice).'],
  ['keepWinPct', '🛡 Keep winners', [[0, 'off'], [5, '+5%'], [10, '+10%'], [20, '+20%']], 'A coin up this much (or ❄ frozen) is carried into the next shape — a re-shape never sells a winner'],
  ['rideAt', '❄ Freeze a coin running', [[0, 'off'], [10, '+10%'], [15, '+15%'], [20, '+20%'], [25, '+25%'], [50, '+50%'], [100, '+100%'], [150, '+150%']], 'A coin up this much is frozen: no TP, stop or rotation while it keeps making highs. It still leaves if it gives back half the freeze (e.g. frozen at +20% → out under +10%) — so a small freeze locks a small win'],
  ['rideTrail', '⇄ Then swap it off its peak', [[5, '−5%'], [8, '−8%'], [10, '−10%'], [15, '−15%'], [20, '−20%'], [30, '−30%']], 'A frozen coin is swapped for the best coin of its kind once it falls this far from its highest price (the gain moves into the new coin)'],
  ['tp', '🎯 Card take-profit', [[0, 'tier'], [25, '+25%'], [50, '+50%'], [100, '+100%'], [200, '+200%'], [300, '+300%']], "Every coin's take-profit on this card (a coin's own TP still wins). Tier = the tier's built-in TP"],
  ['sl', '🛑 Card stop', [[0, 'tier'], [10, '−10%'], [15, '−15%'], [20, '−20%'], [30, '−30%']], "Every coin's stop on this card (a coin's own stop still wins). Tier = the tier's built-in stop"],
  ['trenchCoins', '🗑 Trench coins per card', [[1, '1'], [2, '2']], 'How many fresh trench breakouts the 🗑 trench cycle may hold at once. They are the riskiest coins on the site — 2 is the hard max.'],
  ['coins', '🪙 Coins on the card', [[0, 'auto'], [2, '2'], [3, '3'], [4, '4'], [5, '5'], [6, '6']], 'Your call, at any card size. Auto = sized to the card (each coin at least $0.75). Pick a number and the card holds exactly that many — smaller coins pay more in fees per swap, and the first 5 rounds of network fees are on the wallet reserve.'],
  ['cycleEvery', '🧩 Re-shape every', [[0, 'off'], [3, '3'], [6, '6'], [12, '12']], 'Rounds between shape changes'],
  ['slMode', '🛑 On a stop', [['replace', '⇄ replace'], ['park', '🅿 park'], ['hold', '❄ hold']], 'Replace with the best coin · sell to SOL and rebuy later · keep holding'],
  ['rescuePct', '🛟 Rescue at', [[0, 'off'], [30, '−30%'], [40, '−40%'], [50, '−50%'], [60, '−60%']], 'On: card this far under its start → safest coins, and a −40% day re-deals into majors. Off: NO fix of any kind — your coins and config stay, only your floor protects the card'],
  ['floorPct', '🧱 Card floor', [[15, '−15%'], [25, '−25%'], [40, '−40%'], [60, '−60%']], 'The WHOLE card this far under its run start → every coin is sold into the anchors, then fresh coins are dealt. This is the card, not one coin: per-coin exits are ⚡ Instant swap above. A tight floor on a small card trips on one bad coin.'],
  ['floorRestMins', '🛌 Rest after floor', [[0, 'off'], [15, '15m'], [30, '30m'], [60, '1h']], 'Off = fresh coins are dealt right after a floor. On = the card sits in its anchors this long first (no swaps while it rests).'],
  ['skimAt', '💰 Auto-skim profit', [[0, 'off'], [10, '+10%'], [20, '+20%'], [30, '+30%'], [50, '+50%'], [100, '+100%']], 'Each time a coin gains this much (since you bought it, or since its last skim) ONLY its profit is sold — what you put into it keeps riding. Off = you take profit yourself with 💰 on the coin.'],
  ['skimTo', '💰 Skimmed profit goes', [['card', '♻ into my other coins'], ['cash', '🏦 held as cash']], 'Into my other coins = it is spread over the rest of the card (helps the ones that are down). Held as cash = it waits as card cash for you to withdraw — for example to set tax money aside. It is never put back into coins by itself.'],
  ['recyclePct', '♻ Recycle profit into the card', [[0, 'off'], [50, '50%'], [70, '70%'], [100, '100%']], 'Every few rounds, this share of each coin\'s PROFIT is sold and spread over the card\'s other coins — the ones under an equal share get the most. What you put into a coin and the rest of its profit stay in it. A coin that is down is never sold for this. Nothing leaves the card.'],
  ['recycleEvery', '♻ Recycle every', [[1, '1'], [2, '2'], [3, '3'], [4, '4'], [6, '6'], [12, '12 rounds']], 'How often the profit recycle runs (only when ♻ Recycle profit is on). On 5-minute rounds, 6 rounds = every 30 minutes.'],
  ['peakSellPct', '🏔 Off its peak', [[25, 'sell 25% of profit'], [50, 'sell 50% of profit'], [75, 'sell 75% of profit'], [100, 'swap the coin']], 'A locked coin that falls your trail % from its peak. Sell part of its PROFIT and let it keep riding (the trail starts again from there) — or swap the whole coin for a new one. If it falls under half your freeze level the ride is over either way.'],
  ['lockBankPct', '🏦 Bank at the lock', [[0, 'off'], [25, '25%'], [33, '33%'], [50, '50%']], 'When a coin hits your ❄ freeze level it locks and rides. This sells part of it right then and spreads that money over your other coins — so a winner that comes all the way back still paid. The rest keeps riding until it falls off its peak.'],
  ['swapEdge', '⚖ Stay or swap', [[true, 'on'], [false, 'off']], 'On: at the bell a losing coin is swapped only when the next coin is beating SOL over the last hour AND beats this coin by more than the swap costs (fees + spread + impact, +1%). Otherwise it stays — its stop still protects it. Off: every patient loser is swapped.'],
  ['swapCapHr', '🤖 Swaps an hour', [[0, 'auto'], [2, '2'], [4, '4'], [6, '6'], [8, '8'], [12, '12'], [-1, 'no cap']], 'How many engine rotations (round swaps + trench fills) this card may make in an hour. Auto = tuned from what one swap costs on a card this size, so churn stays under 2% of the card an hour. Stops, instant swaps, rides and your own picks are never capped.'],
  ['autoBrain', '🧠 Auto-tune', [[true, 'on'], [false, 'off']], 'Let the sim brain adjust patience / drop (never below 3 on 5m rounds)'],
];
const TIER_KEYS = ['rideAt', 'rideTrail', 'rotateMinDrop', 'rotateConfirm', 'minHoldMins', 'instantSwapPct', 'tp', 'sl', 'trenchCoins'];   // = arena_prime.TIER_KEYS
const CYCLES = [['trench', '🗑 trench'], ['safe', '🛡 safe'], ['classic', 'classic'], ['adaptive', 'adaptive'], ['press', '🔥 press'], ['rescue', '🛟 rescue'], ['auto', '🤖 auto'], ['off', 'off']];
// ⚙ Edit Fuse groups: [key, tab label, what lives there]
const CFG_GROUPS = [['rounds', '⏱ Rounds', 'When a round may swap a coin'], ['exits', '⚡ Exits', 'Per-coin: instant swap, stops, winners, riders'],
  ['shape', '🧬 Shape', 'Which mix of coins the card holds'], ['safety', '🧱 Safety', 'Whole-card floor, rest, rescue, auto-tune'], ['limits', '💵 Limits', 'Hard caps on every real swap']];

// ✍ Type exact limits (server clamps every value to its safe range: slippage 0.1–3%, impact 0.2–10%, pool ≥ $0, swap $1+, daily $5+)
const TYPED = [['slippageBps', 'Slippage %', v => v * 100, v => v / 100, 0.1, 3, 0.1], ['maxImpactPct', 'Max price impact %', v => v, v => v, 0.2, 10, 0.1],
  ['minLiqUsd', 'Min pool $', v => v, v => v, 0, 10000000, 1000], ['arenaMinLiqUsd', 'Arena coin min pool $', v => v, v => v, 0, 10000000, 1000], ['pickMinLiqUsd', 'My own pick min pool $', v => v, v => v, 5000, 10000000, 1000], ['pickSellBackPct', 'My own pick: max sell-back loss %', v => v, v => v, 6, 10, 0.5], ['maxSwapUsd', 'Max per swap $', v => v, v => v, 1, 10000, 1],
  ['dailyUsd', 'Daily cap $', v => v, v => v, 5, 100000, 5], ['minOrderUsd', 'Min buy $', v => v, v => v, 0.1, 50, 0.05]];
function TypedLimits({ keeper, busy, save }) {
  const [v, setV] = useState({});
  const cur = k => { const t = TYPED.find(x => x[0] === k); return keeper?.[k] == null ? '' : t[3](keeper[k]); };
  const dirty = Object.keys(v).filter(k => v[k] !== '' && Number(v[k]) !== Number(cur(k)));
  const go = () => save(Object.fromEntries(dirty.map(k => [k, TYPED.find(x => x[0] === k)[2](Number(v[k]))])), true).then(() => setV({}));
  return <div className="ce-typed" data-testid="typed-limits">{TYPED.map(([k, l, , , lo, hi, st]) => <label key={k} data-tip={`${lo} – ${hi}`}><small>{l}</small>
    <input className="m-input" type="number" min={lo} max={hi} step={st} placeholder={String(cur(k))} value={v[k] ?? ''} onChange={e => setV(x => ({ ...x, [k]: e.target.value }))} /></label>)}
    <button type="button" className="m-btn m-go" disabled={busy || !dirty.length} onClick={go}>Save {dirty.length || ''} limit{dirty.length === 1 ? '' : 's'}</button></div>;
}

// 🧠 The sim brain's pick for THIS card's round length (300 sim cards on real recorded prices, re-run every ~15 min).
// It never claims profit: when the typical card on this clock lost, it says so and points at the clock that did best.
export function enginePick(suggest, rotateHours) {
  const rows = Object.entries(suggest || {}).map(([k, v]) => ({ clock: Number(k), ...v }));
  if (!rows.length) return null;
  const mine = rows.reduce((a, b) => (Math.abs(b.clock - rotateHours * 60) < Math.abs(a.clock - rotateHours * 60) ? b : a));
  const top = rows.reduce((a, b) => ((b.medPct ?? -1e9) > (a.medPct ?? -1e9) ? b : a));
  const patch = {}; if (mine.cfg?.minDrop != null) patch.rotateMinDrop = Number(mine.cfg.minDrop); if (mine.cfg?.confirm != null) patch.rotateConfirm = Number(mine.cfg.confirm);
  return { mine, top, patch };
}

function EnginePick({ suggest, cfg, busy, save }) {
  const p = enginePick(suggest, cfg?.rotateHours || 1);
  if (!p) return null;
  const { mine, top, patch } = p; const same = Object.entries(patch).every(([k, v]) => Number(cfg?.[k]) === v);
  const clk = m => (m >= 60 ? `${m / 60}h` : `${m}m`);
  return <p className={`m-note ${mine.profitable ? '' : 'warn'} ce-pick`} data-testid="engine-pick"><b>🧠 ENGINE PICK · {clk(mine.clock)} ROUNDS</b>
    <span>Swap only below −{patch.rotateMinDrop ?? '—'}% · patience {patch.rotateConfirm ?? '—'} rounds · TP +{mine.cfg?.tp}% · SL −{mine.cfg?.sl}% — typical sim card <b className={`m-num ${mine.medPct >= 0 ? 'm-pos' : 'm-neg'}`}>{mine.medPct >= 0 ? '+' : ''}{Number(mine.medPct).toFixed(1)}%</b> over {mine.n} sims, {mine.upPct}% ended up.
      {!mine.profitable && ` Not profitable right now — this is the least-bad setup for ${clk(mine.clock)} rounds.`}{top.clock !== mine.clock && ` Best clock in the same sims: ${clk(top.clock)} (${top.medPct >= 0 ? '+' : ''}${Number(top.medPct).toFixed(1)}%).`}</span>
    {!same && Object.keys(patch).length > 0 && <button type="button" className="m-btn" disabled={busy} onClick={() => save(patch)} data-testid="engine-pick-apply">Apply this pick</button>}</p>;
}

// 🗑 What the trench scan sees right now: every finalist with its holders, market cap and each check it passed or failed.
const TRENCH_FIELDS = [['minHolders', 'Holders ≥', v => v, 'How many wallets must hold the coin (counted on-chain)'], ['minTxns1h', 'Trades / h ≥', v => v, 'Trades in the last hour — a real crowd, not two wallets'],
  ['minVol1h', '1h volume ≥', v => `$${v / 1000}K`, 'Dollar volume in the last hour'], ['minMcap', 'Market cap from', v => `$${v / 1000}K`, 'It must have broken this market cap'],
  ['maxMcap', 'Market cap up to', v => v >= 1e6 ? `$${v / 1e6}M` : `$${v / 1000}K`, 'Above this it is no longer a fresh breakout'], ['maxAgeH', 'Age up to', v => `${v}h`, 'How old the launch may be']];

const FLOW_WORD = { done: ['✓', 'done'], failed: ['✕', 'refused'], sending: ['⏳', 'sending'], next: ['·', 'next'] };

/* 👁 A swap, one transaction at a time: SELL (confirmed) → BUY (sending) → next. Only the chain turns a step green. */
export function SwapFlow({ k }) {
  const f = (k && k.flow) || [];
  if (!f.length && !k?.holdingSell) return null;
  return <ol className="hrt-flow" data-testid="swap-flow" aria-label="Swap in progress">
    {k.holdingSell && <li className="is-hold" data-tip="The new coin failed a buy check, so the old coin was NOT sold. The engine is picking the next best coin (about 15 seconds).">🔒 old coin kept — new coin not buyable, re-picking</li>}
    {f.map((s, i) => { const w = FLOW_WORD[s.state] || FLOW_WORD.next;
      return <li key={`${s.side}${s.symbol}${i}`} className={`is-${s.state}`} style={{ '--i': i }} data-tip={s.err || (s.state === 'done' ? 'Confirmed on-chain' : s.state === 'sending' ? 'Signed and sent — waiting for the chain' : 'Runs after the step before it confirms')}>
        <i>{i + 1}</i><b>{s.side === 'sell' ? 'SELL' : s.side === 'swap' ? '🔀 SWAP' : 'BUY'} ${s.symbol}</b><span className="m-num">{usd(s.usd)}</span><em>{w[0]} {w[1]}</em></li>; })}</ol>;
}

export function TrenchScan({ call, bare, onSaved }) {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState('');   // 👁 a meta being looked at (read-only; the cards follow HQ's saved setting)
  const load = useCallback(() => fetch(apiUrl(`/api/reputation/fuses/trench${view ? `?meta=${view}` : ''}`)).then(r => r.json()).then(setD).catch(() => {}), [view]);
  useEffect(() => { let alive = true; const go = () => alive && load();
    go(); const t = setInterval(() => !document.hidden && go(), 30000); return () => { alive = false; clearInterval(t); }; }, [load]);
  if (!d) return <div className="tscan is-ghost" />;
  const own = d.cfg || { mode: 'auto' }; const mine = own.mode === 'own'; const onMeta = own.mode === 'meta' ? own.meta : '';
  const metaName = k => ((d.metas || []).find(m => m.key === k) || {}).label || k;
  const save = async patch => { if (!call) return; setBusy(true);
    try { await call('/admin/arena/prime', { method: 'POST', body: JSON.stringify({ trenchCfg: { ...own, ...patch } }) }); toast.success('Trench settings saved — the list is re-judged now, a fresh scan follows (≤ 2 min)'); await load(); onSaved?.(); }
    catch (e) { toast.error(e.message || 'Could not save'); } finally { setBusy(false); } };
  return <div className="tscan" data-testid="trench-scan"><span className="m-label">🗑 TRENCH SCAN · {d.pass || 0} PASS NOW{d.view ? ` · 👁 VIEWING ${metaName(d.view)}` : mine ? ' · 🎛 YOUR SETTINGS' : onMeta ? ` · 🧪 ${metaName(onMeta)}` : Number(d.level) > 0 ? ` · 🔧 WIDENED ×${d.level}` : ''}</span>
    {(d.metas || []).length > 0 && <div className="tscan-metas" role="group" aria-label="Trench metas" data-testid="trench-metas">{d.metas.map(m => { const on = call ? onMeta === m.key : view === m.key;
      return <button key={m.key} type="button" disabled={busy} className={`tscan-meta ${on ? 'on' : ''} ${m.pass ? 'has' : ''}`} aria-pressed={on} data-testid={`trench-meta-${m.key}`}
        data-tip={`${m.blurb}. ≤ ${m.cfg.maxAgeH}h old · $${m.cfg.minMcap / 1000}K–$${m.cfg.maxMcap >= 1e6 ? `${m.cfg.maxMcap / 1e6}M` : `${m.cfg.maxMcap / 1000}K`} cap · ≥ ${m.cfg.minHolders} holders · ≥ ${m.cfg.minTxns1h} trades/h · ≥ $${m.cfg.minVol1h / 1000}K 1h volume. Safety checks are the same in every meta.${m.proof?.n ? ` 📈 Paper record: ${m.proof.n} coins it passed, held 1 hour — typical ${m.proof.medPct >= 0 ? '+' : ''}${m.proof.medPct}%, ${m.proof.wonPct}% ended up (a vanished coin counts as −100%). A record, never a promise.` : ' 📈 No paper record yet — it builds as coins pass.'}${call ? ' Tap = your trench slots hunt this way.' : ' Tap = see what it finds right now.'}`}
        onClick={() => (call ? save({ mode: 'meta', meta: m.key }) : setView(v => (v === m.key ? '' : m.key)))}><b>{m.label}</b><i className="m-num">{m.pass}</i>{m.proof?.n >= 5 && <u className={m.proof.medPct > 0 ? 'm-pos' : 'm-neg'} data-testid={`trench-proof-${m.key}`}>{m.proof.proven ? '✅ ' : ''}{m.proof.medPct >= 0 ? '+' : ''}{m.proof.medPct}%</u>}</button>; })}</div>}
    {call && <div className="tscan-cfg" data-testid="trench-cfg">
      <div className="m-seg" role="group" aria-label="Trench settings">
        <button type="button" disabled={busy} className={!mine && !onMeta ? 'on' : ''} data-testid="trench-auto" data-tip="The engine tunes it: strict first; when nothing passes it loosens crowd / trades / volume / cap band / age one step at a time (max 3) and tightens again when coins pass" onClick={() => save({ mode: 'auto' })}>🤖 Engine tunes</button>
        <button type="button" disabled={busy} className={mine ? 'on' : ''} data-testid="trench-own" data-tip="Your own numbers for crowd, trades, volume, market cap and age. The safety checks (top-10, snipers, dev, creator, mint + freeze, buyers, green candles) are never options" onClick={() => save({ mode: 'own' })}>🎛 My settings</button></div>
      {mine && <div className="tscan-own">{TRENCH_FIELDS.map(([key, name, fmt, tip]) => <label key={key} data-tip={tip}><small>{name}</small>
        <select className="m-input" disabled={busy} value={own[key]} data-testid={`trench-${key}`} aria-label={name} onChange={e => save({ [key]: Number(e.target.value) })}>
          {((d.options || {})[key] || []).map(o => <option key={o} value={o}>{fmt(o)}</option>)}</select></label>)}</div>}</div>}
    {!bare && <><small className="m-dim">{d.rules}</small>
    {!d.pass && (d.funnel || []).length > 0 && <small className="m-dim tscan-why" data-testid="trench-why">🔎 Why nothing passed ({d.seen} coins checked): {d.funnel.slice(0, 5).map(f => `${f.n}× ${f.why}`).join(' · ')}</small>}
    {!(d.checked || []).length ? <small className="m-dim">No fresh coin is breaking out with a real crowd right now — the trench slots stay normal runners until one does.</small>
      : <ul>{d.checked.map((r, i) => <li key={r.mint} className={r.ok ? 'is-ok' : 'is-out'} style={{ '--i': i }}><b>{r.ok ? '✅' : '❌'} ${r.symbol}</b>
        <span className="m-num">{r.holders ?? '—'} holders · ${Math.round((r.mcap || 0) / 1000)}K mc · {r.ageH != null ? `${Number(r.ageH).toFixed(1)}h` : '—'}</span>
        <small>{r.ok ? (r.trenchWhy || []).map(p => p.why).join(' · ') : (r.fails || []).join(' · ')}</small></li>)}</ul>}</>}</div>;
}

function CardEditor({ c, cfg, keeper, locked, call, real, suggest }) {
  const [busy, setBusy] = useState(false);
  const save = async (patch, wallet) => {
    setBusy(true);
    try {
      if (wallet) await call('/admin/fuse-wallet/cfg', { method: 'POST', body: JSON.stringify(patch) });
      else {
        // a locked tier edits ONLY its own frozen config; an unlocked one edits the shared engine config
        // 💵 the real card edits ITS OWN config (paper untouched); a locked paper tier its frozen config; else the shared paper config
        await call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(real ? { realCfg: patch } : locked ? { lock: c.tpl, patch } : { cfg: patch }) });
      }
      toast.success('Saved — applies from the next tick'); window.dispatchEvent(new Event('feeless:prime'));
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  // one setting = one line: what it is + what it does on the left, the choices on the right. One group on screen at a time.
  const seg = (key, label, opts, tip, cur, wallet, to) => <div key={key} className="ce-row"><span><b>{label}</b><small>{tip}</small></span>
    <div className="m-seg">{opts.map(([v, t]) => <button key={String(v)} type="button" disabled={busy} className={String(cur) === String(v) ? 'active' : ''} aria-pressed={String(cur) === String(v)} onClick={() => (to ? to({ [key]: v }) : save({ [key]: v }, wallet))}>{t}</button>)}</div></div>;
  // ⏱ a paper tier that isn't locked saves ITS OWN clock (`clocks[tier]`); the real card and locked tiers save their own rotateHours
  const ownClock = !real && !locked;
  const row = ([k, l, o, t]) => (k === 'rotateHours' && ownClock
    ? <div key={k} className="ce-row"><span><b>{l} · this tier</b><small>Every tier plays its own round length — this sets {c.label} only.</small></span>
      <div className="m-seg">{o.map(([v, txt]) => <button key={String(v)} type="button" disabled={busy} className={Math.abs(v - (cfg?.rotateHours || 0)) < 0.02 ? 'active' : ''} onClick={() => save({ clocks: { ...(cfg?.clocks || {}), [c.tpl]: v } })}>{txt}</button>)}</div></div>
    : seg(k, l, o, t, k === 'rotateHours' ? (o.find(x => Math.abs(x[0] - (cfg?.[k] || 0)) < 0.02) || [cfg?.[k]])[0] : cfg?.[k]));
  const own = !real && !locked;   // 🃏 an unlocked paper tier keeps ITS OWN exits (unique per card); the shared config stays for the rest
  const saveExit = patch => (own ? save({ tierCfg: { [c.tpl]: patch } }) : save(patch));
  const rowX = e => (own && TIER_KEYS.includes(e[0]) ? seg(e[0], `${e[1]} · this card`, e[2], e[3], cfg?.[e[0]], false, saveExit) : row(e));
  const rows = keys => keys.map(k => EDIT.find(e => e[0] === k)).filter(Boolean).map(rowX);
  const churn = (cfg?.rotateHours || 1) < 0.25 && (cfg?.rotateConfirm || 1) < 3;   // 5-min rounds + low patience = swaps on noise (fees, missed buys)
  const [grp, setGrp] = useState('rounds');
  return <details className="hrt-edit" data-testid="card-editor"><summary>⚙ Edit Fuse {real ? '· 💵 real-money config — paper cards untouched' : locked ? '· 🔒 locked — edits change only this Fuse' : '· this card\'s own exits, patience + hold · shape is shared'}</summary>
    <div className="m-seg ce-tabs" role="tablist" aria-label="Config groups">{CFG_GROUPS.map(([k, l, tip]) => <button key={k} type="button" role="tab" aria-selected={grp === k} className={grp === k ? 'active' : ''} data-tip={tip} onClick={() => setGrp(k)} data-testid={`ce-tab-${k}`}>{l}</button>)}</div>
    <div className="ce-group" key={grp} data-testid={`ce-pane-${grp}`}>
      {grp === 'rounds' && <>{rows(['rotateHours', 'rotateConfirm', 'rotateMinDrop', 'minHoldMins', 'swapEdge', 'swapCapHr'])}
        {c.swapCap && <p className="m-note" data-testid="swap-cap-why">{c.swapCap.why} · used {c.swapCap.used || 0}{c.swapCap.cap ? ` of ${c.swapCap.cap}` : ''} this hour</p>}
        <EnginePick suggest={suggest} cfg={cfg} busy={busy} save={save} />
        {churn && <p className="m-note ce-warn" data-testid="churn-warn">⚠ Round rotation is aggressive at {Math.round((cfg?.rotateHours || 0) * 60)}m with patience {cfg?.rotateConfirm || 1}. The ⚡ instant swap (Exits) is separate and fires immediately at its loss.
          <button type="button" className="m-btn" disabled={busy} onClick={() => save({ rotateConfirm: 3 })}>Use 3</button></p>}</>}
      {grp === 'exits' && <><StrategyPicks hours={cfg?.rotateHours || 1} current={cfg} busy={busy} onApply={s => saveExit(stratPatch(s.cfg))} testid={`strats-${c.tpl}`} />
        {rows(['rideAt', 'rideTrail', 'peakSellPct', 'lockBankPct', 'skimAt', 'skimTo', 'recyclePct', 'recycleEvery', 'tp', 'sl', 'instantSwapPct', 'slMode', 'keepWinPct'])}</>}
      {grp === 'shape' && <>{rows(['coins', 'cycleEvery', 'trenchCoins'])}
        {(cfg?.cycles || {})[c.tpl] === 'trench' && <TrenchScan call={call} />}
        <div className="ce-row"><span><b>🔄 Cycle</b><small>The shapes this card moves through (anchor · mixed · degen · safest …)</small></span><div className="m-seg">{CYCLES.map(([v, t]) => <button key={v} type="button" disabled={busy} className={(cfg?.cycles || {})[c.tpl] === v ? 'active' : ''} onClick={() => save({ cycles: { ...(cfg?.cycles || {}), [c.tpl]: v } })}>{t}</button>)}</div></div>
      {!real && <div className="ce-row"><span><b>🔒 Lock tier</b><small>Freeze this tier's whole config so engine tunes never change it</small></span><div className="m-seg">{[[true, 'locked'], [false, 'free']].map(([v, t]) => <button key={t} type="button" disabled={busy} className={!!locked === v ? 'active' : ''} onClick={() => { setBusy(true); call('/admin/arena/prime', { method: 'POST', body: JSON.stringify({ lock: c.tpl, on: v }) }).then(() => { toast.success(v ? '🔒 Locked' : 'Unlocked'); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)).finally(() => setBusy(false)); }}>{t}</button>)}</div></div>}</>}
      {grp === 'safety' && rows(['floorPct', 'floorRestMins', 'rescuePct', 'autoBrain'])}
      {grp === 'limits' && <TypedLimits keeper={keeper} busy={busy} save={save} />}
    </div>
    <small className="m-dim">{real ? 'This real card runs its own config — HQ, engine tunes and paper edits never change it.' : 'Clock, exits, patience and hold are this card\'s own (no two cards share them); shape, floor and safety are shared by every paper tier that isn\'t 🔒 locked.'} Limits cover every real buy and sell.</small></details>;
}

const SHAPE = { anchor: ['⚓', 'anchor', '3 majors + a new major'], mixed: ['⚖', 'mixed', '2 majors + a new major + a runner'], degen: ['🔥', 'degen', '1 major + 3 runners'],
  safest: ['🛡', 'safest', '3 majors + 1 new major'], breakeven: ['♻', 'breakeven', '1 busy pool + 3 busy runners'], trench: ['🗑', 'trench', '1 major + 1 pool + 1–2 trench breakouts'] };
// 🔄 NOW → NEXT shape (server `cyclePeek`, same rules as the engine) + the card's vitals at a glance
export function CycleStrip({ c }) {
  const p = c.cyclePeek || {}; const sh = k => SHAPE[k] || ['·', k || '—', ''];
  const legs = (c.legs || []).filter(l => l.symbol !== 'SOL' && l.costUsd > 0);
  const best = legs.reduce((a, l) => (!a || l.pnlPct > a.pnlPct ? l : a), null); const worst = legs.reduce((a, l) => (!a || l.pnlPct < a.pnlPct ? l : a), null);
  const riding = (c.legs || []).filter(l => l.ride).length;
  return <div className="hrt-cycle m-live" data-testid="cycle-strip">
    <span className="hrt-shape is-now" data-tip={sh(p.now)[2]}><small>NOW</small><b>{sh(p.now)[0]} {sh(p.now)[1]}</b></span>
    <span className="hrt-arrow" aria-hidden>→</span>
    <span className="hrt-shape" data-tip={p.next ? `${sh(p.next)[2]}${['adaptive', 'auto'].includes(p.mode) ? ' — picked by how the next round moves' : ''}` : 'This card does not cycle'}><small>{p.next ? `NEXT · IN ${p.inRounds} RND` : 'NEXT'}</small><b>{p.next ? `${sh(p.next)[0]} ${sh(p.next)[1]}` : '➡ steady'}</b></span>
    <span className="hrt-mode m-chip" data-tip={p.fix ? `Auto ${p.fix} fix is on — pick a cycle in ⚙ Edit Fuse to override` : 'The cycle this card runs'}>🔄 {p.mode || 'off'}{p.fix ? ' · fix' : ''}</span>
    <span className="hrt-vital" data-tip="Best coin on the card now"><small>BEST</small><b className="m-pos">{best ? `$${best.symbol} ${pct(best.pnlPct)}` : '—'}</b></span>
    <span className="hrt-vital" data-tip="Weakest coin on the card now"><small>WORST</small><b className={worst && worst.pnlPct < 0 ? 'm-neg' : ''}>{worst ? `$${worst.symbol} ${pct(worst.pnlPct)}` : '—'}</b></span>
    <span className="hrt-vital" data-tip="Coins frozen while they run (swapped once they fall off their peak)"><small>RIDING</small><b>❄ {riding}</b></span>
    <span className="hrt-vital" data-tip="Network fees this card paid — kept apart from P&L. HQ / creator wallets pay 0 FEELESS fee; only the network (Solana) is paid"><small>🧾 FEES</small><b>{usd(c.realBook?.feesUsd ?? c.feesUsd ?? 0)}</b></span></div>;
}

// ⛽ gas tank + 📶 landing rate: the two things that decide whether a real buy lands (server `fuse_wallet.gas_tank` / `landing`)
export function RealHealth({ k }) {
  const g = k?.gas; const L = k?.landing || {};
  const gasPct = g ? Math.min(100, (g.sol / Math.max(g.reserve || 0.03, 0.001)) * 100) : 0;
  const land = L.pct == null ? null : L.pct;
  return <div className="hrt-health" data-testid="real-health">
    <div className={`hrt-gauge is-${g?.state || 'na'}`} data-tip={g ? `${g.sol.toFixed(4)} SOL free for network fees + new-coin rent (keep ≥ ${g.reserve} SOL). Enough rent for ${g.newCoins} new coin${g.newCoins === 1 ? '' : 's'}. Send SOL to the Fuse wallet to refill — it never comes out of a card.` : 'Reading the wallet…'}>
      <small>⛽ GAS</small><i className="hrt-bar"><i style={{ transform: `scaleX(${gasPct / 100})` }} /></i>
      <b>{g ? `${g.sol.toFixed(3)} SOL` : '—'}</b><em>{!g ? '' : g.state === 'empty' ? '⚠ empty' : g.state === 'low' ? '⚠ low' : `${g.newCoins} coins`}</em></div>
    <div className={`hrt-gauge is-${land == null ? 'na' : land >= 80 ? 'ok' : land >= 50 ? 'low' : 'empty'}`} data-tip={L.top ? `Most common miss (24h): ${L.top} ×${L.topN}` : 'Every real swap the keeper tried in the last 24h'}>
      <small>📶 LANDED</small><i className="hrt-bar"><i style={{ transform: `scaleX(${(land || 0) / 100})` }} /></i>
      <b>{land == null ? '—' : `${land}%`}</b><em>{L.tried ? `${L.filled}/${L.tried}` : '—'}</em></div></div>;
}

const WEATHER = { clear: '☀ Runners: clear', rain: '🌧 Runners: strong only', storm: '⛈ Runners: off' };

const bigUsd = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(0)}K` : `$${Math.round(v || 0)}`);
const TOP3_DIVS = ['volume', 'fresh', 'proven', 'risers', 'paid', 'dip'];
export const topThree = (divisions, onCard = [], cool = {}) => { const seen = new Set(onCard); const out = [];
  for (const r of (divisions || []).filter(d => TOP3_DIVS.includes(d.key)).flatMap(d => (d.rows || []).map(x => ({ ...x, div: d.key }))).filter(r => !r.watch && r.mint && r.pairAddress && !(cool[r.mint] > 0)).sort((a, b) => (b.vol1h || 0) - (a.vol1h || 0) || (b.score || 0) - (a.score || 0)))
    if (!seen.has(r.mint)) { seen.add(r.mint); out.push(r); if (out.length === 3) break; }
  return out; };

/* 🔥 TOP 3 right now (busiest safe coins not on the card), one at a time, changing every few seconds — tap one, choose which of
   your coins it replaces at the next round. One light fetch every 30s. */
export function TopThree({ c, busy, onSwap }) {
  const [rows, setRows] = useState([]); const [i, setI] = useState(0); const [open, setOpen] = useState(null);
  const onCard = (c.legs || []).map(l => l.mint).join(',');
  useEffect(() => { let alive = true; const load = () => fetch(apiUrl('/api/reputation/fuses/contenders')).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setRows(topThree(x.divisions, onCard.split(','), c.pickCool || {}))).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 30000); return () => { alive = false; clearInterval(t); }; }, [onCard]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (open || rows.length < 2) return undefined; const t = setInterval(() => setI(n => (n + 1) % rows.length), 5000); return () => clearInterval(t); }, [rows.length, open]);
  useEffect(() => { if (!open) return undefined; const k = e => e.key === 'Escape' && setOpen(null); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [open]);
  if (!rows.length) return null;
  const r = rows[i % rows.length]; const m5 = r.chg5m; const fall = isFalling(m5, r.chg1h);
  return <span className="t3" data-testid="top-three"><small>🔥 TOP {(i % rows.length) + 1}/{rows.length}</small>
    <button type="button" key={r.mint} className={`t3-chip ${fall ? 'is-fall' : ''}`} disabled={busy} aria-expanded={open === r.mint} data-testid="top-three-chip"
      data-tip={`$${r.symbol} · 1h volume ${bigUsd(r.vol1h || 0)}${m5 != null ? ` · 5m ${m5 >= 0 ? '+' : ''}${Number(m5).toFixed(1)}%` : ''} · 1h ${r.chg1h >= 0 ? '+' : ''}${Number(r.chg1h || 0).toFixed(1)}% — tap to swap one of your coins for it at the next round`}
      onClick={() => setOpen(open === r.mint ? null : r.mint)}><b>${r.symbol}</b><i className="m-num">{bigUsd(r.vol1h || 0)}/h</i>
      <em className={`m-num ${(r.chg1h || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{(r.chg1h || 0) >= 1000 ? `${(r.chg1h / 100 + 1).toFixed(0)}x` : `${(r.chg1h || 0) >= 0 ? '+' : ''}${Number(r.chg1h || 0).toFixed(0)}%`}</em>{fall && <u>⚠</u>}</button>
    {open === r.mint && <span className="t3-pop" role="menu" data-testid="top-three-menu"><small>swap ${r.symbol} in for…</small>
      {(c.legs || []).filter(l => !l.buying).map(l => <button key={l.pairAddress} type="button" role="menuitem" className="m-btn" disabled={busy || l.frozen || l.ride}
        data-tip={l.frozen || l.ride ? 'Locked — it is riding' : undefined} onClick={() => { onSwap(l, r); setOpen(null); }}>${l.symbol} <i className={`m-num ${(l.pnlPct || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(l.pnlPct || 0)}</i></button>)}
      <button type="button" className="m-btn t3-x" onClick={() => setOpen(null)}>cancel</button></span>}
  </span>;
}

const VITAL_KIND = { skim: '💰 Profit taken', 'lock-bank': '🏦 Banked at the lock', 'peak-sell': '🏔 Sold off its peak', seat: '🪑 Seat filled', slot: '🪑 Seat released', keep: '⚖ Kept', ride: '❄ Locked (riding)', rotate: '⇄ Swap',
  compound: '♻ Cash back to work', balance: '⚖ Equal weight', floor: '🧱 Floor', deal: '🃏 Dealt', hold: '✋ Hold', 'manual-sell': '✂ Sold by you' };

/* Under the real card: what matters right now, alive — the stack seat by seat, swaps used this hour, profit pulled out — plus
   📜 Full activity and 🎞 Share. Transform / opacity animation only; still under fx-lite and reduced motion. */
export function CardVitals({ c, funded, onTrail }) {
  const st = c.stack || {}; const cap = c.swapCap || {};
  const seats = (c.legs || []).map(l => ({ sym: l.symbol, state: l.buying ? 'buying' : (l.ride || l.frozen) ? 'locked' : (l.pnlPct || 0) >= 5 ? 'winning' : (l.pnlPct || 0) <= -10 ? 'hurt' : 'proving', pct: l.pnlPct || 0 }));
  const best = [...(c.legs || [])].filter(l => (l.usd || 0) > 0).sort((a, b) => (b.pnlPct || 0) - (a.pnlPct || 0))[0];
  const pnl = allTime(c, funded); const used = cap.used || 0; const max = cap.cap || 0;
  const tl = (TIER[c.tier] || TIER.gold).look || {};
  const share = { tone: pnl >= 0 ? 'up' : 'down', theme: { degen: 'blaze', gold: 'gold', diamond: 'ice', next: 'synth', ever: 'nebula' }[c.tier], kicker: 'FEELESS · FUSE CARD', title: String(c.label || 'Fuse card').slice(0, 22), big: `${pnl >= 0 ? '+' : '−'}${usd(Math.abs(pnl))}`,
    lines: [`${(c.legs || []).length} coins · ${st.locked || 0} locked · ${c.rounds || 0} rounds`, best ? `best: $${best.symbol} ${pct(best.pnlPct || 0)}` : 'many coins, one fuse'], footer: 'feeless · fuse 🧬',
    // 🃏 the GIF shows THIS card: its tier colours, its coins with their logos and live %
    fuse: { name: (TIER[c.tier] || TIER.gold).name, accent: tl.accent, accent2: tl.accent2, coins: (c.legs || []).slice(0, 6).map(l => ({ symbol: l.symbol, pct: l.pnlPct || 0, logo: tokenImageUrls({ chainId: 'solana', baseToken: { address: l.mint }, info: { imageUrl: l.logo } })[0], locked: !!(l.ride || l.frozen) })) } };
  return <div className="hrt-under" data-testid="card-vitals">
    <ol className="cv-seats" aria-label="Seats">{seats.map((s, i) => <li key={s.sym + i} className={`is-${s.state}`} style={{ '--i': i }} data-tip={`$${s.sym} · ${s.state === 'locked' ? 'locked — riding, sold only off its peak' : s.state === 'winning' ? 'winning' : s.state === 'buying' ? 'being bought' : s.state === 'hurt' ? 'down — its stop is watching it' : 'proving itself'} · ${pct(s.pct)}`}><i /><small>{s.sym}</small></li>)}</ol>
    <div className="cv-row" data-tip={cap.why || 'Engine rotations this hour'}><small>SWAPS THIS HOUR</small><span className="cv-bar"><i style={{ transform: `scaleX(${max ? Math.min(1, used / max) : 0})` }} /></span><b className="m-num">{used}{max ? ` / ${max}` : ''}</b></div>
    <div className="cv-row" data-tip="Gains this card has already sold out of its coins (banked at the lock, skimmed, sold off the peak). It went back into the other coins or to cash."><small>PROFIT PULLED</small><b key={(c.takenUsd || 0).toFixed(2)} className="m-num m-pos fl-tick">{usd(c.takenUsd || 0)}</b></div>
    {best && <div className="cv-row"><small>BEST COIN</small><b className={`m-num ${(best.pnlPct || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>${best.symbol} {pct(best.pnlPct || 0)}</b></div>}
    <div className="cv-acts"><button type="button" className="m-btn" onClick={onTrail} data-testid="full-activity" data-tip="Everything this card did, newest first — every swap, lock, profit take and why">📜 Full activity</button>
      <ShareGifButton className="m-btn" label="🎞 Share" card={share} /></div>
  </div>;
}

const WX = { clear: ['☀', 'CLEAR'], rain: ['🌧', 'RAIN'], storm: ['⛈', 'STORM'] };
const WX_TREND = { clearing: '↗ clearing', worsening: '↘ worsening', steady: '→ steady' };
const WX_OUT = { tailwind: ['🟢', 'tailwind'], mixed: ['🟡', 'mixed'], headwind: ['🔴', 'headwind'] };

/* 🌦 Weather forecast on top of My cards: now · heading · how many launch coins are green · what real money buys in this weather.
   One tiny cached fetch a minute. A reading of right now — never a promise. */
export function WeatherStrip() {
  const [f, setF] = useState(null);
  useEffect(() => { let alive = true; const load = () => fetch(apiUrl('/api/reputation/fuses/forecast')).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setF(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 60000); return () => { alive = false; clearInterval(t); }; }, []);
  if (!f) return null;
  const [ico, word] = WX[f.level] || WX.clear; const [dot, out] = WX_OUT[f.outlook] || WX_OUT.mixed;
  return <div className={`wx is-${f.level}`} data-testid="weather-strip" data-tip={`Runner weather, measured by the engine's own sim cards on real recorded prices${f.avgPct != null ? ` (typical sim card ${f.avgPct >= 0 ? '+' : ''}${f.avgPct}% over ${f.n} sims)` : ' (not enough sims yet — reads clear)'}. Heading = the last 6h of sims against the last 24h. A reading of right now, never a promise.`}>
    <b className="wx-now"><i className="wx-ico" aria-hidden="true">{ico}</i>{word}</b>
    <span>{WX_TREND[f.trend] || WX_TREND.steady}</span>
    {f.breadthPct != null && <span data-testid="wx-breadth"><i className="m-num">{f.breadthPct}%</i> of {f.coins} launch coins green 1h{f.buyersPct != null ? <> · buyers <i className="m-num">{f.buyersPct}%</i></> : null}</span>}
    <span className="wx-out">{dot} {out}</span>
    <small>{f.buys}</small>
    {(f.entries || []).length > 0 && <span className="wx-entries" data-testid="wx-entries"><i className="m-label">ENTRIES NOW</i>{f.entries.map(e => <button type="button" key={e.mint} className="wx-entry" onClick={() => openWarRoom({ chainId: 'solana', pairAddress: e.pairAddress, baseToken: { address: e.mint, symbol: e.symbol } })}
      data-tip={`${e.name}: ${e.why}. 5m ${e.chg5m >= 0 ? '+' : ''}${e.chg5m}% · 1h ${e.chg1h >= 0 ? '+' : ''}${e.chg1h}% · buyers ${Math.round(e.buyShare)}%. Passes every safety gate.${e.proof?.n ? ` Last ${e.proof.n} ${e.name} reads, held 1h on paper: typical ${e.proof.medPct >= 0 ? '+' : ''}${e.proof.medPct}%, ${e.proof.wonPct}% up.` : ' No paper record for this setup yet.'} A read of the tape right now, never a promise.`}>{e.ico} <b>${e.symbol}</b> <em>{e.name}</em>{e.proof?.n >= 5 && <i className={`m-num ${e.proof.medPct >= 0 ? 'm-pos' : 'm-neg'}`}> {e.proof.medPct >= 0 ? '+' : ''}{e.proof.medPct}%</i>}</button>)}</span>}</div>;
}

/* 🎯 What happened to your picks: the last few "came in" / "refused" lines with the keeper's own reason — a refused pick is never silent. */
const MOVE_KINDS = { skim: '💰', 'lock-bank': '🏦', 'peak-sell': '🏔', compound: '♻', balance: '⚖', seat: '🪑', slot: '🪑', ride: '❄', 'ride-end': '❄', rotate: '⇄', 'instant-swap': '⚡', keep: '⚖', rug: '🚨', sl: '🛑', tp: '🎯', replace: '⇄', floor: '🧱', 'manual-sell': '✂' };
/* 🧾 What the CARD decided, newest first, in its own words: recycles, profit takes, cash put back to work, picks, locks, stops. */
export function CardMoves({ events, ago }) {
  const rows = [...(events || [])].filter(e => MOVE_KINDS[e.kind] && e.why).sort((x, y) => (y.at || 0) - (x.at || 0)).slice(0, 12);
  if (!rows.length) return null;
  return <><span className="m-label hrt-sub">WHAT THE CARD DID</span><ul className="hrt-moves" data-testid="card-moves">{rows.map((e, i) => <li key={`${e.at}-${i}`}><b>{MOVE_KINDS[e.kind]}</b>
    <span>{e.symbol ? <i>${e.symbol} </i> : null}{e.why}{(e.to || []).length && !/cash|card/.test(e.to[0]) ? ` → ${e.to.map(s => `$${s}`).join(', ')}` : ''}{e.n > 1 ? ` (×${e.n})` : ''}</span>
    <em className="m-num">{e.kind !== 'compound' && e.usd > 0 ? usd(e.usd) : ''}</em><small className="m-dim">{ago(e.at)}</small></li>)}</ul></>;
}

export const pickLog = events => (events || []).filter(e => e.kind === 'rotate' && /your pick|couldn't be bought|buy was refused|never landed/.test(e.why || '')).slice(-3).reverse()
  .map(e => (/your pick/.test(e.why) ? { ok: true, at: e.at, text: `$${(e.to || [])[0] || '?'} came in for $${e.symbol}` } : { ok: false, at: e.at, text: `$${e.symbol} was not bought — ${String(e.why).replace(/^⏳ \$\S+ /, '').replace(/ — (swapped for a buyable coin|slot back to card cash)$/, '')}${(e.to || []).length ? ` → $${e.to[0]} took the seat` : ' → its money is back in the card'}` }));
export function PickLog({ events }) {
  const rows = pickLog(events);
  if (!rows.length) return null;
  return <ul className="hrt-picklog" data-testid="pick-log">{rows.map((r, i) => <li key={`${r.at}-${i}`} className={r.ok ? 'is-ok' : 'is-no'}><b>{r.ok ? '🎯 ✓' : '🎯 ✕'}</b><span>{r.text}</span></li>)}</ul>;
}

export function HqRealCards({ addr, onCount }) {
  const [owner, setOwner] = useState(false);
  useEffect(() => { if (!addr) return; fetch(apiUrl(`/api/reputation/admin/is-admin/${addr}`)).then(r => r.json()).then(d => setOwner(!!(d.owner || d.admin))).catch(() => {}); }, [addr]);
  const { call } = useAdmin();
  const [busy, setBusy] = useState('');
  const [amt, setAmt] = useState('');
  const [pickFor, setPickFor] = useState(null);   // which coin's 🎯 picker is open
  const [trail, setTrail] = useState(null);       // 📜 full activity pop-up (card id)
  const d = usePrime(10000);   // 💵 live: the server's Jupiter value every 10s (real cards never show DexScreener-only numbers)
  const real = (d?.cards || []).filter(c => c.real);
  const n = owner ? real.length : 0;
  useEffect(() => { onCount?.(n); }, [n, onCount]);   // My cards hides its "no cards" box under a real card
  if (!owner) return null;
  if (!real.length) return <RecentRuns cards={d?.cards || []} />;
  const act = (tpl, action) => { if (action === 'defund' && !window.confirm('Sell every coin back to SOL? The card goes back to its paper card.')) return;
    setBusy(action); call('/admin/fuse-wallet/card', { method: 'POST', body: JSON.stringify({ tpl, action }) }).then(() => { toast.success(action === 'defund' ? '↩ Selling every coin to SOL' : action === 'halt' ? '⏸ Card paused' : '▶ Resumed'); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const topup = tpl => { const v = Number(amt); if (!(v >= 1)) { toast.error('Top up at least $1'); return; } if (!window.confirm(`Add ${v.toFixed(2)} of NEW money from the Fuse wallet? PUT IN increases by this amount.`)) return;
    setBusy('topup'); call('/admin/fuse-wallet/topup', { method: 'POST', body: JSON.stringify({ tpl, usd: v }) }).then(() => { toast.success(`＋ ${v.toFixed(2)} new money added`); setAmt(''); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const reinvestPaid = (tpl, paid) => { if (!(paid > 0)) { toast.error('No paid-out balance to reinvest'); return; }
    if (!window.confirm(`Reinvest the card's current paid-out balance (~${paid.toFixed(2)})? PUT IN stays unchanged; this only moves the card's own paid-out SOL back into active capital.`)) return;
    setBusy('reinvest'); call('/admin/fuse-wallet/reinvest-paid', { method: 'POST', body: JSON.stringify({ tpl }) }).then(() => { toast.success('↩ Paid-out money moved back into the card · PUT IN unchanged'); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  // 🎛 one-tap coin controls on YOUR real card (no trip to HQ): ⇄ swap a coin · ❄ freeze it · 🃏 re-deal the card (same money, same run)
  const prime = (body, ok, tag) => { setBusy(tag); call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(body) }).then(() => { toast.success(ok); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const retryDead = (tpl, o) => { setBusy(`retry-${o.side}-${o.mint}`); call('/admin/fuse-wallet/retry-dead', { method: 'POST', body: JSON.stringify({ tpl, side: o.side, mint: o.mint }) }).then(() => { toast.success(`Retrying ${o.side} $${o.symbol}`); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const ago = t => { const s = Math.max(0, Date.now() / 1000 - (t || 0)); return s < 60 ? `${s.toFixed(0)}s ago` : s < 3600 ? `${(s / 60).toFixed(0)}m ago` : `${(s / 3600).toFixed(1)}h ago`; };
  const fee = v => (v > 0 && v < 0.01 ? `$${v.toFixed(4)}` : usd(v));
  return <section className="m-card hq-reals" data-testid="hq-real-cards"><span className="m-label">💵 FEELESS REAL-MONEY TIER CARDS · FUSE WALLET</span>
    {real.map(c => { const t = TIER[c.tier] || TIER.gold; const b = c.realBook || {}; const k = b.keeper || {};
      const state = k.paused ? ['⏸', 'paused', 'is-warn'] : !k.armed ? ['○', 'not armed', 'is-warn'] : k.pending ? ['⏳', `sending ${k.pending}`, 'is-busy'] : c.legs.some(l => l.buying) ? ['⏳', 'retrying a buy', 'is-busy'] : ['●', 'in sync', 'is-ok'];
      const cf = c.cfgEff || (d.lockCfg?.[c.tpl] ? { ...d.cfg, ...d.lockCfg[c.tpl] } : d.cfg);   // the config this card REALLY runs (real card = its own)
      return <div key={c.id} className="hq-real">
        <div className="hq-real-card"><LiveFuseCard r={primeRow(c)} aura={t.aura} look={t.look} label="💵 REAL · FUSE WALLET" serverOnly />
          <CardVitals c={c} funded={b.fundedUsd || c.startUsd} onTrail={() => setTrail(c.id)} /><PickLog events={c.audit || c.events} /></div>
        {trail === c.id && <CardEarnings title={c.label} onClose={() => setTrail(null)} taken={c.walletUsd || 0} compounded={c.compoundedUsd} fees={c.cardFeesUsd}
          gainNow={allTime(c, b.fundedUsd || c.startUsd)} events={(c.audit || c.events || []).map(e => ({ ...e, label: KIND[e.kind] || VITAL_KIND[e.kind] || e.kind }))} />}
        <div className="hq-real-track">
          <div className="hrt-top"><b>{c.label}</b><TopThree c={c} busy={!!busy} onSwap={(leg, r) => prime({ pickSwap: { tpl: c.tpl, pairAddress: leg.pairAddress, to: r.mint, toPair: r.pairAddress } }, `🎯 $${r.symbol} comes in for $${leg.symbol} at the next round`, 'pick')} /><span className={`hrt-state ${state[2]}`} data-tip="Keeper: moves the real coins to what the card says, every tick">{state[0]} {state[1]}</span></div>
          <div className="hrt-hero">
            <RoundBell at={c.nextRoundAt || c.lastRotateAt + (cf?.rotateHours || 1) * 3600} sec={c.bellSec || 10} rest={!!c.resting} label={`ROUND ${(c.rounds || 0) + 1}`} />
            <span className="is-now" data-tip="What the card is worth right now (selling every coin at live prices) · % vs this run's start"><small>IN CARD NOW</small><b key={(c.valueUsd || 0).toFixed(2)} className="m-num fl-tick">{usd(c.valueUsd)}</b><em className={`m-num ${c.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(c.pnlPct)} this run</em></span>
            <span data-tip="Price result vs every $ you put in (all top-ups). Fees are apart: the wallet reserve carries every coin account's rent (the card never pays it), and the network fees the card paid are added back here."><small>ALL-TIME</small><b className={`m-num ${allTime(c, b.fundedUsd || c.startUsd) >= 0 ? 'm-pos' : 'm-neg'}`}>{usd(allTime(c, b.fundedUsd || c.startUsd))}</b><em className="m-num">{pct(allTime(c, b.fundedUsd || c.startUsd) / (b.fundedUsd || c.startUsd || 1) * 100)} on {usd(b.fundedUsd || c.startUsd)} put in{c.cardFeesUsd > 0.005 ? ` · fees ${usd(c.cardFeesUsd)} apart` : ''}</em>
              {(() => { const w = whereDown(c, b.fundedUsd || c.startUsd); return <em className="m-num hrt-where" data-testid="hrt-where" data-tip="Coins on the card now = what they're worth minus what they cost. Already sold = the price result of every coin that left the card (swaps, stops, instant swaps, rides) — fees are apart. See 🧾 Activity for each one.">
                coins now {w.held >= 0 ? '+' : '−'}{usd(Math.abs(w.held))} · already sold {w.sold >= 0 ? '+' : '−'}{usd(Math.abs(w.sold))}</em>; })()}</span>
            {c.vsSolPct != null && <span data-tip={`Holding SOL over this run: ${pct(c.holdSolPct)}. Fund more only when this stays positive.`}><small>VS HOLDING SOL</small><b className={`m-num ${c.vsSolPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(c.vsSolPct)}</b><em className="m-num">this run</em></span>}</div>
          <p className="hrt-line m-num" data-testid="hrt-line">{c.stack?.seats > 0 && <span className={`hrt-stack ${c.stack.full ? 'is-full' : ''}`} data-testid="hrt-stack" data-tip={`🔒 Locked = a winner the engine froze: it is held while it runs and only sold once it falls off its peak. ✅ Winning = up enough that a re-shape will not sell it. ⏳ Proving = not there yet (its stop still protects it). When every coin is locked the engine stops swapping and just guards the stack.`}>
              🔒 {c.stack.locked}/{c.stack.seats} locked{c.stack.winning ? ` · ✅ ${c.stack.winning} winning` : ''}{c.stack.proving ? ` · ⏳ ${c.stack.proving} proving` : ''}{c.stack.full ? ' · FULL STACK' : ''}</span>}
            <span data-tip="Rounds this card has played">⟳ {c.rounds || 0} rounds</span><span data-tip="This run started at this value (a run restarts on top-ups, re-deals and fixes)">run from {usd(c.startUsd)}</span>
            <span data-tip="Paid-out money still parked outside active card capital right now">paid out now {usd(c.walletUsd || 0)}</span><span data-tip="Lifetime amount this card has paid out. Reinvesting does not erase this history and does not increase PUT IN.">paid out ever {usd(b.paidOutEverUsd || 0)}</span></p>
          <CycleStrip c={c} />
          <SwapFlow k={k} />
          <ul className="hrt-coins">{c.legs.map(l => <li key={l.pairAddress} className={l.buying ? 'is-buying' : ''}><b>{l.role === 'runner' ? '🏃' : '⚓'} <span role="button" tabIndex={0} className="hrt-name" data-testid={`coin-${l.symbol}`} data-tip="Open its war room — live chart, trades and your buys marked"
              onClick={() => openWarRoom({ chainId: 'solana', pairAddress: l.pairAddress, baseToken: { address: l.mint, symbol: l.symbol } })}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openWarRoom({ chainId: 'solana', pairAddress: l.pairAddress, baseToken: { address: l.mint, symbol: l.symbol } }); } }}>${l.symbol}</span>{l.ride && l.high > 0 && <i className="hrt-ride" data-tip={`Frozen while it runs — swapped once it falls ${cf?.rideTrail || 30}% from its peak`}> ❄ riding · peak {pct((l.high / (l.rideFrom || l.entry || l.high) - 1) * 100)}</i>}{l.frozen && !l.ride && <i className="hrt-ride"> ❄ frozen</i>}</b>
            {l.buying || !(l.usd > 0) ? <em className="hrt-buy" data-tip={k.lastFail?.symbol === l.symbol ? `Last try: ${k.lastFail.err} — tap ⇄ to swap it for a coin that can be bought` : l.buying ? 'The keeper has card cash assigned to this coin and retries the buy on its next tick' : 'This slot is empty but the card has no tradable cash assigned to it. Paid-out wallet money is never pulled back into the card; the slot will arm automatically when card cash is available.'}>{l.buying ? (k.lastFail?.symbol === l.symbol ? `⏳ ${String(k.lastFail.err || '').split(' (')[0].slice(0, 34)}` : '⏳ buying… not counted until it lands') : '○ empty · waiting for card cash'}</em> : <><span>{usd(l.costUsd)} → {usd(l.usd)}</span><em className={l.pnlPct >= 0 ? 'm-pos' : 'm-neg'}>{pct(l.pnlPct)}{l.loseRounds > 0 && !l.ride && !l.frozen ? ` · ${l.loseRounds}/${cf?.rotateConfirm || 1} losing` : ''}</em></>}
            {l.symbol !== 'SOL' ? <span className="hrt-ctl">
              {/* ✂ your call, your amount: the ONLY way principal leaves a card. The engine itself pays out profit only. */}
              {(() => { const gain = (l.usd || 0) - (l.costUsd || 0); const can = gain >= 0.05 && !l.buying;   // 💰 profit only — the stake keeps riding
                return <select className={`m-input hrt-skim ${can ? 'is-on' : ''}`} disabled={!!busy || !can} value="" data-testid={`skim-${l.symbol}`} aria-label={`Take ${l.symbol} profit`}
                  data-tip={can ? `Take ONLY the profit of $${l.symbol} (about ${usd(gain)}). What you put into it (${usd(l.costUsd)}) keeps riding. Choose where the profit goes.` : `No profit to take on $${l.symbol} right now`}
                  onChange={e => { const to = e.target.value; if (!to) return;
                    if (window.confirm(`Take about ${usd(gain)} profit from $${l.symbol} and ${to === 'cash' ? 'hold it as card cash' : 'put it into your other coins'}? ${usd(l.costUsd)} stays in $${l.symbol}.`))
                      prime({ skim: { tpl: c.tpl, pairAddress: l.pairAddress, to } }, `💰 Taking $${l.symbol} profit — ${to === 'cash' ? 'held as cash' : 'into your other coins'} once it confirms`, `skim-${l.pairAddress}`); }}>
                  <option value="">💰{can ? ` ${usd(gain)}` : ''}</option><option value="card">♻ into my other coins</option><option value="cash">🏦 hold as cash</option></select>; })()}
              <span className="hrt-sell" role="group" aria-label={`Sell ${l.symbol}`}>{[[25, '25%'], [50, '50%'], [100, 'All']].map(([p, t]) => <button key={p} type="button" className="m-btn danger" disabled={!!busy || l.buying || !(l.usd > 0)} data-testid={p === 100 ? `sell-${l.symbol}` : `sell-${l.symbol}-${p}`}
                data-tip={`Sell ${p === 100 ? 'all' : `${p}%`} of your $${l.symbol} (${usd((l.usd || 0) * p / 100)}) to this card's cash. The total changes only after the transaction confirms.`}
                onClick={() => window.confirm(`Sell ${p === 100 ? 'ALL' : `${p}%`} of $${l.symbol} (about ${usd((l.usd || 0) * p / 100)}) to this card's cash?`) && prime({ manualSell: { tpl: c.tpl, pairAddress: l.pairAddress, pct: p } }, `Selling ${p === 100 ? 'all' : `${p}%`} of $${l.symbol} — card cash updates after confirmation`, `sell-${l.pairAddress}`)}>{t}</button>)}</span>
              {l.role !== 'anchor' && <span className="hrt-own" data-tip={`$${l.symbol}'s OWN take-profit and stop. "tier" = follow the card's (TP +${c.tp}% · SL −${c.sl}%). The ⚡ instant swap and the card floor still apply.${cf?.rideAt ? ` ❄ Freeze runs FIRST: once $${l.symbol} is up +${cf.rideAt}% it rides (no TP) and sells ${cf.rideTrail}% off its peak — the TP only fires if the coin jumps past it before the freeze catches it.` : ''}`}>
                <select className="m-input" aria-label={`${l.symbol} take-profit`} disabled={!!busy} value={l.tp || 0} data-testid={`tp-${l.symbol}`} onChange={e => prime({ leg: { tpl: c.tpl, pairAddress: l.pairAddress, tp: Number(e.target.value) } }, Number(e.target.value) ? `🎯 $${l.symbol} takes profit at +${e.target.value}%` : `$${l.symbol} follows the tier's take-profit`, `tp-${l.pairAddress}`)}>
                  <option value={0}>TP tier</option>{[25, 50, 100, 200, 300].map(v => <option key={v} value={v}>TP +{v}%</option>)}</select>
                <select className="m-input" aria-label={`${l.symbol} stop`} disabled={!!busy} value={l.sl || 0} data-testid={`sl-${l.symbol}`} onChange={e => prime({ leg: { tpl: c.tpl, pairAddress: l.pairAddress, sl: Number(e.target.value) } }, Number(e.target.value) ? `🛑 $${l.symbol} stops at −${e.target.value}%` : `$${l.symbol} follows the tier's stop`, `sl-${l.pairAddress}`)}>
                  <option value={0}>SL tier</option>{[10, 15, 20, 30].map(v => <option key={v} value={v}>SL −{v}%</option>)}</select></span>}
              <button type="button" className="m-btn" disabled={!!busy || l.frozen} data-testid={`swap-${l.symbol}`} data-tip={l.frozen ? 'Frozen — unfreeze to swap it' : `Swap $${l.symbol} for the best coin of its kind not on the card (keeper trades it next tick)`}
                onClick={() => prime({ replace: { tpl: c.tpl, pairAddress: l.pairAddress } }, `⇄ $${l.symbol} swapped — keeper buys the new coin next tick`, `sw-${l.pairAddress}`)}>⇄</button>
              <button type="button" className={`m-btn ${pickFor === l.pairAddress || l.swapTo ? 'active' : ''}`} disabled={!!busy || l.frozen} data-testid={`pick-${l.symbol}`} aria-expanded={pickFor === l.pairAddress}
                data-tip={l.swapTo ? `$${l.swapTo} comes in for $${l.symbol} at the next round — tap to change or cancel` : `Pick the coin that replaces $${l.symbol} at the next round, from the live lists`}
                onClick={() => setPickFor(pickFor === l.pairAddress ? null : l.pairAddress)}>{l.swapTo ? `🎯 → $${l.swapTo}` : '🎯'}</button>
              <button type="button" className={`m-btn ${l.frozen ? 'active' : ''}`} aria-pressed={!!l.frozen} disabled={!!busy} data-testid={`freeze-${l.symbol}`} data-tip={l.frozen ? `Unfreeze $${l.symbol}: the engine may rotate / stop it again` : `Freeze $${l.symbol}: never rotated or stopped (the card floor still protects you)`}
                onClick={() => prime({ leg: { tpl: c.tpl, pairAddress: l.pairAddress, frozen: !l.frozen } }, l.frozen ? `$${l.symbol} back under the engine` : `❄ $${l.symbol} frozen`, `fz-${l.pairAddress}`)}>❄</button></span>
              : <span className="hrt-ctl">{/* SOL is the card's own cash sitting in a seat — it can be swapped into a coin like any other */}
                <button type="button" className={`m-btn ${pickFor === l.pairAddress || l.swapTo ? 'active' : ''}`} disabled={!!busy} data-testid="pick-SOL" aria-expanded={pickFor === l.pairAddress}
                  data-tip={l.swapTo ? `$${l.swapTo} takes this SOL at the next round — tap to change or cancel` : 'This seat is plain SOL (card cash). Pick a coin to put it into at the next round — the buy is checked for price impact first.'}
                  onClick={() => setPickFor(pickFor === l.pairAddress ? null : l.pairAddress)}>{l.swapTo ? `🎯 → $${l.swapTo}` : '🎯 swap SOL into a coin'}</button></span>}</li>)}
            {pickFor && c.legs.some(l => l.pairAddress === pickFor) && <li className="hrt-pickrow"><SwapPicker call={call} out={c.legs.find(l => l.pairAddress === pickFor)} have={c.legs.map(l => l.mint)} cool={c.pickCool || {}} busy={!!busy} minLiq={Math.min(k.minLiqUsd ?? 20000, k.arenaMinLiqUsd ?? k.minLiqUsd ?? 20000, k.pickMinLiqUsd ?? 10000)}
              onPick={r => { prime({ pickSwap: { tpl: c.tpl, pairAddress: pickFor, to: r ? r.mint : null, toPair: r ? r.pairAddress : null } }, r ? `🎯 $${r.symbol} comes in at the next round` : 'Pick cancelled', 'pick'); setPickFor(null); }} onClose={() => setPickFor(null)} /></li>}
            {(() => { const cash = b.reconciliation?.cardCashUsd ?? c.cash ?? 0;   // the book's confirmed SOL — the same number "Withdraw card cash" shows
              return cash > 0.01 && <li data-testid="hrt-cash" data-tip="SOL the card holds right now (confirmed on the book). Part of it may be on its way into a coin that is being bought."><b>◎ cash</b><span>{usd(cash)}</span><em className="m-dim">SOL</em></li>; })()}</ul>
          <details className="hrt-fold" data-testid="hrt-fold-cfg"><summary><b>⚙ Config</b><span>{Math.round((cf?.rotateHours || 0) * 60)}m rounds · instant swap {cf?.instantSwapPct ? `−${cf.instantSwapPct}%` : 'off'} · card floor −{cf?.floorPct}% · rest {cf?.floorRestMins ? `${cf.floorRestMins}m` : 'off'} · rescue {cf?.rescuePct ? `−${cf.rescuePct}%` : 'off'} · patience {cf?.rotateConfirm ?? '—'} · hold {cf?.minHoldMins ?? '—'}m · ❄ freeze {cf?.rideAt ? `+${cf.rideAt}% → −${cf.rideTrail}% off peak (runs before TP)` : 'off'}{cf?.tp ? ` · TP +${cf.tp}%` : ''}{cf?.sl ? ` · SL −${cf.sl}%` : ''}{d.realOwnerSet?.length ? ` · 🪙 ${d.realOwnerSet.length} yours (the engine never changes them)` : ''}</span></summary>
          <div className="hrt-cfg" data-testid="hrt-cfg">{[[`⏱ ${Math.round((cf?.rotateHours || 0) * 60)}m rounds`, 'Round clock'], [`⏳ swap after ${cf?.rotateConfirm || 1} losing rounds · −${cf?.rotateMinDrop || 0}%`, 'A coin is swapped only after this many losing rounds in a row, and only this far down'],
            [`🔒 hold ≥ ${cf?.minHoldMins || 0}m`, 'Every new coin is held at least this long'], [`🔄 ${(cf?.cycles || {})[c.tpl] || c.cycleMode || 'off'}${c.cycleFix ? ` (fix: ${c.cycleFix})` : ''} · ${c.phase || '—'}`, 'Cycle and the shape it is in now'], [`🧩 re-shape every ${cf?.cycleEvery || 6} rounds`, 'How often the card changes shape'],
            [`🛑 stops: ${cf?.slMode || 'replace'}`, 'What happens when a coin hits its stop'], [`🛟 rescue at −${cf?.rescuePct || 50}%`, 'Card this far under its start → safest coins'], [`💧 real buys need $${((k.minLiqUsd || 0) / 1000).toFixed(0)}K pool · 🏟 Arena $${((k.arenaMinLiqUsd ?? k.minLiqUsd ?? 0) / 1000).toFixed(0)}K`, 'Thinner coins stay paper-only; Arena coins (passed every runner gate) have their own floor'],
            [`🪙 min buy $${(k.minOrderUsd || 0).toFixed(2)} · max $${k.maxSwapUsd || 0}`, 'Smallest / largest single real swap'], [`↔ slippage ${((k.slippageBps || 0) / 100).toFixed(1)}%`, 'Retries add a little, never past 3%']].map(([t2, tip]) => <span key={t2} className="m-chip" data-tip={tip}>{t2}</span>)}</div>
          <CardEditor c={c} cfg={c.cfgEff || (d.locks?.[c.tpl] ? { ...d.cfg, ...(d.lockCfg?.[c.tpl] || {}) } : d.cfg)} keeper={k} locked={!!d.locks?.[c.tpl]} real={!!c.real} call={call} suggest={d.suggest} /></details>
          <div className="hrt-acts">
            <button type="button" className="m-btn" disabled={!!busy || k.selling} onClick={() => act(c.tpl, k.halt ? 'resume' : 'halt')} data-tip={k.halt ? 'Keeper trades again' : 'Keeper stops trading this card (coins stay)'}>{k.halt ? '▶ Resume' : '⏸ Pause'}</button>
            <span className="hrt-top-up"><input className="m-input" type="number" min="1" step="1" placeholder="$" value={amt} onChange={e => setAmt(e.target.value)} aria-label="Top up amount" />
              <button type="button" className="m-btn m-go" disabled={!!busy || k.selling} onClick={() => topup(c.tpl)} data-tip="Add NEW money from the Fuse wallet — this increases PUT IN">＋ Add new money</button></span>
            {(c.walletUsd || 0) > 0.005 && <button type="button" className="m-btn" disabled={!!busy || k.selling || !!k.pending} onClick={() => reinvestPaid(c.tpl, c.walletUsd || 0)} data-tip="Move this card's currently PAID OUT SOL back into active card capital. PUT IN stays unchanged.">↩ Reinvest paid out {usd(c.walletUsd || 0)}</button>}
            <button type="button" className={`m-btn ${c.holdAll ? 'active' : ''}`} aria-pressed={!!c.holdAll} disabled={!!busy} data-testid="hold-all" data-tip={c.holdAll ? 'Release: the engine swaps and re-shapes again' : 'Hold every coin: no swaps or re-shapes (stops + rug shield still protect you)'}
              onClick={() => prime({ hold: { tpl: c.tpl, on: !c.holdAll } }, c.holdAll ? '▶ Released — the engine trades again' : '✋ Holding every coin', 'hold')}>{c.holdAll ? '▶ Release' : '✋ Hold all'}</button>
            <select className={`m-input hrt-lock ${c.handsOffUntil ? 'is-on' : ''}`} disabled={!!busy} value={0} data-testid="hands-off" aria-label="Hands-off lock"
              data-tip={c.handsOffUntil ? `🔒 Hands-off: your picks and hand swaps wait ${Math.max(1, Math.round((c.handsOffUntil - Date.now() / 1000) / 60))} more min. The engine, your stops and selling to cash keep working. Choose "unlock" to end it.` : 'Hands-off lock: for the time you choose, picks and hand swaps are refused so the card is not churned by impulse. The engine, your stops and selling to cash keep working.'}
              onChange={e => { const h = Number(e.target.value); if (h === 0 && !c.handsOffUntil) return; prime({ handsOff: { tpl: c.tpl, hours: h < 0 ? 0 : h } }, h > 0 ? `🔒 Hands-off for ${h}h` : '🔓 Unlocked', 'hold'); }}>
              <option value={0}>{c.handsOffUntil ? `🔒 ${Math.max(1, Math.round((c.handsOffUntil - Date.now() / 1000) / 60))}m left` : '🔒 Hands-off'}</option>
              {[1, 3, 6, 12].map(h => <option key={h} value={h}>{h}h</option>)}{c.handsOffUntil && <option value={-1}>unlock</option>}</select>
            <button type="button" className="m-btn" disabled={!!busy || k.selling} data-testid="redeal-real" data-tip="Fresh coins for this card NOW — same money, same run; frozen coins stay. The keeper trades the change next tick."
              onClick={() => window.confirm('Re-deal this card with fresh coins now? Same money, same run.') && prime({ redeal: c.tpl }, '🃏 Re-dealt — keeper trades the new coins next tick', 'redeal')}>🃏 Re-deal</button>
            {(c.legs || []).some(l => l.buying) && <button type="button" className="m-btn hrt-fix" disabled={!!busy} data-testid="fix-real"
              data-tip="A coin is waiting on its buy. Fix = put ALL this card's cash to work (incl. cash you held with ✂), fund waiting coins from the SOL coin's extra, fresh retries. (This also runs by itself: a buy stuck 10 min is swapped for a buyable coin.)"
              onClick={() => prime({ fix: c.tpl }, '🔧 Fixing — waiting coins funded, the keeper retries next tick', 'fix')}>🔧 Fix buys</button>}
            <span className="hrt-sell is-card" role="group" aria-label="Sell part of the card" data-tip="Sell this share of EVERY coin to the card's cash (the card stays real). Engine payouts are profit only — this is how you take out more.">{[25, 50].map(p => <button key={p} type="button" className="m-btn danger" disabled={!!busy || k.selling} data-testid={`sell-card-${p}`}
              onClick={() => window.confirm(`Sell ${p}% of every coin on this card (about ${usd((c.valueUsd || 0) * p / 100)}) to card cash?`) && prime({ manualSell: { tpl: c.tpl, all: true, pct: p } }, `Selling ${p}% of every coin — card cash updates after confirmation`, 'sell-card')}>Sell {p}%</button>)}</span>
            <button type="button" className="m-btn danger" disabled={!!busy || k.selling} onClick={() => act(c.tpl, 'defund')} data-tip="Sell every coin to SOL — the card goes back to its paper card">{k.selling ? '↩ selling…' : '↩ Sell all'}</button></div>
          <details className="hrt-fold" data-testid="hrt-fold-act"><summary><b>🧾 Activity</b><span>{b.swaps || 0} swaps · fees {fee(b.feesUsd || 0)} · last fill {k.lastFill ? ago(k.lastFill) : '—'}{k.lastFail ? ` · ⚠ last miss ${ago(k.lastFail.at)}` : ''}</span></summary>
          <RealHealth k={k} />
          {k.lastFail && <small className="hrt-fail" data-tip={k.lastFail.err}>⚠ last miss: {k.lastFail.side} ${k.lastFail.symbol} · {ago(k.lastFail.at)} — retried automatically {k.lastFail.mint && <button type="button" className="m-btn" disabled={!!busy} onClick={() => retryDead(c.tpl, k.lastFail)}>Retry now</button>}</small>}
          <small className="m-dim">{b.swaps || 0} swaps · network fees {fee(b.feesUsd || 0)} (wallet reserve pays) · last fill {k.lastFill ? ago(k.lastFill) : '—'}</small>
          <CardMoves events={c.audit || c.events} ago={ago} />
          <span className="m-label hrt-sub">SWAPS ON-CHAIN</span>
          <ul className="prime-txs">{(b.orders || []).slice(0, 10).map((o, i) => <li key={o.sig || i}><b>{o.side === 'topup' ? '💵' : o.side === 'reinvest' ? '↩' : o.side === 'buy' ? '🟢' : '🔴'}</b><span>{o.side === 'topup' ? 'new money funded' : o.side === 'reinvest' ? 'paid out reinvested' : `${o.side} ${o.symbol}`} <i className="m-dim">{ago(o.at)}{o.why ? ` · ${o.why}` : ''}</i>
              {o.side === 'sell' && o.costUsd > 0 && <i className={`hrt-pl ${o.usd >= o.costUsd ? 'm-pos' : 'm-neg'}`} data-tip={`This coin cost $${o.costUsd.toFixed(2)} (money that reached the pool) and the sell returned $${(o.usd || 0).toFixed(2)} — fees apart`}> · in {usd(o.costUsd)} → {pct((o.usd / o.costUsd - 1) * 100)}</i>}</span>
            <em className="m-num">{usd(o.usd)}</em>{o.sig ? <a href={txUrl(o.sig)} target="_blank" rel="noreferrer">tx ↗</a> : <i />}</li>)}</ul></details></div></div>; })}</section>;
}


// 🎯 Pick the coin that comes in at the next round: the SAME lenses as the Fuse Lab (Popular · Majors · New majors · Top yield ·
// Deepest · Runners · New 72h · Dip · Dex paid) + search any coin / CA. Live prices, one tap; the server re-checks the pool live.
export const PICK_LENSES = [['popular', '🔥 Popular'], ['majors', '🪙 Majors'], ['stocks', '📈 Stocks'], ['risers', '🚀 New majors'], ['yield', 'Top yield'], ['deep', 'Deepest'],
  ['runners', '🏃 Runners'], ['volume', '🌊 Volume'], ['trench', '🗑 Trench'], ['new', 'New 72h'], ['dip', '📉 Dip'], ['paid', '💳 Dex paid']];
const GAUNTLET = { runners: ['fresh', 'proven'], volume: ['volume'], dip: ['dip'], paid: ['paid'] };
const PICK_STABLES = new Set(['USDC', 'USDT', 'USDS', 'PYUSD', 'USD1', 'DAI', 'USDE', 'FDUSD']);   // a dollar coin never moves — not a swap-in (= contenders.STABLES)
export const isFalling = (m5, h1) => (m5 != null && Number(m5) <= -3) || (h1 != null && Number(h1) <= -8);   // = arena_prime.entry_ok
export const pickRow = r => ({ mint: r.mint || r.baseAddress, pairAddress: r.pairAddress, symbol: r.symbol, price: r.price ?? r.priceUsd, liq: r.liq ?? r.liquidityUsd,
  chg: r.chg1h ?? r.change1h ?? r.chg24h ?? r.change24h, chg1h: r.chg1h ?? r.change1h ?? null, chg5m: r.chg5m ?? r.change5m ?? null, score: r.score, impostor: r.impostor, real: r.real, trench: r.trench, holders: r.holders, soft: r.soft, fails: r.fails, warn: r.warn, pulse: r.pulse, stock: r.stock });
export function SwapPicker({ out, have = [], busy, onPick, onClose, minLiq = 0, cool = {}, call }) {
  const [nonce, setNonce] = useState(0);   // bumps when the trench settings are saved → the list reloads
  const [lens, setLens] = useState('popular'); const [rows, setRows] = useState(null); const [q, setQ] = useState('');
  const [tr, setTr] = useState(null);   // 🗑 trench scan: own pool floor + how many were checked
  const [why, setWhy] = useState('');
  useEffect(() => { let alive = true; setRows(null); setWhy('');
    const s = q.trim();
    const url = s.length >= 2 ? `/api/reputation/fuses/search?q=${encodeURIComponent(s)}` : lens === 'trench' ? '/api/reputation/fuses/trench' : GAUNTLET[lens] ? '/api/reputation/fuses/contenders' : `/api/reputation/fuses/discover?lens=${lens}&chain=solana`;
    const t = setTimeout(() => fetch(apiUrl(url)).then(r => (r.ok ? r.json() : null)).then(x => { if (!alive || !x) return; setWhy(x.why || '');
      if (x.checked) setTr({ floor: x.floor || 0, checked: x.checked.length, rules: x.rules, level: Number(x.level) || 0 });
      const raw = x.pools || (x.checked ? x.rows || [] : (x.divisions || []).filter(dv => (GAUNTLET[lens] || []).includes(dv.key)).flatMap(dv => dv.rows));
      const seen = new Set(); setRows(raw.map(pickRow).filter(r => r.mint && r.pairAddress && !PICK_STABLES.has(String(r.symbol || '').toUpperCase()) && !seen.has(r.mint) && seen.add(r.mint)).slice(0, 30)); }).catch(() => alive && setRows([])), s.length >= 2 ? 300 : 0);
    return () => { alive = false; clearTimeout(t); }; }, [lens, q, nonce]);
  const live = useLivePrices((rows || []).map(r => r.pairAddress));
  const fmt = v => (!v ? '—' : v >= 1 ? `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}` : `$${Number(v).toPrecision(3)}`);
  const big = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(0)}K` : `$${Math.round(v || 0)}`);
  return <div className="sp" data-testid="swap-picker"><header><span className="m-label">🎯 SWAP ${out.symbol} FOR… <small>goes in at the next round · its money moves over · live prices</small></span>
    <span className="m-row">{out.swapTo && <button type="button" className="m-btn" disabled={busy} onClick={() => onPick(null)} data-testid="sp-cancel">✕ Cancel → ${out.swapTo.symbol || out.swapTo}</button>}<button type="button" className="m-btn" onClick={onClose} aria-label="Close picker">Close</button></span></header>
    <div className="m-seg sp-lens" role="tablist" aria-label="Lists">{PICK_LENSES.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={!q.trim() && lens === k} className={!q.trim() && lens === k ? 'active' : ''} onClick={() => { setLens(k); setQ(''); }} data-testid={`sp-lens-${k}`}>{l}</button>)}</div>
    <input className="m-input sp-q" value={q} onChange={e => setQ(e.target.value)} placeholder="Search any coin — SOL, BTC, ETH, $TICKER, CA" aria-label="Search any coin" data-testid="sp-search" />
    {lens === 'trench' && !q.trim() && tr && <small className="m-dim sp-tnote" data-testid="sp-trench-note">🗑 Fresh breakouts that passed the strictest gate ({tr.checked} checked · own pool floor {big(tr.floor)}). High risk — keep it to 1–2 coins.{tr.level ? ` 🔧 Nothing passed the strict checks, so crowd / trade / volume checks were widened ×${tr.level} — safety checks never move.` : ''} {tr.rules}</small>}
    {lens === 'trench' && !q.trim() && call && <TrenchScan call={call} bare onSaved={() => setNonce(n => n + 1)} />}
    {!rows ? <span className="loader" /> : !rows.length ? <small className="m-dim">{lens === 'trench' && !q.trim() ? 'No fresh coin passes the safety checks right now — the scan re-runs every ~2 min. Try 🌊 Volume.' : (why || 'Nothing live here right now — try another list or search.')}</small> :
    <ul>{rows.map(r => { const lp = live.get?.(r.pairAddress); const on = have.includes(r.mint); const fl = r.trench ? (tr?.floor || 0) : minLiq; const thin = minLiq > 0 && (r.liq || 0) < fl; const chg = lp?.h1 ?? r.chg1h ?? r.chg;
      const m5 = lp?.m5 ?? r.chg5m; const falling = isFalling(m5, lp?.h1 ?? r.chg1h);   // same rule the engine uses before a real buy
      return <li key={r.mint} className={r.impostor ? 'is-fake' : ''}><b>${r.symbol}{r.real ? ' ✓' : ''}{r.stock ? <i className="sp-pulse" data-tip="Tokenized stock (xStock) trading in a real Solana pool"> 📈</i> : null}{r.pulse ? <i className="sp-pulse" data-tip="Pump Pulse: a burst of buys in the last 5 minutes" data-testid={`sp-pulse-${r.symbol}`}> ⚡</i> : null}</b><span className="m-num fl-tick" key={fmt(lp?.price || r.price)}>{fmt(lp?.price || r.price)}</span>
        <em className={`m-num sp-m5 ${(m5 || 0) >= 0 ? 'm-pos' : 'm-neg'}`} data-tip="Move over the last 5 minutes" data-testid={`sp-m5-${r.symbol}`}><i>5m</i> {m5 == null ? '—' : `${m5 >= 0 ? '+' : ''}${Number(m5).toFixed(1)}%`}</em>
        <em className={`m-num ${(chg || 0) >= 0 ? 'm-pos' : 'm-neg'}`} data-tip="Move over the last hour"><i>1h</i> {chg == null ? '—' : `${chg >= 0 ? '+' : ''}${Number(chg).toFixed(1)}%`}</em>
        <small className="sp-fall" data-testid={r.warn ? `sp-warn-${r.symbol}` : falling ? `sp-fall-${r.symbol}` : undefined} data-tip={r.warn ? `${r.warn} You still can — it is your pick.` : falling ? 'Falling right now (−3% or more in 5 minutes, or −8% or more in the hour). The engine would not buy this with real money; you still can — it is your pick.' : undefined}>{r.warn ? '⚠ creator' : falling ? '⚠ falling' : ''}</small><small className="m-num">pool {r.liq > 0 ? big(r.liq) : 'curve'}</small><small className="m-num">{r.soft ? <i className="sp-soft" data-tip={`Near-miss: every safety check passed, it only missed — ${(r.fails || []).join(' · ')}. Not seated by the engine; yours to pick.`}>near-miss</i> : <>{r.trench && r.holders ? `${r.holders} holders · ` : ''}{r.score != null ? `score ${Number(r.score).toFixed(0)}` : ''}</>}</small>
        <button type="button" className="m-btn primary" disabled={busy || on || thin || r.impostor || cool[r.mint] > 0} onClick={() => onPick(r)}
          data-tip={cool[r.mint] > 0 ? `$${r.symbol} just left this card — you can pick it again in ${cool[r.mint]} round${cool[r.mint] === 1 ? '' : 's'} (no back-to-back)` : thin ? `Pool under your $${Math.round(fl / 1000)}K pick floor — change it in Edit Fuse › Limits (My own pick min pool)` : undefined} data-testid={`sp-pick-${r.symbol}`}>{on ? 'on card' : cool[r.mint] > 0 ? `in ${cool[r.mint]} rnd` : thin ? 'too thin' : r.impostor ? 'lookalike' : 'Swap in'}</button></li>; })}</ul>}
  </div>;
}

// 🏁 where a coin came in from (its Gauntlet division) — the visible proof that every card is fed by every category
export const DIVISION = { majors: '🪙 anchor', risers: '🚀 new major', yield: '💸 top yield', deep: '🌊 deepest', popular: '🔥 popular', fresh: '⚡ fresh runner', proven: '🏃 proven runner', new: '🆕 new 72h', volume: '🌊 volume runner', trench: '🗑 trench' };

// 🕘 Your last real card stays on My cards as a FAINT card (not a list): tap it for the run-by-run history.
export function RecentRuns({ cards = [] }) {
  const [runs, setRuns] = useState(null);
  const [open, setOpen] = useState(false);
  const key = cards.map(c => c.tpl).join(',');
  useEffect(() => { if (!key) return undefined; let alive = true;
    Promise.all(key.split(',').map(t => fetch(apiUrl(`/api/reputation/fuses/record/${t}`)).then(r => r.json()).catch(() => null)))
      .then(all => alive && setRuns(all.flatMap(x => (x?.runs || []).filter(r => r.real)).sort((a, b) => b.at - a.at).slice(0, 8)));
    return () => { alive = false; }; }, [key]);
  if (!runs?.length) return null;
  const last = runs[0]; const c = cards.find(x => x.tpl === last.card); const t = TIER[c?.tier] || TIER.gold;
  const first = runs[runs.length - 1]; const day = v => new Date(v * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  return <section className="rr" data-testid="recent-runs"><span className="m-label">🕘 YOUR LAST REAL FUSE · CLOSED</span>
    <div className="rr-row">
      <div className={`rr-card ${open ? 'is-open' : ''}`} role="button" tabIndex={0} aria-expanded={open} aria-label={`${last.label} — closed, show its history`} data-testid="recent-card"
        onClick={e => { if (!e.target.closest('.fcd-flip')) setOpen(o => !o); }} onKeyDown={e => e.key === 'Enter' && setOpen(o => !o)}>
        {c ? <LiveFuseCard r={primeRow({ ...c, real: false })} aura="" look={t.look} label="🕘 CLOSED · now paper" /> : <span className="rr-ghost">{last.label}</span>}
        <b className="rr-stamp" aria-hidden="true">CLOSED</b></div>
      <div className="rr-side"><b>{last.label}</b>
        <span className="m-num">closed {day(last.at)} at {usd(last.endUsd)} <em className={last.pct >= 0 ? 'm-pos' : 'm-neg'}>{pct(last.pct)} on its last run</em></span>
        <small className="m-dim">{runs.length} real run{runs.length === 1 ? '' : 's'} on record since {day(first.at)}. The card you see is this tier's live paper card — your real coins were all sold. Tap the card for the history.</small>
        {open && <ul className="rr-list">{runs.map((r, i) => <li key={`${r.card}-${r.at}`} style={{ '--i': i }}><span>{day(r.at)}</span><span className="m-num">{usd(r.startUsd)} → {usd(r.endUsd)}</span><em className={`m-num ${r.pct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(r.pct)}</em></li>)}</ul>}</div>
    </div>
  </section>;
}

// 📜 A tier card's permanent record (every run it ever finished, kept forever on the server's append-only ledger)
export function CardRecord({ tpl }) {
  const [r, setR] = useState(null);
  useEffect(() => { let alive = true; const load = () => fetch(apiUrl(`/api/reputation/fuses/record/${tpl}`)).then(x => x.json()).then(x => alive && setR(x)).catch(() => {});
    load(); const t = setInterval(load, 120000); return () => { alive = false; clearInterval(t); }; }, [tpl]);
  if (!r?.n) return <small className="m-dim prime-record" data-testid={`record-${tpl}`}>📜 Record starts with its first finished run</small>;
  return <small className="prime-record" data-testid={`record-${tpl}`} data-tip="Every run this card ever finished — kept forever, never edited">📜 {r.n} runs · {r.won} up · best {pct(r.bestPct)} · worst {pct(r.worstPct)} · avg {pct(r.avgPct)}</small>;
}
