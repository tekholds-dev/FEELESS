import React, { useCallback, useEffect, useState } from 'react';
import NumInput from '../NumInput';
import { createPortal } from 'react-dom';
import { Activity, AlertTriangle, ArrowLeft, Cat, ChevronRight, Gauge, Play, Plus, Trophy, X } from 'lucide-react';
import { CAT_VARIATIONS, CatAvatar, catByName } from './catCoats';
import { ShareGifButton } from '../ShareGif';
import '../../styles/feecatPage.css';

import { tiny } from '../../lib/num';
import { LaunchCat, BrainPanel } from './LaunchCat';
import { LookAvatar, LookPicker, DEFAULT_LOOK } from './CatLook';
import { readMyCat } from '../../lib/myCat';
import { EngineLine } from './CatBrainSwitch';
import { CatDesk } from './CatDesk';
import { AgentPicker, AGENT_MAX } from './AgentPicker';
const OWNER_KEY = 'feeless-paper-owner';
const api = async (path, options = {}) => {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || body.error || 'Paper agent request failed.');
  return body;
};
const ownerId = () => {
  try {
    let value = localStorage.getItem(OWNER_KEY);
    if (!value) { value = `browser-${crypto.randomUUID()}`; localStorage.setItem(OWNER_KEY, value); }
    return value;
  } catch { return 'preview-browser-owner'; }
};
const money = value => `${Number(value || 0) >= 0 ? '+' : ''}${Number(value || 0).toFixed(4)} SOL`;
const time = value => value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';
const usd = value => Number(value) > 0 ? `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : 'MC unavailable';
const eventSymbol = event => event.symbol || event.detail?.match(/\bof\s+([A-Z0-9_]{2,})\b/i)?.[1] || 'TRADE';
const tradeCard = event => ({
  kicker: `FEELESS · ${event.catName?.toUpperCase() || 'FEE'} TRADE RECEIPT`,
  title: `$${eventSymbol(event)}`,
  tone: event.type === 'SELL' && Number(event.pnlSol) < 0 ? 'down' : 'up',
  big: event.type === 'BUY' ? 'ENTRY' : `${Number(event.pnlSol || 0) >= 0 ? '+' : '−'}${Math.abs(Number(event.pnlSol || 0)).toFixed(4)} SOL`,
  lines: [event.type === 'BUY' ? `BUY · entry MC ${usd(event.marketCapUsd)}` : `SELL · entry MC ${usd(event.entryMarketCapUsd)} · exit MC ${usd(event.marketCapUsd)}`, event.priceNative ? `Execution price ${tiny(Number(event.priceNative), 6)} SOL` : 'Execution price unavailable', `Receipt ${event.id?.slice(0, 10) || '—'}`],
  footer: 'FEELESS · trade receipt',
});

function PaperBadge() {
  return <span className="paper-badge"><i /> PAPER TRADING · NO REAL SOL</span>;
}

function AvatarPicker({ value, onChange }) {
  return <div className="paper-avatar-picker" role="group" aria-label="Choose a Cat avatar">{CAT_VARIATIONS.slice(0, 10).map((cat, index) => <button type="button" key={cat[0]} className={value === index ? 'selected' : ''} aria-label={`Choose ${cat[0]}`} onClick={() => onChange(index)}><CatAvatar cat={cat} /></button>)}</div>;
}

// 🐱 ONE set of cat fields (name · handle · coat · look · risk) for Create a Cat AND Launch a Cat (owner: "they must ask the same data");
// the name + look start from the cat you built in 🎨 Build a cat (lib/myCat)
export const catForm = (presetAvatar = 0, preset, mine = readMyCat()) => ({ name: mine?.name || '', handle: '', avatar: presetAvatar, brain: 'rules', strategy: 'trend', instructions: '', look: mine?.look || DEFAULT_LOOK, startingBalanceSol: '10', maxPositionSol: preset?.maxPositionSol || '0.5', dailyBuyLimitSol: '2', maxDailyLossSol: '0.5', thinkEvery: '15 min', bio: '', xHandle: '', allowlist: '', blocklist: '', walletMode: 'paper', coinPlan: 'later' });
export const catOk = f => f.name.trim().length >= 2 && /^[a-z0-9_-]{3,20}$/.test(f.handle);
export function CatFields({ form, update }) {
  return <>
        <div className="cct-form">
          <div className="cct-grid2">
            <label className="cct-field"><span>Name</span><input className="m-input" autoFocus required minLength="2" maxLength="24" value={form.name} onChange={event => update('name', event.target.value)} placeholder="e.g. Specter" data-testid="cat-name" /></label>
            <label className="cct-field"><span>Handle</span><div className="cct-at"><i>@</i><input className="m-input" required pattern="[a-zA-Z0-9_-]{3,20}" value={form.handle} onChange={event => update('handle', event.target.value.toLowerCase())} placeholder="specter" data-testid="cat-handle" /></div><small>3–20 · a–z 0–9 _ -</small></label>
          </div>
          <div className="cct-field"><span>Coat</span><AvatarPicker value={form.avatar} onChange={value => update('avatar', value)} /></div>
          <LookPicker look={form.look} onChange={value => update('look', value)} />
          <div className="cct-grid2 cct-risk">
            <label className="cct-field"><span>Starting paper balance</span><div className="cct-unit"><NumInput className="m-input" type="number" min="0.1" max="100" step="0.1" value={form.startingBalanceSol} onChange={event => update('startingBalanceSol', event.target.value)} /><i>SOL</i></div><small>Simulated capital only.</small></label>
            <label className="cct-field"><span>Daily buy limit</span><div className="cct-unit"><NumInput className="m-input" type="number" min="0.01" max="100" step="0.01" value={form.dailyBuyLimitSol} onChange={event => update('dailyBuyLimitSol', event.target.value)} /><i>SOL</i></div><small>New paper entries a day.</small></label>
            <label className="cct-field"><span>Max position</span><div className="cct-unit"><NumInput className="m-input" type="number" min="0.01" max="2" step="0.01" value={form.maxPositionSol} onChange={event => update('maxPositionSol', event.target.value)} /><i>SOL</i></div></label>
            <label className="cct-field"><span>Daily loss limit</span><div className="cct-unit"><NumInput className="m-input" type="number" min="0.01" max="5" step="0.01" value={form.maxDailyLossSol} onChange={event => update('maxDailyLossSol', event.target.value)} /><i>SOL</i></div></label>
          </div>
        </div>
  </>;
}

export function CatPreview({ form }) {
  return <>
          <span className="cct-stage"><LookAvatar cat={CAT_VARIATIONS[form.avatar] || CAT_VARIATIONS[0]} look={form.look} large /></span>
          <b className="cct-name">{form.name || 'Your Cat'}</b><small className="cct-handle">@{form.handle || 'handle'}</small>
          <div className="cct-meters">
            {[['Risk / trade', Number(form.maxPositionSol) / Math.max(0.1, Number(form.startingBalanceSol))], ['Daily loss cap', Number(form.maxDailyLossSol) / Math.max(0.1, Number(form.startingBalanceSol))], ['Daily buys', Number(form.dailyBuyLimitSol) / Math.max(0.1, Number(form.startingBalanceSol))]].map(([k, v]) =>
              <span key={k}><small>{k}</small><i><i style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, v || 0))})` }} /></i><b>{Math.round((v || 0) * 100)}%</b></span>)}
          </div>
          <small className="cct-note">of the starting balance · paper only, nothing is signed</small>

  </>;
}

