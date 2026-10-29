import React, { useEffect, useMemo, useState } from 'react';
import { Panther } from '../Panther';
import NumInput from '../NumInput';
import { LookAvatar } from './CatLook';
import { CAT_VARIATIONS } from './catCoats';
import { useMyCat } from '../../lib/myCat';
import { FundReceipt } from './FundReceipt';
import '../../styles/launchCat.css';

// 🚀 LAUNCH A CAT (owner, 2026-10-20): pick up to two AI brains from OpenRouter's whole public list, choose how they work together, write
// ONE brief they keep for life, choose how model calls are paid. A brain is asked once before a buy and ≤ 3 times while the coin is live,
// only on a ±10% move — so credit pays for decisions, never a chat loop. You can chime in (advice); you never trade for it. Paper cats.
export const SORTS = [['smart', '♟ Smartest'], ['cheap', '💸 Cheapest'], ['ctx', '📚 Biggest memory'], ['new', '🆕 Newest']];
export const STEPS = ['🧠 Brains', '🤝 How they work', '🐱 Identity + risk + brief', '🚀 Launch → 💵 go real'];
const GEN_STEPS = ['🧠 Its minds', '🧭 How they work', '🐱 Identity + standing orders', '🚀 Launch → 👛 its wallet'];
// 📈 TRADING hunts coins on its own · 🧭 GENERAL does what you order (owner, 2026-10-23) — both end on the wallet switch (link → budget → REAL)
export const KIND = { trading: { eyebrow: '📈 TRADING AI CAT', cat: 'trading', brief: '📜 THE BRIEF', hint: 'e.g. Only buy coins sitting on their germ floor with higher lows. Bank half at +30%. Never chase a green candle.',
  pitch: 'Pick 1–2 trading models. They decide once before a buy and up to 3 times while a coin is live — only on a ±10% move.',
  next: ['🚀 launch', '👛 its own wallet', '✍ you sign ONE funding', '🤖 it trades inside the caps'] },
  general: { eyebrow: '🧭 GENERAL AI CAT', cat: '', brief: '📜 STANDING ORDERS', hint: 'e.g. You are my content scout: every morning find 3 trending crypto topics with sources and draft posts in my voice — never post or sign up without asking me. Coin orders: never more than 0.1 SOL a coin.',
  pitch: 'Pick 1–2 all-round models — its two minds. Ask in plain words: it answers from memory, or each mind researches half in its own cloud browser while you watch, then they merge. Coin orders go from its own wallet — you OK each one until you switch it to auto.',
  next: ['🚀 launch', '👛 its own wallet', '✍ you sign ONE funding', '✅ you OK each move · or 🤖 auto'] } };
// 🧭 how a General cat's two minds work (cat_agent.py — change both): shown as step 2 instead of the trading modes
export const GENERAL_FLOW = [
  ['⚡', 'You ask', 'mind A answers from memory when it can — one call, no browsing'],
  ['🧠🧠', 'They split it', 'each mind works its half in its own cloud browser — you watch both live'],
  ['✋', 'You step in', 'a sign-in or CAPTCHA pauses that window for you — it never types a password'],
  ['🔗', 'One answer', 'mind A merges both halves with sources — it stops at your $ cap per task'],
];
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

export function filterModels(models, { q = '', cat = '', sort = 'smart' } = {}) {
  const t = q.trim().toLowerCase();
  const rows = (models || []).filter(m => (!cat || m.cats.includes(cat)) && (!t || `${m.name} ${m.id} ${m.desc}`.toLowerCase().includes(t)));
  const key = { smart: m => -(m.intel ?? -1), cheap: m => m.perDecision, ctx: m => -m.ctx, new: m => -m.created }[sort] || (() => 0);
  return [...rows].sort((a, b) => key(a) - key(b));
}

