import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { ShieldCheck, Users, Gift, Award, Bug, RefreshCw, Download, X, Activity } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { shortAddress, formatUSD } from '../../lib/dexscreener';
import { AirdropStudio, Snapshots } from './AirdropStudio';

const SESSION_KEY = 'feeless:cc-session';
const readSession = addr => { try { const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); return s && s.address === addr && Date.now() / 1000 - s.ts < 86000 ? s : null; } catch { return null; } };

const csv = rows => rows.map(r => r.map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
const download = (name, text) => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: 'text/csv' })); a.download = name; a.click(); URL.revokeObjectURL(a.href); };

export function CommandCenter({ address, signMessage, onClose }) {
  const [session, setSession] = useState(() => readSession(address));
  const [tab, setTab] = useState('pulse');
  const [sec, setSec] = useState(null);
  const [holders, setHolders] = useState(null);
  const [asset, setAsset] = useState('fee');
  const [selected, setSelected] = useState(() => new Set());
  const [hidePools, setHidePools] = useState(true);
  const [drops, setDrops] = useState([]);
  const [bugs, setBugs] = useState([]);
  const [busy, setBusy] = useState(false);

  const call = useCallback(async (path, opts = {}) => {
    const res = await fetch(apiUrl(`/api/reputation${path}`), { ...opts, headers: { 'Content-Type': 'application/json', 'x-admin-address': address, 'x-admin-ts': String(session?.ts || ''), 'x-admin-sig': session?.sig || '', ...(opts.headers || {}) } });
    const body = await res.json().catch(() => ({}));
    if (res.status === 401) { localStorage.removeItem(SESSION_KEY); setSession(null); }
    if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
    return body;
  }, [address, session]);

  const signIn = async () => {
    setBusy(true);
    try {
      const ts = Math.floor(Date.now() / 1000);
      const sig = await signMessage(`FEELESS command center\naddress:${address}\nts:${ts}`);
      const s = { address, ts, sig };
      localStorage.setItem(SESSION_KEY, JSON.stringify(s)); setSession(s);
    } catch (e) { toast.error(e.code === 4001 ? 'Signature declined.' : e.message); } finally { setBusy(false); }
  };

  const loadSec = useCallback(() => call('/admin/security').then(setSec).catch(e => toast.error(e.message)), [call]);
  const loadHolders = useCallback(() => { setHolders(null); call(`/admin/holders?asset=${asset}`).then(setHolders).catch(e => { toast.error(e.message); setHolders({ rows: [], error: e.message }); }); }, [call, asset]);
  const loadDrops = useCallback(() => call('/admin/airdrops').then(d => setDrops(d.airdrops || [])).catch(() => {}), [call]);
  const loadBugs = useCallback(() => call('/admin/bugs').then(d => setBugs((d.bugs || []).slice().reverse())).catch(() => {}), [call]);

  useEffect(() => { if (!session) return; loadSec(); loadDrops(); loadBugs(); const t = setInterval(loadSec, 30000); return () => clearInterval(t); }, [session, loadSec, loadDrops, loadBugs]);
  useEffect(() => { if (session && (tab === 'holders' || tab === 'studio') && !holders) loadHolders(); }, [session, tab, loadHolders]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (session) loadHolders(); }, [asset]); // eslint-disable-line react-hooks/exhaustive-deps

  const visible = useMemo(() => (holders?.rows || []).filter(r => !(hidePools && r.likelyPool)), [holders, hidePools]);
  const toggle = a => setSelected(s => { const n = new Set(s); n.has(a) ? n.delete(a) : n.add(a); return n; });

  if (!session) return <div className="cc-shell" data-testid="command-center"><div className="cc-gate">
    <div className="cc-crown">👑</div><h2 className="trenches-font live-gradient-text">FEELESS Command Center</h2>
    <p>This wallet created $FEE. Sign once (free, no transaction) to open holders, airdrops, badges and the security monitor for the next 24 hours.</p>
    <div className="cc-gate-actions"><button type="button" className="btn-primary" disabled={busy} onClick={signIn}><ShieldCheck size={15} />{busy ? 'Check your wallet…' : 'Sign in to Command Center'}</button><button type="button" className="btn-outline" onClick={onClose}>Back to profile</button></div>
  </div></div>;

  const TABS = [['pulse', 'Pulse', Activity], ['overview', 'Security', ShieldCheck], ['mod', 'Moderation', Bug], ['broadcast', 'Broadcast', Gift], ['treasury', 'Treasury', Award], ['holders', 'Holders', Users], ['studio', 'Airdrop Studio', Gift], ['airdrops', 'Scheduled', Gift], ['snapshots', 'Snapshots', Users], ['badges', 'Badges', Award], ['feecat', 'Fee 🐱', Award], ['pools', 'Pools', Gift], ['fees', 'Fees & Pricing', ShieldCheck], ['ads', 'Ads', Gift], ['invites', 'Invites', Users], ['bugs', `Bugs${sec?.stats?.openBugs ? ` (${sec.stats.openBugs})` : ''}`, Bug]];
  return <div className="cc-shell" data-testid="command-center">
    <header className="cc-head"><div><h2 className="trenches-font live-gradient-text">Command Center</h2><small>👑 {shortAddress(address)} · session signed · live</small></div>
      <nav className="cc-tabs">{TABS.map(([id, label, Icon]) => <button key={id} type="button" className={tab === id ? 'active' : ''} onClick={() => setTab(id)}><Icon size={14} />{label}</button>)}</nav>
      <button type="button" className="cc-close" onClick={onClose} aria-label="Close command center"><X size={16} /></button></header>

    {tab === 'pulse' && <PulsePanel call={call} />}
    {tab === 'mod' && <ModPanel call={call} />}
    {tab === 'broadcast' && <BroadcastPanel call={call} />}
    {tab === 'treasury' && <TreasuryPanel call={call} />}
    {tab === 'overview' && <Overview sec={sec} reload={loadSec} />}
    {tab === 'holders' && <section className="cc-panel">
      <div className="cc-toolbar">
        <select value={asset} onChange={e => { setAsset(e.target.value); setSelected(new Set()); }}>{(holders?.assets || ['fee', 'feecat', 'rfee']).map(a => <option key={a} value={a}>{a.toUpperCase()}</option>)}</select>
        <label className="cc-check"><input type="checkbox" checked={hidePools} onChange={e => setHidePools(e.target.checked)} />Hide pools / curve</label>
        <button type="button" onClick={() => setSelected(new Set(visible.slice(0, 50).map(r => r.owner)))}>Top 50</button>
        <button type="button" onClick={() => setSelected(new Set(visible.filter(r => !r.blocked).map(r => r.owner)))}>All clean</button>
        <button type="button" onClick={() => setSelected(new Set())}>Clear</button>
        <button type="button" onClick={loadHolders}><RefreshCw size={13} />Refresh</button>
        <button type="button" onClick={() => download(`${asset}-holders.csv`, csv([['owner', 'amount', 'pct', 'usd', 'blocked'], ...visible.map(r => [r.owner, r.amount, r.pct.toFixed(4), r.usd ?? '', r.blocked])]))}><Download size={13} />CSV</button>
      </div>
      {holders && <div className="cc-kpis"><span><small>Holders</small><b>{holders.holders?.toLocaleString() ?? '—'}</b></span><span><small>Price</small><b>{holders.price ? `$${holders.price.toPrecision(4)}` : '—'}</b></span><span><small>Selected</small><b>{selected.size}</b></span><span><small>Blocklisted</small><b>{(holders.rows || []).filter(r => r.blocked).length}</b></span></div>}
      {selected.size > 0 && <div className="cc-selbar"><b>{selected.size} selected</b><button type="button" className="btn-primary" onClick={() => setTab('studio')}><Gift size={13} />Airdrop them</button><button type="button" onClick={() => setTab('badges')}>Award a badge</button></div>}
      {!holders ? <p className="cc-empty">Reading every {asset.toUpperCase()} token account from the chain…</p> : holders.error ? <p className="cc-empty">{holders.error}</p>
        : <div className="cc-table"><div className="cc-tr cc-th"><span /><span>#</span><span>Wallet</span><span>Amount</span><span>Share</span><span>Value</span><span>Tags</span></div>
          {visible.slice(0, 400).map((r, i) => <label key={r.owner} className={`cc-tr ${selected.has(r.owner) ? 'sel' : ''} ${r.blocked ? 'bad' : ''}`}>
            <input type="checkbox" checked={selected.has(r.owner)} onChange={() => toggle(r.owner)} /><span>{i + 1}</span>
            <a href={`/terminal/profile/${r.owner}`} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}>{shortAddress(r.owner)}</a>
            <span>{r.amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span><span>{r.pct.toFixed(2)}%</span><span>{r.usd != null ? formatUSD(r.usd) : '—'}</span>
            <span className="cc-tags">{r.isAdmin && <em className="t-gold">HQ</em>}{r.likelyPool && <em>pool</em>}{r.blocked && <em className="t-bad">blocked</em>}{r.customBadges.map(b => <em key={b.id} title={b.why}>{b.icon}</em>)}</span>
          </label>)}</div>}
    </section>}
    {tab === 'studio' && (holders?.rows ? <AirdropStudio call={call} asset={asset} holders={holders.rows} selected={[...selected]} onScheduled={() => { loadDrops(); setTab('airdrops'); }} /> : <p className="cc-empty">Loading holders…</p>)}
    {tab === 'snapshots' && <Snapshots call={call} asset={asset} />}
    {tab === 'airdrops' && <Airdrops drops={drops} call={call} reload={loadDrops} />}
    {tab === 'badges' && <AwardBadges call={call} initial={[...selected]} />}
    {tab === 'feecat' && <FeeCatPanel call={call} />}
    {tab === 'pools' && <PoolsPanel />}
    {tab === 'fees' && <FeesPanel call={call} />}
    {tab === 'ads' && <AdsPanel call={call} />}
    {tab === 'invites' && <InvitesPanel call={call} />}
    {tab === 'bugs' && <section className="cc-panel">{!bugs.length ? <p className="cc-empty">No reports yet. Anyone can file one from a profile's “Report a bug” button.</p>
      : <div className="cc-bugs">{bugs.map(b => <div key={b.id} className={`cc-bug k-${b.kind} s-${b.status}`}><div><em>{b.kind}</em><b>{b.text}</b><small>{b.page || '—'} · {new Date(b.at * 1000).toLocaleString()}{b.address ? ` · ${shortAddress(b.address)}` : ''}</small></div>
        <select value={b.status} onChange={e => call(`/admin/bugs/${b.id}?status=${e.target.value}`, { method: 'POST' }).then(loadBugs).catch(err => toast.error(err.message))}>{['open', 'fixing', 'fixed', 'wontfix'].map(s => <option key={s}>{s}</option>)}</select></div>)}</div>}</section>}
  </div>;
}

