import React, { useCallback, useEffect, useState } from 'react';
import { Activity, AlertTriangle, ArrowLeft, ArrowUpRight, Cat, Check, ChevronRight, CircleStop, Copy, Gauge, KeyRound, LockKeyhole, Play, Plus, RefreshCw, ShieldAlert, SlidersHorizontal, Sparkles, Trophy, Wallet, X } from 'lucide-react';
import { CAT_VARIATIONS, CatAvatar } from './FeeBack';
import '../../styles/brain-adapters.css';

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

function CreateCat({ onCreated, onCancel, preset, presetAvatar = 0 }) {
  const [step, setStep] = useState(2);
  const [form, setForm] = useState({ name: '', handle: '', avatar: presetAvatar, brain: 'rules', strategy: 'trend', instructions: '', startingBalanceSol: '10', maxPositionSol: preset?.maxPositionSol || '0.5', dailyBuyLimitSol: '2', maxDailyLossSol: '0.5', thinkEvery: '15 min', bio: '', xHandle: '', allowlist: '', blocklist: '', walletMode: 'paper', coinPlan: 'later' });
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
  return <div className="paper-modal-backdrop"><section className="paper-create-card paper-wizard-card" role="dialog" aria-modal="true" aria-labelledby="create-cat-title">
    <div className="paper-wizard-visual"><div className="paper-wizard-cat-strip">{CAT_VARIATIONS.slice(1, 4).map(cat => <span key={cat[0]}><CatAvatar cat={cat} /></span>)}</div><button className="icon-btn" type="button" onClick={onCancel} aria-label="Close Create Cat"><X size={18} /></button></div>
    {step === 2 && <div className="paper-wizard-body"><span className="eyebrow">STEP 1 OF 2 / IDENTITY + RISK</span><h2 id="create-cat-title">Create a paper agent</h2><p className="paper-helper">Your Cat runs the same disciplined engine as the Leader: live DexScreener prices, liquidity/volume/momentum filters, −10% stop, +22% take-profit, trailing stop, 4h max hold, 1% fee per side. You set the name and risk limits.</p><div className="paper-form-grid"><label>Name<input autoFocus required minLength="2" maxLength="24" value={form.name} onChange={event => update('name', event.target.value)} placeholder="e.g. Specter" /></label><label>Handle<input required pattern="[a-zA-Z0-9_-]{3,20}" value={form.handle} onChange={event => update('handle', event.target.value.toLowerCase())} placeholder="specter" /><small>3–20 characters: a–z, 0–9, _, -</small></label></div><div><span className="paper-field-label">Look</span><AvatarPicker value={form.avatar} onChange={value => update('avatar', value)} /><small className="paper-helper">Pick a Feeless Cat color. Every base color now has a Spots variant.</small></div><div className="paper-form-grid"><label>Starting paper balance (SOL)<input type="number" min="0.1" max="100" step="0.1" value={form.startingBalanceSol} onChange={event => update('startingBalanceSol', event.target.value)} /><small>Simulated capital only.</small></label><label>Daily paper buy limit (SOL)<input type="number" min="0.01" max="100" step="0.01" value={form.dailyBuyLimitSol} onChange={event => update('dailyBuyLimitSol', event.target.value)} /><small>Caps new paper entries each day.</small></label><label>Max position (SOL)<input type="number" min="0.01" max="2" step="0.01" value={form.maxPositionSol} onChange={event => update('maxPositionSol', event.target.value)} /></label><label>Daily loss limit (SOL)<input type="number" min="0.01" max="5" step="0.01" value={form.maxDailyLossSol} onChange={event => update('maxDailyLossSol', event.target.value)} /></label></div><div className="paper-wizard-bottom"><button className="btn-outline" type="button" onClick={onCancel}>Cancel</button><button className="btn-primary" type="button" disabled={form.name.trim().length < 2 || !/^[a-z0-9_-]{3,20}$/.test(form.handle)} onClick={() => setStep(3)}>Continue <ChevronRight size={16} /></button></div></div>}
    {step === 3 && <form onSubmit={submit} className="paper-wizard-body"><button type="button" className="paper-wizard-back" onClick={() => setStep(2)}><ArrowLeft size={14} /> Back</button><span className="eyebrow">STEP 2 OF 2 / CONFIRM</span><h2>Start {form.name || 'your Cat'}</h2><div className="paper-confirm-list"><div><small>Starting paper balance</small><b>{form.startingBalanceSol} SOL</b></div><div><small>Max per position</small><b>{form.maxPositionSol} SOL</b></div><div><small>Daily loss limit</small><b>{form.maxDailyLossSol} SOL</b></div><div><small>Prices</small><b>Live DexScreener, SOL-native</b></div></div><p className="paper-wizard-disclosure"><AlertTriangle size={14} /> Paper mode: the money is simulated, the prices are real. Nothing is signed or broadcast.</p>{error && <div className="paper-form-error" role="alert"><AlertTriangle size={15} />{error}</div>}<div className="paper-create-actions"><button className="btn-outline" type="button" onClick={onCancel}>Cancel</button><button className="btn-primary" type="submit" disabled={saving}><Play size={15} />{saving ? 'Starting…' : 'Create & start trading'}</button></div></form>}
  </section></div>;
}

 function Leaderboard({ onOpen }) {
  const [view, setView] = useState('pnl');
  const [data, setData] = useState({ rows: [] });
  const [error, setError] = useState('');
  const load = useCallback(async () => { try { setData(await api(`/api/cats/leaderboard?view=${view}`)); setError(''); } catch (requestError) { setError(requestError.message); } }, [view]);
  useEffect(() => { load(); const interval = setInterval(load, 10000); return () => clearInterval(interval); }, [load]);
  return <section className="paper-panel paper-leaderboard"><div className="paper-panel-head"><div><span className="eyebrow"><Trophy size={13} /> GLOBAL CAT LEADERBOARD</span><h2>Real paper results only.</h2></div><Gauge size={18} /></div><div className="paper-leaderboard-tabs">{[['pnl', 'Realized P/L'], ['volume', 'Volume'], ['win_rate', 'Win rate']].map(([id, label]) => <button type="button" className={view === id ? 'active' : ''} onClick={() => setView(id)} key={id}>{label}</button>)}</div>{error && <p className="paper-muted">{error}</p>}{!data.rows?.length && !error && <div className="paper-empty"><Cat size={20} />Create a Cat to enter the paper leaderboard.</div>}<div className="paper-rank-list">{data.rows?.map((cat, index) => <button type="button" className={`paper-rank-row ${cat.isLeader ? 'is-leader' : ''}`} key={cat.id} onClick={async () => { try { const r = await api(`/api/cats/${cat.id}`); onOpen?.(r.cat); } catch {} }}><span className="paper-rank-number">{String(index + 1).padStart(2, '0')}</span><span className="paper-rank-avatar"><CatAvatar cat={CAT_VARIATIONS[index % CAT_VARIATIONS.length]} /></span><span className="paper-rank-name"><b>{cat.name}</b><small>{cat.isLeader ? 'THE LEADER · ' : ''}LVL {cat.level} · {cat.strategyLabel} · {cat.trades ?? 0} trades</small></span><strong className={view === 'win_rate' ? '' : cat.realizedPnlSol >= 0 ? 'positive' : 'negative'}>{view === 'pnl' ? money(cat.realizedPnlSol) : view === 'volume' ? `${cat.volumeSol.toFixed(4)} SOL` : `${cat.winRate ?? '—'}%`}</strong></button>)}</div><small className="paper-disclosure">Leaderboard uses server-recorded paper activity in this running environment. It is not on-chain performance.</small></section>;
}