export function planOf(picked, mode, budget, kind = 'trading') {   // mirrors launch_cat.plan (change both)
  if (!picked.length) return null;
  if (kind === 'general') { const task = picked.reduce((s, m) => s + (m.perTask || 0), 0) / picked.length;   // a task runs both windows; perTask counts both
    return { perTask: task, perDecision: task, tasks: task > 0 ? Math.floor((budget?.start ?? 10) / task) : null }; }
  const calls = picked.length > 1 && (mode === 'discuss' || mode === 'together') ? 2 : 1;
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
        <span className="is-hot"><small>{gen ? 'A TASK ≤' : 'A DECISION'}</small>{fmtUsd(gen ? m.perTask : m.perDecision)}</span><span><small>MEMORY</small>{fmtCtx(m.ctx)}</span></span>
      <span className="lct-chips">{m.cats.slice(0, 4).map(c => <i key={c} className={CHIP[c]}>{c}</i>)}</span></button>
    {desc ? <details className="lct-desc"><summary data-tip="What this model is and what it is good at">ABOUT</summary><p>{desc}</p></details> : null}
  </div>;
}

// 🧠 THE BRAIN SOCKET (FeeCat redo, 2026-10-23): YOUR built cat with the picked brains drawn as lit orbs, each wired into its head — the wire
// pulses toward the cat; two brains = two wires; none = an empty socket waiting.
export function BrainSocket({ picked, mood }) {
  const mine = useMyCat(); const coat = CAT_VARIATIONS[mine?.coat ?? 0] || CAT_VARIATIONS[0];
  const slots = [picked[0] || null, picked[1] || null];
  return <div className={`lct-socket n-${picked.length}`} aria-hidden="true">
    <svg className="lct-wires" viewBox="0 0 220 120" preserveAspectRatio="none">{slots.map((m, i) => <path key={i} className={`w w${i}${m ? ' on' : ''}`} d={i ? 'M188 30 C 160 30, 150 58, 118 60' : 'M32 30 C 60 30, 70 58, 102 60'} />)}</svg>
    {slots.map((m, i) => <span key={i} className={`lct-node n${i}${m ? ' on' : ''}`}>{m ? mono(m) : '+'}<u>{i ? 'B' : 'A'}</u></span>)}
    <span className="lct-cat"><LookAvatar cat={[coat[0], coat[1], coat[2], mine?.pattern || coat[3]]} look={mine?.look} size={92} gesture={mood} /></span>
  </div>;
}

// 🫧 the two minds (owner 2026-10-29: "better design for the 2 bubbles"): a lit orb with the maker's monogram, its role, its full name and its price —
// never a name cut to four letters
function Mind({ m, i, kind }) {
  const gen = kind === 'general';
  return <span className={`lct-mind m${i}${m ? '' : ' is-empty'}`}><span className={i ? "lct-orb o2" : "lct-orb o1"}><b>{m ? mono(m) : '+'}</b><i aria-hidden="true" /></span>
    <em>{gen ? `MIND ${i ? 'B' : 'A'}${i ? '' : ' · LEADS'}` : `BRAIN ${i ? 'B' : 'A'}`}</em><strong title={m ? shortName(m) : ''}>{m ? shortName(m) : i ? 'no second pick' : 'pick one'}</strong>
    {m ? <small className="m-num">{gen ? `≤ ${fmtUsd(m.perTask)} a task` : `${fmtUsd(m.perDecision)} a decision`}</small> : null}</span>;
}
function Duo({ mode, picked, kind }) {
  const [a, b] = picked;
  return <div className={`lct-duo ${kind === 'general' ? 'is-general' : DUO[mode] || ''}${b ? '' : ' is-solo'}`} aria-hidden="true">
    <Mind m={a} i={0} kind={kind} /><i className="lct-beam" /><Mind m={b} i={1} kind={kind} /><i className="lct-ring" />
  </div>;
}

const plainForm = () => ({ name: '', handle: '', avatar: 0, startingBalanceSol: '10', maxPositionSol: '0.5', dailyBuyLimitSol: '2', maxDailyLossSol: '0.5' });
const plainOk = f => f.name.trim().length > 1;