function Overview({ sec, reload }) {
  const [clicks, setClicks] = useState([]);
  useEffect(() => { fetch(apiUrl('/api/reputation/clicks/top?limit=10')).then(r => r.json()).then(d => setClicks(d.rows || [])).catch(() => {}); }, [sec]);
  if (!sec) return <p className="cc-empty">Running security checks…</p>;
  const tone = sec.score >= 85 ? 'good' : sec.score >= 60 ? 'warn' : 'bad';
  return <section className="cc-panel cc-overview">
    <div className={`cc-score s-${tone}`}><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" /><circle cx="60" cy="60" r="52" className="arc" style={{ strokeDasharray: `${(sec.score / 100) * 327} 327` }} /></svg><b>{sec.score}</b><small>security score</small><button type="button" onClick={reload}><RefreshCw size={12} />Re-scan</button></div>
    <div className="cc-block"><h4>Services</h4>{sec.services.map(s => <div key={s.name} className={`cc-svc ${s.up ? 'up' : 'down'}`}><i />{s.name}<small>{s.up ? `${s.ms} ms` : 'DOWN'}</small></div>)}</div>
    <div className="cc-block"><h4>Attack signals · last hour</h4>{[['forgedSignatures', 'Forged signatures'], ['replays', 'Replay attempts'], ['rateLimited', 'Rate-limited'], ['forbidden', 'Forbidden'], ['serverErrors', 'Server errors']].map(([k, l]) => <div key={k} className={`cc-sig ${sec.signals[k] ? 'hot' : ''}`}><span>{l}</span><b>{sec.signals[k]}</b></div>)}</div>
    <div className="cc-block"><h4>Platform</h4>{[['chat24h', 'Chat msgs (24h)'], ['chatRooms', 'Chat rooms'], ['blocklisted', 'Blocklisted wallets'], ['openBugs', 'Open bugs'], ['customBadges', 'Badges awarded']].map(([k, l]) => <div key={k} className="cc-sig"><span>{l}</span><b>{sec.stats[k]}</b></div>)}</div>
    <div className="cc-block cc-wide"><h4>Vulnerability checks</h4>{sec.checks.map(c => <div key={c.name} className={`cc-check-row sev-${c.severity}`}><span>{c.ok ? '✅' : c.severity === 'high' ? '🚨' : '⚠️'}</span><b>{c.name}</b><small>{c.detail}</small></div>)}</div>
    <div className="cc-block"><h4>Most clicked in chat</h4>{!clicks.length ? <small className="cc-empty">No $TICKER / CA clicks yet.</small> : clicks.map(c => <div key={`${c.kind}:${c.value}`} className="cc-sig"><span>{c.kind === 'ticker' ? `$${c.value}` : c.kind === 'ca' ? `${c.value.slice(0, 4)}…${c.value.slice(-4)}` : c.kind === 'mention' ? `@${c.value}` : c.value}</span><b>{c.count}</b></div>)}</div>
    <div className="cc-block"><h4>Top errors</h4>{!sec.topErrors.length ? <small className="cc-empty">Clean — no errors this hour.</small> : sec.topErrors.map(e => <div key={e.key} className="cc-sig"><code>{e.key}</code><b>{e.count}</b></div>)}</div>
    <div className="cc-block"><h4>Audit log</h4>{!sec.audit.length ? <small className="cc-empty">No admin actions yet.</small> : sec.audit.map((a, i) => <div key={i} className="cc-audit"><small>{new Date(a.at * 1000).toLocaleString()}</small><b>{a.action}</b><span>{a.detail}</span></div>)}</div>
  </section>;
}

