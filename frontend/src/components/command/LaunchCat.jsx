import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { Panther } from '../Panther';
import { readChatSession } from '../../lib/chatSession';
import NumInput from '../NumInput';
import { LookAvatar } from './CatLook';
import { CAT_VARIATIONS } from './catCoats';
import { useMyCat } from '../../lib/myCat';
import { FundReceipt } from './FundReceipt';
import { AgentDemo } from './AgentDemo';
import { AgentCritter } from './Critters';
import '../../styles/launchCat.css';

// 🚀 LAUNCH A CAT (owner, 2026-10-20): pick up to two AI brains from OpenRouter's whole public list, choose how they work together, write
// ONE brief they keep for life, choose how model calls are paid. A brain is asked once before a buy and ≤ 3 times while the coin is live,
// only on a ±10% move — so credit pays for decisions, never a chat loop. You can chime in (advice); you never trade for it. Paper cats.
export const SORTS = [['smart', '♟ Smartest'], ['cheap', '💸 Cheapest'], ['ctx', '📚 Biggest memory'], ['new', '🆕 Newest']];
export const STEPS = ['🧠 Brains', '🤝 How they work', '🐱 Identity + risk + brief', '🚀 Launch → 💵 go real'];
const GEN_STEPS = ['🧠 Its minds', '🧭 How they work', '🎯 Its job + brief', '🚀 Launch → 👛 its wallet'];
// 📈 TRADING hunts coins on its own · 🧭 GENERAL does what you order (owner, 2026-10-23) — both end on the wallet switch (link → budget → REAL)
export const KIND = { trading: { eyebrow: '📈 TRADING AI CAT', cat: 'trading', brief: '📜 THE BRIEF', hint: 'e.g. Only buy coins sitting on their germ floor with higher lows. Bank half at +30%. Never chase a green candle.',
  pitch: 'Pick 1–2 trading models. They decide once before a buy and up to 3 times while a coin is live — only on a ±10% move.',
  next: ['🚀 launch', '🔑 save its recovery PIN', '👛 its own wallet', '💵 fund it once', '🤖 it trades inside your limits'] },
  general: { eyebrow: '🧭 GENERAL AI CAT', cat: '', brief: '📜 STANDING ORDERS', hint: 'e.g. You are my content scout: every morning find 3 trending crypto topics with sources and draft posts in my voice — never post or sign up without asking me. Coin orders: never more than 0.1 SOL a coin.',
  pitch: 'Pick 1–2 all-round models — its two minds. Ask in plain words: it answers from memory, or each mind researches half in its own cloud browser while you watch, then they merge. Coin orders go from its own wallet — you OK each one until you switch it to auto.',
  next: ['🚀 launch', '🔑 save its recovery PIN', '👛 its own wallet', '💵 fund it once', '✅ it checks with you · or 🤖 auto'] } };
// 🧾 THE PROMPT GENERATOR (owner 2026-10-30: "robust prompts for both kinds — specific, so both models work properly together"): the job's brief +
// HOW THE TWO WORK for the mode you picked + the house rules → one brief both models read on every step. Edit it freely before launch.
const STUCK = 'WHEN STUCK — after 2 failed tries take another route or report it. A human-needed step (my own sign-ins, CAPTCHAs, codes, payments, ID) never stops the rest: ask me exactly what you need and keep going on everything else.';
const NO_GUESS = ' Missing or stale data means SKIP, never a guess.';
export const SOLO = { general: `${STUCK}\n\nFINISH WITH — DONE (with links), NEEDS ME, STILL UNCERTAIN.`, trading: NO_GUESS.trim() };
export const COLLAB = {
  general: { plan: `HOW YOU TWO WORK — ONE GOAL. Mind A leads: restate the goal in one line, split it into two halves with no overlap and take one. Mind B takes the other half and checks A's key claims. If your half depends on theirs, do what you can, then get the rest through a handoff note. If one of you is blocked or done early, the other takes over what is left, so nothing stops and nothing is done twice. Keep every source. Save only vital facts to the shared cloud.\n\n${STUCK}\n\nFINISH WITH — one clear answer: DONE (with links), NEEDS ME, STILL UNCERTAIN.`,
    jobs: `HOW YOU TWO WORK — TWO JOBS. I give them as A: … B: …, and each of you owns your own job in your own window. Only one job given? Mind A owns it and Mind B supports: checks facts, finds what A needs and never does the same work twice. When one result helps the other (A's research feeds B's posts), hand it off with a note. Waiting on your partner? Do everything else first and say what you are waiting for. If one of you is blocked, the other still finishes.\n\n${STUCK}\n\nFINISH WITH — each result under its job, ready to use, then NEEDS ME.` },
  trading: { turns: 'HOW YOU TWO WORK — you take turns: one of you makes each call alone, on the evidence given (germ floor, buyers %, liquidity, holders, rug flags).' + NO_GUESS,
    discuss: 'HOW YOU TWO WORK — Brain A reads the coin first and answers BUY or SKIP with one reason; Brain B sees A\'s call, challenges it and makes the final call. Disagree whenever the evidence says so.' + NO_GUESS,
    together: 'HOW YOU TWO WORK — you both judge every coin on your own; money only moves when you BOTH say BUY, and a SELL from either of you exits.' + NO_GUESS,
    battle: 'HOW YOU TWO WORK — each of you trades every other coin on your own record; the better record earns trust. Never copy the other.' + NO_GUESS },
};
// 🔒 the house rules are HARDCODED on the server (cat_agent ACT_SYS + cat_policy refusals + URL guards) — shown here, never editable
export const HOUSE = { general: 'RULES — never invent facts; stop for human-needed sign-ins, CAPTCHAs, payments and ID checks; never create another agent or launch a coin on FEELESS; stay inside the $ cap per task.',
  trading: 'RULES — trade only on FEELESS; size inside the caps; never chase a candle that already ran; respect every rug / bundler / dev flag; explain each call in one sentence.' };
// 🔐 what protects the agent, said plainly BEFORE any money moves (owner 2026-10-30: "assure account secure and a recovery pin will show next"). Only true things.
const SAFE = gen => [['👛', 'Its own wallet', 'Separate from yours. Its keys stay with Crossmint, never in a browser.'], ['↩', 'Money comes back to you', 'Withdrawals go only to your linked wallet.'],
  ['🗝', 'Passwords sealed', 'Encrypted. Its minds never see them and its log never shows them.'], ['🛑', 'Your limits hold', gen ? 'A $ cap per task, and it asks before each move until you choose auto.' : 'Caps on every buy and every day, enforced by the server.']];
export function SafetyCard({ gen }) {
  return <section className="lct-safe" data-testid="lct-safe"><span className="m-label">🔐 HOW YOUR AGENT STAYS SAFE</span>
    <div className="lct-safe-grid">{SAFE(gen).map(([ic, t, why], i) => <span key={t} style={{ '--i': i }}><i aria-hidden="true">{ic}</i><b>{t}</b><small>{why}</small></span>)}</div>
    <p className="lct-safe-next" data-testid="lct-safe-next"><i aria-hidden="true">🔑</i><span><b>Next: your recovery PIN.</b> It shows once, right after launch. It gets this agent back if you lose this browser. Your wallet's own recovery phrase stays yours: FEELESS never asks for it.</span></p></section>;
}
export function briefFor(persona, kind, mode, solo = false) {
  const k = kind === 'general' ? 'general' : 'trading';
  const how = solo ? SOLO[k] : (COLLAB[k][mode] || COLLAB[k][k === 'general' ? 'plan' : 'discuss']);
  return [persona?.brief || '', how].filter(Boolean).join('\n\n').slice(0, 1200);   // HOUSE rules ride server-side on every call — never in the editable brief
}
// 🎯 a general agent's job, grouped so the choice is quick (the 26 presets)
export const JOB_GROUPS = [['research', '🔎 Research', ['detective', 'researcher', 'news', 'competitor', 'sports', 'kalshi']], ['content', '✍ Content', ['content', 'thread', 'video', 'brand', 'community', 'seo', 'email']],
  ['build', '💻 Build', ['code', 'fullstack', 'bugfix', 'landing']], ['crypto', '🪙 Crypto', ['coin_research', 'trench_scout', 'perps_brief', 'pools']], ['errands', '🌐 Errands', ['social', 'shopping', 'travel', 'admin', 'agent']]];