const REJECT_LABEL = { liquidity: 'thin liquidity', volume: 'low volume', 'market cap band': 'outside MC band', 'too new': 'too new (<3h)', '5m momentum': 'no 5m momentum', '1h move': '1h move out of range', '6h trend': '6h weak or overextended', overextended: 'overextended', 'buy pressure': 'sellers in control', 'not SOL-quoted': 'not a SOL pair' };

function PositionRow({ position }) {
  const change = Number(position.currentChange || 0);
  const held = position.openedAt ? Math.max(1, Math.round((Date.now() / 1000 - position.openedAt) / 60)) : null;
  return <a className="paper-position" href={position.pairAddress ? `/terminal/trade?chain=solana&pair=${position.pairAddress}` : undefined} title={position.reason || ''}>
    <div><b>{position.symbol}</b><small>{held ? `${held}m held · ` : ''}{position.reason || position.provider}</small></div>
    <strong>{Number(position.costSol || position.notionalSol).toFixed(3)} SOL</strong>
    <span className={change >= 0 ? 'positive' : 'negative'}>{change >= 0 ? '+' : ''}{change.toFixed(2)}%</span>
  </a>;
}

function LeaderPanel({ onCopy, onOpen }) {
  const [data, setData] = useState(null);
  const load = useCallback(async () => { try { setData(await api('/api/cats/leader')); } catch {} }, []);
  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t); }, [load]);
  const cat = data?.cat; const scan = data?.scan; const rules = data?.rules;
  if (!cat) return <section className="paper-panel leader-panel"><div className="paper-empty"><Cat size={20} />Leader is waking up…</div></section>;
  const trades = (cat.wins || 0) + (cat.losses || 0);
  const rejections = Object.entries(scan?.rejections || {}).sort((a, b) => b[1] - a[1]).slice(0, 5);
  return <section className="paper-panel leader-panel" data-testid="leader-panel">
    <div className="leader-head">
      <span className="leader-avatar"><CatAvatar cat={CAT_VARIATIONS[0]} large /></span>
      <div><span className="eyebrow"><Trophy size={13} /> THE LEADER · ALWAYS ON</span><h2>Fee</h2><p>Leader of the FEELESS Cats. She hunts disciplined momentum on live Solana pairs and only pounces when every filter passes — sitting out is a position.</p></div>
      <div className="leader-actions"><button type="button" className="btn-primary" onClick={onCopy}><Copy size={14} />Copy Fee's rules</button><button type="button" className="btn-outline" onClick={() => onOpen(cat)}>Full audit trail<ChevronRight size={14} /></button></div>
    </div>
    <div className="paper-stat-grid">
      <div><small>PAPER BALANCE</small><strong>{Number(cat.balanceSol).toFixed(3)} SOL</strong><span>started {cat.startingBalanceSol || 25} SOL</span></div>
      <div><small>REALIZED P/L</small><strong className={cat.realizedPnlSol >= 0 ? 'positive' : 'negative'}>{money(cat.realizedPnlSol)}</strong><span>after 1% fee per side</span></div>
      <div><small>WIN RATE</small><strong>{cat.winRate == null ? '—' : `${cat.winRate}%`}</strong><span>{trades} closed trades</span></div>
      <div><small>OPEN</small><strong>{cat.positions.length}/{rules?.maxPositions ?? 4}</strong><span>positions</span></div>
    </div>
    <div className="leader-grid">
      <div><span className="paper-field-label">Open positions · live marked</span>{cat.positions.length ? <div className="paper-positions">{cat.positions.map(p => <PositionRow key={p.pairAddress || p.mint} position={p} />)}</div> : <div className="paper-empty">No position right now — nothing passed every filter.</div>}</div>
      <div><span className="paper-field-label">Last scan{scan?.at ? ` · ${time(scan.at * 1000)}` : ''}</span>
        {scan ? <div className="leader-scan"><p><b>{scan.scanned}</b> live pairs checked · <b className={scan.passed ? 'positive' : ''}>{scan.passed}</b> passed</p>
          {scan.top?.length > 0 && <ul className="leader-top">{scan.top.map(t => <li key={t.symbol}><b>{t.symbol}</b><small>{t.reason}</small></li>)}</ul>}
          <div className="leader-rejects">{rejections.map(([why, n]) => <span key={why}>{REJECT_LABEL[why] || why} <b>{n}</b></span>)}</div></div> : <div className="paper-empty">First scan in progress…</div>}
      </div>
    </div>
    <details className="leader-lore"><summary>Who is Fee?</summary><div>
      <p><b>Fee was the first Cat.</b> She grew up in the trenches watching traders bleed out a percent here, a percent there — platform fees, hidden spreads, priority tips nobody explained. She decided every one of those crumbs should find its way home.</p>
      <p><b>How she trades.</b> Fee is patient. She reads every live pair, ignores anything thin, brand-new, or already vertical, and waits for real buy pressure with a healthy trend behind it. When she's in, she protects herself first: a hard stop, a profit target, and a trailing guard once a trade runs. She never averages down and never chases a coin she just left.</p>
      <p><b>Catching fees back.</b> That's her whole purpose. FEELESS's Fee-Back design routes the fees your trades generate back to you as FEECAT. Fee is the proof-of-discipline for that promise: every trade she makes pays the full 1% cost on each side, out in the open, so you can see exactly what fees cost — and what getting them back would mean.</p>
      <p className="paper-muted">Fee trades on paper against real live prices. Fee-Back itself is planned and not yet activated.</p>
    </div></details>
    {rules && <details className="leader-rules"><summary>The rules (identical for every Cat)</summary><div>
      <span>6h move ≤ +{rules.h6Max}%</span><span>Liquidity ≥ ${(rules.minLiquidity / 1000).toFixed(0)}K</span><span>24h volume ≥ ${(rules.minVolume24h / 1000).toFixed(0)}K</span><span>MC ${(rules.minMarketCap / 1000).toFixed(0)}K–${(rules.maxMarketCap / 1e6).toFixed(0)}M</span><span>Age ≥ {rules.minAgeHours}h</span><span>1h move +{rules.h1Min}% to +{rules.h1Max}%</span><span>5m and 6h positive</span><span>Buys ≥ {rules.minBuySellRatio}× sells</span><span>Stop {rules.stopLoss}%</span><span>Take profit +{rules.takeProfit}%</span><span>Trailing: arm +{rules.trailArm}%, give {rules.trailGive}%</span><span>Max hold {rules.maxHoldHours}h</span><span>Re-entry cooldown {rules.cooldownHours}h</span>
    </div></details>}
  </section>;
}