export function LaunchCat({ api, ownerId, onCreated, onCancel, Fields, Preview, newForm = plainForm, formOk = plainOk, avatarOf = () => 'Fee', kind = 'trading' }) {
  const K = KIND[kind] || KIND.trading;
  const [d, setD] = useState(null); const [err, setErr] = useState('');
  const [step, setStep] = useState(0); const [q, setQ] = useState(''); const [cat, setCat] = useState(K.cat); const [sort, setSort] = useState('smart'); const [n, setN] = useState(PAGE);
  const gen = kind === 'general'; const steps = gen ? GEN_STEPS : STEPS;
  const [picked, setPicked] = useState([]); const [mode, setMode] = useState('turns'); const [billing, setBilling] = useState(gen ? 'payg' : 'profit');
  const [form, setForm] = useState(() => newForm()); const update = (k, v) => setForm(f => ({ ...f, [k]: v })); const name = form.name;
  const [prompt, setPrompt] = useState(''); const [saving, setSaving] = useState(false);
  useEffect(() => { let on = true; api('/api/cats/models').then(x => on && setD(x)).catch(e => on && setErr(e.message)); return () => { on = false; }; }, [api]);
  const rows = useMemo(() => filterModels(d?.models, { q, cat, sort }), [d, q, cat, sort]);
  useEffect(() => setN(PAGE), [q, cat, sort]);
  const pick = m => setPicked(p => p.some(x => x.id === m.id) ? p.filter(x => x.id !== m.id) : [...p, m].slice(-2));
  const plan = planOf(picked, mode, d?.budget, kind);
  // 🧭 the General wizard leads with its own jobs (agent · content · code); the trading wizard never shows them
  const cats = useMemo(() => { const c = (d?.cats || []).filter(x => gen || !x.general); return gen ? [...c.filter(x => x.general), ...c.filter(x => !x.general)] : c; }, [d, gen]);
  const bills = (d?.billing || []).filter(b => !gen || b.key === 'payg');   // a general cat earns nothing to pay from — it runs on credit
  const ready = [picked.length > 0, true, formOk(form), true];
  const launch = async () => {
    setSaving(true); setErr('');
    try {
      const handle = form.handle || form.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 20) || 'cat';
      const r = await api('/api/cats', { method: 'POST', body: JSON.stringify({ strategy: 'momentum', ...form, ownerId: ownerId(), name: form.name.trim(), handle, avatar: avatarOf(form.avatar),
        brains: picked.map(m => m.id), brainMode: gen ? 'turns' : mode, billing, prompt, brainKind: kind }) });
      const started = await api(`/api/cats/${r.cat.id}/action`, { method: 'POST', body: JSON.stringify({ action: 'start' }) }).catch(() => r);   // same as Create a Cat: it starts trading at once
      onCreated?.(started.cat || r.cat);
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };
  return <section className={`lct is-${kind}`} data-testid="launch-cat">
    <header className="lct-head"><BrainSocket picked={picked} mood={saving ? 'pounce' : picked.length === 2 ? 'celebrate' : picked.length ? 'purr' : 'think'} />
      <div><span className="eyebrow" data-testid="lct-kind">{K.eyebrow} · ITS OWN WALLET</span><h2>Give your cat <em>{picked.length === 2 ? (gen ? 'two minds' : 'two brains') : (gen ? 'a mind' : 'a brain')}</em>.</h2>
        <p>{K.pitch}</p></div></header>
    <nav className="lct-steps" style={{ '--p': step / (steps.length - 1) }}><i className="lct-prog" aria-hidden="true"><u /></i>{steps.map((s, i) => <button key={s} type="button" className={`${i === step ? 'is-on' : ''}${i < step ? ' is-done' : ''}`} onClick={() => i <= step || ready.slice(0, i).every(Boolean) ? setStep(i) : null} data-testid={`lct-step-${i}`}><b>{i + 1}</b>{s}</button>)}</nav>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    {step === 0 ? <div className="lct-pane">
      {!d ? <p className="lct-load">Reading OpenRouter's model list…</p> : <>
        {d.rec?.length ? <><h4 className="lct-h">⭐ FEELESS PICKS — the brains FEELESS already runs</h4><div className="lct-rec">{d.rec.map((m, i) => <ModelTile key={m.id} m={m} i={i} kind={kind} on={picked.some(x => x.id === m.id)} onPick={pick} />)}</div></> : null}
        <div className="lct-bar"><input className="m-input" placeholder={`Search ${d.models.length} models…`} value={q} onChange={e => setQ(e.target.value)} data-testid="lct-q" />
          <div className="m-seg">{SORTS.map(([k, l]) => <button key={k} type="button" className={sort === k ? 'is-on' : ''} onClick={() => setSort(k)}>{l}</button>)}</div></div>
        <div className="lct-cats"><button type="button" className={!cat ? 'is-on' : ''} onClick={() => setCat('')}>✨ All <small>{d.models.length}</small></button>{cats.map(c => <button key={c.key} type="button" className={`${cat === c.key ? 'is-on' : ''}${c.general ? ' is-job' : ''}`} onClick={() => setCat(c.key === cat ? '' : c.key)} data-tip={c.why} data-testid={`lct-cat-${c.key}`}>{c.label} <small>{c.n}</small></button>)}</div>
        <div className="lct-grid">{rows.slice(0, n).map((m, i) => <ModelTile key={m.id} m={m} i={i} kind={kind} on={picked.some(x => x.id === m.id)} onPick={pick} />)}</div>
        {rows.length > n ? <button type="button" className="m-btn lct-more" onClick={() => setN(x => x + PAGE)}>Show {Math.min(PAGE, rows.length - n)} more of {rows.length}</button> : null}
        {!rows.length ? <p className="lct-load">No model matches that.</p> : null}</>}
    </div> : null}
    {step === 1 ? <div className="lct-pane lct-mode"><Duo mode={mode} picked={picked} kind={kind} />
      {gen ? <><ol className="lct-flow" data-testid="lct-flow">{GENERAL_FLOW.map(([ic, t, w], i) => <li key={t} style={{ '--i': i }}><i aria-hidden="true">{ic}</i><b>{t}</b><small>{w}</small></li>)}</ol>
        <p className="lct-note">{picked.length < 2 ? 'One mind: it takes every task in its own window. Pick a second in step 1 and they split the work.' : 'In its chat you talk to 🧠🧠 both minds or to 🧠 one of them — one mind takes the whole task in its own window.'}</p></>
      : picked.length < 2 ? <p className="lct-note">One brain: it makes every call. Pick a second in step 1 to choose how they work together.</p> :
        <div className="lct-modes">{(d?.modes || []).map(m => <button key={m.key} type="button" className={mode === m.key ? 'is-on' : ''} onClick={() => setMode(m.key)} data-testid={`lct-mode-${m.key}`}><b>{m.label}</b><small>{m.why}</small></button>)}</div>}
    </div> : null}
    {step === 2 ? <div className="lct-pane lct-brief">
      {Fields ? <div className="cct-split lct-ident">{<Fields form={form} update={update} />}{Preview ? <aside className="cct-preview m-live" data-testid="lct-preview"><Preview form={form} /></aside> : null}</div> : <>
        <label>Cat name<input className="m-input" maxLength={24} value={form.name} onChange={e => update('name', e.target.value)} placeholder="Midnight Prowler" data-testid="lct-name" /></label>
        <label>Starting paper balance · SOL<NumInput className="m-input" value={form.startingBalanceSol} onChange={e => update('startingBalanceSol', e.target.value)} /></label></>}
      <label className="lct-seal"><span><b>{K.brief}</b><em>{gen ? 'sealed for life — its minds read it on every step of every task; it can never be changed' : 'sealed for life — both brains read it before every call; it can never be changed'}</em></span>
        <textarea className="m-input" rows={6} maxLength={1200} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder={K.hint} data-testid="lct-prompt" />
        <i className="lct-len" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.01, prompt.length / 1200)})` }} /></i><small>{prompt.length} / 1200</small></label>
    </div> : null}
    {step === 3 ? <div className="lct-pane lct-pay">
      <div className="lct-modes">{bills.map(b => <button key={b.key} type="button" className={billing === b.key ? 'is-on' : ''} onClick={() => setBilling(b.key)} data-testid={`lct-bill-${b.key}`}><b>{b.label}</b></button>)}</div>
      {plan && gen ? <div className="lct-meter"><span><small>A TASK (worst case)</small><b>{fmtUsd(plan.perTask)}</b></span><span><small>ITS CAP · YOU SET IT</small><b>$0.02 – $1</b></span>
        <span><small>${d?.budget?.start ?? 10} CREDIT COVERS</small><b>{plan.tasks == null ? '∞ (free models)' : `≈ ${plan.tasks.toLocaleString()} tasks`}</b></span>
        <i className="lct-tank"><em style={{ transform: `scaleX(${plan.tasks == null ? 1 : Math.min(1, plan.tasks / 500)})` }} /></i></div>
      : plan ? <div className="lct-meter"><span><small>A DECISION</small><b>{fmtUsd(plan.perDecision)}</b></span><span><small>A TRADE (worst case)</small><b>{fmtUsd(plan.perTrade)}</b></span>
        <span><small>${d?.budget?.start ?? 10} CREDIT COVERS</small><b>{plan.trades == null ? '∞ (free models)' : `≈ ${plan.trades.toLocaleString()} trades`}</b></span>
        <i className="lct-tank"><em style={{ transform: `scaleX(${plan.trades == null ? 1 : Math.min(1, plan.trades / 500)})` }} /></i></div> : null}
      <p className="lct-note">{(gen ? d?.generalLive : d?.live) ? '🟢 Model calls are ON.' : gen ? '⏸ Model calls are OFF until FEELESS switches them on — until then asking sends and charges nothing.' : '⏸ Model calls are OFF until FEELESS switches them on — until then the FEELESS rule engine trades your cat and nothing is charged.'} The ${d?.budget?.start ?? 10} starting credit is paper credit: real billing isn't built yet.</p>
      <FundReceipt />
      <p className="lct-next" data-testid="lct-next-real">{K.next.map((x, i) => <React.Fragment key={x}>{i ? <u /> : null}<i className={i === K.next.length - 1 ? 'is-real' : ''}>{x}</i></React.Fragment>)}</p>
      <button type="button" className="m-btn m-go lct-go" disabled={saving || !ready.slice(0, 3).every(Boolean)} onClick={launch} data-testid="lct-launch">{saving ? 'Launching…' : `🚀 Launch ${name || 'the cat'} → go real`}</button>
    </div> : null}
    <footer className="lct-foot"><span>{picked.length ? picked.map(m => m.tag || m.name.replace(/^[^:]+:\s*/, '')).join(' + ') : 'no brain picked'}{plan ? (gen ? ` · ≤ ${fmtUsd(plan.perTask)} a task` : ` · ${fmtUsd(plan.perDecision)} a decision`) : ''}</span>
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

// 🧠 a launched cat's brains: credit tank, decisions, the brief, battle records, chime in, pull / top up — re-read every 10s
export function BrainPanel({ cat, api, onChanged }) {
  const b = cat.brainsCfg; const [text, setText] = useState(''); const [err, setErr] = useState('');
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
    <ul className="lct-dec">{(b.decisions || []).slice(-8).reverse().map((x, i) => <li key={`${x.at}-${i}`} style={{ '--i': i }} className={WORD[x.word] || ''}><b>{x.word}</b><span>${x.sym} · {x.by}</span><small>{x.why}</small></li>)}
      {!(b.decisions || []).length ? <li className="lct-load">No decision yet — the first comes before its first buy.</li> : null}</ul>
    {b.kind === 'general' ? <OrderBox cat={cat} act={act} /> : null}
    <form className="lct-chime" onSubmit={async e => { e.preventDefault(); if (text.trim() && await act('chime', { text })) setText(''); }}>
      <input className="m-input" maxLength={280} value={text} onChange={e => setText(e.target.value)} placeholder="Chime in — advice it reads, never an order" data-testid="brain-chime" /><button type="submit" className="m-btn">💬 Send</button></form>
    {(b.chime || []).length ? <p className="lct-note">Last said: “{b.chime[b.chime.length - 1].text}”</p> : null}
    <div className="lct-acts"><button type="button" className="m-btn" onClick={() => window.confirm('Sell every coin and pull all funds? The cat stays locked until you top up.') && act('pull')} data-testid="brain-pull">⏏ Pull all funds</button>
      <button type="button" className="m-btn m-go" onClick={() => act('topup')} data-testid="brain-topup">＋ Top up (paper)</button></div>
    {cat.needsTopup ? <p className="lct-note">🔒 Funds pulled — top up to start this cat again.</p> : null}{cat.brainPaused ? <p className="lct-note">⏸ {cat.brainPaused}</p> : null}
    {err ? <p className="lct-err">⚠ {err}</p> : null}
  </section>;
}