function CreateCat({ onCreated, onCancel, preset, presetAvatar = 0 }) {
  const [step, setStep] = useState(2);
  const [form, setForm] = useState(() => catForm(presetAvatar, preset));
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const update = (key, value) => setForm(current => ({ ...current, [key]: value }));
  const selectedAvatar = CAT_VARIATIONS[form.avatar] || CAT_VARIATIONS[0];
  const submit = async event => {
    event.preventDefault(); setError(''); setSaving(true);
    try {
      const result = await api('/api/cats', { method: 'POST', body: JSON.stringify({ ...form, ownerId: ownerId(), avatar: selectedAvatar[0] }) });
      const started = await api(`/api/cats/${result.cat.id}/action`, { method: 'POST', body: JSON.stringify({ action: 'start' }) });
      onCreated(started.cat);
    } catch (requestError) { setError(requestError.message); } finally { setSaving(false); }
  };
  return <CreateCatWizard form={form} update={update} step={step} setStep={setStep} onCancel={onCancel} submit={submit} error={error} saving={saving} />;
}

function CreateCatWizard({ form, update, step, setStep, onCancel, submit, error, saving }) {
  return createPortal(<div className="paper-modal-backdrop"><section className="paper-create-card paper-wizard-card" role="dialog" aria-modal="true" aria-labelledby="create-cat-title">
    <div className="paper-wizard-visual"><div className="paper-wizard-cat-strip">{CAT_VARIATIONS.slice(1, 4).map(cat => <span key={cat[0]}><CatAvatar cat={cat} /></span>)}</div><button className="icon-btn" type="button" onClick={onCancel} aria-label="Close Create Cat"><X size={18} /></button></div>
    {step === 2 && <div className="paper-wizard-body cct-body">
      <div className="cct-head"><span className="eyebrow">STEP 1 OF 2 / IDENTITY + LOOK + RISK</span><h2 id="create-cat-title">Create a paper agent</h2>
        <p className="paper-helper">Your Cat runs the Leader's engine on live prices: −10% stop, +22% take-profit, trailing stop, 4h max hold, 1% fee a side. You pick the name, the look and the limits.</p></div>
      <div className="cct-split">
        <CatFields form={form} update={update} />
        <aside className="cct-preview m-live" data-testid="cat-preview"><CatPreview form={form} /></aside>
      </div>
      <div className="paper-wizard-bottom"><button className="btn-outline" type="button" onClick={onCancel}>Cancel</button><button className="btn-primary m-go" type="button" disabled={!catOk(form)} onClick={() => setStep(3)} data-testid="cat-continue">Continue <ChevronRight size={16} /></button></div></div>}
    {step === 3 && <form onSubmit={submit} className="paper-wizard-body"><button type="button" className="paper-wizard-back" onClick={() => setStep(2)}><ArrowLeft size={14} /> Back</button><span className="eyebrow">STEP 2 OF 2 / CONFIRM</span><div className="cct-confirm-head"><LookAvatar cat={CAT_VARIATIONS[form.avatar] || CAT_VARIATIONS[0]} look={form.look} /><h2>Start {form.name || 'your Cat'}</h2></div><div className="paper-confirm-list"><div><small>Starting paper balance</small><b>{form.startingBalanceSol} SOL</b></div><div><small>Max per position</small><b>{form.maxPositionSol} SOL</b></div><div><small>Daily loss limit</small><b>{form.maxDailyLossSol} SOL</b></div><div><small>Prices</small><b>Live DexScreener, SOL-native</b></div></div><p className="paper-wizard-disclosure"><AlertTriangle size={14} /> Paper mode: the money is simulated, the prices are real. Nothing is signed or broadcast.</p>{error && <div className="paper-form-error" role="alert"><AlertTriangle size={15} />{error}</div>}<div className="paper-create-actions"><button className="btn-outline" type="button" onClick={onCancel}>Cancel</button><button className="btn-primary" type="submit" disabled={saving}><Play size={15} />{saving ? 'Starting…' : 'Create & start trading'}</button></div></form>}
  </section></div>, document.body);
}

 function Leaderboard({ onOpen }) {
  const [view, setView] = useState('pnl');
  const [data, setData] = useState({ rows: [] });
  const [error, setError] = useState('');
  const load = useCallback(async () => { try { setData(await api(`/api/cats/leaderboard?view=${view}`)); setError(''); } catch (requestError) { setError(requestError.message); } }, [view]);
  useEffect(() => { load(); const interval = setInterval(load, 10000); return () => clearInterval(interval); }, [load]);
  return <section className="paper-panel paper-leaderboard"><div className="paper-panel-head"><div><span className="eyebrow"><Trophy size={13} /> GLOBAL CAT LEADERBOARD</span><h2>Real paper results only.</h2></div><Gauge size={18} /></div><div className="paper-leaderboard-tabs">{[['pnl', 'Realized P/L'], ['volume', 'Volume'], ['win_rate', 'Win rate']].map(([id, label]) => <button type="button" className={view === id ? 'active' : ''} onClick={() => setView(id)} key={id}>{label}</button>)}</div>{error && <p className="paper-muted">{error}</p>}{!data.rows?.length && !error && <div className="paper-empty"><Cat size={20} />Create a Cat to enter the paper leaderboard.</div>}<div className="paper-rank-list">{data.rows?.map((cat, index) => <button type="button" className={`paper-rank-row ${cat.isLeader ? 'is-leader' : ''}`} key={cat.id} onClick={async () => { try { const r = await api(`/api/cats/${cat.id}`); onOpen?.(r.cat); } catch {} }}><span className="paper-rank-number">{String(index + 1).padStart(2, '0')}</span><span className="paper-rank-avatar"><CatAvatar cat={CAT_VARIATIONS[index % CAT_VARIATIONS.length]} /></span><span className="paper-rank-name"><b>{cat.name}</b><small>{cat.isLeader ? 'THE LEADER · ' : ''}LVL {cat.level} · {cat.strategyLabel} · {cat.trades ?? 0} trades</small></span><strong className={view === 'win_rate' ? '' : cat.realizedPnlSol >= 0 ? 'positive' : 'negative'}>{view === 'pnl' ? money(cat.realizedPnlSol) : view === 'volume' ? `${cat.volumeSol.toFixed(4)} SOL` : `${cat.winRate ?? '—'}%`}</strong></button>)}</div><small className="paper-disclosure">Leaderboard uses server-recorded paper activity in this running environment. It is not on-chain performance.</small></section>;
}

