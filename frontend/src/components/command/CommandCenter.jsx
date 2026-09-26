import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { ShieldCheck, Users, Gift, Award, Bug, RefreshCw, Download, X, Activity } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { shortAddress, formatUSD } from '../../lib/dexscreener';
import { AirdropStudio, Snapshots } from './AirdropStudio';

const SESSION_KEY = 'feeless:cc-session';
const readSession = addr => { try { const s = JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null'); return s && s.address === addr && Date.now() / 1000 - s.ts < 3500 ? s : null; } catch { return null; } };

const csv = rows => rows.map(r => r.map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
const download = (name, text) => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: 'text/csv' })); a.download = name; a.click(); URL.revokeObjectURL(a.href); };

export function CommandCenter({ address, signMessage, onClose }) {
  const [session, setSession] = useState(() => readSession(address));
  const [tab, setTab] = useState('overview');
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
    if (res.status === 401) { sessionStorage.removeItem(SESSION_KEY); setSession(null); }
    if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
    return body;
  }, [address, session]);

  const signIn = async () => {
    setBusy(true);
    try {
      const ts = Math.floor(Date.now() / 1000);
      const sig = await signMessage(`FEELESS command center\naddress:${address}\nts:${ts}`);
      const s = { address, ts, sig };
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(s)); setSession(s);
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
    <p>This wallet created $FEE. Sign once (free, no transaction) to open holders, airdrops, badges and the security monitor for the next hour.</p>
    <div className="cc-gate-actions"><button type="button" className="btn-primary" disabled={busy} onClick={signIn}><ShieldCheck size={15} />{busy ? 'Check your wallet…' : 'Sign in to Command Center'}</button><button type="button" className="btn-outline" onClick={onClose}>Back to profile</button></div>
  </div></div>;

  const TABS = [['overview', 'Overview', Activity], ['holders', 'Holders', Users], ['studio', 'Airdrop Studio', Gift], ['airdrops', 'Scheduled', Gift], ['snapshots', 'Snapshots', Users], ['badges', 'Badges', Award], ['fees', 'Fees & Pricing', ShieldCheck], ['bugs', `Bugs${sec?.stats?.openBugs ? ` (${sec.stats.openBugs})` : ''}`, Bug]];
  return <div className="cc-shell" data-testid="command-center">
    <header className="cc-head"><div><h2 className="trenches-font live-gradient-text">Command Center</h2><small>👑 {shortAddress(address)} · session signed · live</small></div>
      <nav className="cc-tabs">{TABS.map(([id, label, Icon]) => <button key={id} type="button" className={tab === id ? 'active' : ''} onClick={() => setTab(id)}><Icon size={14} />{label}</button>)}</nav>
      <button type="button" className="cc-close" onClick={onClose} aria-label="Close command center"><X size={16} /></button></header>

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
    {tab === 'fees' && <FeesPanel call={call} />}
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
