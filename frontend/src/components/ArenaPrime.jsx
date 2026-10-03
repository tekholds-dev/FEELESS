import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useAdmin } from '../lib/adminCall';
import { LiveFuseCard, revalue } from './FuseCard';
import { useLivePrices } from '../lib/livePrices';
import { openWarRoom } from './WarRoomHost';
import { CardEarnings } from './CardEarnings';
import { RoundBell, TrailSummary, CycleBuilder, usd, usdK, pct, txUrl } from './FuseMoney';

// ⭐ ARENA PRIME: FEELESS's own top-tier cards, FULLY AUTO on paper — auto TP/SL, auto-compound, 2 coins rotate every 6h. Different
// from creator picks: these are the public proof the automation works before any trader's config goes auto. "Buy now" loads the
// card into the Lab (traders: up to 3 pools + 3 runners; you approve one wallet transaction).
const CYCLE_PICKS = [['off', 'Off', "Keep the tier's own shape every round"], ['classic', '⚓→🔥', 'anchor (3 majors + 1 new major) → degen (1 major + 3 runners) → anchor → mixed (2 majors + new major + runner)'],
  ['adaptive', '🧠 Adaptive', 'A −3% round rests in anchor (3 majors + 1 new major), a +5% round goes degen, anything else = mixed'], ['safe', '⚓⇄⚖', 'anchor (3 majors + 1 new major) ⇄ mixed (2 majors + new major + runner)'], ['press', '🔥⇄⚖', 'degen (1 major + 3 runners) ⇄ mixed (2 majors + new major + runner)'],
  ['rescue', '🛟', '🛡 safest (3 majors + 1 new major) ⇄ ⚖ breakeven (1 high-volume pool + 3 high-volume runners)'], ['auto', '🤖 Auto', 'Engine picks each round: deep red → breakeven · red → safest · +5% → degen · flat → mixed']];