function ActivityFeed({ catId }) {
  const [data, setData] = useState({ events: [] });
  const load = useCallback(async () => { try { setData(await api(`/api/cats/activity${catId ? `?catId=${encodeURIComponent(catId)}` : ''}`)); } catch {} }, [catId]);
  useEffect(() => { load(); const interval = setInterval(load, 7000); return () => clearInterval(interval); }, [load]);
  return <section className="paper-panel paper-activity"><div className="paper-panel-head"><div><span className="eyebrow"><Activity size={13} /> LIVE CAT ACTIVITY</span><h2>{catId ? 'This Cat’s audit trail.' : 'Watch the paper engine.'}</h2></div><span className="paper-live-dot"><i /> LIVE</span></div>{!data.events?.length && <div className="paper-empty"><Activity size={20} />No activity yet. Start a Cat to begin scanning.</div>}<div className="paper-event-list">{data.events?.map((event, k) => <article className={`paper-event event-${event.type.toLowerCase()}`} key={event.id} style={{ '--i': Math.min(k, 12) }}><span className="paper-event-icon">{event.type === 'BUY' ? '↗' : event.type === 'SELL' ? '↘' : event.type === 'STOPPED' ? '!' : '·'}</span><div><b>{event.catName} <small>{event.type}</small></b><p>{event.detail}</p><time>{time(event.ts)} · PAPER{event.decisionSource ? ` · ${event.decisionSource === 'selected_brain' ? `${event.brainLabel || 'Selected brain'} decision` : 'FEELESS rule engine · live prices'}` : ''}</time>{['BUY', 'SELL'].includes(event.type) && <small className="paper-event-mc">{event.type === 'BUY' ? `Entry MC: ${usd(event.marketCapUsd)}` : `Entry: ${usd(event.entryMarketCapUsd)} · Exit: ${usd(event.marketCapUsd)}`}</small>}</div>{event.pnlSol != null && <strong className={event.pnlSol >= 0 ? 'positive' : 'negative'}>{money(event.pnlSol)}</strong>}{['BUY', 'SELL'].includes(event.type) && <ShareGifButton className="btn-outline paper-event-share" label="🎞 Share" card={tradeCard(event)} />}</article>)}</div></section>;
}