function Airdrops({ drops, call, reload }) {
  const [sigs, setSigs] = useState({});
  const mark = async (d, status) => {
    try { await call(`/admin/airdrops/${d.id}`, { method: 'POST', body: JSON.stringify({ status, txSig: sigs[d.id]?.trim() || null }) }); toast.success(status === 'sent' ? 'Verified on-chain — recipients got the 🪂 badge.' : `Marked ${status}.`); reload(); }
    catch (e) { toast.error(e.message); }
  };
  return <section className="cc-panel">
    <p className="cc-note">FEELESS never holds your keys. Schedule here, send from your wallet (CSV works with any multisender), then paste the transaction signature — it's checked on-chain and the receipt is kept.</p>
    {!drops.length ? <p className="cc-empty">No airdrops yet. Select holders on the Holders tab to schedule one.</p> : drops.map(d => { const due = d.scheduledAt * 1000 <= Date.now() && d.status === 'scheduled';
      return <div key={d.id} className={`cc-drop s-${d.status} ${due ? 'due' : ''}`}>
        <div className="cc-drop-top"><b>🪂 {d.name}</b><em>{due ? 'DUE NOW' : d.status}</em><small>{new Date(d.scheduledAt * 1000).toLocaleString()} · {d.recipients.length} wallets · {d.total.toLocaleString(undefined, { maximumFractionDigits: 4 })} {d.asset.toUpperCase()}</small></div>
        <div className="cc-drop-actions">
          <button type="button" onClick={() => download(`${d.name}.csv`, csv([['address', 'amount'], ...d.recipients.map(r => [r.address, r.amount])]))}><Download size={13} />CSV</button>
          {d.status === 'scheduled' && <><input placeholder="Paste tx signature after sending" value={sigs[d.id] || ''} onChange={e => setSigs(s => ({ ...s, [d.id]: e.target.value }))} /><button type="button" className="btn-primary" onClick={() => mark(d, 'sent')}>Verify & mark sent</button><button type="button" onClick={() => mark(d, 'cancelled')}>Cancel</button></>}
          {d.txs?.map(t => <a key={t.sig} href={`https://solscan.io/tx/${t.sig}`} target="_blank" rel="noopener noreferrer">receipt {t.sig.slice(0, 8)}…</a>)}
        </div>
      </div>; })}
  </section>;
}