// 📈 a trading cat's two brains: our pick is DISCUSS — A reads, B sees A and makes the call (two looks before money moves, one short extra call)
export const BEST_MODE = 'discuss';
// 🧭 a GENERAL cat's two ways (owner 2026-10-30: "only 2 options" — cat_agent.MODES, change both): plan together → split → ONE answer, or each mind its own job
export const WORK_WAYS = [
  ['plan', '🧠🤝', 'Plan together → one answer', 'They plan it in a sentence each (tiny cost), split it, research in their own windows, then merge into one answer — e.g. "the best bet tonight".', [
    ['💬', 'Quick plan', 'a sentence each, minimal tokens'], ['🧠🧠', 'Split + run', 'each researches its half, FEELESS first'], ['☁', 'Keep the best', 'their scratch → the main cloud'], ['🔗', 'One answer', 'with sources']]],
  ['jobs', '🎯🎯', 'Each its own job', 'Give each mind its own job and both run at once — e.g. A writes the video script, B makes the social posts.', [
    ['✍', 'You give two jobs', 'A: … B: …'], ['⚡', 'Both run at once', 'own window, own tools'], ['📦', 'Two results', 'each under its job, the best kept']]],
];
// 🧭 how a General cat's two minds work (cat_agent.py — change both): shown as step 2 instead of the trading modes
export const GENERAL_FLOW = [
  ['⚡', 'You ask', 'mind A answers from memory when it can — one call, no browsing'],
  ['🧠🧠', 'They split it', 'each mind works its half in its own cloud browser — you watch both live'],
  ['✋', 'You step in', 'a sign-in or CAPTCHA pauses that window for you — it never types a password'],
  ['🔗', 'One answer', 'mind A merges both halves with sources — it stops at your $ cap per task'],
];
// 📈 a trading cat trades on FEELESS rails ONLY (owner 2026-10-29) — mirrors cat_keys.VENUES / VENUES_LIVE (change both)
export const VENUES = [['trench', '🫧 Trench', 'Solana coins on the FEELESS swap — its wallet sends, inside your caps', true],
  ['perps', '📉 Perps', 'the FEELESS perps desk — it proposes, the agent sender for perps is the next build', false]];
// 🔐 the API drawer (cat_keys.PROVIDERS mirror): your own keys for the cat's tools, sealed on the server, only the last 4 ever come back
export const API_PROVIDERS = [['openrouter', 'OpenRouter', 'its models run on YOUR key — you pay OpenRouter, no FEELESS credit used', true, 'sk-or-v1-…'],
  ['birdeye', 'Birdeye', 'holder + price reads for its scans', false, 'api key'], ['helius', 'Helius', 'its own Solana RPC — faster wallet + tape reads', false, 'api key'],
  ['x', 'X (Twitter)', "a bearer token — reads the coin's X chatter", false, 'bearer token'], ['telegram', 'Telegram channel', 'a public @channel it reads for calls', false, '@channel'],
  ['webhook', 'Signal webhook', 'your own signal URL (https) it reads before a buy', false, 'https://…']];
