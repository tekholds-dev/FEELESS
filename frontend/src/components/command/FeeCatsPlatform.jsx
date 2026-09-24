import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, ArrowLeft, ArrowUpRight, Cat, Check, ChevronRight, CircleStop, Copy, Gauge, LockKeyhole, Play, Plus, RefreshCw, ShieldAlert, SlidersHorizontal, Sparkles, Trophy, Wallet, X } from 'lucide-react';
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

function CreateCat({ onCreated, onCancel }) {
  const [form, setForm] = useState({ name: '', avatar: 0, strategy: 'balanced', maxPositionSol: '0.25', maxDailyLossSol: '0.5', allowlist: '', blocklist: '' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const update = (key, value) => setForm(current => ({ ...current, [key]: value }));
  const submit = async event => {
    event.preventDefault(); setError(''); setSaving(true);
    try {
      const result = await api('/api/cats', { method: 'POST', body: JSON.stringify({ ...form, ownerId: ownerId(), avatar: CAT_VARIATIONS[form.avatar]?.[0] || 'Mint Mackerel' }) });
      onCreated(result.cat);
    } catch (requestError) { setError(requestError.message); } finally { setSaving(false); }
  };
  return <section className="paper-create-card">
    <div className="paper-create-head"><div><span className="eyebrow"><Sparkles size={13} /> CREATE A FEE CAT</span><h2>Ready in under a minute.</h2><p>Start with a paper wallet and a strategy you can inspect before real Solana execution is ever enabled.</p></div><button className="icon-btn" type="button" onClick={onCancel} aria-label="Close Create Cat"><X size={18} /></button></div>
    <form onSubmit={submit} className="paper-create-form">
      <label>Cat name<input autoFocus required minLength="2" maxLength="24" value={form.name} onChange={event => update('name', event.target.value)} placeholder="e.g. Mint Scout" /></label>
      <div><span className="paper-field-label">Choose a look</span><AvatarPicker value={form.avatar} onChange={value => update('avatar', value)} /></div>
      <label>Strategy<select value={form.strategy} onChange={event => update('strategy', event.target.value)}><option value="balanced">Balanced scout</option><option value="momentum">Momentum hunter</option><option value="conservative">Capital guard</option></select><small>Strategy rules use provider-observed snapshots. They do not guarantee a result.</small></label>
      <div className="paper-form-grid"><label>Max position · SOL<input type="number" min="0.01" max="2" step="0.01" value={form.maxPositionSol} onChange={event => update('maxPositionSol', event.target.value)} /></label><label>Max daily loss · SOL<input type="number" min="0.01" max="5" step="0.01" value={form.maxDailyLossSol} onChange={event => update('maxDailyLossSol', event.target.value)} /></label></div>
      <div className="paper-form-grid"><label>Allow only symbols / mints<input value={form.allowlist} onChange={event => update('allowlist', event.target.value)} placeholder="Optional: SOL, BONK" /><small>Comma separated. Empty means any eligible provider result.</small></label><label>Block symbols / mints<input value={form.blocklist} onChange={event => update('blocklist', event.target.value)} placeholder="Optional: SCAM" /></label></div>
      {error && <div className="paper-form-error" role="alert"><AlertTriangle size={15} />{error}</div>}
      <div className="paper-create-actions"><button className="btn-outline" type="button" onClick={onCancel}>Cancel</button><button className="btn-primary" type="submit" disabled={saving}><Plus size={15} />{saving ? 'Creating paper Cat…' : 'Create paper Cat'}</button></div>
    </form>
  </section>;
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