function AwardBadges({ call, initial }) {
  const [text, setText] = useState(initial.join('\n'));
  const [label, setLabel] = useState('');
  const [icon, setIcon] = useState('⭐');
  const [tone, setTone] = useState('gold');
  const [why, setWhy] = useState('');
  const addrs = text.split(/[\s,]+/).filter(a => /^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$/.test(a));
  const award = async () => {
    try { const r = await call('/admin/badges', { method: 'POST', body: JSON.stringify({ addresses: addrs, label, icon, tone, why }) }); toast.success(`Awarded ${label} to ${r.awarded} wallet(s).`); }
    catch (e) { toast.error(e.message); }
  };
  return <section className="cc-panel cc-award">
    <div className="cc-award-preview"><span className={`badge-pill tone-${tone}`}>{icon} {label || 'Badge name'}</span><small>{why || 'Why they earned it'}</small></div>
    <div className="cc-award-form">
      <div className="cc-icons">{['⭐', '💎', '🔥', '🏆', '🧠', '🐞', '🛠️', '🎖️', '🦾', '🌙'].map(i => <button key={i} type="button" className={icon === i ? 'active' : ''} onClick={() => setIcon(i)}>{i}</button>)}</div>
      <input placeholder="Badge name (e.g. Bug Hunter)" maxLength={32} value={label} onChange={e => setLabel(e.target.value)} />
      <input placeholder="Why (shown on hover)" maxLength={140} value={why} onChange={e => setWhy(e.target.value)} />
      <div className="cc-icons">{['gold', 'mint', 'plain', 'bad'].map(t => <button key={t} type="button" className={`tone-${t} ${tone === t ? 'active' : ''}`} onClick={() => setTone(t)}>{t}</button>)}</div>
      <textarea rows={6} placeholder="Wallet addresses — one per line (select holders first to prefill)" value={text} onChange={e => setText(e.target.value)} />
      <button type="button" className="btn-primary" disabled={!addrs.length || label.length < 2} onClick={award}><Award size={14} />Award to {addrs.length} wallet{addrs.length === 1 ? '' : 's'}</button>
    </div>
  </section>;
}

export function ReportBug({ address }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [kind, setKind] = useState('bug');
  const send = async () => {
    const res = await fetch(apiUrl('/api/reputation/bugs'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, kind, page: window.location.pathname, address }) });
    const b = await res.json().catch(() => ({}));
    if (!res.ok) { toast.error(b.detail || 'Could not send.'); return; }
    toast.success('Sent to FEELESS HQ — thank you!'); setText(''); setOpen(false);
  };
  if (!open) return <button type="button" className="btn-outline wp-report" onClick={() => setOpen(true)}><Bug size={13} />Report a bug</button>;
  return <div className="wp-report-box"><select value={kind} onChange={e => setKind(e.target.value)}><option value="bug">🐞 Bug</option><option value="security">🔐 Security issue</option><option value="idea">💡 Idea</option></select>
    <textarea rows={3} maxLength={2000} placeholder="What happened? What did you expect?" value={text} onChange={e => setText(e.target.value)} />
    <div><button type="button" className="btn-primary" disabled={text.trim().length < 5} onClick={send}>Send</button><button type="button" className="btn-outline" onClick={() => setOpen(false)}>Cancel</button></div></div>;
}

function FeesPanel({ call }) {
  const [cfg, setCfg] = useState(null);
  const [limits, setLimits] = useState({ minBps: 50, maxBps: 255 });
  const [zero, setZero] = useState('');
  const [promoDays, setPromoDays] = useState(0);
  useEffect(() => { call('/admin/fees').then(d => { setCfg(d.fees); setLimits(d.limits); setZero((d.fees.zeroFeeMints || []).join('\n')); }).catch(e => toast.error(e.message)); }, [call]);
  if (!cfg) return <p className="cc-empty">Loading fee settings…</p>;
  const set = (k, v) => setCfg(c => ({ ...c, [k]: v }));
  const save = async () => {
    const body = { ...cfg, platformFeeBps: Number(cfg.platformFeeBps) || 0, zeroFeeMints: zero.split(/[\s,]+/).filter(Boolean),
      promo: { ...(cfg.promo || {}), until: promoDays > 0 ? Date.now() / 1000 + promoDays * 86400 : cfg.promo?.until || 0 } };
    try { const d = await call('/admin/fees', { method: 'POST', body: JSON.stringify(body) }); setCfg(d.fees); toast.success('Fee settings saved — applied to the next quote.'); } catch (e) { toast.error(e.message); }
  };
  const TIERS = ['Trencher', 'Fee Friend', 'Fee Insider', 'Fee Whale'];
  return <section className="cc-panel cc-fees" data-testid="fees-panel">
    <p className="cc-note">Fees are charged by Jupiter as an integrator fee straight into your referral account — FEELESS never touches user funds. Jupiter allows {limits.minBps / 100}%–{limits.maxBps / 100}% (set 0 for free trading). $FEE ecosystem trades are always free. Every trader sees the fee before signing.</p>
    <div className="cc-studio-grid">
      <div className="cc-block"><h4>Platform fee</h4>
        <label>Fee (basis points · 100 = 1%)<input type="number" min="0" max={limits.maxBps} value={cfg.platformFeeBps} onChange={e => set('platformFeeBps', e.target.value)} /></label>
        <small className="cc-empty">{Number(cfg.platformFeeBps) ? `${(cfg.platformFeeBps / 100).toFixed(2)}% per swap` : 'Free trading'}</small>
        <label>Jupiter referral account (your fee wallet)<input placeholder="Create at referral.jup.ag, paste the account" value={cfg.referralAccount} onChange={e => set('referralAccount', e.target.value.trim())} /></label>
      </div>
      <div className="cc-block"><h4>$FEE holder discounts</h4>
        {TIERS.map((t, i) => <label key={t}>{t}<input type="number" min="0" max="100" value={cfg.tierDiscountPct?.[String(i)] ?? 0} onChange={e => set('tierDiscountPct', { ...cfg.tierDiscountPct, [String(i)]: Number(e.target.value) })} /></label>)}
        <small className="cc-empty">% off the platform fee for each tier.</small>
      </div>
      <div className="cc-block"><h4>Promo + fee-free tokens</h4>
        <label>Promo label<input value={cfg.promo?.label || ''} onChange={e => set('promo', { ...cfg.promo, label: e.target.value })} placeholder="e.g. Launch week" /></label>
        <label>Promo discount %<input type="number" min="0" max="100" value={cfg.promo?.discountPct || 0} onChange={e => set('promo', { ...cfg.promo, discountPct: Number(e.target.value) })} /></label>
        <label>Run promo for (days from now)<input type="number" min="0" value={promoDays} onChange={e => setPromoDays(Number(e.target.value))} /></label>
        {cfg.promo?.until > Date.now() / 1000 && <small className="cc-empty">Live until {new Date(cfg.promo.until * 1000).toLocaleString()}</small>}
        <label>Fee-free token mints (one per line)<textarea rows={3} value={zero} onChange={e => setZero(e.target.value)} /></label>
      </div>
    </div>
    <button type="button" className="btn-primary" onClick={save}>Save fee settings</button>
  </section>;
}

