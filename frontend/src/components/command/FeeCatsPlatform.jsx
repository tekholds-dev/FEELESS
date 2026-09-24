import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, ArrowLeft, ArrowUpRight, Cat, Check, ChevronRight, CircleStop, Copy, Gauge, KeyRound, LockKeyhole, Play, Plus, RefreshCw, ShieldAlert, SlidersHorizontal, Sparkles, Trophy, Wallet, X } from 'lucide-react';
import { CAT_VARIATIONS, CatAvatar } from './FeeBack';

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
const short = value => value ? `${value.slice(0, 6)}…${value.slice(-5)}` : '—';
const time = value => value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';

function PaperBadge() {
  return <span className="paper-badge"><i /> PAPER TRADING · NO REAL SOL</span>;
}

function Sparkline({ points = [] }) {
  const values = points.length ? points.map(point => Number(point.value || 0)) : [0];
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const range = max - min || 1;
  const polyline = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${94 - ((value - min) / range) * 78}`).join(' ');
  return <svg className="paper-pnl-chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Paper realized and unrealized P/L history"><line x1="0" x2="100" y1={94 - ((0 - min) / range) * 78} y2={94 - ((0 - min) / range) * 78} className="chart-zero" /><polyline points={polyline} /></svg>;
}

function AvatarPicker({ value, onChange }) {
  return <div className="paper-avatar-picker" role="group" aria-label="Choose a Cat avatar">{CAT_VARIATIONS.slice(0, 10).map((cat, index) => <button type="button" key={cat[0]} className={value === index ? 'selected' : ''} aria-label={`Choose ${cat[0]}`} onClick={() => onChange(index)}><CatAvatar cat={cat} /></button>)}</div>;
}

const BRAIN_OPTIONS = [
  ['claude-opus', 'Anthropic', 'Claude Opus 5.5'],
  ['claude-fable', 'Anthropic', 'Claude Fable 5.1'],
  ['gpt-astra', 'OpenAI', 'GPT-6 Astra'],
  ['gpt-sol', 'OpenAI', 'GPT-6 Sol'],
  ['muse', 'Meta', 'Muse Spark 1.3'],
  ['grok', 'xAI', 'Grok 4.7'],
  ['gemini', 'Google', 'Gemini 3.8 Flash'],
  ['qwen', 'Alibaba', 'Qwen 3.8 Max'],
  ['kimi', 'Moonshot', 'Kimi K3'],
  ['deepseek', 'DeepSeek', 'DeepSeek V4 Pro'],
];

const STRATEGIES = [['balanced', 'Momentum'], ['momentum', 'Breakouts'], ['conservative', 'Scalping'], ['signals', 'On-chain signals'], ['trend', 'Trend following'], ['conviction', 'Conviction']];

function CreateCat({ onCreated, onCancel }) {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({ name: '', handle: '', avatar: 0, brain: 'gpt-astra', strategy: 'momentum', instructions: '', startingBalanceSol: '10', maxPositionSol: '0.25', dailyBuyLimitSol: '2', maxDailyLossSol: '0.5', thinkEvery: '15 min', bio: '', xHandle: '', allowlist: '', blocklist: '', walletMode: 'paper', coinPlan: 'later' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [created, setCreated] = useState(null);
  const [recoverySaved, setRecoverySaved] = useState(false);
  const update = (key, value) => setForm(current => ({ ...current, [key]: value }));
  const brain = BRAIN_OPTIONS.find(item => item[0] === form.brain) || BRAIN_OPTIONS[2];
  const selectedAvatar = CAT_VARIATIONS[form.avatar] || CAT_VARIATIONS[0];
  const submit = async event => {
    event.preventDefault(); setError(''); setSaving(true);
    try {
      const result = await api('/api/cats', { method: 'POST', body: JSON.stringify({ ...form, ownerId: ownerId(), avatar: selectedAvatar[0] }) });
      setCreated(result);
    } catch (requestError) { setError(requestError.message); } finally { setSaving(false); }
  };
  const confirmRecovery = async () => {
    if (!created?.recoveryKey || !recoverySaved) return;
    setSaving(true); setError('');
    try {
      const result = await api(`/api/cats/${created.cat.id}/action`, { method: 'POST', body: JSON.stringify({ action: 'confirm_recovery', recoveryKey: created.recoveryKey }) });
      onCreated(result.cat);
    } catch (requestError) { setError(requestError.message); } finally { setSaving(false); }
  };
  const copyRecovery = async () => {
    try { await navigator.clipboard.writeText(created.recoveryKey); setError('Recovery key copied. Check the saved box when it is stored safely.'); } catch { setError('Copy was blocked. Select and save the recovery key manually.'); }
  };
  const downloadRecovery = () => {
    const blob = new Blob([`FEE CAT RECOVERY KEY\n\nCat: ${created.cat.name}\nKey: ${created.recoveryKey}\n\nKeep this offline. Anyone with this key may recover the Cat.`], { type: 'text/plain' });
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `${created.cat.name.replace(/\s+/g, '-').toLowerCase()}-recovery.txt`; link.click(); URL.revokeObjectURL(link.href);
  };
  if (created) return <div className="paper-modal-backdrop"><section className="paper-create-card paper-recovery-card" role="dialog" aria-modal="true" aria-labelledby="recovery-title"><div className="paper-create-head"><div><span className="eyebrow"><LockKeyhole size={13} /> SAVE THIS ONCE</span><h2 id="recovery-title">Your Cat has a recovery key.</h2><p>Save it offline before continuing. If the key is not saved and the Cat is never funded, it expires after 14 days.</p></div><button className="icon-btn" type="button" onClick={onCancel} aria-label="Close recovery key"><X size={18} /></button></div><div className="paper-recovery-key"><code>{created.recoveryKey}</code><div><button type="button" className="btn-outline" onClick={copyRecovery}><Copy size={14} /> Copy key</button><button type="button" className="btn-outline" onClick={downloadRecovery}><ArrowUpRight size={14} /> Save file</button></div></div><label className="paper-recovery-check"><input type="checkbox" checked={recoverySaved} onChange={event => setRecoverySaved(event.target.checked)} /><span><b>I saved the recovery key somewhere safe.</b><small>This is a required owner confirmation. It is never shown again by the API.</small></span></label>{error && <div className="paper-form-error" role="alert"><AlertTriangle size={15} />{error}</div>}<div className="paper-create-actions"><button className="btn-outline" type="button" onClick={onCancel}>I’ll do this later</button><button className="btn-primary" type="button" disabled={!recoverySaved || saving} onClick={confirmRecovery}><Check size={15} />{saving ? 'Confirming…' : 'Save and open Cat'}</button></div></section></div>;
  return <CreateCatWizard form={form} update={update} brain={brain} step={step} setStep={setStep} onCancel={onCancel} submit={submit} error={error} saving={saving} />;
}

function CreateCatWizard({ form, update, brain, step, setStep, onCancel, submit, error, saving }) {
  return <div className="paper-modal-backdrop"><section className="paper-create-card paper-wizard-card" role="dialog" aria-modal="true" aria-labelledby="create-cat-title">
    <div className="paper-wizard-visual"><div className="paper-wizard-cat-strip">{CAT_VARIATIONS.slice(1, 4).map(cat => <span key={cat[0]}><CatAvatar cat={cat} /></span>)}</div><button className="icon-btn" type="button" onClick={onCancel} aria-label="Close Create Cat"><X size={18} /></button></div>
    <div className="paper-create-tabs" role="tablist" aria-label="Agent creation mode"><button type="button" role="tab" aria-selected="true" className="active" onClick={() => setStep(0)}><Sparkles size={14} /> Create one</button><button type="button" role="tab" aria-selected="false" disabled title="Connect flow is available after the first paper MVP"><Wallet size={14} /> Connect yours</button></div>
    {step === 0 && <div className="paper-wizard-body"><span className="eyebrow">NO AGENT YET</span><h2 id="create-cat-title">Create an agent</h2><p>Pick a brain, give it a name and rules, then choose whether it starts as paper or gets a clean wallet assigned to it.</p><div className="paper-step-list">{[['01', 'Pick a brain', 'Choose the reasoning profile for this Cat.'], ['02', 'Name it and set the rules', 'Strategy, instructions, position and daily limits.'], ['03', 'Choose its wallet + coin plan', 'Paper mode is safe; a clean assigned wallet is ready for a later funding flow.'], ['04', 'Save the recovery key', 'Without a saved key or first deposit, an unfunded Cat expires after 14 days.']].map(([number, title, copy]) => <div key={number}><b>{number}</b><span><strong>{title}</strong><small>{copy}</small></span></div>)}</div><button className="btn-primary paper-wizard-next" type="button" onClick={() => setStep(1)}>Create agent <ChevronRight size={16} /></button><small className="paper-wizard-footnote">Anyone can create one. No connected wallet is required to start in paper mode.</small></div>}
    {step === 1 && <div className="paper-wizard-body"><button type="button" className="paper-wizard-back" onClick={() => setStep(0)}><ArrowLeft size={14} /> Back</button><span className="eyebrow">STEP 01 / BRAIN</span><h2>Pick a brain</h2><p>This selection is stored with the Cat. The paper MVP still executes the transparent rule engine; no AI provider call is implied.</p><div className="paper-brain-grid">{BRAIN_OPTIONS.map(option => <button type="button" className={form.brain === option[0] ? 'selected' : ''} key={option[0]} onClick={() => update('brain', option[0])}><small>{option[1]}</small><b>{option[2]}</b></button>)}</div><div className="paper-wizard-bottom"><small><KeyRound size={13} /> Have an existing Cat with its own wallet? Connect flow is planned.</small><button className="btn-primary" type="button" onClick={() => setStep(2)}>Continue <ChevronRight size={16} /></button></div></div>}
    {step === 2 && <div className="paper-wizard-body"><button type="button" className="paper-wizard-back" onClick={() => setStep(1)}><ArrowLeft size={14} /> Back</button><span className="eyebrow">STEP 02 / IDENTITY + RULES</span><h2>Name your agent</h2><div className="paper-selected-brain"><b>Brain: {brain[2]}</b><span>{brain[1]}</span><button type="button" onClick={() => setStep(1)}>Change</button></div><div className="paper-form-grid"><label>Name<input autoFocus required minLength="2" maxLength="24" value={form.name} onChange={event => update('name', event.target.value)} placeholder="e.g. Specter" /></label><label>Handle<input required pattern="[a-zA-Z0-9_-]{3,20}" value={form.handle} onChange={event => update('handle', event.target.value.toLowerCase())} placeholder="specter" /><small>3–20 characters: a–z, 0–9, _, -</small></label></div><div><span className="paper-field-label">Look</span><AvatarPicker value={form.avatar} onChange={value => update('avatar', value)} /><small className="paper-helper">Pick a Feeless Cat color. Every base color now has a Spots variant.</small></div><div><span className="paper-field-label">Strategy</span><div className="paper-choice-row">{STRATEGIES.map(([id, label]) => <button type="button" className={form.strategy === id ? 'selected' : ''} key={id} onClick={() => update('strategy', id)}>{label}</button>)}</div></div><label>Instructions <small>optional</small><textarea value={form.instructions} onChange={event => update('instructions', event.target.value)} placeholder="e.g. Only trade tokens with $1M+ market cap. Cut losers at −20%." /></label><div className="paper-form-grid"><label>Starting paper balance (SOL)<input type="number" min="0.1" max="100" step="0.1" value={form.startingBalanceSol} onChange={event => update('startingBalanceSol', event.target.value)} /><small>Simulated capital only.</small></label><label>Daily paper buy limit (SOL)<input type="number" min="0.01" max="100" step="0.01" value={form.dailyBuyLimitSol} onChange={event => update('dailyBuyLimitSol', event.target.value)} /><small>Caps new paper entries each day.</small></label><label>Max position (SOL)<input type="number" min="0.01" max="2" step="0.01" value={form.maxPositionSol} onChange={event => update('maxPositionSol', event.target.value)} /></label><label>Daily loss limit (SOL)<input type="number" min="0.01" max="5" step="0.01" value={form.maxDailyLossSol} onChange={event => update('maxDailyLossSol', event.target.value)} /></label></div><div className="paper-wizard-bottom"><button className="btn-primary" type="button" onClick={() => setStep(3)}>Continue <ChevronRight size={16} /></button></div></div>}
    {step === 3 && <form onSubmit={submit} className="paper-wizard-body"><button type="button" className="paper-wizard-back" onClick={() => setStep(2)}><ArrowLeft size={14} /> Back</button><span className="eyebrow">STEP 03 / WALLET + COIN</span><h2>Choose how it starts</h2><div className="paper-option-grid"><button type="button" className={form.walletMode === 'paper' ? 'selected' : ''} onClick={() => update('walletMode', 'paper')}><Gauge size={18} /><b>Paper mode</b><small>Starts with a simulated balance and never broadcasts a transaction.</small></button><button type="button" className={form.walletMode === 'assigned' ? 'selected' : ''} onClick={() => update('walletMode', 'assigned')}><Wallet size={18} /><b>Clean assigned wallet</b><small>Creates a fresh Solana address for this Cat. Funding and signing remain disabled in this preview.</small></button></div><span className="paper-field-label">Coin plan</span><div className="paper-choice-row"><button type="button" className={form.coinPlan === 'later' ? 'selected' : ''} onClick={() => update('coinPlan', 'later')}>Choose later</button><button type="button" className={form.coinPlan === 'create' ? 'selected' : ''} onClick={() => update('coinPlan', 'create')}>Plan a coin on creation</button></div><p className="paper-wizard-disclosure"><AlertTriangle size={14} /> Planning a coin records your choice only. No token is created until a supported launch adapter is enabled.</p>{error && <div className="paper-form-error" role="alert"><AlertTriangle size={15} />{error}</div>}<div className="paper-create-actions"><button className="btn-outline" type="button" onClick={() => setStep(2)}>Back</button><button className="btn-primary" type="submit" disabled={saving}><Plus size={15} />{saving ? 'Creating…' : 'Create agent'}</button></div></form>}
  </section></div>;
}

 function Leaderboard() {
  const [view, setView] = useState('pnl');
  const [data, setData] = useState({ rows: [] });
  const [error, setError] = useState('');
  const load = useCallback(async () => { try { setData(await api(`/api/cats/leaderboard?view=${view}`)); setError(''); } catch (requestError) { setError(requestError.message); } }, [view]);
  useEffect(() => { load(); const interval = setInterval(load, 10000); return () => clearInterval(interval); }, [load]);
  return <section className="paper-panel paper-leaderboard"><div className="paper-panel-head"><div><span className="eyebrow"><Trophy size={13} /> GLOBAL CAT LEADERBOARD</span><h2>Real paper results only.</h2></div><Gauge size={18} /></div><div className="paper-leaderboard-tabs">{[['pnl', 'Realized P/L'], ['volume', 'Volume'], ['win_rate', 'Win rate']].map(([id, label]) => <button type="button" className={view === id ? 'active' : ''} onClick={() => setView(id)} key={id}>{label}</button>)}</div>{error && <p className="paper-muted">{error}</p>}{!data.rows?.length && !error && <div className="paper-empty"><Cat size={20} />Create a Cat to enter the paper leaderboard.</div>}<div className="paper-rank-list">{data.rows?.map((cat, index) => <button type="button" className="paper-rank-row" key={cat.id}><span className="paper-rank-number">{String(index + 1).padStart(2, '0')}</span><span className="paper-rank-avatar"><CatAvatar cat={CAT_VARIATIONS[index % CAT_VARIATIONS.length]} /></span><span className="paper-rank-name"><b>{cat.name}</b><small>LVL {cat.level} · {cat.strategyLabel}</small></span><strong className={view === 'win_rate' ? '' : cat.realizedPnlSol >= 0 ? 'positive' : 'negative'}>{view === 'pnl' ? money(cat.realizedPnlSol) : view === 'volume' ? `${cat.volumeSol.toFixed(4)} SOL` : `${cat.winRate ?? '—'}%`}</strong></button>)}</div><small className="paper-disclosure">Leaderboard uses server-recorded paper activity in this running environment. It is not on-chain performance.</small></section>;
}

function ActivityFeed({ catId }) {
  const [data, setData] = useState({ events: [] });
  const load = useCallback(async () => { try { setData(await api(`/api/cats/activity${catId ? `?catId=${encodeURIComponent(catId)}` : ''}`)); } catch {} }, [catId]);
  useEffect(() => { load(); const interval = setInterval(load, 7000); return () => clearInterval(interval); }, [load]);
  return <section className="paper-panel paper-activity"><div className="paper-panel-head"><div><span className="eyebrow"><Activity size={13} /> LIVE CAT ACTIVITY</span><h2>{catId ? 'This Cat’s audit trail.' : 'Watch the paper engine.'}</h2></div><span className="paper-live-dot"><i /> LIVE</span></div>{!data.events?.length && <div className="paper-empty"><Activity size={20} />No activity yet. Start a Cat to begin scanning.</div>}<div className="paper-event-list">{data.events?.map(event => <article className={`paper-event event-${event.type.toLowerCase()}`} key={event.id}><span className="paper-event-icon">{event.type === 'BUY' ? '↗' : event.type === 'SELL' ? '↘' : event.type === 'STOPPED' ? '!' : '·'}</span><div><b>{event.catName} <small>{event.type}</small></b><p>{event.detail}</p><time>{time(event.ts)} · PAPER</time></div>{event.pnlSol != null && <strong className={event.pnlSol >= 0 ? 'positive' : 'negative'}>{money(event.pnlSol)}</strong>}</article>)}</div></section>;
}

function CatDetail({ cat: initialCat, onBack, onChanged }) {
  const [cat, setCat] = useState(initialCat);
  const [error, setError] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [controls, setControls] = useState({ maxPositionSol: initialCat.risk.maxPositionSol, maxDailyLossSol: initialCat.risk.maxDailyLossSol, allowlist: initialCat.risk.allowlist.join(', '), blocklist: initialCat.risk.blocklist.join(', ') });
  useEffect(() => {
    const refresh = async () => {
      try {
        const result = await api(`/api/cats/${initialCat.id}`);
        if (result.cat) { setCat(result.cat); onChanged?.(result.cat); }
      } catch {}
    };
    const interval = setInterval(refresh, 8000);
    return () => clearInterval(interval);
  }, [initialCat.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (action, extra = {}) => { setError(''); try { const result = await api(`/api/cats/${cat.id}/action`, { method: 'POST', body: JSON.stringify({ action, ...extra }) }); setCat(result.cat); onChanged?.(result.cat); } catch (requestError) { setError(requestError.message); } };
  const copyWallet = async () => { try { await navigator.clipboard.writeText(cat.wallet); setError('Paper wallet address copied.'); } catch { setError('Paper wallet: ' + cat.wallet); } };
  const updateControls = event => { event.preventDefault(); act('controls', controls); };
  return <div className="paper-cat-detail"><button className="paper-back-link" type="button" onClick={onBack}><ArrowLeft size={14} /> All Cats</button><div className="paper-cat-hero"><div className="paper-cat-identity"><span className="paper-detail-avatar"><CatAvatar cat={CAT_VARIATIONS.find(item => item[0] === cat.avatar) || CAT_VARIATIONS[0]} large /></span><div><PaperBadge /><h1>{cat.name}</h1><p>Level {cat.level} · {cat.xp} XP · {cat.strategyLabel}</p><button type="button" className="paper-wallet-address" onClick={copyWallet}><Wallet size={13} />{short(cat.wallet)}<Copy size={12} /></button></div></div><div className="paper-cat-actions">{cat.status === 'running' ? <button type="button" className="btn-outline stop-action" onClick={() => act('stop')}><CircleStop size={15} /> Emergency stop</button> : <button type="button" className="btn-primary" disabled={cat.revoked} onClick={() => act('start')}><Play size={15} /> Start paper agent</button>}<button type="button" className="btn-outline" onClick={() => act('run')}><RefreshCw size={14} /> Run cycle</button></div></div>{error && <div className="paper-inline-message"><AlertTriangle size={14} />{error}</div>}<div className="paper-stat-grid"><div><small>BALANCE</small><strong>{cat.balanceSol.toFixed(4)} SOL</strong><span>paper wallet</span></div><div><small>REALIZED P/L</small><strong className={cat.realizedPnlSol >= 0 ? 'positive' : 'negative'}>{money(cat.realizedPnlSol)}</strong><span>closed paper trades</span></div><div><small>POSITIONS</small><strong>{cat.positions.length}</strong><span>open paper positions</span></div><div><small>WIN RATE</small><strong>{cat.winRate == null ? '—' : `${cat.winRate}%`}</strong><span>{cat.wins + cat.losses} closed trades</span></div></div><div className="paper-detail-grid"><div className="paper-detail-main"><section className="paper-panel paper-chart-panel"><div className="paper-panel-head"><div><span className="eyebrow">P/L TRACE</span><h2>Performance over paper cycles</h2></div><span className="paper-muted">SOL · {cat.pnlHistory?.length || 1} points</span></div><Sparkline points={cat.pnlHistory} /><div className="paper-chart-labels"><span>START</span><strong className={cat.totalPnlSol >= 0 ? 'positive' : 'negative'}>{money(cat.totalPnlSol)}</strong><span>NOW</span></div></section><section className="paper-panel"><div className="paper-panel-head"><div><span className="eyebrow">OPEN POSITIONS</span><h2>What this Cat holds</h2></div><span className="paper-muted">Provider marked</span></div>{!cat.positions.length ? <div className="paper-empty">No open paper positions.</div> : <div className="paper-positions">{cat.positions.map(position => <div className="paper-position" key={position.mint}><div><b>{position.symbol}</b><small>{short(position.mint)} · {position.provider}</small></div><strong>{position.notionalSol.toFixed(4)} SOL</strong><span className={position.currentChange >= position.entryChange ? 'positive' : 'negative'}>{position.currentChange >= 0 ? '+' : ''}{position.currentChange.toFixed(2)}%</span></div>)}</div>}</section><ActivityFeed catId={cat.id} /></div><aside className="paper-detail-side"><section className="paper-panel paper-controls"><div className="paper-panel-head"><div><span className="eyebrow"><SlidersHorizontal size={13} /> STRATEGY + LIMITS</span><h2>Owner controls</h2></div></div><form onSubmit={updateControls}><label>Strategy<select value={cat.strategy} disabled><option>{cat.strategyLabel}</option></select></label><label>Max position · SOL<input type="number" min="0.01" max="2" step="0.01" value={controls.maxPositionSol} onChange={event => setControls({ ...controls, maxPositionSol: event.target.value })} /></label><label>Max daily loss · SOL<input type="number" min="0.01" max="5" step="0.01" value={controls.maxDailyLossSol} onChange={event => setControls({ ...controls, maxDailyLossSol: event.target.value })} /></label><label>Allowlist<input value={controls.allowlist} onChange={event => setControls({ ...controls, allowlist: event.target.value })} placeholder="Any token if empty" /></label><label>Blocklist<input value={controls.blocklist} onChange={event => setControls({ ...controls, blocklist: event.target.value })} placeholder="No blocked tokens" /></label><button className="btn-outline" type="submit">Save controls</button></form><div className="paper-safety-row"><ShieldAlert size={15} /><span>Agent signing is disabled in paper MVP.<small>No real SOL can be spent.</small></span></div></section><section className="paper-panel paper-withdraw"><span className="eyebrow"><Wallet size={13} /> WITHDRAW</span><h2>Keep control of the balance.</h2><p>Paper withdrawals update the ledger only. No blockchain transfer is claimed.</p><div><input type="number" min="0.0001" step="0.0001" value={withdrawAmount} onChange={event => setWithdrawAmount(event.target.value)} placeholder={cat.balanceSol.toFixed(4)} /><button type="button" className="btn-primary" onClick={() => act('withdraw', { amount: withdrawAmount || cat.balanceSol })}>Withdraw</button></div></section><section className="paper-panel paper-danger"><span className="eyebrow"><LockKeyhole size={13} /> ACCESS</span><h2>Revoke this agent</h2><p>Stops future cycles permanently for this Cat.</p><button type="button" className="btn-outline" onClick={() => act('revoke')} disabled={cat.revoked}>Revoke agent</button></section></aside></div><p className="paper-disclosure"><AlertTriangle size={13} /> PAPER MODE: all balances, P/L, positions, XP and trades on this page are non-broadcast simulations based on public provider snapshots. No private key or signing capability is exposed to the browser.</p></div>;
}

export default function FeeCatsPlatform() {
  const [view, setView] = useState('home');
  const [cats, setCats] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState('');
  const loadCats = useCallback(async () => { try { const result = await api(`/api/cats?ownerId=${encodeURIComponent(ownerId())}`); setCats(result.cats || []); setError(''); } catch (requestError) { setError(requestError.message); } }, []);
  useEffect(() => { loadCats(); }, [loadCats]);
  const openCat = cat => { setSelected(cat); setView('cat'); };
  const created = cat => { setCats(current => [cat, ...current]); openCat(cat); };
  return <div className="fee-cats-platform"><header className="paper-platform-head"><div><span className="eyebrow"><Cat size={14} /> FEE CATS / AUTONOMOUS AGENT LAB</span><h1>Let your Cat work the <em>signal.</em></h1><p>Build a strategy, set hard limits, and observe the full paper-trading loop before any real Solana execution exists.</p></div><div className="paper-platform-actions"><PaperBadge /><button type="button" className="btn-primary" onClick={() => { setSelected(null); setView('create'); }}><Plus size={15} /> Create Cat</button></div></header><nav className="paper-platform-tabs" aria-label="Fee Cats sections"><button type="button" className={view === 'home' ? 'active' : ''} onClick={() => setView('home')}><Activity size={14} /> Activity</button><button type="button" className={view === 'cats' ? 'active' : ''} onClick={() => setView('cats')}><Cat size={14} /> My Cats <span>{cats.length}</span></button><button type="button" className={view === 'leaderboard' ? 'active' : ''} onClick={() => setView('leaderboard')}><Trophy size={14} /> Leaderboard</button></nav>{error && <div className="paper-inline-message" role="alert"><AlertTriangle size={14} />{error}</div>}{view === 'create' && <CreateCat onCreated={created} onCancel={() => setView('home')} />}{view === 'cat' && selected && <CatDetail cat={selected} onBack={() => setView('cats')} onChanged={cat => { setSelected(cat); setCats(current => current.map(item => item.id === cat.id ? cat : item)); }} />}{view === 'home' && <div className="paper-dashboard-grid"><ActivityFeed /><Leaderboard /></div>}{view === 'leaderboard' && <div className="paper-single-column"><Leaderboard /></div>}{view === 'cats' && <section className="paper-my-cats"><div className="paper-panel-head"><div><span className="eyebrow">YOUR PAPER AGENTS</span><h2>Choose a Cat to inspect</h2></div><button type="button" className="btn-outline" onClick={() => setView('create')}><Plus size={14} /> New Cat</button></div>{!cats.length ? <div className="paper-empty large-empty"><Cat size={28} />No Cats yet. Create the first one in under a minute.<button type="button" className="btn-primary" onClick={() => setView('create')}>Create a paper Cat</button></div> : <div className="paper-my-cat-grid">{cats.map(cat => <button type="button" className="paper-my-cat-card" key={cat.id} onClick={() => openCat(cat)}><span className="paper-my-cat-art"><CatAvatar cat={CAT_VARIATIONS.find(item => item[0] === cat.avatar) || CAT_VARIATIONS[0]} /></span><span><b>{cat.name}</b><small>{cat.status.toUpperCase()} · LVL {cat.level}</small></span><strong className={cat.realizedPnlSol >= 0 ? 'positive' : 'negative'}>{money(cat.realizedPnlSol)}</strong><ChevronRight size={15} /></button>)}</div>}</section>}</div>;
}