const LEG_MODES = ['', 'replace', 'park', 'hold'];   // '' = follow the card
const LEG_WORD = { '': '🃏 card', replace: '⇄ replace', park: '🅿 park', hold: '❄ hold' };
const KIND = { rescue: '🛟 Rescue cycle', fix: '🔧 Config fixed', streak: '📈 Streak', 'ride-end': '🏇 Ride over', rug: '🚨 Rug shield', payout: '💸 Paid to wallet', tp: '💰 Auto TP', sl: '🛑 Auto stop', rotate: '⇄ Rotate', compound: '♻ Compound', deal: '🃏 Dealt', floor: '🛡 Floor', park: '🅿 Parked', rebuy: '↩ Bought back', phase: '🔄 Phase', topup: '💵 Top-up', defund: '↩ Back to paper', run: '🏁 Run closed', ride: '🏇 Riding' };
// Tier FX: 💎 Diamond = frost aura + prism ring + glints · 🥇 Gold = gold dust + shine sweep · 🔥 Blaze = fire + embers.
// They burn brighter (is-hot) when the card is up ≥ +10%. Transform/opacity only; frozen under fx-lite / reduced motion.
// Each tier is its OWN MetaCard build: design pattern, rarity frame, colours and aura — recognisable at a glance (and in lite mode).
const TIER = {
  diamond: { aura: 'frost', name: 'DIAMOND', look: { design: 'prism', rarity: 'legendary', accent: '#9fe3ff', accent2: '#e4d4ff' } },
  gold: { aura: 'gold', name: 'GOLD', look: { design: 'obsidian', rarity: 'epic', accent: '#ffd56a', accent2: '#ff9a4d' } },
  blaze: { aura: 'fire', name: 'BLAZE', look: { design: 'ember', rarity: 'epic', accent: '#ff7a2f', accent2: '#ff3d5a' } },
  next: { aura: 'lightning', name: 'NEXT LEVEL', look: { design: 'plasma', rarity: 'mythic', accent: '#c58bff', accent2: '#3cdcff' } },
  ever: { aura: 'aurora', name: 'EVERLASTING', look: { design: 'nebula', rarity: 'legendary', accent: '#19f58f', accent2: '#6ad7ff' } },
};
// HQ ⚡ meta config: the settings the Arena proof backs today (hourly rotation of 1 coin, −15% floor, compound on, park & rebuy).
export const PRIME_META = { rotateHours: 1, rotateCount: 1, floorPct: 15, compound: true, slMode: 'park' };
// realizedUsd = what the card PAID OUT (walletUsd) — never the gross take-profits (those mostly compounded back in and are still held)
export const primeRow = c => ({ id: c.id, name: c.label, closed: false, costUsd: c.startUsd, valueUsd: c.valueUsd, realizedUsd: c.walletUsd || 0,
  // extra = everything that's the card's but not a coin: cash + parked SOL + what it PAID OUT (live value must include it, like the server)
  baseUsd: c.startUsd, extraUsd: (c.cash || 0) + (c.parked || []).reduce((a, p) => a + (p.usd || 0), 0) + (c.walletUsd || 0),
  pnlUsd: c.valueUsd - c.startUsd, pnlPct: c.pnlPct,
  legs: c.legs.map(l => ({ pairAddress: l.pairAddress, symbol: l.symbol, role: l.role, mint: l.mint, usd: l.costUsd, tokens: l.units, valueUsd: l.usd,
    pnlUsd: l.usd - l.costUsd, pnlPct: l.costUsd ? (l.usd / l.costUsd - 1) * 100 : 0, priced: true, priceNow: l.now, stars: l.stars, liq: l.liq, buying: l.buying || (c.real && !(l.usd > 0)) })) });

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
      <p className="m-dim">Only 3–5★ coins: a stable major anchor (SOL / JitoSOL / cbBTC — never rotated) + deep pools + gated runners. Auto TP / SL per coin · {d.cfg.compound ? 'gains auto-compound into the other coins' : 'gains kept as cash'} · the {d.cfg.rotateCount} weakest rotate every {d.cfg.rotateHours < 1 ? `${Math.round(d.cfg.rotateHours * 60)} min` : `${d.cfg.rotateHours}h`} (a floored card is re-dealt at once) · 🛡 card floor at −{d.cfg.floorPct}% (everything into the anchor). {d.cards.some(c => c.real) ? ' 💵 REAL cards trade from the FEELESS Fuse wallet — every swap has its transaction below the card.' : ' Paper fills at the price a wallet would really get (pool impact both ways).'} Fees tracked apart, never in P&L.</p>
      {d.paperMatch?.n > 0 && <span className="m-chip ok" data-tip="Every ~5 min the coins on these cards are priced the way paper fills them AND with a real Jupiter quote for the same $. + = real gives more coins than paper." data-testid="paper-match">📏 Paper vs real quotes: avg {d.paperMatch.avgDevPct >= 0 ? '+' : ''}{d.paperMatch.avgDevPct}% · {d.paperMatch.within2Pct}% within 2% · {d.paperMatch.n} checks</span>}</header>
    <div className="prime-row">{d.cards.map(c0 => { const rv = revalue(primeRow(c0), live); const c = { ...c0, pnlPct: rv.pnlPct, valueUsd: rv.valueUsd }; const t = TIER[c.tier] || TIER.gold; return <article key={c.id} className={`prime-card t-${c.tpl} tier-${c.tier || 'gold'} ${c.pnlPct >= 10 ? 'is-hot' : ''}`} data-testid={`prime-${c.tpl}`}>
      <span className="prime-tier" aria-hidden="true"><i className="pt-ring" /><i className="pt-sweep" />{Array.from({ length: 6 }, (_, i) => <i key={i} className="pt-spark" style={{ '--i': i }} />)}</span>
      <b className="prime-badge">{t.name}</b><span className={`prime-real ${c.real ? 'is-real' : 'is-paper'}`} data-tip={c.real ? `Real money from the FEELESS Fuse wallet since ${new Date((c.realSince || 0) * 1000).toLocaleDateString()} — every swap is on-chain` : 'Paper at true fills — same engine, same entries, no money'} data-testid={`prime-real-${c.tpl}`}>{c.real ? '💵 REAL MONEY' : '📄 PAPER'}</span>{d.roundWinner?.id === c.id && <span className="prime-crown" data-testid={`prime-crown-${c.tpl}`} data-tip="Best card of the last round">🏆 ROUND WINNER</span>}{c.why && <small className="prime-why">{c.why}</small>}
      {c.cycle && <span className="prime-phase" data-tip="This tier cycles every round: anchor (rest in majors) → degen (runners strike) → anchor → mixed (half and half). One continuous run.">🔄 {(c.phase || 'start').toUpperCase()} ROUND · next {c.cycle[(c.rounds || 0) % c.cycle.length]}</span>}
      <LiveFuseCard r={primeRow(c)} aura={t.aura} look={t.look} label={c.real ? '💵 REAL · FUSE WALLET' : '📄 PAPER · TRUE FILLS'} />
      {c.cfgView && <div className="prime-cfgv" data-tip="This card's live config (changes show here at once)">{[`⏱ ${c.cfgView.clockMin}m`, `🔄 ${c.cfgView.cycle || 'off'}${c.cycleFix ? ` · fix ${c.cycleFix}` : ''}`, `⏳ ${c.cfgView.confirm}× · −${c.cfgView.minDrop}%`, `🔒 ${c.cfgView.holdMin}m`, `🧩 /${c.cfgView.reshape}`, `🛑 ${c.cfgView.slMode}`, c.cfgView.locked ? '🔐 locked' : null, c.phase ? `▸ ${c.phase}` : null].filter(Boolean).map(t => <span key={t} className="m-chip">{t}</span>)}</div>}
      <ul className="prime-legs">{c.legs.map(l => ({ ...l, pnlPct: l.pnlPct ?? (l.costUsd ? (l.usd / l.costUsd - 1) * 100 : 0) })).map(l => <li key={l.pairAddress}><b role="button" tabIndex={0} className="pl-open" data-tip="Open its chart — trade this coin on its own" onClick={() => openWarRoom({ chainId: 'solana', pairAddress: l.pairAddress, baseToken: { address: l.mint, symbol: l.symbol } })}>${l.symbol}</b><small className={`pl-${l.role}`} data-tip={l.ride ? 'Riding: frozen through rounds until it falls 30% from its high' : undefined}>{l.ride ? '🏇 riding' : l.role === 'anchor' ? '⚓ anchor' : l.role}</small><i data-tip={`${l.stars || 3}★ — ${l.role === 'anchor' ? 'real major, the stable base' : l.role === 'pool' ? 'depth + volume' : 'runner score'}`}>{'★'.repeat(l.stars || 3)}</i>
        <em key={l.pnlPct.toFixed(1)} className={`m-num fl-tick ${l.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{l.pnlPct >= 0 ? '+' : ''}{l.pnlPct.toFixed(1)}%</em></li>)}</ul>
      {c.parked?.length > 0 && <ul className="prime-parked">{c.parked.map(p => <li key={p.pairAddress} data-tip="Stopped out and sold to SOL — the slot is kept; it's bought back when price returns to its entry with momentum">🅿 ${p.symbol} <b className="m-num">${p.usd.toFixed(2)}</b> parked · back at ${Number(p.backAt).toPrecision(3)}</li>)}</ul>}
      <div className="prime-round" data-tip={`One round = one rotation (every ${d.cfg.rotateHours < 1 ? `${Math.round(d.cfg.rotateHours * 60)} min` : `${d.cfg.rotateHours}h`}). The best card each round is crowned.`}>
        <span><small>ROUND</small><b className="m-num">{(c.rounds || 0) + 1}</b></span>
        <span><small>THIS ROUND</small><b key={(c.roundPct || 0).toFixed(1)} className={`m-num fl-tick ${(c.roundPct || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{(c.roundPct || 0) >= 0 ? '+' : ''}{(c.roundPct || 0).toFixed(1)}%</b></span>
        <span><small>ROUNDS WON</small><b className="m-num">{c.roundWins || 0}</b></span></div>
      <div className="prime-rec" data-testid={`prime-rec-${c.tpl}`}><span data-tip="Of the last logged days (max 10), how many the card was up ≥ +10% over 24h. The goal is 8/10 — the Arena shows the truth, never a promise.">
        <small>GOOD DAYS (+10%)</small><b className="m-num">{c.loggedDays ? `${c.goodDays}/${c.loggedDays}` : '—'}</b></span>
        <span data-tip={`Lowest this run has been. The floor moves everything into the anchor at −${d.cfg.floorPct}%, so −25% is never reached short of a price gap.`}><small>WORST</small><b className={`m-num ${(c.lowPct || 0) < 0 ? 'm-neg' : ''}`}>{(c.lowPct || 0).toFixed(1)}%</b></span>
        {c.floored && <span className="prime-floored" data-tip="Floored: holding the anchor until tomorrow's fresh deal">🛡 FLOORED</span>}</div>
      <div className="prime-stats"><span data-tip={`Profit = now ${usd(c.valueUsd)} − put in ${usd(c.startUsd)} (fees apart)`}><small>PROFIT</small><b key={c.pnlPct.toFixed(1)} className={`m-num fl-tick ${c.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{usdK(c.valueUsd - c.startUsd)}</b><small className={`ps-pct ${c.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(c.pnlPct)}</small></span>
        <span data-tip="Profit already paid out of the card to the owner's wallet"><small>PAID OUT</small><b className="m-num m-pos">{usdK(c.walletUsd)}</b></span>
        {c.floored ? <span data-tip="Floored: everything moved into the anchor; the card is re-dealt with fresh 3★+ coins (Arena picks first) on the next tick — a new run"><small>FLOORED</small><b className="m-num">re-dealing…</b></span>
        : <RoundBell at={c.nextRoundAt || c.lastRotateAt + d.cfg.rotateHours * 3600} sec={c.bellSec || 10} label={`ROUND ${(c.rounds || 0) + 2}`} />}</div>
      {c.realBook && <div className="prime-money" data-testid={`prime-book-${c.tpl}`}><span className="m-label">💵 REAL BOOK · FUNDED {usd(c.realBook.fundedUsd)} · {c.realBook.swaps} SWAPS · NETWORK FEES {usd(c.realBook.feesUsd)}</span>
        <ul className="prime-txs">{c.realBook.orders.slice(0, 5).map((o, i) => <li key={i}><b>{o.side === 'topup' ? '💵' : o.side === 'buy' ? '🟢' : '🔴'}</b><span>{o.side === 'topup' ? 'top-up' : `${o.side} $${o.symbol}`}</span>
          <em className="m-num">{usd(o.usd)}</em>{o.sig ? <a href={txUrl(o.sig)} target="_blank" rel="noreferrer" data-tip="Open the transaction">tx ↗</a> : <i />}</li>)}</ul></div>}
      <CardRecord tpl={c.tpl} />
      <div className="prime-acts"><button type="button" className="m-btn" onClick={() => setOpen(open === c.id ? null : c.id)} data-testid={`prime-earn-${c.tpl}`}>🪟 Open card · profit trail</button>
        <button type="button" className="m-btn primary m-go" onClick={() => { onLoad?.(c.legs.map(l => ({ chainId: 'solana', pairAddress: l.pairAddress, symbol: l.symbol, baseAddress: l.mint, runner: l.role === 'runner', role: l.role }))); toast.success(`${c.label} loaded into the Lab — you approve the buy`); }} data-testid={`prime-buy-${c.tpl}`}>⚡ Buy now</button></div>
      {open === c.id && <CardEarnings title={c.label} events={(c.audit || c.events).map(e => ({ ...e, label: e.kind === 'tp' ? ({ ride: '🚀 Ride · house money', bank: '🏦 Banked 75%' }[e.mode] || KIND.tp) : KIND[e.kind] || e.kind }))} taken={c.walletUsd || 0} compounded={c.compoundedUsd}
        book={{ putIn: c.startUsd || 0, held: Math.max(0, (c.valueUsd || 0) - (c.walletUsd || 0)), taken: c.walletUsd || 0, fees: c.feesUsd, rounds: c.rounds }} fees={c.feesUsd} onClose={() => setOpen(null)} paper={!c.real}
        extra={<TrailSummary events={c.audit || c.events} legs={c.legs} />}
        legs={c.legs.map(l => ({ ...l, ...(p => (p > 0 && l.entry ? { now: p, pnlPct: (p / l.entry - 1) * 100, usdNow: l.units * p } : { usdNow: l.usd }))(live.get?.(l.pairAddress)?.price), rundown: l.role === 'anchor' ? 'Solid hold — never stopped or rotated; the floor moves everything here' : `TP +${c.tp}% (momentum decides ride / gain / bank) · stop −${c.sl}% (cut at −${c.sl / 2}% if fading) · rotates when weakest` }))} autos={c.events.filter(e => Date.now() / 1000 - e.at < 86400 && e.kind !== 'deal').map(e => ({ at: e.at, text: `${KIND[e.kind] || e.kind} ${e.symbol ? `$${e.symbol} ` : ''}— ${e.why || ''}`, url: '#' }))} />}
    </article>; })}</div>
  </section>;
}

// HQ › ⚔ Arena: Prime controls — on/off, size, rotation (hours + coins), compound, deal fresh cards.
export function PrimeControls({ call }) {
  const d = usePrime(30000);
  const [cfg, setCfg] = useState(null);
  useEffect(() => { if (d?.cfg && !cfg) setCfg(d.cfg); }, [d, cfg]);
  const [mins, setMins] = useState('');
  useEffect(() => { if (cfg) setMins(String(Math.round(cfg.rotateHours * 60))); }, [cfg]);
  if (!cfg) return null;
  const save = (patch, reset = false) => call('/admin/arena/prime', { method: 'POST', body: JSON.stringify({ cfg: patch, reset }) })
    .then(r => { setCfg(r.cfg); toast.success(reset ? 'Fresh Prime cards dealt' : 'Prime config saved'); }).catch(e => toast.error(e.message));
  // HQ ⇄ one coin / 🃏 one tier — paper cards only, audited server-side.
  const act = (body, msg) => call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(body) }).then(() => { toast.success(msg); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message));
  const seg = (k, vals, fmt) => <div className="m-seg">{vals.map(v => <button key={v} type="button" className={cfg[k] === v ? 'active' : ''} onClick={() => save({ [k]: v })}>{fmt(v)}</button>)}</div>;
  const cyc = cfg.cycles || {};
  return <section className="m-card fops" data-testid="prime-controls"><div className="m-row"><span className="m-label">⭐ ARENA PRIME · FULLY AUTO (PAPER)</span>
    <label className="m-toggle"><input type="checkbox" checked={cfg.on} onChange={e => save({ on: e.target.checked })} /><span>{cfg.on ? 'Running' : 'Off'}</span></label></div>
    <div className="prime-ctl"><span>Size</span>{seg('sizeUsd', [25, 100, 500], v => `$${v}`)}<span data-tip="One clock for every swap: the weakest coins rotate out AND floored cards re-deal — replacements come from the Arena first (battle / stage cards, this round's runners, lit cards), then any 3★+ coin">Rotate every</span>{seg('rotateHours', [5 / 60, 0.25, 0.5, 1], v => (v < 1 ? `${v * 60}m` : `${v}h`))}
      <label className="prime-min" data-tip="Any interval: 15 min – 48 h. The weakest non-anchor coins rotate out on this clock."><input className="m-input m-num" inputMode="numeric" value={mins} onChange={e => setMins(e.target.value.replace(/[^0-9]/g, ''))}
        onBlur={() => Number(mins) >= 15 && Number(mins) !== Math.round(cfg.rotateHours * 60) && save({ rotateHours: Math.min(48, Number(mins) / 60) })} onKeyDown={e => e.key === 'Enter' && e.currentTarget.blur()} data-testid="prime-rotate-min" /><span>min</span></label>{null}
      <span>Coins per rotation</span>{seg('rotateCount', [1, 2, 3], v => `${v}`)}
      <span data-tip="Rotation only swaps a coin that is actually losing — winners are never churned (fewer fees, less price impact)">Rotate only coins down</span>{seg('rotateMinDrop', [0, 5, 10, 20], v => (v ? `−${v}%` : 'any'))}
      <span data-tip="⏳ Patience: a coin is only rotated after losing this many rounds IN A ROW — one noisy 5-min dip never sells it">Losing rounds before a swap</span>{seg('rotateConfirm', [1, 2, 3, 4], v => `${v}`)}
      <span data-tip="A freshly bought coin is never flipped straight back out">Hold a new coin at least</span>{seg('minHoldMins', [0, 15, 30, 60], v => (v ? `${v}m` : 'off'))}
      <label className="m-toggle" data-tip="🔧 The engine fixes itself from the sim brain: runner weather (strict runners when they're bleeding) + its rotation pick. Never touches your clock."><input type="checkbox" checked={cfg.autoBrain !== false} onChange={e => save({ autoBrain: e.target.checked })} data-testid="prime-autobrain" /><span>🔧 Engine self-fix {cfg.strictRunners ? '· 🌧 strict runners ON' : ''}</span></label>
      <span data-tip="🛟 When a card falls this far under what it started with, it switches to the rescue cycle (safest run ⇄ breakeven runners)">Rescue at</span>{seg('rescuePct', [30, 40, 50, 60], v => `−${v}%`)}
      <span data-tip="How often a cycling card re-shapes. Every re-shape sells + re-buys coins — every 6 rounds on 5-min rounds = every 30 min">Re-shape every</span>{seg('cycleEvery', [1, 3, 6, 12], v => `${v} rnd`)}
      <span data-tip="Rounds per run: when they're done the run closes on the record (its %) and the next run starts from there. ∞ = one endless run. Every round opens with a 10s countdown.">Rounds per run</span>{seg('roundsPerRun', [0, 5, 10, 20, 50], v => (v ? `${v}` : '∞'))}
      <span data-tip="Card-level floor: at this loss every pool + runner moves into the anchor, then the card is re-dealt as a new run">Floor</span>{seg('floorPct', [10, 15, 20, 25], v => `−${v}%`)}
      <label className="m-toggle"><input type="checkbox" checked={cfg.compound} onChange={e => save({ compound: e.target.checked })} /><span>Auto-compound gains</span></label>
      <label className="m-toggle" data-tip="A coin that ran +50% is sold before it gives it all back (≤ +5% left) — winners never turn into losers"><input type="checkbox" checked={cfg.trail !== false} onChange={e => save({ trail: e.target.checked })} data-testid="prime-trail" /><span>🔒 Lock +50% runs</span></label>
      <span data-tip="What a stop does: ⇄ swap the coin for the best gated one · 🅿 sell to SOL, keep the slot, buy back at entry with momentum · ❄ never sell on a stop (the floor still protects)">On stop</span>{seg('slMode', ['replace', 'park', 'hold'], v => ({ replace: '⇄ Replace', park: '🅿 Park & rebuy', hold: '❄ Hold' }[v]))}</div>
    <div className="prime-cycles" data-testid="prime-cycles"><span className="m-label" data-tip="What each tier deals into every round (same run, P&L continues)">🔄 ROUND CYCLES</span>
      {(d?.cards || []).map(c => <div key={c.tpl} className="m-row"><b>{c.label}</b><span className="m-seg" role="group">{CYCLE_PICKS.map(([m, l, tip]) =>
        <button key={m} type="button" className={(cyc[c.tpl] || 'off') === m ? 'active' : ''} data-tip={tip} onClick={() => save({ cycles: { ...cyc, [c.tpl]: m } })} data-testid={`cycle-${c.tpl}-${m}`}>{l}</button>)}</span>
        <CycleBuilder value={cyc[c.tpl]} onChange={v => save({ cycles: { ...cyc, [c.tpl]: v } })} />
        <span className="m-seg" role="group" data-tip="Share of every profit take paid straight to the owner's wallet — the rest compounds">{[0, 25, 50, 75, 100].map(v =>
          <button key={v} type="button" className={(cfg.payouts || {})[c.tpl] === v ? 'active' : ''} onClick={() => save({ payouts: { ...(cfg.payouts || {}), [c.tpl]: v } })} data-testid={`payout-${c.tpl}-${v}`}>💸{v}%</button>)}</span></div>)}
      <div className="m-row"><b>Compound style</b><span className="m-seg" role="group">{[['smart', '🧲 Smart', 'Gains go to the strongest coins (momentum-weighted), never into fading ones'], ['even', '⚖ Even', 'Gains split evenly across the other coins']].map(([v, l, tip]) =>
        <button key={v} type="button" data-tip={tip} className={(cfg.compoundStyle || 'smart') === v ? 'active' : ''} onClick={() => save({ compoundStyle: v })}>{l}</button>)}</span></div></div>
    <div className="m-row"><button type="button" className="m-btn primary m-go" onClick={() => save(PRIME_META)} data-testid="prime-meta" data-tip="Hourly rotation of 1 coin · −15% floor · compound on · park & rebuy on stops">⚡ Apply meta config</button>
      <small className="m-dim">the config the Arena proof backs right now — tweak anything after</small></div>
    <div className="prime-edit">{(d?.cards || []).map(c => <div key={c.id} className="m-row"><b>{c.label}</b>
      {c.legs.map(l => { const next = LEG_MODES[(LEG_MODES.indexOf(l.slMode || '') + 1) % LEG_MODES.length];
        return <span key={l.pairAddress} className={`prime-leg ${l.frozen ? 'is-frozen' : ''}`}>
        <button type="button" className="m-btn" disabled={l.frozen} data-tip={`Replace $${l.symbol} with the best 3★+ ${l.role} not on the card (same $)`} onClick={() => act({ replace: { tpl: c.tpl, pairAddress: l.pairAddress } }, `$${l.symbol} replaced`)} data-testid={`prime-swap-${c.tpl}-${l.pairAddress}`}>⇄ ${l.symbol}</button>
        <button type="button" className={`m-btn ${l.frozen ? 'is-on' : ''}`} aria-pressed={l.frozen} data-tip={l.frozen ? 'Frozen: never rotated or stopped (the floor still protects). Tap to unfreeze.' : 'Freeze: the engine never rotates or stops this coin'} onClick={() => act({ leg: { tpl: c.tpl, pairAddress: l.pairAddress, frozen: !l.frozen } }, l.frozen ? `$${l.symbol} back under the engine` : `❄ $${l.symbol} frozen`)} data-testid={`prime-frz-${c.tpl}-${l.pairAddress}`}>❄</button>
        <button type="button" className="m-btn" data-tip={`At this coin's stop: ${LEG_WORD[l.slMode || '']} — tap for ${LEG_WORD[next]}`} onClick={() => act({ leg: { tpl: c.tpl, pairAddress: l.pairAddress, slMode: next } }, `$${l.symbol} stop: ${LEG_WORD[next]}`)} data-testid={`prime-mode-${c.tpl}-${l.pairAddress}`}>{LEG_WORD[l.slMode || ''].split(' ')[0]}</button></span>; })}
      <button type="button" className="m-btn" onClick={() => act({ redeal: c.tpl }, `${c.label} re-dealt`)} data-testid={`prime-redeal-${c.tpl}`}>🃏 Re-deal</button>
      <button type="button" className={`m-btn ${d?.locks?.[c.tpl] ? 'is-on' : ''}`} aria-pressed={!!d?.locks?.[c.tpl]} onClick={() => act({ lock: c.tpl, on: !d?.locks?.[c.tpl] }, d?.locks?.[c.tpl] ? `${c.label} follows the shared config again` : `🔒 ${c.label} config locked as it is now`)}
        data-tip="Lock this tier's FULL config as it is now (clock, cycle, payout, stops, floor…) — tunes, meta config and the engine never change it" data-testid={`prime-lock-${c.tpl}`}>{d?.locks?.[c.tpl] ? '🔒 Locked' : '🔓 Lock config'}</button></div>)}</div>
    <div className="m-row"><button type="button" className="m-btn" onClick={() => save({}, true)} data-testid="prime-reset">🃏 Deal fresh Prime cards</button>
      <small className="m-dim">{(d?.cards || []).map(c => `${c.label} ${c.pnlPct >= 0 ? '+' : ''}${c.pnlPct.toFixed(1)}%`).join(' · ') || 'dealing…'}</small></div></section>;
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
  ['rotateHours', '⏱ Round clock', [[0.08, '5m'], [0.25, '15m'], [0.5, '30m'], [1, '1h']], 'How long each round lasts'],
  ['rotateConfirm', '⏳ Patience', [[1, '1'], [2, '2'], [3, '3'], [4, '4']], 'Losing rounds in a row before a coin may be swapped (more = less churn, fewer fees)'],
  ['rotateMinDrop', '📉 Swap only below', [[5, '−5%'], [10, '−10%'], [15, '−15%'], [20, '−20%']], 'A coin is swapped only when it is at least this far down'],
  ['minHoldMins', '🔒 Min hold', [[15, '15m'], [30, '30m'], [60, '1h'], [120, '2h']], 'Every new coin is held at least this long'],
  ['cycleEvery', '🧩 Re-shape every', [[3, '3'], [6, '6'], [12, '12']], 'Rounds between shape changes'],
  ['slMode', '🛑 On a stop', [['replace', '⇄ replace'], ['park', '🅿 park'], ['hold', '❄ hold']], 'Replace with the best coin · sell to SOL and rebuy later · keep holding'],
  ['rescuePct', '🛟 Rescue at', [[30, '−30%'], [40, '−40%'], [50, '−50%'], [60, '−60%']], 'Card this far under its start → safest coins'],
  ['autoBrain', '🧠 Auto-tune', [[true, 'on'], [false, 'off']], 'Let the sim brain adjust patience / drop (never below 3 on 5m rounds)'],
];
const CYCLES = [['safe', '🛡 safe'], ['classic', 'classic'], ['adaptive', 'adaptive'], ['press', '🔥 press'], ['rescue', '🛟 rescue'], ['auto', '🤖 auto'], ['off', 'off']];
const ROUND_KEYS = ['rotateHours', 'rotateConfirm', 'rotateMinDrop', 'minHoldMins'];   // ⏱ group 1; the rest of EDIT = 🧬 shape group

// ✍ Type exact limits (server clamps every value to its safe range: slippage 0.1–3%, impact 0.2–10%, pool ≥ $0, swap $1+, daily $5+)
const TYPED = [['slippageBps', 'Slippage %', v => v * 100, v => v / 100, 0.1, 3, 0.1], ['maxImpactPct', 'Max price impact %', v => v, v => v, 0.2, 10, 0.1],
  ['minLiqUsd', 'Min pool $', v => v, v => v, 0, 10000000, 1000], ['maxSwapUsd', 'Max per swap $', v => v, v => v, 1, 10000, 1],
  ['dailyUsd', 'Daily cap $', v => v, v => v, 5, 100000, 5], ['minOrderUsd', 'Min buy $', v => v, v => v, 0.25, 50, 0.05]];
function TypedLimits({ keeper, busy, save }) {
  const [v, setV] = useState({});
  const cur = k => { const t = TYPED.find(x => x[0] === k); return keeper?.[k] == null ? '' : t[3](keeper[k]); };
  const dirty = Object.keys(v).filter(k => v[k] !== '' && Number(v[k]) !== Number(cur(k)));
  const go = () => save(Object.fromEntries(dirty.map(k => [k, TYPED.find(x => x[0] === k)[2](Number(v[k]))])), true).then(() => setV({}));
  return <div className="ce-typed" data-testid="typed-limits">{TYPED.map(([k, l, , , lo, hi, st]) => <label key={k} data-tip={`${lo} – ${hi}`}><small>{l}</small>
    <input className="m-input" type="number" min={lo} max={hi} step={st} placeholder={String(cur(k))} value={v[k] ?? ''} onChange={e => setV(x => ({ ...x, [k]: e.target.value }))} /></label>)}
    <button type="button" className="m-btn m-go" disabled={busy || !dirty.length} onClick={go}>Save {dirty.length || ''} limit{dirty.length === 1 ? '' : 's'}</button></div>;
}

function CardEditor({ c, cfg, keeper, locked, call }) {
  const [busy, setBusy] = useState(false);
  const save = async (patch, wallet) => {
    setBusy(true);
    try {
      if (wallet) await call('/admin/fuse-wallet/cfg', { method: 'POST', body: JSON.stringify(patch) });
      else {
        // a locked tier edits ONLY its own frozen config; an unlocked one edits the shared engine config
        await call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(locked ? { lock: c.tpl, patch } : { cfg: patch }) });
      }
      toast.success('Saved — applies from the next tick'); window.dispatchEvent(new Event('feeless:prime'));
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const seg = (key, label, opts, tip, cur, wallet) => <div key={key} className="ce-row" data-tip={tip}><small>{label}</small>
    <div className="m-seg">{opts.map(([v, t]) => <button key={String(v)} type="button" disabled={busy} className={String(cur) === String(v) ? 'active' : ''} aria-pressed={String(cur) === String(v)} onClick={() => save({ [key]: v }, wallet)}>{t}</button>)}</div></div>;
  const row = ([k, l, o, t]) => seg(k, l, o, t, k === 'rotateHours' ? (o.find(x => Math.abs(x[0] - (cfg?.[k] || 0)) < 0.02) || [cfg?.[k]])[0] : cfg?.[k]);
  const churn = (cfg?.rotateHours || 1) < 0.25 && (cfg?.rotateConfirm || 1) < 3;   // 5-min rounds + low patience = swaps on noise (fees, missed buys)
  return <details className="hrt-edit" data-testid="card-editor"><summary>⚙ Edit card {locked ? '· 🔒 locked — edits change only this card' : '· shared engine settings'}</summary>
    <div className="ce-group"><span className="m-label">⏱ ROUNDS · when a coin may be swapped</span>
      <div className="ce-grid">{EDIT.filter(e => ROUND_KEYS.includes(e[0])).map(row)}</div>
      {churn && <p className="m-note ce-warn" data-testid="churn-warn">⚠ {Math.round((cfg?.rotateHours || 0) * 60)}-min rounds with patience {cfg?.rotateConfirm || 1}: a coin is swapped after {(cfg?.rotateConfirm || 1) * Math.round((cfg?.rotateHours || 0) * 60)} min of noise — every swap pays fees and needs a real buy. Patience 3 is the proven setting.
        <button type="button" className="m-btn" disabled={busy} onClick={() => save({ rotateConfirm: 3 })}>Use 3</button></p>}</div>
    <div className="ce-group"><span className="m-label">🧬 SHAPE · which coins the card holds</span><div className="ce-grid">
      {EDIT.filter(e => !ROUND_KEYS.includes(e[0])).map(row)}
      <div className="ce-row" data-tip="The shapes this card cycles through"><small>🔄 Cycle</small><div className="m-seg">{CYCLES.map(([v, t]) => <button key={v} type="button" disabled={busy} className={(cfg?.cycles || {})[c.tpl] === v ? 'active' : ''} onClick={() => save({ cycles: { ...(cfg?.cycles || {}), [c.tpl]: v } })}>{t}</button>)}</div></div>
      <div className="ce-row" data-tip="Freeze this tier's whole config so engine tunes never change it"><small>🔒 Lock tier</small><div className="m-seg">{[[true, 'locked'], [false, 'free']].map(([v, t]) => <button key={t} type="button" disabled={busy} className={!!locked === v ? 'active' : ''} onClick={() => { setBusy(true); call('/admin/arena/prime', { method: 'POST', body: JSON.stringify({ lock: c.tpl, on: v }) }).then(() => { toast.success(v ? '🔒 Locked' : 'Unlocked'); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)).finally(() => setBusy(false)); }}>{t}</button>)}</div></div>
    </div></div>
    <div className="ce-group"><span className="m-label">💵 REAL MONEY · limits on every real swap (server-enforced)</span>
      <TypedLimits keeper={keeper} busy={busy} save={save} /></div>
    <small className="m-dim">Rounds + shape are shared by every tier that isn't 🔒 locked. Real-money limits cover every real buy and sell.</small></details>;
}

export function HqRealCards({ addr, onCount }) {
  const [owner, setOwner] = useState(false);
  useEffect(() => { if (!addr) return; fetch(apiUrl(`/api/reputation/admin/is-admin/${addr}`)).then(r => r.json()).then(d => setOwner(!!(d.owner || d.admin))).catch(() => {}); }, [addr]);
  const { call } = useAdmin();
  const [busy, setBusy] = useState('');
  const [amt, setAmt] = useState('');
  const d = usePrime(30000);
  const real = (d?.cards || []).filter(c => c.real);
  const n = owner ? real.length : 0;
  useEffect(() => { onCount?.(n); }, [n, onCount]);   // My cards hides its "no cards" box under a real card
  if (!owner || !real.length) return null;
  const act = (tpl, action) => { if (action === 'defund' && !window.confirm('Sell every coin back to SOL? The card goes back to its paper card.')) return;
    setBusy(action); call('/admin/fuse-wallet/card', { method: 'POST', body: JSON.stringify({ tpl, action }) }).then(() => { toast.success(action === 'defund' ? '↩ Selling every coin to SOL' : action === 'halt' ? '⏸ Card paused' : '▶ Resumed'); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const topup = tpl => { const v = Number(amt); if (!(v >= 1)) { toast.error('Top up at least $1'); return; } if (!window.confirm(`Add $${v.toFixed(2)} from the Fuse wallet? A new real run starts at the new total.`)) return;
    setBusy('topup'); call('/admin/fuse-wallet/topup', { method: 'POST', body: JSON.stringify({ tpl, usd: v }) }).then(() => { toast.success(`＋ $${v.toFixed(2)} added`); setAmt(''); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  // 🎛 one-tap coin controls on YOUR real card (no trip to HQ): ⇄ swap a coin · ❄ freeze it · 🃏 re-deal the card (same money, same run)
  const prime = (body, ok, tag) => { setBusy(tag); call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(body) }).then(() => { toast.success(ok); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const ago = t => { const s = Math.max(0, Date.now() / 1000 - (t || 0)); return s < 60 ? `${s.toFixed(0)}s ago` : s < 3600 ? `${(s / 60).toFixed(0)}m ago` : `${(s / 3600).toFixed(1)}h ago`; };
  const fee = v => (v > 0 && v < 0.01 ? `$${v.toFixed(4)}` : usd(v));
  return <section className="m-card hq-reals" data-testid="hq-real-cards"><span className="m-label">💵 FEELESS REAL-MONEY TIER CARDS · FUSE WALLET</span>
    {real.map(c => { const t = TIER[c.tier] || TIER.gold; const b = c.realBook || {}; const k = b.keeper || {};
      const state = k.paused ? ['⏸', 'paused', 'is-warn'] : !k.armed ? ['○', 'not armed', 'is-warn'] : k.pending ? ['⏳', `sending ${k.pending}`, 'is-busy'] : c.legs.some(l => l.buying) ? ['⏳', 'retrying a buy', 'is-busy'] : ['●', 'in sync', 'is-ok'];
      const cf = d.lockCfg?.[c.tpl] ? { ...d.cfg, ...d.lockCfg[c.tpl] } : d.cfg;   // a locked tier runs its own config
      return <div key={c.id} className="hq-real">
        <div className="hq-real-card"><LiveFuseCard r={primeRow(c)} aura={t.aura} look={t.look} label="💵 REAL · FUSE WALLET" serverOnly /></div>
        <div className="hq-real-track">
          <div className="hrt-top"><b>{c.label}</b><span className={`hrt-state ${state[2]}`} data-tip="Keeper: moves the real coins to what the card says, every tick">{state[0]} {state[1]}</span></div>
          <div className="hrt-kpis">
            <RoundBell at={c.nextRoundAt || c.lastRotateAt + (cf?.rotateHours || 1) * 3600} sec={c.bellSec || 10} label={`ROUND ${(c.rounds || 0) + 1}`} />
            <span><small>ROUNDS DONE</small><b className="m-num">{c.rounds || 0}</b></span>
            <span data-tip="Every $ you funded this card with (all top-ups)"><small>PUT IN · TOTAL</small><b className="m-num">{usd(b.fundedUsd || c.startUsd)}</b></span>
            {b.fundedUsd > 0 && <span data-tip="Now vs everything you put in"><small>ALL-TIME</small><b className={`m-num ${(c.valueUsd - b.fundedUsd) >= 0 ? 'm-pos' : 'm-neg'}`}>{usd(c.valueUsd - b.fundedUsd)} · {pct((c.valueUsd / b.fundedUsd - 1) * 100)}</b></span>}
            <span data-tip="This run started at this value (a run restarts on top-ups, re-deals and fixes)"><small>THIS RUN FROM</small><b className="m-num">{usd(c.startUsd)}</b></span>
            {c.vsSolPct != null && <span data-tip={`Holding SOL over this run: ${pct(c.holdSolPct)}. Fund more only when this stays positive.`}><small>VS HOLDING SOL</small><b className={`m-num ${c.vsSolPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(c.vsSolPct)}</b></span>}
            <span data-tip="Value now · % vs this run's start"><small>NOW · THIS RUN</small><b key={(c.valueUsd || 0).toFixed(2)} className={`m-num fl-tick ${c.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{usd(c.valueUsd)} · {pct(c.pnlPct)}</b></span></div>
          <ul className="hrt-coins">{c.legs.map(l => <li key={l.pairAddress} className={l.buying ? 'is-buying' : ''}><b>{l.role === 'runner' ? '🏃' : '⚓'} ${l.symbol}</b>
            {l.buying || !(l.usd > 0) ? <em className="hrt-buy" data-tip={k.lastFail?.symbol === l.symbol ? `Last try: ${k.lastFail.err} — tap ⇄ to swap it for a coin that can be bought` : 'The keeper buys it on its next tick'}>{l.buying ? (k.lastFail?.symbol === l.symbol ? `⏳ ${String(k.lastFail.err || '').split(' (')[0].slice(0, 34)}` : '⏳ buying… keeper retries') : '⏳ empty — rebuy at the next round'}</em> : <><span>{usd(l.costUsd)} → {usd(l.usd)}</span><em className={l.pnlPct >= 0 ? 'm-pos' : 'm-neg'}>{pct(l.pnlPct)}</em></>}
            {l.symbol !== 'SOL' ? <span className="hrt-ctl">
              <button type="button" className="m-btn" disabled={!!busy || l.frozen} data-testid={`swap-${l.symbol}`} data-tip={l.frozen ? 'Frozen — unfreeze to swap it' : `Swap $${l.symbol} for the best coin of its kind not on the card (keeper trades it next tick)`}
                onClick={() => prime({ replace: { tpl: c.tpl, pairAddress: l.pairAddress } }, `⇄ $${l.symbol} swapped — keeper buys the new coin next tick`, `sw-${l.pairAddress}`)}>⇄</button>
              <button type="button" className={`m-btn ${l.frozen ? 'active' : ''}`} aria-pressed={!!l.frozen} disabled={!!busy} data-testid={`freeze-${l.symbol}`} data-tip={l.frozen ? `Unfreeze $${l.symbol}: the engine may rotate / stop it again` : `Freeze $${l.symbol}: never rotated or stopped (the card floor still protects you)`}
                onClick={() => prime({ leg: { tpl: c.tpl, pairAddress: l.pairAddress, frozen: !l.frozen } }, l.frozen ? `$${l.symbol} back under the engine` : `❄ $${l.symbol} frozen`, `fz-${l.pairAddress}`)}>❄</button></span> : <span />}</li>)}
            {(c.cash || 0) > 0.01 && <li><b>◎ cash</b><span>{usd(c.cash)}</span><em className="m-dim">SOL</em></li>}</ul>
          <div className="hrt-cfg" data-testid="hrt-cfg">{[[`⏱ ${Math.round((cf?.rotateHours || 0) * 60)}m rounds`, 'Round clock'], [`⏳ swap after ${cf?.rotateConfirm || 1} losing rounds · −${cf?.rotateMinDrop || 0}%`, 'A coin is swapped only after this many losing rounds in a row, and only this far down'],
            [`🔒 hold ≥ ${cf?.minHoldMins || 0}m`, 'Every new coin is held at least this long'], [`🔄 ${(cf?.cycles || {})[c.tpl] || c.cycleMode || 'off'}${c.cycleFix ? ` (fix: ${c.cycleFix})` : ''} · ${c.phase || '—'}`, 'Cycle and the shape it is in now'], [`🧩 re-shape every ${cf?.cycleEvery || 6} rounds`, 'How often the card changes shape'],
            [`🛑 stops: ${cf?.slMode || 'replace'}`, 'What happens when a coin hits its stop'], [`🛟 rescue at −${cf?.rescuePct || 50}%`, 'Card this far under its start → safest coins'], [`💧 real buys need $${((k.minLiqUsd || 0) / 1000).toFixed(0)}K pool`, 'Thinner coins stay paper-only'],
            [`🪙 min buy $${(k.minOrderUsd || 0).toFixed(2)} · max $${k.maxSwapUsd || 0}`, 'Smallest / largest single real swap'], [`↔ slippage ${((k.slippageBps || 0) / 100).toFixed(1)}%`, 'Retries add a little, never past 3%']].map(([t2, tip]) => <span key={t2} className="m-chip" data-tip={tip}>{t2}</span>)}</div>
          <CardEditor c={c} cfg={d.locks?.[c.tpl] ? { ...d.cfg, ...(d.lockCfg?.[c.tpl] || {}) } : d.cfg} keeper={k} locked={!!d.locks?.[c.tpl]} call={call} />
          <div className="hrt-acts">
            <button type="button" className="m-btn" disabled={!!busy || k.selling} onClick={() => act(c.tpl, k.halt ? 'resume' : 'halt')} data-tip={k.halt ? 'Keeper trades again' : 'Keeper stops trading this card (coins stay)'}>{k.halt ? '▶ Resume' : '⏸ Pause'}</button>
            <span className="hrt-top-up"><input className="m-input" type="number" min="1" step="1" placeholder="$" value={amt} onChange={e => setAmt(e.target.value)} aria-label="Top up amount" />
              <button type="button" className="m-btn m-go" disabled={!!busy || k.selling} onClick={() => topup(c.tpl)} data-tip="Add money from the Fuse wallet — a new real run at the new total">＋ Top up</button></span>
            <button type="button" className="m-btn" disabled={!!busy || k.selling} data-testid="redeal-real" data-tip="Fresh coins for this card NOW — same money, same run; frozen coins stay. The keeper trades the change next tick."
              onClick={() => window.confirm('Re-deal this card with fresh coins now? Same money, same run.') && prime({ redeal: c.tpl }, '🃏 Re-dealt — keeper trades the new coins next tick', 'redeal')}>🃏 Re-deal</button>
            <button type="button" className="m-btn danger" disabled={!!busy || k.selling} onClick={() => act(c.tpl, 'defund')} data-tip="Sell every coin to SOL — the card goes back to its paper card">{k.selling ? '↩ selling…' : '↩ Sell all'}</button></div>
          {k.lastFail && <small className="hrt-fail" data-tip={k.lastFail.err}>⚠ last miss: {k.lastFail.side} ${k.lastFail.symbol} · {ago(k.lastFail.at)} — retried automatically</small>}
          <small className="m-dim">{b.swaps || 0} swaps · network fees {fee(b.feesUsd || 0)} (wallet reserve pays) · last fill {k.lastFill ? ago(k.lastFill) : '—'}</small>
          <ul className="prime-txs">{(b.orders || []).slice(0, 6).map((o, i) => <li key={o.sig || i}><b>{o.side === 'topup' ? '💵' : o.side === 'buy' ? '🟢' : '🔴'}</b><span>{o.side === 'topup' ? 'funded' : `${o.side} $${o.symbol}`} <i className="m-dim">{ago(o.at)}</i></span>
            <em className="m-num">{usd(o.usd)}</em>{o.sig ? <a href={txUrl(o.sig)} target="_blank" rel="noreferrer">tx ↗</a> : <i />}</li>)}</ul></div></div>; })}</section>;
}


// 📜 A tier card's permanent record (every run it ever finished, kept forever on the server's append-only ledger)
export function CardRecord({ tpl }) {
  const [r, setR] = useState(null);
  useEffect(() => { let alive = true; const load = () => fetch(apiUrl(`/api/reputation/fuses/record/${tpl}`)).then(x => x.json()).then(x => alive && setR(x)).catch(() => {});
    load(); const t = setInterval(load, 120000); return () => { alive = false; clearInterval(t); }; }, [tpl]);
  if (!r?.n) return <small className="m-dim prime-record" data-testid={`record-${tpl}`}>📜 Record starts with its first finished run</small>;
  return <small className="prime-record" data-testid={`record-${tpl}`} data-tip="Every run this card ever finished — kept forever, never edited">📜 {r.n} runs · {r.won} up · best {pct(r.bestPct)} · worst {pct(r.worstPct)} · avg {pct(r.avgPct)}</small>;
}