export function ApiDrawer({ rows, draft, onDraft, onSave, onDrop, busy }) {
  const [open, setOpen] = useState(!!draft);
  const saved = API_PROVIDERS.filter(([k]) => (rows || []).some(r => r.provider === k && r.saved)).length + Object.values(draft || {}).filter(Boolean).length;
  return <details className="akd" open={open} onToggle={e => setOpen(e.currentTarget.open)} data-testid="api-drawer">
    <summary data-tip="Add your own API keys for this cat's tools — sealed on the server, never shown again (last 4 only)"><i aria-hidden="true">🔐</i><b>API DRAWER</b>
      <small>{saved ? `${saved} key${saved > 1 ? 's' : ''} in` : 'your keys · optional'}</small><span className="akd-pips" aria-hidden="true">{API_PROVIDERS.map(([k]) => <u key={k} className={(rows || []).some(r => r.provider === k && r.saved) || draft?.[k] ? 'on' : ''} />)}</span></summary>
    <ul className="akd-list">{API_PROVIDERS.map(([k, label, use, wired, ph], i) => { const row = (rows || []).find(r => r.provider === k);
      return <li key={k} style={{ '--i': i }} className={row?.saved ? 'is-saved' : ''}>
        <span className="akd-name"><b>{label}</b><em className={wired ? 'is-live' : ''}>{wired ? 'LIVE' : 'STORED'}</em><small>{use}</small></span>
        {row?.saved ? <span className="akd-have"><code>••••{row.last4}</code><button type="button" className="m-btn" disabled={busy} onClick={() => onDrop?.(k)} data-tip={`Remove the ${label} key`} data-testid={`akd-drop-${k}`}>Remove</button></span>
          : <input className="m-input" type="password" autoComplete="off" spellCheck={false} placeholder={ph} value={draft?.[k] || ''} aria-label={`${label} key`} data-testid={`akd-${k}`}
            onChange={e => onDraft?.(k, e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && onSave && draft?.[k]) { e.preventDefault(); onSave(k, draft[k]); } }} />}
        {!row?.saved && onSave ? <button type="button" className="m-btn m-go" disabled={busy || !draft?.[k]} onClick={() => onSave(k, draft[k])} data-testid={`akd-save-${k}`} data-tip="Seal it on the server">Seal</button> : null}
      </li>; })}</ul>
    <p className="akd-note">🔒 Sealed at rest, never sent back. A key never opens another exchange — the cat trades on FEELESS rails only.</p>
  </details>;
}
export function VenuePick({ value, onChange }) {
  return <div className="akv" role="group" aria-label="Where it trades" data-testid="venue-pick"><span className="akv-h"><b>WHERE IT TRADES</b><small>FEELESS rails only</small></span>
    {VENUES.map(([k, l, why, live]) => { const on = value.includes(k);
      return <button key={k} type="button" className={`${on ? 'is-on' : ''}${live ? '' : ' is-next'}`} aria-pressed={on} data-tip={why} data-testid={`venue-${k}`}
        onClick={() => onChange(on ? (value.length > 1 ? value.filter(x => x !== k) : value) : [...value, k])}><b>{l}</b><small>{live ? 'LIVE' : 'PROPOSES'}</small></button>; })}</div>;
}
const PAGE = 60;
const CHIP = { degen: 'lct-c-degen', trading: 'lct-c-trading', thinking: 'lct-c-thinking', reasoning: 'lct-c-reasoning', meta: 'lct-c-meta', free: 'lct-c-free', agent: 'lct-c-agent', content: 'lct-c-content', code: 'lct-c-code' };
const DUO = { turns: 'is-turns', discuss: 'is-discuss', together: 'is-together', battle: 'is-battle' };
const WORD = { BUY: 'w-buy', SKIP: 'w-skip', HOLD: 'w-hold', SELL: 'w-sell', TRIM: 'w-trim', RULES: 'w-rules' };
export const fmtUsd = v => v == null ? '—' : v === 0 ? 'free' : v < 0.001 ? `$${v.toFixed(6)}` : v < 1 ? `$${v.toFixed(4)}` : `$${v.toFixed(2)}`;
const fmtM = v => v == null ? '—' : v === 0 ? 'free' : v < 0.01 ? `$${v.toFixed(3)}` : v < 10 ? `$${v.toFixed(2)}` : `$${Math.round(v)}`;   // $ per 1M tokens
export const mono = m => String(m?.provider || m?.name || '?').replace(/[^a-z0-9]/gi, '').slice(0, 2).toUpperCase() || '?';
export const shortName = m => String(m?.name || m?.id || '').replace(/^[^:]+:\s*/, '');
// 💵 what a real move takes, said truthfully: its own wallet (approve = one tap, auto = nothing) or, linked to yours, your wallet signs
export const signWord = cat => (cat?.agentWallet ? (cat.agentWallet.mode === 'auto' ? 'its own wallet sends it — no signing' : 'you OK it with one tap — its own wallet sends it') : 'a proposal your wallet signs');
const fmtCtx = n => n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}K` : String(n || '—');

// 🧭 a GENERAL agent's job → the models best at it (owner 2026-10-30: "a dropdown in the model picker for the type of task"): its category, what the
// model must support (tools to drive a browser, vision to read a chart / page image), and how to rank them
export const JOBS = [['', 'Any job', null], ['research', '🔎 Research + browse the web', { cat: 'agent', need: ['tools'], sort: 'smart' }],
  ['trade', '📈 Read charts + trade on FEELESS', { need: ['tools', 'vision'], sort: 'smart' }], ['content', '✍ Write posts + content', { cat: 'content', sort: 'smart' }],
  ['code', '💻 Code + build', { cat: 'code', need: ['tools'], sort: 'smart' }], ['vision', '👁 Read screenshots + images', { need: ['vision'], sort: 'smart' }],
  ['memory', '📚 Long documents', { sort: 'ctx' }], ['cheap', '💸 Cheap everyday tasks', { sort: 'cheap' }]];
export function filterModels(models, { q = '', cat = '', sort = 'smart', min = 0, max = Infinity, kind = 'trading', need = [] } = {}) {
  const t = q.trim().toLowerCase();
  const rows = (models || []).filter(m => (!(Array.isArray(cat) ? cat.length : cat) || (Array.isArray(cat) ? cat : [cat]).every(c => m.cats.includes(c))) && (Number(kind === 'general' ? m.perTask : m.perDecision) >= min && Number(kind === 'general' ? m.perTask : m.perDecision) <= max) && (!t || `${m.name} ${m.id} ${m.desc}`.toLowerCase().includes(t)) && need.every(k => m[k]));
  const key = { smart: m => -(m.intel ?? -1), cheap: m => m.perDecision, ctx: m => -m.ctx, new: m => -m.created }[sort] || (() => 0);
  return [...rows].sort((a, b) => key(a) - key(b));
}

export function planOf(picked, mode, budget, kind = 'trading') {   // mirrors launch_cat.plan (change both)
  if (!picked.length) return null;
  if (kind === 'general') { const task = picked.reduce((s, m) => s + (m.perTask || 0), 0) / picked.length;   // a task runs both windows; perTask counts both
    return { perTask: task, perDecision: task, tasks: task > 0 ? Math.floor((budget?.start ?? 10) / task) : null }; }
  const calls = picked.length > 1 && (mode === 'discuss' || mode === 'together') ? picked.length : 1;
  const avg = picked.reduce((s, m) => s + (m.perDecision || 0), 0) / picked.length;
  const one = calls > 1 ? avg * calls : avg;
  const trade = one * (1 + (budget?.liveAsks ?? 3));
  return { perDecision: one, perTrade: trade, trades: trade > 0 ? Math.floor((budget?.start ?? 10) / trade) : null, calls };
}

// 💵 every model's real price (owner 2026-10-29: "the pricing for all models"): $ per 1M tokens in / out, what one decision (trading) or one task
// (general, worst case) costs, its memory — and its description in a dropdown, never a cut-off line
function ModelTile({ m, on, onPick, i, kind }) {
  const gen = kind === 'general'; const desc = m.why ? `${m.why}${m.desc ? ` — ${m.desc}` : ''}` : m.desc;
  return <div className={`lct-tile${on ? ' is-on' : ''}${m.tag ? ' is-rec' : ''}`} style={{ '--i': Math.min(i, 20) }}>
    <button type="button" className="lct-tile-pick" onClick={() => onPick(m)} data-testid={`lct-m-${m.id}`} aria-pressed={on} data-tip={on ? 'Picked — tap to drop it' : `Pick ${shortName(m)} as a ${gen ? 'mind' : 'brain'}`}>
      <span className="lct-tile-top"><i className="lct-mono" aria-hidden="true">{mono(m)}</i>{m.tag ? <b className="lct-tag">⭐ {m.tag}</b> : <small>{m.provider}</small>}{m.intel != null ? <em title="intelligence index">♟ {m.intel}</em> : null}</span>
      <strong>{shortName(m)}</strong>
      <span className="lct-tile-nums"><span><small>IN · 1M</small>{fmtM(m.inUsd)}</span><span><small>OUT · 1M</small>{fmtM(m.outUsd)}</span>
        <span className="is-hot"><small>{gen ? 'TASK EST.' : 'A DECISION'}</small>{fmtUsd(gen ? m.perTask : m.perDecision)}</span><span><small>MEMORY</small>{fmtCtx(m.ctx)}</span></span>
      <span className="lct-chips">{[m.tools && 'tools', m.vision && 'vision', m.cats.includes('code') && 'code', m.reasoning && 'reasoning'].filter(Boolean).map(c => <i key={c}>{c}</i>)}{m.cats.slice(0, 4).map(c => <i key={c} className={CHIP[c]}>{c}</i>)}</span></button>
    {desc ? <details className="lct-desc"><summary data-tip="What this model is and what it is good at">ABOUT</summary><p>{desc}</p></details> : null}
  </div>;
}

// 🧠 THE BRAIN SOCKET (FeeCat redo, 2026-10-23): YOUR built cat with the picked brains drawn as lit orbs, each wired into its head — the wire
// pulses toward the cat; two brains = two wires; none = an empty socket waiting.
// its body in the general setup: the agent you built (cat / queen ant / fly / ants)
function BodyPreview() {
  const mine = useMyCat(); const coat = CAT_VARIATIONS[mine?.coat ?? 0] || CAT_VARIATIONS[0];
  return mine?.agent?.species && mine.agent.species !== 'cat' ? <AgentCritter agent={mine.agent} size={86} /> : <LookAvatar cat={[coat[0], coat[1], coat[2], mine?.pattern || coat[3]]} look={mine?.look} size={86} />;
}
export function BrainSocket({ picked, mood, kind = 'trading' }) {
  const mine = useMyCat(); const coat = CAT_VARIATIONS[mine?.coat ?? 0] || CAT_VARIATIONS[0];
  const slots = picked.length > 2 ? picked : [picked[0] || null, picked[1] || null];
  return <div className={`lct-socket n-${picked.length}`} aria-hidden="true">
    <svg className="lct-wires" viewBox="0 0 220 120" preserveAspectRatio="none">{slots.map((m, i) => <path key={i} className={`w w${i}${m ? ' on' : ''}`} d={i ? 'M188 30 C 160 30, 150 58, 118 60' : 'M32 30 C 60 30, 70 58, 102 60'} />)}</svg>
    {slots.map((m, i) => <span key={i} style={i > 1 ? { top: 95 + (i - 2) * 20, left: 10, fontSize: 10, width: 28, height: 28 } : undefined} className={`lct-node n${i}${m ? ' on has-bub' : ''}`}>{m ? <Bubble m={m} i={i} kind={kind} size={i > 1 ? 28 : 56} /> : '+'}<u>{String.fromCharCode(65 + i)}</u></span>)}
    <span className="lct-cat">{mine?.agent?.species && mine.agent.species !== 'cat' ? <AgentCritter agent={mine.agent} size={78} gesture={mood === 'pounce' || mood === 'celebrate' ? 'march' : null} /> : <LookAvatar cat={[coat[0], coat[1], coat[2], mine?.pattern || coat[3]]} look={mine?.look} size={92} gesture={mood} />}</span>
  </div>;
}

// 🫧 a REAL soap bubble per mind (owner 2026-10-30: "a realistic bubble with blurred thoughts in them, not dead pink + purple"): a clear centre, a
// thin-film rainbow rim (interference colours: magenta → gold → cyan, strongest at the edge — the Fresnel rim), a window-shaped glint top-left + a
// small one bottom-right, a slow film swirl and a soft wobble; its thoughts drift inside, out of focus. LIVE like the new Siri: flowing
// orange → pink → violet → blue light swirls inside and a glow breathes around it while the mind is picked (still when empty)
export const THOUGHTS = { trading: [['germ floor?', 'buyers 71%', 'hold?', '+18%'], ['rug check', 'bundlers 0', 'trim?', 'volume ↑']],
  general: [['sources…', 'why?', 'summary', 'draft'], ['odds', 'compare', 'sign-in?', 'merge']] };
// 🫧 the two minds (owner 2026-10-29: "better design for the 2 bubbles"): a lit orb with the maker's monogram, its role, its full name and its price —
// never a name cut to four letters
// 🫧 one mind as a live soap bubble (the wizard's socket, its minds step, the agent's live desk) — `thoughts` overrides the kind's idle words
export function Bubble({ m, i = 0, kind = 'trading', thoughts, size, live = true }) {
  const th = (thoughts?.length ? thoughts : THOUGHTS[kind === 'general' ? 'general' : 'trading'][i % 2]).slice(0, 4);
  return <span className={`lct-orb ${i % 2 ? 'o2' : 'o1'}${m && live ? '' : ' is-idle'}`} style={size ? { width: size, height: size } : undefined}>
    <span className="lct-think" aria-hidden="true">{th.map((w, j) => <span key={`${w}${j}`} className="lct-th" style={{ '--j': j }}>{w}</span>)}</span>
    <i className="lct-siri" aria-hidden="true"><u /><u /><u /></i><i className="lct-film" aria-hidden="true" /><i className="lct-shine" aria-hidden="true" /><b>{m ? mono(m) : '+'}</b></span>;
}
function Mind({ m, i, kind }) {
  const gen = kind === 'general';
  return <span className={`lct-mind m${i}${m ? '' : ' is-empty'}`}><Bubble m={m} i={i} kind={kind} />
    <em>{gen ? `MIND ${String.fromCharCode(65 + i)}${i ? '' : ' · LEADS'}` : `BRAIN ${String.fromCharCode(65 + i)}`}</em><strong title={m ? shortName(m) : ''}>{m ? shortName(m) : i ? 'no second pick' : 'pick one'}</strong>
    {m ? <small className="m-num">{gen ? `≈ ${fmtUsd(m.perTask)} a task` : `${fmtUsd(m.perDecision)} a decision`}</small> : null}</span>;
}
function Duo({ mode, picked, kind }) {
  const [a, b] = picked;
  return <div style={{ gap: picked.length > 2 ? 16 : undefined, height: picked.length > 2 ? 'auto' : undefined, flexWrap: 'wrap' }} className={`lct-duo ${kind === 'general' ? 'is-general' : DUO[mode] || ''}${b ? '' : ' is-solo'}`} aria-hidden="true">
    {(picked.length > 2 ? picked : [a, b]).map((m, i) => <Mind key={m?.id || i} m={m} i={i} kind={kind} />)}<i className="lct-beam" /><i className="lct-ring" />
  </div>;
}

const plainForm = () => ({ name: '', handle: '', avatar: 0, startingBalanceSol: '10', maxPositionSol: '0.5', dailyBuyLimitSol: '2', maxDailyLossSol: '0.5' });
const plainOk = f => f.name.trim().length > 1;

// 🧭 THE MODEL BROWSER — one smart list for every place a model is picked (the wizard's step 1 · Fee's model pop-out · a cat's model switch):
// its job (general), search, sort, a $ range, categories that combine, and the tiles — tap to pick, tap again to drop
export function ModelBrowser({ d, kind = 'trading', picked = [], onPick }) {
  const gen = kind === 'general';
  const [q, setQ] = useState(''); const [cat, setCat] = useState((KIND[kind] || KIND.trading).cat || ''); const [sort, setSort] = useState('smart'); const [n, setN] = useState(PAGE); const [job, setJob] = useState('');
  const [cost, setCost] = useState(['', '']); const jobCfg = gen ? (JOBS.find(j => j[0] === job) || JOBS[0])[2] : null;
  const range = useMemo(() => { const lo = Number(cost[0]) || 0; const hi = cost[1] === '' ? Infinity : Math.max(lo, Number(cost[1]) || 0); return [lo, hi]; }, [cost]);
  const setCostAt = (i, v) => setCost(c => (i ? [c[0], v] : [v, c[1]]));
  const rows = useMemo(() => filterModels(d?.models, { q, cat: jobCfg?.cat ? [jobCfg.cat] : cat, sort: jobCfg?.sort || sort, min: range[0], max: range[1], kind, need: jobCfg?.need || [] }), [d, q, cat, sort, range, kind, jobCfg]);
  useEffect(() => setN(PAGE), [q, cat, sort, range]);
  const cats = useMemo(() => { const c = (d?.cats || []).filter(x => gen || !x.general); return gen ? [...c.filter(x => x.general), ...c.filter(x => !x.general)] : c; }, [d, gen]);
  const pick = onPick;
  if (!d) return <p className="lct-load">Reading OpenRouter's model list…</p>;
  return <>
          {gen ? <label className="lct-job" data-tip="Pick the job — the list shows the models best at it (category, tools / vision it needs, ranked)"><span>WHAT'S ITS JOB?</span>
          <select className="m-input" value={job} onChange={e => setJob(e.target.value)} data-testid="lct-job" aria-label="What is its job">{JOBS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
          <small>{jobCfg ? `${rows.length} models fit · ${[jobCfg.cat, ...(jobCfg.need || [])].filter(Boolean).join(' + ') || (jobCfg.sort === 'cheap' ? 'cheapest first' : 'biggest memory first')}` : 'every model'}</small></label> : null}
        <div className="lct-bar"><input className="m-input" placeholder={`Search ${d.models.length} models…`} value={q} onChange={e => setQ(e.target.value)} data-testid="lct-q" />
          <div className="m-seg">{SORTS.map(([k, l]) => <button key={k} type="button" className={sort === k ? 'is-on' : ''} onClick={() => setSort(k)}>{l}</button>)}</div></div>
        <div className="lct-bar lct-cost" data-tip="Only models whose cost sits between these two $ amounts — leave Max empty for no cap">
          <label>Min $ / {gen ? 'task' : 'decision'}<span className="lct-usd"><i>$</i><NumInput className="m-input" type="number" inputMode="decimal" min="0" step="0.0001" placeholder="0" value={cost[0]} onChange={e => setCostAt(0, e.target.value)} aria-label="Minimum model cost" data-testid="lct-min" /></span></label>
          <i className="lct-cost-to" aria-hidden="true">→</i>
          <label>Max $ / {gen ? 'task' : 'decision'}<span className="lct-usd"><i>$</i><NumInput className="m-input" type="number" inputMode="decimal" min="0" step="0.0001" placeholder="no cap" value={cost[1]} onChange={e => setCostAt(1, e.target.value)} aria-label="Maximum model cost" data-testid="lct-max" /></span></label>
          <span className="lct-cost-n m-num" key={rows.length}>{rows.length}<small>match</small></span></div>
        <div className="lct-cats"><button type="button" className={!cat.length ? 'is-on' : ''} onClick={() => setCat('')}>✨ All <small>{d.models.length}</small></button>{cats.map(c => <button key={c.key} type="button" className={`${(Array.isArray(cat) ? cat.includes(c.key) : cat === c.key) ? 'is-on' : ''}${c.general ? ' is-job' : ''}`} onClick={() => setCat(prev => { const a = Array.isArray(prev) ? prev : prev ? [prev] : []; return a.includes(c.key) ? a.filter(x => x !== c.key) : [...a, c.key]; })} data-tip={c.why} data-testid={`lct-cat-${c.key}`}>{c.label} <small>{c.n}</small></button>)}</div>
        <div className="lct-grid">{rows.slice(0, n).map((m, i) => <ModelTile key={m.id} m={m} i={i} kind={kind} on={picked.some(x => x.id === m.id)} onPick={pick} />)}</div>
        {rows.length > n ? <button type="button" className="m-btn lct-more" onClick={() => setN(x => x + PAGE)}>Show {Math.min(PAGE, rows.length - n)} more of {rows.length}</button> : null}
        {!rows.length ? <p className="lct-load">No model matches that.</p> : null}</>;
}

// 🪟 the model list as a POP-OUT (owner 2026-10-30: "a popout of the full list, not a dropdown") — Fee's models and every agent's model switch
export function ModelPop({ d, title, kind = 'trading', picked = [], onPick, onClose }) {
  useEffect(() => { const k = e => e.key === 'Escape' && onClose(); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose]);
  return createPortal(<div className="lct-pop" role="dialog" aria-modal="true" aria-label={title} onClick={e => e.target === e.currentTarget && onClose()} data-testid="model-pop">
    <section className={`lct is-${kind} lct-pop-card m-pop`}>
      <header className="lct-pop-head"><b>{title}</b><small>pick a smart, cheap one — sort by Cheapest or set a max $</small>
        <button type="button" className="m-btn" onClick={onClose} data-testid="model-pop-close" aria-label="Close the model list">✕</button></header>
      <ModelBrowser d={d} kind={kind} picked={picked} onPick={m => { onPick(m.id); onClose(); }} />
    </section></div>, document.body);
}

export function LaunchCat({ api, ownerId, onCreated, onCancel, Fields, Preview, newForm = plainForm, formOk = plainOk, avatarOf = () => 'Fee', kind = 'trading' }) {
  const K = KIND[kind] || KIND.trading;
  const [d, setD] = useState(null); const [err, setErr] = useState('');
  const [step, setStep] = useState(0);
  const gen = kind === 'general'; const steps = gen ? GEN_STEPS : STEPS;
  const [picked, setPicked] = useState([]); const [mode, setMode] = useState(gen ? 'turns' : BEST_MODE); const [workMode, setWorkMode] = useState('plan'); const [billing, setBilling] = useState(gen ? 'payg' : 'profit');
  const [form, setForm] = useState(() => newForm()); const update = (k, v) => setForm(f => ({ ...f, [k]: v })); const name = form.name;
  const [efforts, setEfforts] = useState({});
  const [jobTab, setJobTab] = useState('research'); const [taskCap, setTaskCap] = useState(0.05);
  const [persona, setPersona] = useState(''); const [fundUsd, setFundUsd] = useState('10'); const [fundToken, setFundToken] = useState('SOL');   // 💵 what goes into its wallet (owner: "enter the amount at launch")
  const [prompt, setPrompt] = useState(''); const [saving, setSaving] = useState(false);
  const [venues, setVenues] = useState(['trench']); const [keys, setKeys] = useState({});
  useEffect(() => { let on = true; api(`/api/cats/models?session=${encodeURIComponent(readChatSession() || '')}`).then(x => on && setD(x)).catch(e => on && setErr(e.message)); return () => { on = false; }; }, [api]);
  const pick = m => setPicked(p => p.some(x => x.id === m.id) ? p.filter(x => x.id !== m.id) : [...p, m].slice(-(d?.maxModels || 2)));
  const plan = planOf(picked, mode, d?.budget, kind);
  const bills = (d?.billing || []).filter(b => !gen || b.key === 'payg');   // a general cat earns nothing to pay from — it runs on credit
  const ready = [picked.length > 0, true, gen ? form.name.trim().length > 1 && prompt.trim().length >= 20 : formOk(form), true];
  const launch = async () => {
    setSaving(true); setErr('');
    try {
      const handle = form.handle || form.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 20) || 'cat';
      const r = await api('/api/cats', { method: 'POST', body: JSON.stringify({ strategy: 'momentum', ...form, ownerId: ownerId(), name: form.name.trim(), handle, avatar: avatarOf(form.avatar),
        brains: picked.map(m => m.id), brainMode: gen ? 'turns' : mode, billing, prompt, efforts: Object.fromEntries(picked.filter(m => efforts[m.id]).map(m => [m.id, efforts[m.id]])), brainKind: kind, session: readChatSession() || '', job: gen ? (((d?.personas?.general || []).find(x => x.key === persona) || {}).job || 'agent') : 'trading', ...(gen ? { workMode, taskCap } : { venues }) }) });
      try { if (Number(fundUsd) > 0) localStorage.setItem(`feeless.fundIntent.${r.cat.id}`, String(Number(fundUsd))); localStorage.setItem(`feeless.fundToken.${r.cat.id}`, fundToken); } catch { /* private window */ }   // its funding step opens on this $
      for (const [provider, secret] of Object.entries(keys).filter(([, v]) => v)) await api(`/api/cats/${r.cat.id}/action`, { method: 'POST', body: JSON.stringify({ action: 'api_key', provider, secret }) }).catch(e => setErr(`Key not saved: ${e.message}`));
      const started = await api(`/api/cats/${r.cat.id}/action`, { method: 'POST', body: JSON.stringify({ action: 'start' }) }).catch(() => r);   // same as Create a Cat: it starts trading at once
      onCreated?.(started.cat || r.cat);
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };
  return <section className={`lct is-${kind}`} data-testid="launch-cat">
    <header className="lct-head"><BrainSocket kind={kind} picked={picked} mood={saving ? 'pounce' : picked.length === 2 ? 'celebrate' : picked.length ? 'purr' : 'think'} />
      <div><span className="eyebrow" data-testid="lct-kind">{K.eyebrow} · ITS OWN WALLET</span><h2>Give your cat <em>{picked.length === 2 ? (gen ? 'two minds' : 'two brains') : (gen ? 'a mind' : 'a brain')}</em>.</h2>
        <p>{K.pitch.replace(/1–2/g, `1–${d?.maxModels || 2}`)}</p><small>{picked.length} / {d?.maxModels || 2} models</small></div></header>
    <nav className="lct-steps" style={{ '--p': step / (steps.length - 1) }}><i className="lct-prog" aria-hidden="true"><u /></i>{steps.map((s, i) => <button key={s} type="button" className={`${i === step ? 'is-on' : ''}${i < step ? ' is-done' : ''}`} onClick={() => i <= step || ready.slice(0, i).every(Boolean) ? setStep(i) : null} data-testid={`lct-step-${i}`}><b>{i + 1}</b>{s}</button>)}</nav>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    {step === 0 ? <div className="lct-pane">
      <div className="lct-slots" data-testid="lct-slots">{[0, 1].map(k => picked[k] ? <ModelTile key={picked[k].id} m={picked[k]} i={k} kind={kind} on onPick={pick} />
        : <div key={k} className="lct-slot" data-testid={`lct-slot-${k}`}><b>{gen ? 'MIND' : 'BRAIN'} {'AB'[k]}</b><small>{k ? 'optional · a second model to work with it' : 'pick a model from the list below'}</small></div>)}
        <button type="button" className="m-btn m-go lct-next-top" disabled={!ready[0]} onClick={() => setStep(1)} data-testid="lct-next-top" data-tip="Next: how its models work together">Next ›</button></div>
      <ModelBrowser d={d} kind={kind} picked={picked} onPick={pick} />
    </div> : null}
    {step === 0 && picked.some(m => m.efforts?.length) ? <div className="lct-bar">{picked.filter(m => m.efforts?.length).map(m => <label key={m.id}>{shortName(m)} · effort<select className="m-input" aria-label={`${shortName(m)} effort`} value={efforts[m.id] || ''} onChange={e => setEfforts(v => ({ ...v, [m.id]: e.target.value }))}><option value="">Provider default</option>{m.efforts.map(e => <option key={e}>{e}</option>)}</select><small>Output incl. reasoning: {fmtM(m.outUsd)} / 1M tokens. Actual cost depends on tokens used.</small></label>)}</div> : null}
    {step === 1 ? <div className="lct-pane lct-mode"><Duo mode={mode} picked={picked} kind={kind} /><AgentDemo kind={kind} models={picked} mode={gen ? workMode : mode} />
      {gen ? <><div className="lct-ways" role="radiogroup" aria-label="How its two minds work">{WORK_WAYS.map(([k, ic, t, why, flow], i) => <button key={k} type="button" role="radio" aria-checked={workMode === k}
          className={`lct-way${workMode === k ? ' is-on' : ''}`} style={{ '--i': i }} onClick={() => setWorkMode(k)} data-testid={`lct-work-${k}`} data-tip={why}>
          <span className="lct-way-h"><i aria-hidden="true">{ic}</i><b>{t}</b>{k === 'plan' ? <em>⭐ BEST FOR ONE BIG QUESTION</em> : <em>TWO JOBS AT ONCE</em>}</span><small>{why}</small>
          <ol className="lct-flow" data-testid={k === 'plan' ? 'lct-flow' : undefined}>{flow.map(([fi, ft, fw], j) => <li key={ft} style={{ '--i': j }}><i aria-hidden="true">{fi}</i><b>{ft}</b><small>{fw}</small></li>)}</ol></button>)}</div>
        <p className="lct-note">{picked.length < 2 ? 'One mind: it takes every task in its own window. Pick a second in step 1 and they split the work.' : workMode === 'jobs' ? 'In its chat you write a job for each mind — A: … B: … — and both run at once.' : 'Ask one thing — they plan it in a sentence each, split it, research in their own windows, then hand you ONE answer.'}</p></>
      : <><VenuePick value={venues} onChange={setVenues} />{picked.length < 2 ? <p className="lct-note">One brain: it makes every call. Pick a second in step 1 to choose how they work together.</p> :
        <div className="lct-modes">{(d?.modes || []).map(m => <button key={m.key} type="button" className={`${mode === m.key ? 'is-on' : ''}${m.key === BEST_MODE ? ' is-best' : ''}`} onClick={() => setMode(m.key)} data-testid={`lct-mode-${m.key}`}
          data-tip={m.key === BEST_MODE ? 'Our pick: two looks per decision for the price of a short second call — B checks A before money moves' : m.why}>{m.key === BEST_MODE ? <em className="lct-best">⭐ BEST</em> : null}<b>{m.label}</b><small>{m.why}</small></button>)}</div>}</>}
    </div> : null}
    {step === 2 && gen ? <div className="lct-pane lct-brief" data-testid="lct-gsetup">
      <section className="lct-pane"><h4 className="lct-h">🎯 WHAT IS IT FOR?</h4>
        <nav className="m-seg" role="tablist" aria-label="Kind of job">{JOB_GROUPS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={jobTab === k} className={jobTab === k ? 'active' : ''} onClick={() => setJobTab(k)} data-testid={`lct-jobtab-${k}`}>{l}</button>)}</nav>
        <div className="lct-modes lct-jobs">{(d?.personas?.general || []).filter(p => (JOB_GROUPS.find(g => g[0] === jobTab)?.[2] || []).includes(p.key)).map((p, i) => <button key={p.key} type="button" className={persona === p.key ? 'is-on' : ''} style={{ '--i': i }}
          onClick={() => { setPersona(p.key); setPrompt(briefFor(p, 'general', workMode, picked.length < 2)); }} data-testid={`lct-job-${p.key}`}><b>{p.label}</b><small>{p.brief}</small></button>)}</div></section>
      <div className="lct-gid">
        <label className="cct-field"><span>Name</span><input className="m-input" maxLength={24} value={form.name} onChange={e => update('name', e.target.value)} placeholder="e.g. Scout" data-testid="lct-name" /></label>
        <span className="lct-gbody" data-tip="Its body is the agent you built in 🎨 Build an agent"><BodyPreview /><small>its body · change it in 🎨 Build an agent</small></span>
        <div className="lct-gcap"><span>MOST IT MAY SPEND ON ONE TASK</span><div className="m-seg" role="radiogroup" aria-label="Spend cap per task">{[0.02, 0.05, 0.25, 1].map(c => <button key={c} type="button" role="radio" aria-checked={taskCap === c} className={taskCap === c ? 'active' : ''} onClick={() => setTaskCap(c)} data-testid={`lct-cap-${c}`}>${c}</button>)}</div></div>
      </div>
      <label className="lct-seal lct-gbrief"><span><b>📜 ITS BRIEF · BOTH MINDS</b><em>you can change it once an hour after launch — or let its minds propose a better one</em></span>
        <textarea className="m-input" rows={7} maxLength={1200} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Pick a job above — its brief is written for both minds — or write your own." data-testid="lct-prompt" />
        <i className="lct-len" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.01, prompt.length / 1200)})` }} /></i><small>{prompt.length} / 1200</small></label>
      <p className="lct-note lct-house" data-testid="lct-house" data-tip="Built into FEELESS on every step — no brief can remove these">🔒 ALWAYS ON · {HOUSE.general.replace(/^RULES — /, '')} It makes its own email + sign-ups first and stops only for your own accounts, CAPTCHAs, codes, payments and ID.</p>
    </div> : null}
    {step === 2 && !gen ? <div className="lct-pane lct-brief">
      {Fields ? <div className="cct-split lct-ident">{<Fields form={form} update={update} />}{Preview ? <aside className="cct-preview m-live" data-testid="lct-preview"><Preview form={form} /></aside> : null}</div> : <>
        <label>Cat name<input className="m-input" maxLength={24} value={form.name} onChange={e => update('name', e.target.value)} placeholder="Midnight Prowler" data-testid="lct-name" /></label>
        <label>Starting paper balance · SOL<NumInput className="m-input" value={form.startingBalanceSol} onChange={e => update('startingBalanceSol', e.target.value)} /></label></>}
      <label>Character<select className="m-input" aria-label="Cat character" value={persona} onChange={e => { setPersona(e.target.value); const p = (d?.personas?.[kind] || []).find(x => x.key === e.target.value); setPrompt(p ? briefFor(p, 'trading', mode, picked.length < 2) : ''); }}><option value="">Custom brief</option>{(d?.personas?.[kind] || []).map(p => <option key={p.key} value={p.key}>{p.label}</option>)}</select></label>
      <label className="lct-seal"><span><b>{K.brief}</b><em>sealed at launch — both brains read it before every call; it can't be changed after</em></span>
        <textarea className="m-input" rows={6} maxLength={1200} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder={K.hint} data-testid="lct-prompt" />
        <i className="lct-len" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.01, prompt.length / 1200)})` }} /></i><small>{prompt.length} / 1200</small></label>
    </div> : null}
    {step === 3 ? <div className="lct-pane lct-pay">
      <div className="lct-modes">{bills.map(b => <button key={b.key} type="button" className={billing === b.key ? 'is-on' : ''} onClick={() => setBilling(b.key)} data-testid={`lct-bill-${b.key}`}><b>{b.label}</b></button>)}</div>
      {plan && gen ? <div className="lct-meter"><span><small>A TASK (estimate)</small><b>{fmtUsd(plan.perTask)}</b></span><span><small>ITS CAP · YOU SET IT</small><b>$0.02 – $1</b></span>
        <span><small>${d?.budget?.start ?? 10} CREDIT COVERS</small><b>{plan.tasks == null ? '∞ (free models)' : `≈ ${plan.tasks.toLocaleString()} tasks`}</b></span>
        <i className="lct-tank"><em style={{ transform: `scaleX(${plan.tasks == null ? 1 : Math.min(1, plan.tasks / 500)})` }} /></i></div>
      : plan ? <div className="lct-meter"><span><small>A DECISION</small><b>{fmtUsd(plan.perDecision)}</b></span><span><small>A TRADE (worst case)</small><b>{fmtUsd(plan.perTrade)}</b></span>
        <span><small>${d?.budget?.start ?? 10} CREDIT COVERS</small><b>{plan.trades == null ? '∞ (free models)' : `≈ ${plan.trades.toLocaleString()} trades`}</b></span>
        <i className="lct-tank"><em style={{ transform: `scaleX(${plan.trades == null ? 1 : Math.min(1, plan.trades / 500)})` }} /></i></div> : null}
      <p className="lct-note">{(gen ? d?.generalLive : d?.live) ? '🟢 Model calls are ON.' : gen ? '⏸ Model calls are OFF until FEELESS switches them on — until then asking sends and charges nothing.' : '⏸ Model calls are OFF until FEELESS switches them on — until then the FEELESS rule engine trades your cat and nothing is charged.'} Its ${d?.budget?.start ?? 10} model credit is covered by FEELESS — at $0 its minds pause until you add more from its wallet panel, in SOL or USDC. Your funding never pays for model calls: it goes to its own wallet.</p>
      {gen ? null : <ApiDrawer draft={keys} onDraft={(k, v) => setKeys(x => ({ ...x, [k]: v.trim() }))} />}
      <SafetyCard gen={gen} />
      <FundReceipt general={gen} />
      <div className="lct-bar lct-cost lct-fund" data-tip="What goes into its own wallet, paid from your wallet; you sign once after launch">
        <label>FUND ITS WALLET WITH<span className="lct-usd"><i>$</i><NumInput className="m-input" type="number" inputMode="decimal" min="1" step="1" value={fundUsd} onChange={e => setFundUsd(e.target.value)} aria-label="Dollars to put in its wallet" data-testid="lct-fund-usd" /></span></label>
        <div className="m-seg" role="radiogroup" aria-label="Quick amounts">{[10, 25, 50, 100].map(a => <button key={a} type="button" role="radio" aria-checked={Number(fundUsd) === a} className={Number(fundUsd) === a ? 'active' : ''} onClick={() => setFundUsd(String(a))}>${a}</button>)}</div>
        <div className="m-seg" role="radiogroup" aria-label="Pay with">{['SOL', 'USDC'].map(t => <button key={t} type="button" role="radio" aria-checked={fundToken === t} className={fundToken === t ? 'active' : ''} onClick={() => setFundToken(t)} data-tip={`Pay with ${t} from your wallet`} data-testid={`lct-pay-${t}`}>{t}</button>)}</div>
        <small className="lct-fund-note">{fundToken === 'USDC' ? 'paid in USDC · keep a little SOL in your wallet for the network fee' : 'paid in SOL at the live price'} · nothing is charged until you sign the receipt after launch</small></div>
      <p className="lct-next" data-testid="lct-next-real">{K.next.map((x, i) => <React.Fragment key={x}>{i ? <u /> : null}<i className={i === K.next.length - 1 ? 'is-real' : ''}>{x}</i></React.Fragment>)}</p>
      <button type="button" className="m-btn m-go lct-go" disabled={saving || !ready.slice(0, 3).every(Boolean)} onClick={launch} data-testid="lct-launch">{saving ? 'Launching…' : `🚀 Launch ${name || 'the cat'} → go real`}</button>
    </div> : null}
    <footer className="lct-foot"><span>{picked.length ? picked.map(m => m.tag || m.name.replace(/^[^:]+:\s*/, '')).join(' + ') : 'no brain picked'}{plan ? (gen ? ` · ≈ ${fmtUsd(plan.perTask)} a task` : ` · ${fmtUsd(plan.perDecision)} a decision`) : ''}</span>
      <span>{onCancel ? <button type="button" className="m-btn" onClick={onCancel}>Cancel</button> : null}{step < 3 ? <button type="button" className="m-btn m-go" disabled={!ready[step]} onClick={() => setStep(s => s + 1)} data-testid="lct-next">Next ›</button> : null}</span></footer>
  </section>;
}

// 🧭 A GENERAL cat's orders (owner, 2026-10-23): you order in plain words → the cat checks the coin (pool · age · already-ran · rug / holders) →
// REAL = its own wallet (approve: one tap · auto: it sends) or, linked to yours, a proposal your wallet signs · paper = a paper fill. Each order shows what it understood and what happened.
export const ORDER_STATE = { proposed: ['✍', 'waiting for your signature', 'is-prop'], filled: ['📄', 'filled on paper', 'is-fill'], refused: ['🛡', 'stopped by a guard', 'is-stop'], unclear: ['🤔', 'not understood', 'is-unclear'] };
export const ORDER_EXAMPLES = ['buy 0.05 SOL of $JUP', 'sell half of $WIF', 'sell all $BONK'];
export const orderWords = o => (!o ? '—' : o.side === 'buy' ? `BUY ${o.sol} SOL · $${String(o.coin).slice(0, 12)}` : `SELL ${Math.round((o.fraction || 1) * 100)}% · $${String(o.coin).slice(0, 12)}`);
export function OrderBox({ cat, act }) {
  const [t, setT] = useState(''); const [busy, setBusy] = useState(false);
  const rows = (cat.orders || []).slice(-6).reverse();
  const go = async e => { e?.preventDefault?.(); if (!t.trim() || busy) return; setBusy(true); if (await act('order', { text: t })) setT(''); setBusy(false); };
  return <div className="lct-orders" data-testid="cat-orders">
    <span className="lct-orders-h"><b>🧭 YOUR ORDERS</b><small>{cat.mode === 'real' ? `each one → ${signWord(cat)}` : 'paper fills — go real to run them'}</small></span>
    <form className="lct-order-form" onSubmit={go}><input className="m-input" maxLength={200} value={t} onChange={e => setT(e.target.value)} placeholder="Order it in plain words — buy 0.05 SOL of $JUP" data-testid="order-text" aria-label="Your order" />
      <button type="submit" className="m-btn m-go" disabled={busy || !t.trim()} data-testid="order-go" data-tip="It checks the coin first (pool, age, already-ran, rug / holders) — a stopped order says which guard">{busy ? 'Checking…' : '🧭 Order'}</button></form>
    <span className="lct-order-ex">{ORDER_EXAMPLES.map(x => <button key={x} type="button" onClick={() => setT(x)} data-tip="Fill the box with this order">{x}</button>)}</span>
    {rows.length ? <ol className="lct-order-log">{rows.map((r, i) => { const [ic, word, cls] = ORDER_STATE[r.state] || ORDER_STATE.unclear;
      return <li key={`${r.at}-${i}`} className={cls} style={{ '--i': i }} data-tip={`You said: “${r.text}” — ${word}`}><i aria-hidden="true">{ic}</i><b>{orderWords(r.order)}</b><small>{r.why}</small></li>; })}</ol> : null}
  </div>;
}

// 📜 a GENERAL agent's one brief for both minds (owner 2026-10-30): you rewrite it once an hour (or pick one of the presets), and its minds can propose
// a better one for both of them — at most once an hour — that only goes live when you approve it. A trader's brief stays sealed from purchase.
export function BriefCard({ cat, act, api }) {
  const b = cat.brainsCfg || {}; const [t, setT] = useState(''); const [presets, setPresets] = useState([]); const [busy, setBusy] = useState(false);
  useEffect(() => { let on = true; api('/api/cats/models').then(d => on && setPresets(d?.personas?.general || [])).catch(() => {}); return () => { on = false; }; }, [api]);
  const now = Date.now() / 1000; const editIn = Math.max(0, 3600 - (now - Number(b.briefAt || 0))); const askIn = Math.max(0, 3600 - (now - Number(b.briefAskAt || 0)));
  const run = async (action, extra = {}) => { setBusy(true); const ok = await act(action, extra); setBusy(false); return ok; };
  const pr = b.briefProposal;
  return <section className="lct-briefcard" data-testid="brief-card">
    <header><b>📜 ITS BRIEF · BOTH MINDS</b><small>{editIn ? `you can change it in ${Math.ceil(editIn / 60)} min` : 'you can change it now'}</small></header>
    <p className="lct-briefnow">{b.prompt || 'No brief yet — write one or pick a preset.'}</p>
    {pr ? <div className="lct-proposal" data-testid="brief-proposal"><em>🧠🧠 THEIR PROPOSAL</em><p>{pr.text}</p>{pr.why ? <small>why: {pr.why}</small> : null}
      <span><button type="button" className="m-btn m-go" disabled={busy} onClick={() => run('brief_approve')} data-testid="brief-approve">✓ Use it</button>
        <button type="button" className="m-btn" disabled={busy} onClick={() => run('brief_dismiss')}>Keep mine</button></span></div> : null}
    <select className="m-input" value="" onChange={e => { const p = presets.find(x => x.key === e.target.value); if (p) setT(p.brief); }} aria-label="Fill from a preset" data-testid="brief-preset">
      <option value="">✨ Fill from a preset ({presets.length})…</option>{presets.map(p => <option key={p.key} value={p.key}>{p.label}</option>)}</select>
    <textarea className="m-input" rows={3} maxLength={1200} value={t} onChange={e => setT(e.target.value)} placeholder="Write a new brief for both minds" data-testid="brief-text" />
    <span className="lct-briefacts"><button type="button" className="m-btn m-go" disabled={busy || editIn > 0 || t.trim().length < 20} onClick={async () => { if (await run('brief', { text: t })) setT(''); }} data-testid="brief-save">Save brief</button>
      <button type="button" className="m-btn" disabled={busy || askIn > 0 || !!pr} onClick={() => run('brief_propose')} data-testid="brief-ask" data-tip="One short model call — they propose ONE better brief for both of them; nothing changes until you approve">{askIn ? `🧠 ask again in ${Math.ceil(askIn / 60)} min` : '🧠 Let them propose a better one'}</button></span>
  </section>;
}

// 🧠 a launched cat's brains: credit tank, decisions, the brief, battle records, chime in, pull / top up — re-read every 10s
export function BrainPanel({ cat, api, onChanged, noTalk = false }) {   // noTalk: the desk's cockpit carries its calls + your chime-ins
  const b = cat.brainsCfg; const [text, setText] = useState(''); const [err, setErr] = useState(''); const [keys, setKeys] = useState({}); const [busy, setBusy] = useState(false);
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) api(`/api/cats/${cat.id}`).then(r => r?.cat && onChanged?.(r.cat)).catch(() => {}); }, 10000); return () => clearInterval(t); }, [api, cat.id, onChanged]);
  if (!b) return null;
  const act = async (action, extra = {}) => { setErr(''); try { const r = await api(`/api/cats/${cat.id}/action`, { method: 'POST', body: JSON.stringify({ action, ...extra }) }); onChanged?.(r.cat); return true; } catch (e) { setErr(e.message); return false; } };
  const start = 10; const left = Math.max(0, b.credit ?? 0);
  return <section className="paper-panel lct-brains" data-testid="brain-panel">
    <div className="paper-panel-head"><div><span className="eyebrow">🧠 BRAINS · {b.brainMode?.toUpperCase()}</span><h2>{b.brains.map(x => x.split('/').pop()).join(' + ')}</h2></div><Panther size={56} gesture={cat.status === 'running' ? 'purr' : 'sleep'} /></div>
    <div className="lct-vitals">
      <span><small>CREDIT LEFT</small><b className="fl-tick" key={left}>{fmtUsd(left)}</b><i className="lct-tank"><em style={{ transform: `scaleX(${Math.min(1, left / start)})` }} /></i></span>
      <span><small>DECISIONS</small><b className="fl-tick" key={b.asks}>{b.asks || 0}</b><small>{fmtUsd(b.spent || 0)} spent</small></span>
      <span><small>OWED</small><b className={b.owed > 0 ? 'negative' : ''}>{fmtUsd(b.owed || 0)}</b><small>{b.billing === 'profit' ? 'paid from winning sales' : 'pay as you go'}</small></span>
      <span><small>MODEL FEES PAID</small><b>{fmtUsd(cat.brainFeesUsd || 0)}</b><small>apart from P/L</small></span>
    </div>
    {b.record ? <div className="lct-battle">{Object.entries(b.record).map(([m, r]) => <span key={m}><b>{m.split('/').pop()}</b>{r.n} trades · {r.won} won · <em className={r.pnlSol >= 0 ? 'positive' : 'negative'}>{r.pnlSol >= 0 ? '+' : ''}{r.pnlSol.toFixed(4)} SOL</em></span>)}</div> : null}
    {b.prompt ? <details className="lct-fold"><summary>📜 Its one-time brief (locked)</summary><p>{b.prompt}</p></details> : null}
    {noTalk ? null : <ul className="lct-dec">{(b.decisions || []).slice(-8).reverse().map((x, i) => <li key={`${x.at}-${i}`} style={{ '--i': i }} className={WORD[x.word] || ''}><b>{x.word}</b><span>${x.sym} · {x.by}</span><small>{x.why}</small></li>)}
      {!(b.decisions || []).length ? <li className="lct-load">No decision yet — the first comes before its first buy.</li> : null}</ul>}
    {b.kind === 'general' ? <><BriefCard cat={cat} act={act} api={api} /><OrderBox cat={cat} act={act} /></> : <><VenuePick value={cat.venues || ['trench']} onChange={v => act('venues', { venues: v })} />
      <ApiDrawer rows={cat.apiDrawer} draft={keys} onDraft={(k, v) => setKeys(x => ({ ...x, [k]: v.trim() }))} busy={busy}
        onSave={async (k, v) => { setBusy(true); if (await act('api_key', { provider: k, secret: v })) setKeys(x => ({ ...x, [k]: '' })); setBusy(false); }}
        onDrop={async k => { setBusy(true); await act('api_key', { provider: k }); setBusy(false); }} /></>}
    {noTalk ? null : <form className="lct-chime" onSubmit={async e => { e.preventDefault(); if (text.trim() && await act('chime', { text })) setText(''); }}>
      <input className="m-input" maxLength={280} value={text} onChange={e => setText(e.target.value)} placeholder="Chime in — advice it reads, never an order" data-testid="brain-chime" /><button type="submit" className="m-btn">💬 Send</button></form>}
    {(b.chime || []).length ? <p className="lct-note">Last said: “{b.chime[b.chime.length - 1].text}”</p> : null}
    <div className="lct-acts"><button type="button" className="m-btn" onClick={() => window.confirm('Sell every coin and pull all funds? The cat stays locked until you top up.') && act('pull')} data-testid="brain-pull">⏏ Pull all funds</button>
      {cat.agentWallet || cat.brainsCfg?.kind === 'general' ? <small className="lct-note">Add model credit from its wallet panel, in SOL or USDC.</small> : <button type="button" className="m-btn m-go" onClick={() => act('topup')} data-testid="brain-topup">＋ Top up (paper)</button>}</div>
    {cat.needsTopup ? <p className="lct-note">🔒 Funds pulled — top up to start this cat again.</p> : null}{cat.brainPaused ? <p className="lct-note">⏸ {cat.brainPaused}</p> : null}
    {err ? <p className="lct-err">⚠ {err}</p> : null}
  </section>;
}