function AdsPanel({ call }) {
  const blank = { title: '', text: '', url: '', imageUrl: '', placement: 'banner', sponsor: '', active: true, days: 7 };
  const [ads, setAds] = useState([]);
  const [f, setF] = useState(blank);
  const load = useCallback(() => call('/admin/ads').then(d => setAds(d.ads || [])).catch(e => toast.error(e.message)), [call]);
  useEffect(() => { load(); }, [load]);
  const save = async () => {
    const now = Date.now() / 1000;
    try { await call('/admin/ads', { method: 'POST', body: JSON.stringify({ ...f, startsAt: f.startsAt || now, endsAt: f.days ? now + f.days * 86400 : 0 }) }); toast.success(f.id ? 'Ad updated' : 'Ad live'); setF(blank); load(); } catch (e) { toast.error(e.message); }
  };
  const set = (k, v) => setF(x => ({ ...x, [k]: v }));
  return <section className="cc-panel">
    <p className="cc-note">Run announcements, $FEE promos or paid sponsor slots. Every ad is labelled (Sponsored when a sponsor is set), users can hide it for the session, and views/clicks are counted. Links must be https:// or an in-app path.</p>
    <div className="cc-studio-grid">
      <div className="cc-block"><h4>{f.id ? 'Edit ad' : 'New ad'}</h4>
        <label>Title<input maxLength={60} value={f.title} onChange={e => set('title', e.target.value)} /></label>
        <label>Text<input maxLength={200} value={f.text} onChange={e => set('text', e.target.value)} /></label>
        <label>Link (https:// or /terminal/…)<input value={f.url} onChange={e => set('url', e.target.value)} /></label>
        <label>Image URL (optional)<input value={f.imageUrl} onChange={e => set('imageUrl', e.target.value)} /></label>
        <label>Sponsor (leave blank for FEELESS)<input maxLength={40} value={f.sponsor} onChange={e => set('sponsor', e.target.value)} /></label>
        <label>Placement<select value={f.placement} onChange={e => set('placement', e.target.value)}>{['banner', 'trenches', 'profile', 'ticker'].map(p => <option key={p}>{p}</option>)}</select></label>
        <label>Run for (days, 0 = until turned off)<input type="number" min="0" value={f.days} onChange={e => set('days', Number(e.target.value))} /></label>
        <button type="button" className="btn-primary" disabled={f.title.length < 2} onClick={save}>{f.id ? 'Save' : 'Publish ad'}</button>
      </div>
      <div className="cc-block cc-wide"><h4>Ads</h4>{!ads.length ? <small className="cc-empty">No ads yet.</small> : ads.map(a => <div key={a.id} className={`cc-drop ${a.active ? 's-sent' : 's-cancelled'}`}>
        <div className="cc-drop-top"><b>{a.title}</b><em>{a.placement}{a.active ? '' : ' · off'}</em><small>{a.views || 0} views · {a.clicks || 0} clicks · CTR {a.views ? ((100 * (a.clicks || 0)) / a.views).toFixed(1) : 0}%{a.endsAt ? ` · ends ${new Date(a.endsAt * 1000).toLocaleDateString()}` : ''}{a.sponsor ? ` · ${a.sponsor}` : ''}</small></div>
        <div className="cc-drop-actions"><button type="button" onClick={() => setF({ ...a, days: 0 })}>Edit</button><button type="button" onClick={() => call('/admin/ads', { method: 'POST', body: JSON.stringify({ ...a, active: !a.active }) }).then(load)}>{a.active ? 'Pause' : 'Resume'}</button><button type="button" onClick={() => call(`/admin/ads/${a.id}`, { method: 'DELETE' }).then(load)}>Delete</button></div>
      </div>)}</div>
    </div>
  </section>;
}

function InvitesPanel({ call }) {
  const [d, setD] = useState(null);
  const [url, setUrl] = useState('');
  useEffect(() => { call('/admin/referrals').then(setD).catch(e => toast.error(e.message)); fetch('/api/reputation/site').then(r => r.json()).then(x => setUrl(x.publicUrl || '')).catch(() => {}); }, [call]);
  const saveUrl = () => call('/admin/site', { method: 'POST', body: JSON.stringify({ publicUrl: url }) }).then(() => toast.success('Invite links now use ' + url)).catch(e => toast.error(e.message));
  if (!d) return <p className="cc-empty">Loading invites…</p>;
  return <section className="cc-panel">
    <div className="cc-block"><h4>Public site domain (used in every invite link)</h4><div className="cc-toolbar"><input placeholder="https://your-domain.com" value={url} onChange={e => setUrl(e.target.value)} /><button type="button" className="btn-primary" onClick={saveUrl}>Save</button></div><small className="cc-empty">Links look like {url || 'https://your-domain.com'}/r/b26hhajg — one unique code per wallet.</small></div>
    <div className="cc-kpis"><span><small>Wallets invited</small><b>{d.total}</b></span><span><small>Active inviters</small><b>{d.top.length}</b></span></div>
    <div className="cc-block"><h4>Top inviters</h4>{!d.top.length ? <small className="cc-empty">No invites yet — every wallet has a link in Settings and on its profile.</small> : d.top.map((r, i) => <div key={r.address} className="cc-sig"><span>{i + 1}. <a href={`/terminal/profile/${r.address}`} target="_blank" rel="noopener noreferrer">@{r.handle}</a></span><b>{r.invited}</b></div>)}</div>
  </section>;
}

function PulsePanel({ call }) {
  const [d, setD] = useState(null);
  useEffect(() => { const load = () => call('/admin/pulse').then(setD).catch(() => {}); load(); const t = setInterval(load, 20000); return () => clearInterval(t); }, [call]);
  if (!d) return <p className="cc-empty">Taking the pulse…</p>;
  const max = Math.max(1, ...d.hourly);
  return <section className="cc-panel">
    <div className="cc-kpis cc-kpis-5"><span><small>Messages 24h</small><b>{d.messages24h}</b></span><span><small>Active wallets 24h</small><b>{d.activeWallets24h}</b></span><span><small>Profiles</small><b>{d.profiles}</b></span><span><small>Push subscribers</small><b>{d.pushSubscribers}</b></span><span><small>Muted</small><b>{d.muted}</b></span></div>
    <div className="cc-block"><h4>Chat activity · last 24h</h4><div className="cc-spark">{d.hourly.map((v, i) => <i key={i} style={{ height: `${(v / max) * 100}%` }} title={`${v} msgs, ${23 - i}h ago`} />)}</div></div>
    <div className="cc-studio-grid">
      <div className="cc-block"><h4>Busiest rooms</h4>{!d.busiestRooms.length ? <small className="cc-empty">Quiet.</small> : d.busiestRooms.map(r => <div key={r.room} className="cc-sig"><span>{r.room.replace(/^coin-solana-/, '🪙 ').slice(0, 34)}</span><b>{r.messages}</b></div>)}</div>
      <div className="cc-block"><h4>Top voices</h4>{!d.topPosters.length ? <small className="cc-empty">No posters yet.</small> : d.topPosters.map(p => <div key={p.address} className="cc-sig"><a href={`/terminal/profile/${p.address}`} target="_blank" rel="noopener noreferrer">@{p.handle}</a><b>{p.messages}</b></div>)}</div>
      <div className="cc-block"><h4>🐱 Fee right now</h4><div className="cc-sig"><span>Balance</span><b>{Number(d.fee.balanceSol || 0).toFixed(2)} SOL</b></div><div className="cc-sig"><span>Realized</span><b>{Number(d.fee.realizedPnlSol || 0).toFixed(3)} SOL</b></div><div className="cc-sig"><span>W / L</span><b>{d.fee.wins || 0} / {d.fee.losses || 0}</b></div><div className="cc-sig"><span>Open</span><b>{d.fee.open}</b></div></div>
      <div className="cc-block"><h4>Most clicked</h4>{!d.topClicks.length ? <small className="cc-empty">No clicks yet.</small> : d.topClicks.map(c => <div key={c.key} className="cc-sig"><span>{c.key.replace('ticker:', '$').replace('ca:', '').replace('mention:', '@').slice(0, 26)}</span><b>{c.count}</b></div>)}</div>
    </div>
  </section>;
}

function ModPanel({ call }) {
  const [msgs, setMsgs] = useState([]);
  const [q, setQ] = useState('');
  const load = useCallback(() => call('/admin/chat-feed').then(d => setMsgs(d.messages || [])).catch(e => toast.error(e.message)), [call]);
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, [load]);
  const del = m => call('/admin/moderate/delete', { method: 'POST', body: JSON.stringify({ room: m.room, id: m.id }) }).then(() => { toast.success('Removed'); load(); }).catch(e => toast.error(e.message));
  const mute = (m, hours) => call('/admin/moderate/mute', { method: 'POST', body: JSON.stringify({ address: m.address, hours }) }).then(() => { toast.success(hours ? `Muted ${hours}h` : 'Unmuted'); load(); }).catch(e => toast.error(e.message));
  const shown = msgs.filter(m => !q || `${m.text} ${m.handle} ${m.username} ${m.room}`.toLowerCase().includes(q.toLowerCase()));
  return <section className="cc-panel">
    <div className="cc-toolbar"><input placeholder="Filter messages, @handles, rooms…" value={q} onChange={e => setQ(e.target.value)} /><button type="button" onClick={load}>Refresh</button></div>
    <div className="cc-bugs">{!shown.length ? <p className="cc-empty">No messages.</p> : shown.map(m => <div key={m.id} className={`cc-bug ${m.muted ? 'k-security' : ''}`}><div><em>{m.room.slice(0, 40)}</em><b>{m.text}</b><small>@{m.handle || m.username} · {new Date(m.ts).toLocaleString()}{m.muted ? ' · MUTED' : ''}</small></div>
      <div className="cc-drop-actions"><button type="button" onClick={() => del(m)}>Delete</button><button type="button" onClick={() => call('/admin/verify', { method: 'POST', body: JSON.stringify({ address: m.address, hours: 0 }) }).then(() => toast.success('✔ Verified')).catch(e => toast.error(e.message))}>✔ Verify</button>{m.muted ? <button type="button" onClick={() => mute(m, 0)}>Unmute</button> : <><button type="button" onClick={() => mute(m, 1)}>Mute 1h</button><button type="button" onClick={() => mute(m, 24)}>24h</button></>}</div></div>)}</div>
  </section>;
}