function ActivityFeed({ catId }) {
  const [data, setData] = useState({ events: [] });
  const load = useCallback(async () => { try { setData(await api(`/api/cats/activity${catId ? `?catId=${encodeURIComponent(catId)}` : ''}`)); } catch {} }, [catId]);
  useEffect(() => { load(); const interval = setInterval(load, 7000); return () => clearInterval(interval); }, [load]);
  return <section className="paper-panel paper-activity"><div className="paper-panel-head"><div><span className="eyebrow"><Activity size={13} /> LIVE CAT ACTIVITY</span><h2>{catId ? 'This Cat’s audit trail.' : 'Watch the paper engine.'}</h2></div><span className="paper-live-dot"><i /> LIVE</span></div>{!data.events?.length && <div className="paper-empty"><Activity size={20} />No activity yet. Start a Cat to begin scanning.</div>}<div className="paper-event-list">{data.events?.map(event => <article className={`paper-event event-${event.type.toLowerCase()}`} key={event.id}><span className="paper-event-icon">{event.type === 'BUY' ? '↗' : event.type === 'SELL' ? '↘' : event.type === 'STOPPED' ? '!' : '·'}</span><div><b>{event.catName} <small>{event.type}</small></b><p>{event.detail}</p><time>{time(event.ts)} · PAPER{event.decisionSource ? ` · ${event.decisionSource === 'selected_brain' ? `${event.brainLabel || 'Selected brain'} decision` : 'FEELESS rule engine · live prices'}` : ''}</time></div>{event.pnlSol != null && <strong className={event.pnlSol >= 0 ? 'positive' : 'negative'}>{money(event.pnlSol)}</strong>}</article>)}</div></section>;
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
  return <div className="paper-cat-detail"><button className="paper-back-link" type="button" onClick={onBack}><ArrowLeft size={14} /> All Cats</button><div className="paper-cat-hero"><div className="paper-cat-identity"><span className="paper-detail-avatar"><CatAvatar cat={CAT_VARIATIONS.find(item => item[0] === cat.avatar) || CAT_VARIATIONS[0]} large /></span><div><PaperBadge /><h1>{cat.name}</h1><p>Level {cat.level} · {cat.xp} XP · {cat.strategyLabel}</p><button type="button" className="paper-wallet-address" onClick={copyWallet}><Wallet size={13} />{short(cat.wallet)}<Copy size={12} /></button></div></div><div className="paper-cat-actions">{cat.status === 'running' ? <button type="button" className="btn-outline stop-action" onClick={() => act('stop')}><CircleStop size={15} /> Emergency stop</button> : <button type="button" className="btn-primary" disabled={cat.revoked} onClick={() => act('start')}><Play size={15} /> Start paper agent</button>}<button type="button" className="btn-outline" onClick={() => act('run')}><RefreshCw size={14} /> Run cycle</button></div></div>{error && <div className="paper-inline-message"><AlertTriangle size={14} />{error}</div>}<div className="paper-stat-grid"><div><small>BALANCE</small><strong>{cat.balanceSol.toFixed(4)} SOL</strong><span>paper wallet</span></div><div><small>REALIZED P/L</small><strong className={cat.realizedPnlSol >= 0 ? 'positive' : 'negative'}>{money(cat.realizedPnlSol)}</strong><span>closed paper trades</span></div><div><small>POSITIONS</small><strong>{cat.positions.length}</strong><span>open paper positions</span></div><div><small>WIN RATE</small><strong>{cat.winRate == null ? '—' : `${cat.winRate}%`}</strong><span>{cat.wins + cat.losses} closed trades</span></div></div><div className="paper-detail-grid"><div className="paper-detail-main"><section className="paper-panel paper-chart-panel"><div className="paper-panel-head"><div><span className="eyebrow">P/L TRACE</span><h2>Performance over paper cycles</h2></div><span className="paper-muted">SOL · {cat.pnlHistory?.length || 1} points</span></div><Sparkline points={cat.pnlHistory} /><div className="paper-chart-labels"><span>START</span><strong className={cat.totalPnlSol >= 0 ? 'positive' : 'negative'}>{money(cat.totalPnlSol)}</strong><span>NOW</span></div></section><section className="paper-panel"><div className="paper-panel-head"><div><span className="eyebrow">OPEN POSITIONS</span><h2>What this Cat holds</h2></div><span className="paper-muted">Provider marked</span></div>{!cat.positions.length ? <div className="paper-empty">No open paper positions.</div> : <div className="paper-positions">{cat.positions.map(position => <PositionRow key={position.pairAddress || position.mint} position={position} />)}</div>}</section><ActivityFeed catId={cat.id} /></div><aside className="paper-detail-side"><section className="paper-panel paper-controls"><div className="paper-panel-head"><div><span className="eyebrow"><SlidersHorizontal size={13} /> STRATEGY + LIMITS</span><h2>Owner controls</h2></div></div><div className="paper-brain-summary"><span className="eyebrow">DECISION ENGINE</span><b>FEELESS rule engine</b><small>Live DexScreener prices · transparent entry/exit rules</small></div><form onSubmit={updateControls}><label>Strategy<select value={cat.strategy} disabled><option>{cat.strategyLabel}</option></select></label><label>Max position · SOL<input type="number" min="0.01" max="2" step="0.01" value={controls.maxPositionSol} onChange={event => setControls({ ...controls, maxPositionSol: event.target.value })} /></label><label>Max daily loss · SOL<input type="number" min="0.01" max="5" step="0.01" value={controls.maxDailyLossSol} onChange={event => setControls({ ...controls, maxDailyLossSol: event.target.value })} /></label><label>Allowlist<input value={controls.allowlist} onChange={event => setControls({ ...controls, allowlist: event.target.value })} placeholder="Any token if empty" /></label><label>Blocklist<input value={controls.blocklist} onChange={event => setControls({ ...controls, blocklist: event.target.value })} placeholder="No blocked tokens" /></label><button className="btn-outline" type="submit">Save controls</button></form><div className="paper-safety-row"><ShieldAlert size={15} /><span>Agent signing is disabled in paper MVP.<small>No real SOL can be spent.</small></span></div></section><section className="paper-panel paper-withdraw"><span className="eyebrow"><Wallet size={13} /> WITHDRAW</span><h2>Keep control of the balance.</h2><p>Paper withdrawals update the ledger only. No blockchain transfer is claimed.</p><div><input type="number" min="0.0001" step="0.0001" value={withdrawAmount} onChange={event => setWithdrawAmount(event.target.value)} placeholder={cat.balanceSol.toFixed(4)} /><button type="button" className="btn-primary" onClick={() => act('withdraw', { amount: withdrawAmount || cat.balanceSol })}>Withdraw</button></div></section><section className="paper-panel paper-danger"><span className="eyebrow"><LockKeyhole size={13} /> ACCESS</span><h2>Revoke this agent</h2><p>Stops future cycles permanently for this Cat.</p><button type="button" className="btn-outline" onClick={() => act('revoke')} disabled={cat.revoked}>Revoke agent</button></section></aside></div><p className="paper-disclosure"><AlertTriangle size={13} /> PAPER MODE: balances are simulated; every entry and exit price is the real live DexScreener SOL price at that moment, with a 1% fee per side. No private key or signing capability is exposed to the browser.</p></div>;
}