// 🤖 one agent's desk = CatDesk.jsx (violet meta, 2026-10-23); this keeps its live read + the paper actions
function CatDetail({ cat: initialCat, onBack, onChanged }) {
  const [cat, setCat] = useState(initialCat);
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const brainChanged = useCallback(next => { setCat(next); onChanged?.(next); }, [onChanged]);
  useEffect(() => {
    const refresh = async () => { if (document.hidden) return; try { const result = await api(`/api/cats/${initialCat.id}`); if (result.cat) { setCat(result.cat); onChanged?.(result.cat); } } catch {} };
    const interval = setInterval(refresh, 8000);
    return () => clearInterval(interval);
  }, [initialCat.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (action, extra = {}) => { setError(''); setBusy(true); try { const result = await api(`/api/cats/${cat.id}/action`, { method: 'POST', body: JSON.stringify({ action, ...extra }) }); setCat(result.cat); onChanged?.(result.cat); } catch (requestError) { setError(requestError.message); } setBusy(false); };
  return <CatDesk cat={cat} busy={busy} error={error} onBack={onBack} onAct={act} Engine={<EngineLine />}
    Brains={cat.brainsCfg ? <BrainPanel cat={cat} api={api} onChanged={brainChanged} /> : null} Activity={<ActivityFeed catId={cat.id} />} />;
}

// 🤖 AGENTS (FeeCat redo, 2026-10-23): your trading cats — MY AGENTS · NEW AGENT · LIVE ACTIVITY · LEADERBOARD. Fee's own desk, brain and lore
// live in the FeeCat shell's other tabs (this page used to repeat them: a "Fee live" tab, the Leader panel, a "Build your cat" jump).
export default function FeeCatsPlatform() {
  const launchParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : new URLSearchParams();
  const mine = readMyCat(); const pa = Number(launchParams.get('avatar'));
  const presetAvatar = Number.isInteger(pa) && pa >= 0 && launchParams.get('avatar') !== null ? pa : (mine ? mine.coat : 0);
  const [view, setView] = useState(launchParams.get('create') === '1' ? 'create' : 'cats');
  const [cats, setCats] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState('');
  const loadCats = useCallback(async () => { try { const result = await api(`/api/cats?ownerId=${encodeURIComponent(ownerId())}`); setCats(result.cats || []); setError(''); } catch (requestError) { setError(requestError.message); } }, []);
  useEffect(() => { loadCats(); }, [loadCats]);
  const openCat = cat => { setSelected(cat); setView('cat'); };
  const created = cat => { setCats(current => [cat, ...current]); openCat(cat); };
  const live = cats.filter(c => !c.revoked);   // 🤖 agents that count toward the 2-agent limit
  const TABS = [['cats', <><Cat size={14} /> My agents <span>{live.length}/{AGENT_MAX}</span></>, 'Your trading cats with their live P&L'],
    ['new', <><Plus size={14} /> New agent</>, 'Pick a rule trader or an AI trader — up to 2 agents'],
    ['activity', <><Activity size={14} /> Live activity</>, 'Every cat\'s buys and sells as they happen'],
    ['leaderboard', <><Trophy size={14} /> Leaderboard</>, 'Every cat ranked by real paper results']];
  const on = k => (k === 'new' ? ['new', 'create', 'launch'].includes(view) : k === 'cats' ? ['cats', 'cat'].includes(view) : view === k);
  return <div className="fee-cats-platform fc-v2"><header className="paper-platform-head"><div><span className="eyebrow"><Cat size={14} /> AGENTS · CATS THAT TRADE FOR YOU</span><h1>Give your cat a <em>job.</em></h1><p>Paper agents on real, live Solana prices — your name, your look, your limits. No real SOL at risk.</p></div>
    <div className="paper-platform-actions"><PaperBadge /><span className="fc-slots" data-tip={`${live.length} of ${AGENT_MAX} agent slots used`} aria-label={`${live.length} of ${AGENT_MAX} agents`}>{Array.from({ length: AGENT_MAX }, (_, k) => <i key={k} className={k < live.length ? 'is-on' : ''} />)}</span></div></header>
    <nav className="paper-platform-tabs" aria-label="Agents">{TABS.map(([k, label, tip]) => <button key={k} type="button" className={on(k) ? 'active' : ''} onClick={() => { setSelected(null); setView(k); }} data-testid={`fc-tab-${k}`} data-tip={tip}>{label}</button>)}</nav>
    {error && <div className="paper-inline-message" role="alert"><AlertTriangle size={14} />{error}</div>}
    {view === 'new' && <AgentPicker count={live.length} onPick={k => setView(k)} />}
    {view === 'create' && <CreateCat onCreated={created} onCancel={() => setView('cats')} presetAvatar={presetAvatar} />}
    {view === 'cat' && selected && <CatDetail cat={selected} onBack={() => setView('cats')} onChanged={cat => { setSelected(cat); setCats(current => current.map(item => item.id === cat.id ? cat : item)); }} />}
    {view === 'activity' && <div className="paper-single-column"><ActivityFeed /></div>}
    {view === 'launch' && <LaunchCat api={api} ownerId={ownerId} onCreated={created} onCancel={() => setView('cats')} Fields={CatFields} newForm={catForm} formOk={catOk} avatarOf={i => (CAT_VARIATIONS[i] || CAT_VARIATIONS[0])[0]} Preview={CatPreview} />}
    {view === 'leaderboard' && <div className="paper-single-column"><Leaderboard onOpen={openCat} /></div>}
    {view === 'cats' && <section className="paper-my-cats">{!cats.length ? <><div className="paper-panel-head"><div><span className="eyebrow">YOUR AGENTS · 0/{AGENT_MAX}</span><h2>No cats on the job yet — pick a brain.</h2></div></div><AgentPicker count={0} onPick={k => setView(k)} /></>
      : <><div className="paper-panel-head"><div><span className="eyebrow">YOUR AGENTS · {live.length}/{AGENT_MAX}</span><h2>Tap a cat to see its desk</h2></div><button type="button" className="btn-outline" onClick={() => setView('new')} disabled={live.length >= AGENT_MAX}><Plus size={14} /> New agent</button></div>
        <div className="paper-my-cat-grid">{cats.map(cat => <button type="button" className="paper-my-cat-card" key={cat.id} onClick={() => openCat(cat)}><span className="paper-my-cat-art"><LookAvatar cat={catByName(cat.avatar)} look={cat.look} /></span><span><b>{cat.name}</b><small>{cat.status.toUpperCase()} · LVL {cat.level}</small></span><strong className={cat.realizedPnlSol >= 0 ? 'positive' : 'negative'}>{money(cat.realizedPnlSol)}</strong><ChevronRight size={15} /></button>)}</div></>}</section>}
  </div>;
}