function BroadcastPanel({ call }) {
  const [f, setF] = useState({ title: '', body: '', url: '/terminal', push: false, rooms: 'feeless-general' });
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setF(x => ({ ...x, [k]: v }));
  const send = async () => {
    if (!window.confirm(`Send "${f.title}"${f.push ? ' as a push notification to every subscriber' : ''}?`)) return;
    setBusy(true);
    try { const r = await call('/admin/broadcast', { method: 'POST', body: JSON.stringify({ ...f, rooms: f.rooms.split(/[\s,]+/).filter(Boolean) }) }); toast.success(`Posted in ${r.rooms} room(s) · pushed to ${r.pushed}`); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return <section className="cc-panel">
    <p className="cc-note">Announce drops, listings or airdrops. Posts land in chat as 👑 FEELESS HQ; push goes to everyone who enabled alerts. Use sparingly — every push is a real notification on someone's phone.</p>
    <div className="cc-block cc-award-form">
      <input placeholder="Title (e.g. $FEE airdrop is live)" maxLength={60} value={f.title} onChange={e => set('title', e.target.value)} />
      <textarea rows={3} maxLength={240} placeholder="Message" value={f.body} onChange={e => set('body', e.target.value)} />
      <input placeholder="Link (/terminal/… or https://)" value={f.url} onChange={e => set('url', e.target.value)} />
      <input placeholder="Chat rooms (comma separated)" value={f.rooms} onChange={e => set('rooms', e.target.value)} />
      <label className="cc-check"><input type="checkbox" checked={f.push} onChange={e => set('push', e.target.checked)} />Also send as a push notification</label>
      <button type="button" className="btn-primary" disabled={busy || f.title.length < 2 || f.body.length < 2} onClick={send}>📢 Broadcast</button>
    </div>
  </section>;
}

function TreasuryPanel({ call }) {
  const [d, setD] = useState(null);
  useEffect(() => { call('/admin/treasury').then(setD).catch(e => toast.error(e.message)); }, [call]);
  if (!d) return <p className="cc-empty">Reading the creator wallet…</p>;
  return <section className="cc-panel">
    <div className="cc-kpis"><span><small>SOL</small><b>{d.sol != null ? d.sol.toFixed(3) : '—'}</b></span>{Object.entries(d.holdingsUsd).map(([k, v]) => <span key={k}><small>{k.toUpperCase()} value</small><b>{v != null ? formatUSD(v) : '—'}</b></span>)}</div>
    <div className="cc-block"><h4>Recent transactions</h4>{d.recent.map(t => <div key={t.sig} className="cc-sig"><a href={`https://solscan.io/tx/${t.sig}`} target="_blank" rel="noopener noreferrer">{t.sig.slice(0, 10)}…</a><span>{t.at ? new Date(t.at * 1000).toLocaleString() : ''}</span><b className={t.ok ? 'positive' : 'negative'}>{t.ok ? 'ok' : 'failed'}</b></div>)}</div>
  </section>;
}

const FEE_LABELS = { minLiquidity: 'Min liquidity ($)', minVolume24h: 'Min 24h volume ($)', minMarketCap: 'Min market cap ($)', maxMarketCap: 'Max market cap ($)', minAgeHours: 'Min pool age (h)', stopLoss: 'Stop-loss (%)', takeProfit: 'Scale-out at (+%)', maxHoldHours: 'Max hold (h)', maxPositions: 'Max open positions', maxTop10Pct: 'Max top-10 holders (%)', maxSnipers: 'Max snipers', maxBundled: 'Max bundled wallets', maxM5Chase: 'No chase above 5m (%)', breakEvenArm: 'Break-even after (+%)' };
function FeeCatPanel({ call }) {
  const [d, setD] = useState(null);
  const [draft, setDraft] = useState({});
  const [size, setSize] = useState('');
  const load = useCallback(() => call('/admin/feecat').then(x => { setD(x); setDraft(x.rules); setSize(x.leader?.risk?.maxPositionSol ?? ''); }).catch(e => toast.error(e.message)), [call]);
  useEffect(() => { load(); }, [load]);
  if (!d) return <p className="cc-empty">Waking Fee up…</p>;
  const save = extra => call('/admin/feecat', { method: 'POST', body: JSON.stringify({ rules: draft, maxPositionSol: Number(size) || undefined, ...extra }) }).then(() => { toast.success('Fee updated — applies on the next tick.'); load(); }).catch(e => toast.error(e.message));
  const running = d.leader?.status === 'running';
  return <section className="cc-panel">
    <div className="cc-kpis cc-kpis-5"><span><small>Status</small><b className={running ? 'positive' : 'negative'}>{running ? 'Trading' : 'Paused'}</b></span><span><small>Balance</small><b>{Number(d.cat.balanceSol || 0).toFixed(2)} SOL</b></span><span><small>Realized</small><b>{Number(d.cat.realizedPnlSol || 0).toFixed(3)}</b></span><span><small>Win rate</small><b>{d.cat.winRate ?? '—'}%</b></span><span><small>Lessons</small><b>{(d.learning?.missed || 0) + (d.learning?.good || 0)}</b></span></div>
    <div className="cc-toolbar"><button type="button" className="btn-primary" onClick={() => save({ status: running ? 'paused' : 'running' })}>{running ? '⏸ Pause Fee' : '▶ Resume Fee'}</button><button type="button" onClick={() => window.confirm('Reset what Fee has learned? Exits go back to defaults.') && save({ resetLearning: true })}>Reset learning</button><a href="/terminal/feecat" target="_blank" rel="noopener noreferrer">Open Fee's profile ↗</a></div>
    <p className="cc-note">Tune Fee's brain. Every value is clamped to a safe range on the server — Fee can get more aggressive, never reckless. Changes are logged in the audit trail.</p>
    <div className="cc-block"><h4>Entry + safety rules</h4><div className="fee-rules">{Object.keys(d.bounds).map(k => { const [lo, hi] = d.bounds[k]; return <label key={k}><span>{FEE_LABELS[k] || k}<em>{lo}–{hi}</em></span><input type="number" step="any" min={lo} max={hi} value={draft[k] ?? ''} onChange={e => setDraft(x => ({ ...x, [k]: e.target.value }))} /></label>; })}
      <label><span>Max SOL per trade<em>0.1–10</em></span><input type="number" step="0.1" value={size} onChange={e => setSize(e.target.value)} /></label></div>
      <button type="button" className="btn-primary" onClick={() => save({})}>Save Fee's rules</button></div>
    {d.learning && <div className="cc-block"><h4>What Fee has learned</h4>{Object.entries(d.learning.params || {}).map(([k, v]) => <div key={k} className="cc-sig"><span>{k}</span><b>{v} <small className="cc-empty">(default {d.learning.defaults?.[k]})</small></b></div>)}</div>}
  </section>;
}

const DEXES = [
  { id: 'raydium', name: 'Raydium CPMM', url: 'https://raydium.io/liquidity/create-pool/', note: 'Standard constant-product pool. Cheapest to create; works everywhere.' },
  { id: 'meteora', name: 'Meteora DAMM v2', url: 'https://app.meteora.ag/', note: 'Dynamic fees — earns more in volatile markets; supports fee scheduling.' },
  { id: 'orca', name: 'Orca Whirlpool', url: 'https://www.orca.so/pools', note: 'Concentrated liquidity — best depth per dollar if you manage ranges.' },
];
function PoolsPanel() {
  const [mints, setMints] = useState({});
  const [pools, setPools] = useState([]);
  const [asset, setAsset] = useState('fee');
  const [check, setCheck] = useState(''); const [found, setFound] = useState(null);
  useEffect(() => { fetch('/api/market/assets').then(r => r.json()).then(d => setMints(Object.fromEntries((d.assets || []).filter(a => a.mint).map(a => [a.id, a.mint])))).catch(() => {}); }, []);
  const mint = mints[asset];
  useEffect(() => { if (!mint) return; fetch(`https://api.dexscreener.com/latest/dex/tokens/${mint}`).then(r => r.json()).then(d => setPools((d.pairs || []).sort((a, b) => (b.liquidity?.usd || 0) - (a.liquidity?.usd || 0)))).catch(() => {}); }, [mint]);
  const copy = v => navigator.clipboard?.writeText(v).then(() => toast.success('Copied'));
  const verify = async () => { setFound(null); try { const d = await (await fetch(`https://api.dexscreener.com/latest/dex/pairs/solana/${check.trim()}`)).json(); setFound(d.pairs?.[0] || false); } catch { setFound(false); } };
  return <section className="cc-panel">
    <p className="cc-note">Create liquidity pools for your tokens on a real DEX. FEELESS never holds funds — the DEX's own page builds the transaction and your creator wallet signs it. Copy the mints below, create the pool, then verify it here.</p>
    <div className="cc-toolbar"><select value={asset} onChange={e => setAsset(e.target.value)}>{Object.keys(mints).map(k => <option key={k} value={k}>{k.toUpperCase()}</option>)}</select>{mint && <><code className="pool-mint">{mint}</code><button type="button" onClick={() => copy(mint)}>Copy mint</button><button type="button" onClick={() => copy('So11111111111111111111111111111111111111112')}>Copy SOL mint</button></>}</div>
    <div className="cc-studio-grid">{DEXES.map(x => <div key={x.id} className="cc-block"><h4>{x.name}</h4><small className="cc-empty">{x.note}</small><a className="btn-primary" href={x.url} target="_blank" rel="noopener noreferrer">Create on {x.name.split(' ')[0]} ↗</a></div>)}</div>
    <div className="cc-block"><h4>Verify a new pool</h4><div className="cc-toolbar"><input placeholder="Paste the new pool / pair address" value={check} onChange={e => setCheck(e.target.value)} /><button type="button" className="btn-primary" onClick={verify}>Verify</button></div>
      {found === false && <small className="cc-empty">Not indexed yet — DexScreener usually picks up new pools within a few minutes.</small>}
      {found && <div className="cc-sig"><span>✅ {found.baseToken.symbol}/{found.quoteToken.symbol} on {found.dexId}</span><b>{formatUSD(found.liquidity?.usd)} liq</b></div>}</div>
    <div className="cc-block"><h4>Live pools for {asset.toUpperCase()}</h4>{!pools.length ? <small className="cc-empty">No pools indexed.</small> : pools.map(p => <div key={p.pairAddress} className="cc-sig"><a href={`/terminal/coin/solana/${p.pairAddress}`} target="_blank" rel="noopener noreferrer">{p.baseToken.symbol}/{p.quoteToken.symbol} · {p.dexId}</a><span>vol {formatUSD(p.volume?.h24)}</span><b>{formatUSD(p.liquidity?.usd)}</b></div>)}</div>
  </section>;
}