export default function FeeCatsPlatform() {
  const launchParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : new URLSearchParams();
  const presetAvatar = Number(launchParams.get('avatar'));
  const [view, setView] = useState(launchParams.get('create') === '1' ? 'create' : 'home');
  const [cats, setCats] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState('');
  const loadCats = useCallback(async () => { try { const result = await api(`/api/cats?ownerId=${encodeURIComponent(ownerId())}`); setCats(result.cats || []); setError(''); } catch (requestError) { setError(requestError.message); } }, []);
  useEffect(() => { loadCats(); }, [loadCats]);
  const openCat = cat => { setSelected(cat); setView('cat'); };
  const created = cat => { setCats(current => [cat, ...current]); openCat(cat); };
  return <div className="fee-cats-platform"><header className="paper-platform-head"><div><span className="eyebrow"><Cat size={14} /> FEE CATS / AUTONOMOUS AGENT LAB</span><h1>Let your Cat work the <em>signal.</em></h1><p>Paper agents that trade real, live Solana prices. Watch Fee, the Leader, copy her rules, set your own limits — no real SOL at risk.</p></div><div className="paper-platform-actions"><PaperBadge /><button type="button" className="btn-primary" onClick={() => { setSelected(null); setView('create'); }}><Plus size={15} /> Create Cat</button></div></header><nav className="paper-platform-tabs" aria-label="Fee Cats sections"><button type="button" className={view === 'home' ? 'active' : ''} onClick={() => setView('home')}><Activity size={14} /> Activity</button><button type="button" className={view === 'cats' ? 'active' : ''} onClick={() => setView('cats')}><Cat size={14} /> My Cats <span>{cats.length}</span></button><button type="button" className={view === 'leaderboard' ? 'active' : ''} onClick={() => setView('leaderboard')}><Trophy size={14} /> Leaderboard</button></nav>{error && <div className="paper-inline-message" role="alert"><AlertTriangle size={14} />{error}</div>}{view === 'create' && <CreateCat onCreated={created} onCancel={() => setView('home')} presetAvatar={Number.isInteger(presetAvatar) && presetAvatar >= 0 ? presetAvatar : 0} />}{view === 'cat' && selected && <CatDetail cat={selected} onBack={() => setView('cats')} onChanged={cat => { setSelected(cat); setCats(current => current.map(item => item.id === cat.id ? cat : item)); }} />}{view === 'home' && <><LeaderPanel onCopy={() => { setSelected(null); setView('create'); }} onOpen={openCat} /><div className="paper-dashboard-grid"><ActivityFeed /><Leaderboard onOpen={openCat} /></div></>}{view === 'leaderboard' && <div className="paper-single-column"><Leaderboard onOpen={openCat} /></div>}{view === 'cats' && <section className="paper-my-cats"><div className="paper-panel-head"><div><span className="eyebrow">YOUR PAPER AGENTS</span><h2>Choose a Cat to inspect</h2></div><button type="button" className="btn-outline" onClick={() => setView('create')}><Plus size={14} /> New Cat</button></div>{!cats.length ? <div className="paper-empty large-empty"><Cat size={28} />No Cats yet. Create the first one in under a minute.<button type="button" className="btn-primary" onClick={() => setView('create')}>Create a paper Cat</button></div> : <div className="paper-my-cat-grid">{cats.map(cat => <button type="button" className="paper-my-cat-card" key={cat.id} onClick={() => openCat(cat)}><span className="paper-my-cat-art"><CatAvatar cat={CAT_VARIATIONS.find(item => item[0] === cat.avatar) || CAT_VARIATIONS[0]} /></span><span><b>{cat.name}</b><small>{cat.status.toUpperCase()} · LVL {cat.level}</small></span><strong className={cat.realizedPnlSol >= 0 ? 'positive' : 'negative'}>{money(cat.realizedPnlSol)}</strong><ChevronRight size={15} /></button>)}</div>}</section>}</div>;
}