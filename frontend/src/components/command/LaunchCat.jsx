import React, { useEffect, useMemo, useState } from 'react';
import { Panther } from '../Panther';
import NumInput from '../NumInput';
import { LookAvatar } from './CatLook';
import { CAT_VARIATIONS } from './catCoats';
import { useMyCat } from '../../lib/myCat';
import '../../styles/launchCat.css';

// 🚀 LAUNCH A CAT (owner, 2026-10-20): pick up to two AI brains from OpenRouter's whole public list, choose how they work together, write
// ONE brief they keep for life, choose how model calls are paid. A brain is asked once before a buy and ≤ 3 times while the coin is live,
// only on a ±10% move — so credit pays for decisions, never a chat loop. You can chime in (advice); you never trade for it. Paper cats.
export const SORTS = [['smart', '♟ Smartest'], ['cheap', '💸 Cheapest'], ['ctx', '📚 Biggest memory'], ['new', '🆕 Newest']];
export const STEPS = ['🧠 Brains', '🤝 How they work', '🐱 Identity + risk + brief', '🚀 Launch'];
const PAGE = 60;
const CHIP = { degen: 'lct-c-degen', trading: 'lct-c-trading', thinking: 'lct-c-thinking', reasoning: 'lct-c-reasoning', meta: 'lct-c-meta', free: 'lct-c-free' };
const DUO = { turns: 'is-turns', discuss: 'is-discuss', together: 'is-together', battle: 'is-battle' };
const WORD = { BUY: 'w-buy', SKIP: 'w-skip', HOLD: 'w-hold', SELL: 'w-sell', TRIM: 'w-trim', RULES: 'w-rules' };
export const fmtUsd = v => v == null ? '—' : v === 0 ? 'free' : v < 0.001 ? `$${v.toFixed(6)}` : v < 1 ? `$${v.toFixed(4)}` : `$${v.toFixed(2)}`;
const fmtCtx = n => n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}K` : String(n || '—');

export function filterModels(models, { q = '', cat = '', sort = 'smart' } = {}) {
  const t = q.trim().toLowerCase();
  const rows = (models || []).filter(m => (!cat || m.cats.includes(cat)) && (!t || `${m.name} ${m.id} ${m.desc}`.toLowerCase().includes(t)));
  const key = { smart: m => -(m.intel ?? -1), cheap: m => m.perDecision, ctx: m => -m.ctx, new: m => -m.created }[sort] || (() => 0);
  return [...rows].sort((a, b) => key(a) - key(b));
}

export function planOf(picked, mode, budget) {   // mirrors launch_cat.plan (change both)
  if (!picked.length) return null;
  const calls = picked.length > 1 && (mode === 'discuss' || mode === 'together') ? 2 : 1;
  const avg = picked.reduce((s, m) => s + (m.perDecision || 0), 0) / picked.length;
  const one = calls > 1 ? avg * calls : avg;
  const trade = one * (1 + (budget?.liveAsks ?? 3));
  return { perDecision: one, perTrade: trade, trades: trade > 0 ? Math.floor((budget?.start ?? 10) / trade) : null, calls };
}

function ModelTile({ m, on, onPick, i }) {
  return <button type="button" className={`lct-tile${on ? ' is-on' : ''}${m.tag ? ' is-rec' : ''}`} style={{ '--i': Math.min(i, 20) }} onClick={() => onPick(m)} data-testid={`lct-m-${m.id}`} aria-pressed={on}>
    <span className="lct-tile-top">{m.tag ? <b className="lct-tag">⭐ {m.tag}</b> : null}<small>{m.provider}</small>{m.intel != null ? <em title="intelligence index">♟ {m.intel}</em> : null}</span>
    <strong>{m.name.replace(/^[^:]+:\s*/, '')}</strong>
    <span className="lct-tile-nums"><span><small>A DECISION</small>{fmtUsd(m.perDecision)}</span><span><small>MEMORY</small>{fmtCtx(m.ctx)}</span><span><small>$ / 1M OUT</small>{fmtUsd(m.outUsd)}</span></span>
    <span className="lct-chips">{m.cats.slice(0, 4).map(c => <i key={c} className={CHIP[c]}>{c}</i>)}</span>
    {m.why || m.desc ? <p>{m.why || m.desc}</p> : null}
  </button>;
}

// 🧠 THE BRAIN SOCKET (FeeCat redo, 2026-10-23): YOUR built cat with the picked brains drawn as lit orbs, each wired into its head — the wire
// pulses toward the cat; two brains = two wires; none = an empty socket waiting.
export function BrainSocket({ picked, mood }) {
  const mine = useMyCat(); const coat = CAT_VARIATIONS[mine?.coat ?? 0] || CAT_VARIATIONS[0];
  const slots = [picked[0] || null, picked[1] || null];
  return <div className={`lct-socket n-${picked.length}`} aria-hidden="true">
    <svg className="lct-wires" viewBox="0 0 220 120" preserveAspectRatio="none">{slots.map((m, i) => <path key={i} className={`w w${i}${m ? ' on' : ''}`} d={i ? 'M188 30 C 160 30, 150 58, 118 60' : 'M32 30 C 60 30, 70 58, 102 60'} />)}</svg>
    {slots.map((m, i) => <span key={i} className={`lct-node n${i}${m ? ' on' : ''}`}>{m ? (m.tag || m.name.replace(/^[^:]+:\s*/, '')).slice(0, 6) : '+'}</span>)}
    <span className="lct-cat"><LookAvatar cat={[coat[0], coat[1], coat[2], mine?.pattern || coat[3]]} look={mine?.look} size={92} gesture={mood} /></span>
  </div>;
}

function Duo({ mode, picked }) {
  const [a, b] = picked;
  return <div className={`lct-duo ${DUO[mode] || ''}${b ? '' : ' is-solo'}`} aria-hidden="true">
    <span className="lct-orb o1">{(a?.tag || a?.name || '?').slice(0, 4)}</span><i className="lct-beam" /><span className="lct-orb o2">{b ? (b.tag || b.name).slice(0, 4) : '—'}</span><i className="lct-ring" />
  </div>;
}

const plainForm = () => ({ name: '', handle: '', avatar: 0, startingBalanceSol: '10', maxPositionSol: '0.5', dailyBuyLimitSol: '2', maxDailyLossSol: '0.5' });
const plainOk = f => f.name.trim().length > 1;

export function LaunchCat({ api, ownerId, onCreated, onCancel, Fields, Preview, newForm = plainForm, formOk = plainOk, avatarOf = () => 'Fee' }) {
  const [d, setD] = useState(null); const [err, setErr] = useState('');
  const [step, setStep] = useState(0); const [q, setQ] = useState(''); const [cat, setCat] = useState(''); const [sort, setSort] = useState('smart'); const [n, setN] = useState(PAGE);
  const [picked, setPicked] = useState([]); const [mode, setMode] = useState('turns'); const [billing, setBilling] = useState('profit');
  const [form, setForm] = useState(() => newForm()); const update = (k, v) => setForm(f => ({ ...f, [k]: v })); const name = form.name;
  const [prompt, setPrompt] = useState(''); const [saving, setSaving] = useState(false);
  useEffect(() => { let on = true; api('/api/cats/models').then(x => on && setD(x)).catch(e => on && setErr(e.message)); return () => { on = false; }; }, [api]);
  const rows = useMemo(() => filterModels(d?.models, { q, cat, sort }), [d, q, cat, sort]);
  useEffect(() => setN(PAGE), [q, cat, sort]);
  const pick = m => setPicked(p => p.some(x => x.id === m.id) ? p.filter(x => x.id !== m.id) : [...p, m].slice(-2));
  const plan = planOf(picked, mode, d?.budget);
  const ready = [picked.length > 0, true, formOk(form), true];
  const launch = async () => {
    setSaving(true); setErr('');
    try {
      const handle = form.handle || form.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 20) || 'cat';
      const r = await api('/api/cats', { method: 'POST', body: JSON.stringify({ strategy: 'momentum', ...form, ownerId: ownerId(), name: form.name.trim(), handle, avatar: avatarOf(form.avatar),
        brains: picked.map(m => m.id), brainMode: mode, billing, prompt }) });
      const started = await api(`/api/cats/${r.cat.id}/action`, { method: 'POST', body: JSON.stringify({ action: 'start' }) }).catch(() => r);   // same as Create a Cat: it starts trading at once
      onCreated?.(started.cat || r.cat);
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };
  return <section className="lct" data-testid="launch-cat">
    <header className="lct-head"><BrainSocket picked={picked} mood={saving ? 'pounce' : picked.length === 2 ? 'celebrate' : picked.length ? 'purr' : 'think'} />
      <div><span className="eyebrow">🚀 LAUNCH A CAT · PAPER</span><h2>Give your cat <em>{picked.length === 2 ? 'two brains' : 'a brain'}</em>.</h2>
        <p>Pick up to two models from OpenRouter's whole list. They decide once before a buy and up to {d?.budget?.liveAsks ?? 3} times while a coin is live — only on a ±{d?.budget?.alertPct ?? 10}% move. You chime in; the cat trades.</p></div></header>
    <nav className="lct-steps" style={{ '--p': step / (STEPS.length - 1) }}><i className="lct-prog" aria-hidden="true"><u /></i>{STEPS.map((s, i) => <button key={s} type="button" className={`${i === step ? 'is-on' : ''}${i < step ? ' is-done' : ''}`} onClick={() => i <= step || ready.slice(0, i).every(Boolean) ? setStep(i) : null} data-testid={`lct-step-${i}`}><b>{i + 1}</b>{s}</button>)}</nav>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    {step === 0 ? <div className="lct-pane">
      {!d ? <p className="lct-load">Reading OpenRouter's model list…</p> : <>
        {d.rec?.length ? <><h4 className="lct-h">⭐ OUR THREE — the brains FEELESS already runs</h4><div className="lct-rec">{d.rec.map((m, i) => <ModelTile key={m.id} m={m} i={i} on={picked.some(x => x.id === m.id)} onPick={pick} />)}</div></> : null}
        <div className="lct-bar"><input className="m-input" placeholder={`Search ${d.models.length} models…`} value={q} onChange={e => setQ(e.target.value)} data-testid="lct-q" />
          <div className="m-seg">{SORTS.map(([k, l]) => <button key={k} type="button" className={sort === k ? 'is-on' : ''} onClick={() => setSort(k)}>{l}</button>)}</div></div>
        <div className="lct-cats"><button type="button" className={!cat ? 'is-on' : ''} onClick={() => setCat('')}>✨ All <small>{d.models.length}</small></button>{d.cats.map(c => <button key={c.key} type="button" className={cat === c.key ? 'is-on' : ''} onClick={() => setCat(c.key === cat ? '' : c.key)} data-tip={c.why} data-testid={`lct-cat-${c.key}`}>{c.label} <small>{c.n}</small></button>)}</div>
        <div className="lct-grid">{rows.slice(0, n).map((m, i) => <ModelTile key={m.id} m={m} i={i} on={picked.some(x => x.id === m.id)} onPick={pick} />)}</div>
        {rows.length > n ? <button type="button" className="m-btn lct-more" onClick={() => setN(x => x + PAGE)}>Show {Math.min(PAGE, rows.length - n)} more of {rows.length}</button> : null}
        {!rows.length ? <p className="lct-load">No model matches that.</p> : null}</>}
    </div> : null}
    {step === 1 ? <div className="lct-pane lct-mode"><Duo mode={mode} picked={picked} />
      {picked.length < 2 ? <p className="lct-note">One brain: it makes every call. Pick a second in step 1 to choose how they work together.</p> :
        <div className="lct-modes">{(d?.modes || []).map(m => <button key={m.key} type="button" className={mode === m.key ? 'is-on' : ''} onClick={() => setMode(m.key)} data-testid={`lct-mode-${m.key}`}><b>{m.label}</b><small>{m.why}</small></button>)}</div>}
    </div> : null}
    {step === 2 ? <div className="lct-pane lct-brief">
      {Fields ? <div className="cct-split lct-ident">{<Fields form={form} update={update} />}{Preview ? <aside className="cct-preview m-live" data-testid="lct-preview"><Preview form={form} /></aside> : null}</div> : <>
        <label>Cat name<input className="m-input" maxLength={24} value={form.name} onChange={e => update('name', e.target.value)} placeholder="Midnight Prowler" data-testid="lct-name" /></label>
        <label>Starting paper balance · SOL<NumInput className="m-input" value={form.startingBalanceSol} onChange={e => update('startingBalanceSol', e.target.value)} /></label></>}
      <label className="lct-seal"><span><b>📜 THE BRIEF</b><em>sealed for life — both brains read it before every call; it can never be changed</em></span>
        <textarea className="m-input" rows={6} maxLength={1200} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="e.g. Only buy coins sitting on their germ floor with higher lows. Bank half at +30%. Never chase a green candle." data-testid="lct-prompt" />
        <i className="lct-len" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.01, prompt.length / 1200)})` }} /></i><small>{prompt.length} / 1200</small></label>
    </div> : null}
    {step === 3 ? <div className="lct-pane lct-pay">
      <div className="lct-modes">{(d?.billing || []).map(b => <button key={b.key} type="button" className={billing === b.key ? 'is-on' : ''} onClick={() => setBilling(b.key)} data-testid={`lct-bill-${b.key}`}><b>{b.label}</b></button>)}</div>
      {plan ? <div className="lct-meter"><span><small>A DECISION</small><b>{fmtUsd(plan.perDecision)}</b></span><span><small>A TRADE (worst case)</small><b>{fmtUsd(plan.perTrade)}</b></span>
        <span><small>${d?.budget?.start ?? 10} CREDIT COVERS</small><b>{plan.trades == null ? '∞ (free models)' : `≈ ${plan.trades.toLocaleString()} trades`}</b></span>
        <i className="lct-tank"><em style={{ transform: `scaleX(${plan.trades == null ? 1 : Math.min(1, plan.trades / 500)})` }} /></i></div> : null}
      <p className="lct-note">{d?.live ? '🟢 Model calls are ON.' : '⏸ Model calls are OFF until FEELESS switches them on — until then the FEELESS rule engine trades your cat and nothing is charged.'} The ${d?.budget?.start ?? 10} starting credit is paper credit: real billing isn't built yet.</p>
      <button type="button" className="m-btn m-go lct-go" disabled={saving || !ready.slice(0, 3).every(Boolean)} onClick={launch} data-testid="lct-launch">{saving ? 'Launching…' : `🚀 Launch ${name || 'the cat'}`}</button>
    </div> : null}
    <footer className="lct-foot"><span>{picked.length ? picked.map(m => m.tag || m.name.replace(/^[^:]+:\s*/, '')).join(' + ') : 'no brain picked'}{plan ? ` · ${fmtUsd(plan.perDecision)} a decision` : ''}</span>
      <span>{onCancel ? <button type="button" className="m-btn" onClick={onCancel}>Cancel</button> : null}{step < 3 ? <button type="button" className="m-btn m-go" disabled={!ready[step]} onClick={() => setStep(s => s + 1)} data-testid="lct-next">Next ›</button> : null}</span></footer>
  </section>;
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
    <form className="lct-chime" onSubmit={async e => { e.preventDefault(); if (text.trim() && await act('chime', { text })) setText(''); }}>
      <input className="m-input" maxLength={280} value={text} onChange={e => setText(e.target.value)} placeholder="Chime in — advice it reads, never an order" data-testid="brain-chime" /><button type="submit" className="m-btn">💬 Send</button></form>
    {(b.chime || []).length ? <p className="lct-note">Last said: “{b.chime[b.chime.length - 1].text}”</p> : null}
    <div className="lct-acts"><button type="button" className="m-btn" onClick={() => window.confirm('Sell every coin and pull all funds? The cat stays locked until you top up.') && act('pull')} data-testid="brain-pull">⏏ Pull all funds</button>
      <button type="button" className="m-btn m-go" onClick={() => act('topup')} data-testid="brain-topup">＋ Top up (paper)</button></div>
    {cat.needsTopup ? <p className="lct-note">🔒 Funds pulled — top up to start this cat again.</p> : null}{cat.brainPaused ? <p className="lct-note">⏸ {cat.brainPaused}</p> : null}
    {err ? <p className="lct-err">⚠ {err}</p> : null}
  </section>;
}
