import React, { Suspense, lazy, useCallback, useEffect, useState } from 'react';
import NumInput from '../NumInput';
import { createPortal } from 'react-dom';
import { Activity, AlertTriangle, ArrowLeft, Cat, ChevronRight, Gauge, Play, Plus, Trophy, X } from 'lucide-react';
import { CAT_VARIATIONS, CatAvatar, catByName } from './catCoats';
import { ShareGifButton } from '../ShareGif';
import '../../styles/feecatPage.css';
import '../../styles/catForge.css';

import { tiny } from '../../lib/num';
import { FundReceipt } from './FundReceipt';
import { LaunchCat, BrainPanel } from './LaunchCat';
import { LookAvatar, LookPicker, DEFAULT_LOOK } from './CatLook';
import { readMyCat } from '../../lib/myCat';
import { EngineLine } from './CatBrainSwitch';
import { CatDesk } from './CatDesk';
import { CatReal } from './CatReal';
import { useAdmin } from '../../lib/adminCall';
const ProfileFeeCat = lazy(() => import('./ProfileFeeCat').then(m => ({ default: m.ProfileFeeCat })));
const FeeLiveTab = lazy(() => import('./FeeLiveTab').then(m => ({ default: m.FeeLiveTab })));
const ProfileFeeBanner = lazy(() => import('./ProfileFeeCat').then(m => ({ default: m.ProfileFeeBanner })));
import { AgentPicker, AGENT_MAX } from './AgentPicker';
import { useDeskSkin, DeskBackdrop, SkinPicker } from './CatCockpit';
import { useWallet } from '../../hooks/useWallet';
import { getChatSession } from '../../lib/chatSession';
import { useLeaderProfile } from '../../lib/feeLeader';
// 🪟 Fee's (NEXA) dash in My agents wears the same desk as every agent (owner 2026-10-30): her two live windows first, a calm backdrop + card colour
function NexaSkin({ children }) {
  const lead = useLeaderProfile(); const { wallet, signMessage } = useWallet() || {};
  const save = async sk => { const address = wallet?.address; if (!address) return;   // her desk look is saved on Fee — every visitor of her dash sees it
    try { await api('/api/cats/leader/action', { method: 'POST', body: JSON.stringify({ action: 'skin', look: { bg: sk.bg, acc: sk.acc }, address, session: await getChatSession(address, signMessage, { own: true }) }) }); } catch { /* declined */ } };
  const [skin, setSkin] = useDeskSkin(lead?.cat?.skin, save);
  return <div className={`kd has-skin ck-nexa${skin.bg !== 'night' ? ' is-glass' : ''}`} style={{ '--kd-acc': skin.acc }} data-testid="nexa-skin"><DeskBackdrop bg={skin.bg} /><span className="ck-nexa-bar"><SkinPicker skin={skin} set={setSkin} /></span>{children}</div>;
}
const OWNER_KEY = 'feeless-paper-owner';
const api = async (path, options = {}) => {
  // 🔒 every cat action carries this browser's owner id (the service refuses anyone else's cat)
  if (/\/action$/.test(path) && options.body) options = { ...options, body: JSON.stringify({ ...JSON.parse(options.body), ownerId: ownerId() }) };
  if (!options.method && /^\/api\/cats\/[\w-]+$/.test(path)) path = `${path}?ownerId=${encodeURIComponent(ownerId())}`;   // one cat → the server answers `mine` (never sends the owner id)
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

function PaperBadge() {   // 💵 the AI cats are real-first (its own wallet: you sign one funding; linked to yours: you sign each); paper is the test toggle
  return <span className="paper-badge" data-tip="Each agent gets its own wallet. You fund it once from yours; after that it trades from its own wallet inside the limits you set — nothing to sign per trade. FEELESS never sees your wallet's keys."><i /> ITS OWN WALLET · YOUR LIMITS</span>;
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

// 🪜 the drawn step rail (violet): every step a bar that fills as you reach it — "where am I in this" at a glance, no eyebrow line
export const STEPS = ['IDENTITY · LOOK · RISK', 'CONFIRM'];
export function StepRail({ at, steps = STEPS }) {
  return <div className="cf-steps" style={{ '--n': steps.length }} role="progressbar" aria-valuemin={1} aria-valuemax={steps.length} aria-valuenow={at} aria-label={`Step ${at} of ${steps.length}`} data-testid="cat-steps">
    {steps.map((w, i) => <span key={w} className={`cf-step ${i + 1 === at ? 'is-on' : i + 1 < at ? 'is-done' : ''}`}><u><s /></u><em>{i + 1 < at ? '✓' : i + 1} · {w}</em></span>)}</div>;
}

function CreateCatWizard({ form, update, step, setStep, onCancel, submit, error, saving }) {
  return createPortal(<div className="paper-modal-backdrop cfv"><section className="paper-create-card paper-wizard-card" role="dialog" aria-modal="true" aria-labelledby="create-cat-title">
    <div className="paper-wizard-visual"><div className="paper-wizard-cat-strip">{CAT_VARIATIONS.slice(1, 4).map(cat => <span key={cat[0]}><CatAvatar cat={cat} /></span>)}</div><button className="icon-btn" type="button" onClick={onCancel} aria-label="Close Create Cat"><X size={18} /></button></div>
    {step === 2 && <div className="paper-wizard-body cct-body">
      <div className="cct-head"><StepRail at={1} /><h2 id="create-cat-title">Create a paper agent</h2>
        <p className="paper-helper">Your Cat runs the Leader's engine on live prices: −10% stop, +22% take-profit, trailing stop, 4h max hold, 1% fee a side. You pick the name, the look and the limits.</p></div>
      <div className="cct-split">
        <CatFields form={form} update={update} />
        <aside className="cct-preview m-live" data-testid="cat-preview"><CatPreview form={form} /></aside>
      </div>
      <div className="paper-wizard-bottom"><button className="btn-outline" type="button" onClick={onCancel}>Cancel</button><button className="btn-primary m-go" type="button" disabled={!catOk(form)} onClick={() => setStep(3)} data-testid="cat-continue">Continue <ChevronRight size={16} /></button></div></div>}
    {step === 3 && <form onSubmit={submit} className="paper-wizard-body"><button type="button" className="paper-wizard-back" onClick={() => setStep(2)}><ArrowLeft size={14} /> Back</button><StepRail at={2} /><div className="cct-confirm-head"><LookAvatar cat={CAT_VARIATIONS[form.avatar] || CAT_VARIATIONS[0]} look={form.look} /><h2>Start {form.name || 'your Cat'}</h2></div><div className="paper-confirm-list"><div><small>Starting paper balance</small><b>{form.startingBalanceSol} SOL</b></div><div><small>Max per position</small><b>{form.maxPositionSol} SOL</b></div><div><small>Daily loss limit</small><b>{form.maxDailyLossSol} SOL</b></div><div><small>Prices</small><b>Live DexScreener, SOL-native</b></div></div><p className="paper-wizard-disclosure"><AlertTriangle size={14} /> Paper mode: the money is simulated, the prices are real. Nothing is signed or broadcast.</p><FundReceipt />{error && <div className="paper-form-error" role="alert"><AlertTriangle size={15} />{error}</div>}<div className="paper-create-actions"><button className="btn-outline" type="button" onClick={onCancel}>Cancel</button><button className="btn-primary" type="submit" disabled={saving}><Play size={15} />{saving ? 'Starting…' : 'Create & start trading'}</button></div></form>}
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
function CatDetail({ cat: initialCat, onBack, onChanged, onDeleted }) {
  const [cat, setCat] = useState(initialCat);
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const brainChanged = useCallback(next => { setCat(next); onChanged?.(next); }, [onChanged]);
  const { isAdmin } = useAdmin();   // 💵 Fee's real switch shows to the owner only (the server re-checks the signed owner wallet)
  useEffect(() => {
    const refresh = async () => { if (document.hidden) return; try { const result = await api(`/api/cats/${initialCat.id}`); if (result.cat) { setCat(result.cat); onChanged?.(result.cat); } } catch {} };
    refresh(); const interval = setInterval(refresh, 8000);   // at once: opened from the leaderboard, the row has no `mine` yet
    return () => clearInterval(interval);
  }, [initialCat.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (action, extra = {}) => { setError(''); setBusy(true); try { const result = await api(`/api/cats/${cat.id}/action`, { method: 'POST', body: JSON.stringify({ action, ...extra }) }); if (result.deleted) { onDeleted?.(result.deleted); return; } setCat(result.cat); onChanged?.(result.cat); } catch (requestError) { setError(requestError.message); } setBusy(false); };
  const mine = cat.isLeader ? isAdmin : !!cat.mine;   // 👀 opened from the leaderboard: the owner gets the controls, everyone else the view (the server answers `mine`; the owner id never leaves it)
  return <CatDesk canEdit={mine} cat={cat} busy={busy} error={error} onBack={onBack} onAct={act} Engine={<EngineLine />} Real={!mine ? null : <CatReal cat={cat} busy={busy} onAct={act} />}
    Brains={cat.brainsCfg && mine ? <BrainPanel noTalk cat={cat} api={api} onChanged={brainChanged} /> : null} Activity={null} />;
}

// 🤖 AGENTS (FeeCat redo, 2026-10-23): your trading cats — MY AGENTS · NEW AGENT · LIVE ACTIVITY · LEADERBOARD. Fee's own desk, brain and lore
// live in the FeeCat shell's other tabs (this page used to repeat them: a "Fee live" tab, the Leader panel, a "Build your cat" jump).
export default function FeeCatsPlatform() {
  const launchParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : new URLSearchParams();
  const mine = readMyCat(); const pa = Number(launchParams.get('avatar'));
  const presetAvatar = Number.isInteger(pa) && pa >= 0 && launchParams.get('avatar') !== null ? pa : (mine ? mine.coat : 0);
  const [view, setView] = useState(launchParams.get('create') === '1' ? 'new' : 'cats');   // 🎨 Build a cat › "Give it a job" lands on the brain pick (it used to skip to the paper wizard)
  const [kind, setKind] = useState('trading');
  const pickKind = k => { if (k === 'trading' || k === 'general') { setKind(k); setView('launch'); } else setView(k); };   // 📈 / 🧭 → models → your wallet → REAL
  const [cats, setCats] = useState([]);
  const { isAdmin } = useAdmin();   // 🪟 N14/N16: the creator's own Fee (NEXA) sits first in My agents — not one of the 2 agent slots
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState('');
  const loadCats = useCallback(async () => { try { const result = await api(`/api/cats?ownerId=${encodeURIComponent(ownerId())}`); setCats(result.cats || []); setError(''); } catch (requestError) { setError(requestError.message); } }, []);
  useEffect(() => { loadCats(); }, [loadCats]);
  const openCat = cat => { setSelected(cat); setView('cat'); };
  const openReal = cat => { openCat(cat); setTimeout(() => document.querySelector('[data-testid="cat-real"]')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 250); };   // 💵 straight to its wallet switch
  // 🗑 delete from the list (owner 2026-10-30: "I can't delete the test cat"): its name typed → retire (if still live) → delete; the server refuses while its wallet holds money
  const removeCat = async cat => {
    const t = typeof window !== 'undefined' ? window.prompt(`Delete ${cat.name} for good? Type its name to confirm:`) : null;
    if (!t || t.trim().toLowerCase() !== String(cat.name).toLowerCase()) return;
    setError('');
    try {
      if (!cat.revoked) await api(`/api/cats/${cat.id}/action`, { method: 'POST', body: JSON.stringify({ action: 'revoke' }) });
      await api(`/api/cats/${cat.id}/action`, { method: 'POST', body: JSON.stringify({ action: 'delete', text: t.trim() }) });
      setCats(c => c.filter(x => x.id !== cat.id));
    } catch (e) { setError(e.message); loadCats(); }
  };
  const created = cat => { setCats(current => [cat, ...current]); openReal(cat); };   // 💵 a new cat lands on its wallet switch (link → budget → REAL)
  const live = cats.filter(c => !c.revoked);   // 🤖 agents that count toward the 2-agent limit
  const TABS = [['cats', <><Cat size={14} /> My agents <span>{live.length}/{AGENT_MAX}</span></>, 'Your trading cats with their live P&L'],
    ['new', <><Plus size={14} /> New agent</>, 'A Trading AI cat or a General AI cat — models → your wallet → REAL · up to 2 agents'],
    ['activity', <><Activity size={14} /> Live activity</>, 'Every cat\'s buys and sells as they happen'],
    ['leaderboard', <><Trophy size={14} /> Leaderboard</>, 'Every cat ranked by real paper results']];
  const on = k => (k === 'new' ? ['new', 'create', 'launch'].includes(view) : k === 'cats' ? ['cats', 'cat', 'nexa'].includes(view) : view === k);
  return <div className="fee-cats-platform fc-v2"><header className="paper-platform-head"><div><span className="eyebrow"><Cat size={14} /> AGENTS · CATS THAT TRADE FOR YOU</span><h1>Give your cat a <em>job.</em></h1><p>Your own AI agents — pick 1–2 models, a name, a look and limits. Each gets its own wallet: fund it once, and it works from there. A trader trades on FEELESS inside your limits; a general agent researches, builds and acts for you, and checks with you before spending until you switch it to auto.</p></div>
    <div className="paper-platform-actions"><PaperBadge /><span className="fc-slots" data-tip={`${live.length} of ${AGENT_MAX} agent slots used`} aria-label={`${live.length} of ${AGENT_MAX} agents`}>{Array.from({ length: AGENT_MAX }, (_, k) => <i key={k} className={k < live.length ? 'is-on' : ''} />)}</span></div></header>
    <nav className="paper-platform-tabs" aria-label="Agents">{TABS.map(([k, label, tip]) => <button key={k} type="button" className={on(k) ? 'active' : ''} onClick={() => { setSelected(null); setView(k); }} data-testid={`fc-tab-${k}`} data-tip={tip}>{label}</button>)}</nav>
    {error && <div className="paper-inline-message" role="alert"><AlertTriangle size={14} />{error}</div>}
    {view === 'new' && <AgentPicker count={live.length} onPick={pickKind} />}
    {view === 'create' && <CreateCat onCreated={created} onCancel={() => setView('cats')} presetAvatar={presetAvatar} />}
    {view === 'cat' && selected && <CatDetail onDeleted={id => { setCats(c => c.filter(x => x.id !== id)); setSelected(null); setView('cats'); }} cat={selected} onBack={() => setView('cats')} onChanged={cat => { setSelected(cat); setCats(current => current.map(item => item.id === cat.id ? cat : item)); }} />}
    {view === 'activity' && <div className="paper-single-column"><ActivityFeed /></div>}
    {view === 'launch' && <LaunchCat key={kind} kind={kind} api={api} ownerId={ownerId} onCreated={created} onCancel={() => setView('cats')} Fields={CatFields} newForm={() => catForm(presetAvatar)} formOk={catOk} avatarOf={i => (CAT_VARIATIONS[i] || CAT_VARIATIONS[0])[0]} Preview={CatPreview} />}
    {view === 'leaderboard' && <div className="paper-single-column"><Leaderboard onOpen={openCat} /></div>}
    {view === 'cats' && isAdmin ? <Suspense fallback={null}><ProfileFeeBanner mine onOpen={() => { setSelected(null); setView('nexa'); }} /></Suspense> : null}
    {view === 'nexa' && isAdmin ? <Suspense fallback={<p className="paper-muted">🪟 opening NEXA…</p>}><button type="button" className="btn-outline" onClick={() => setView('cats')} data-testid="nexa-back">← My agents</button><NexaSkin><FeeLiveTab /><ProfileFeeCat mine /></NexaSkin></Suspense> : null}
    {view === 'cats' && <section className="paper-my-cats">{!cats.length ? <><div className="paper-panel-head"><div><span className="eyebrow">YOUR AGENTS · 0/{AGENT_MAX}</span><h2>No cats on the job yet — pick a brain.</h2></div></div><AgentPicker count={0} onPick={pickKind} /></>
      : <><div className="paper-panel-head"><div><span className="eyebrow">YOUR AGENTS · {live.length}/{AGENT_MAX}</span><h2>Tap a cat to see its desk</h2></div><button type="button" className="btn-outline" onClick={() => setView('new')} disabled={live.length >= AGENT_MAX}><Plus size={14} /> New agent</button></div>
        <div className="paper-my-cat-grid">{cats.map(cat => { const real = cat.mode === 'real' && !!cat.realWallet; const pend = (cat.proposals || []).filter(p => p.status === 'pending').length;
          return <div key={cat.id} className={`cw-card ${real ? 'is-real' : ''}`} data-testid={`cw-${cat.id}`}><button type="button" className="paper-my-cat-card" onClick={() => openCat(cat)}><span className="paper-my-cat-art"><LookAvatar cat={catByName(cat.avatar)} look={cat.look} /></span><span><b>{cat.name}</b><small>{cat.status.toUpperCase()} · LVL {cat.level}</small></span><strong className={cat.realizedPnlSol >= 0 ? 'positive' : 'negative'}>{money(cat.realizedPnlSol)}</strong><ChevronRight size={15} /></button>
            <button type="button" className={`cw-go ${real ? 'is-real' : ''}`} onClick={() => openReal(cat)} data-testid={`cw-go-${cat.id}`}
              data-tip={real ? `REAL on ${cat.realWallet.slice(0, 4)}…${cat.realWallet.slice(-4)} — open its live proposals` : 'Switch this cat to REAL: pick a per-buy budget, it proposes, your wallet signs every trade'}>
              <i aria-hidden="true" />{real ? `💵 REAL · ${pend ? `${pend} to sign` : 'live'}` : '🧪 PAPER · GO REAL'}</button>
            <button type="button" className="cw-del" onClick={() => removeCat(cat)} data-testid={`cw-del-${cat.id}`} data-tip="Delete it for good — type its name to confirm (never while its own wallet still holds money)" aria-label={`Delete ${cat.name}`}>🗑</button></div>; })}</div></>}</section>}
  </div>;
}
