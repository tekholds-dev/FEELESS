import { VaultDesigner } from './VaultDesigner';
import { FuseBuilder } from './FuseBuilder';
import { BundlePricing } from './FuseAdminSettings';
import { BotShield } from './BotShield';
import { FuseCardMint } from '../nft/FuseCardMint';
import { FuseLab } from '../FuseLab';
import { FuseHQ } from '../FuseHQ';
import { FuseDeck, VaultMath } from '../FuseDeck';
import { RunnersPanel } from '../RunnersPanel';
import { QuestEngineAdmin } from './QuestEngineAdmin';
import { LatencyPanel } from './LatencyPanel';
import { useWallet } from '../../hooks/useWallet';
import { PoolCreator } from './PoolCreator';
import { LaunchRailAdmin } from './LaunchRailAdmin';
import { CircleWallets } from './CircleWallets';
import { UnitInput, TradePreview, useSolUsd, money, LiveMoney, FeeTable } from './FeeInputs';
import { MarketingPanel } from './MarketingPanel';
import React, { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { ShieldCheck, Users, Gift, Award, Bug, RefreshCw, Download, X, Activity, BarChart3, Wallet, Megaphone, Search } from 'lucide-react';
import { apiUrl, errorText } from '../../lib/api';
import { shortAddress, formatUSD } from '../../lib/dexscreener';
import { AirdropStudio, Snapshots } from './AirdropStudio';
import { NumbersPanel } from './NumbersPanel';
import { SeasonEditor } from '../SeasonEditor';
import { Explain } from '../Explain';
import { DEXES } from '../../lib/venues';
import { BadgePools } from './BadgePools';
import { LagCatcher } from './LagCatcher';
import { TreasuryHub } from './TreasuryHub';
import { CoinVerifyPanel } from './CoinVerifyPanel';
import { TreasuryPulse } from './TreasuryPulse';
import { TAB_INFO } from './ccTabInfo';
import { FeeBrain } from './FeeBrain';
import { MoneyFlows } from './MoneyFlows';
import { CirclePay, useCircleWallet } from './CirclePay';
import { CardStudio } from '../cards/CardStudio';
import { IntelDesk } from './IntelDesk';
import { FeeBook } from './FeeBook';
import { useMoneyPulse, refreshPulse } from '../../lib/moneyPulse';
const NftStudio = lazy(() => import('../nft/NftStudio').then(m => ({ default: m.NftStudio })));

const SESSION_KEY = 'feeless:cc-session';
const readSession = addr => { try { const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); return s && s.address === addr && Date.now() / 1000 - s.ts < 86000 ? s : null; } catch { return null; } };

const csv = rows => rows.map(r => r.map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
const download = (name, text) => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: 'text/csv' })); a.download = name; a.click(); URL.revokeObjectURL(a.href); };

// Bug finder triage: critical (security) → bugs → ideas; open work before closed; newest first.
const SEVERITY = { security: [0, '🔴 Critical · security'], bug: [1, '🟠 Bug'], idea: [2, '🔵 Idea'] };
const sortBugs = list => [...list].sort((a, b) => ((SEVERITY[a.kind]?.[0] ?? 1) - (SEVERITY[b.kind]?.[0] ?? 1))
  || ((['fixed', 'wontfix'].includes(a.status) ? 1 : 0) - (['fixed', 'wontfix'].includes(b.status) ? 1 : 0)) || (b.at - a.at));

export function CommandCenter({ address, signMessage, onClose }) {
  const [session, setSession] = useState(() => readSession(address));
  const [tab, setTab] = useState('numbers');
  const [moneyView, setMoneyView] = useState('treasury');
  // Old tab ids (treasury, circle, reserve) and header shortcuts all land in the one Money tab, on the right section.
  const openTab = (t, pre) => { setPrefill(pre || null); if (['treasury', 'circle', 'reserve'].includes(t)) { setMoneyView(t); setTab('money'); } else setTab(t); };
  const [prefill, setPrefill] = useState(null);
  const [sec, setSec] = useState(null);
  const [holders, setHolders] = useState(null);
  const [asset, setAsset] = useState('fee');
  const [selected, setSelected] = useState(() => new Set());
  const [hidePools, setHidePools] = useState(true);
  const [drops, setDrops] = useState([]);
  const [bugs, setBugs] = useState([]);
  const [busy, setBusy] = useState(false);
  const [isOwner, setIsOwner] = useState(false);
  useEffect(() => { fetch(apiUrl(`/api/reputation/admin/is-admin/${address}`)).then(r => r.json()).then(d => setIsOwner(!!d.owner)).catch(() => {}); }, [address]);

  const call = useCallback(async (path, opts = {}) => {
    const res = await fetch(apiUrl(`/api/reputation${path}`), { ...opts, headers: { 'Content-Type': 'application/json', 'x-admin-address': address, 'x-admin-ts': String(session?.ts || ''), 'x-admin-sig': session?.sig || '', ...(opts.headers || {}) } });
    const body = await res.json().catch(() => ({}));
    if (res.status === 401) { localStorage.removeItem(SESSION_KEY); setSession(null); toast.error(body.detail ? errorText(body, 401) : 'Command center session ended — sign in again.'); }
    if (!res.ok) throw new Error(errorText(body, res.status));
    return body;
  }, [address, session]);

  const signIn = async () => {
    setBusy(true);
    try {
      const ts = Math.floor(Date.now() / 1000);
      const sig = await signMessage(`FEELESS command center\naddress:${address}\nts:${ts}`);
      const s = { address, ts, sig };
      // Check the signature before opening the panels, so a bad signature shows its reason instead of looping back here.
      const res = await fetch(apiUrl('/api/reputation/admin/security'), { headers: { 'x-admin-address': address, 'x-admin-ts': String(ts), 'x-admin-sig': sig } });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail || `Sign-in rejected (${res.status}).`); }
      localStorage.setItem(SESSION_KEY, JSON.stringify(s)); setSession(s);
    } catch (e) { toast.error(e.code === 4001 ? 'Signature declined.' : e.message || 'Sign-in failed.'); } finally { setBusy(false); }
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

  // Grouped so the money + infra controls are always first; every tab id appears exactly once.
  const TAB_GROUPS = [['Core', ['launch', 'fees', 'money', 'latency']], ['Growth', ['numbers', 'traffic', 'pulse', 'marketing', 'kols', 'invites', 'ads', 'ideas']],
    ['Community', ['holders', 'studio', 'airdrops', 'snapshots', 'badges', 'nfts', 'seasons', 'pools', 'fuse', 'feecat', 'broadcast']], ['Safety', ['investigate', 'shield', 'verify', 'overview', 'mod', 'access', 'bugs']]];
  const TABS = [['investigate', 'Intel desk', Search], ['verify', 'Verify coins', ShieldCheck], ['launch', 'Launch & setup', ShieldCheck], ['latency', 'Lag catcher', Activity], ['numbers', 'Numbers', BarChart3], ['pulse', 'Pulse', Activity], ['overview', 'Security', ShieldCheck], ['shield', '🛡 Bot shield', ShieldCheck], ['mod', 'Moderation', Bug], ['broadcast', 'Broadcast', Gift], ['money', 'Money', Wallet], ['marketing', 'Marketing', Megaphone], ['holders', 'Holders', Users], ['studio', 'Airdrop Studio', Gift], ['airdrops', 'Scheduled', Gift], ['snapshots', 'Snapshots', Users], ['badges', 'Badges', Award], ['fuse', '⚛️ Fuse', Award], ['nfts', 'NFTs', Gift], ['feecat', 'Fee 🐱', Award], ['pools', 'Pools', Gift], ['fees', 'Trading & fees', ShieldCheck], ['ads', 'Ads', Gift], ['seasons', 'Seasons', Award], ['access', 'Access', ShieldCheck], ['ideas', 'Ideas', Gift], ['traffic', 'Traffic', Activity], ['kols', 'KOLs', Users], ['invites', 'Invites', Users], ['bugs', `Bugs${sec?.stats?.openBugs ? ` (${sec.stats.openBugs})` : ''}`, Bug]];
  return <div className="cc-shell" data-testid="command-center">
    <header className="cc-head"><div><h2 className="trenches-font live-gradient-text">Command Center</h2><small>👑 {shortAddress(address)} · session signed · live</small></div><TreasuryPulse call={call} onOpen={openTab} />
      <nav className="cc-tabs" data-testid="cc-nav">{TAB_GROUPS.map(([group, ids]) => <div key={group} className="cc-tab-group"><small>{group}</small>{ids.map(id => TABS.find(t => t[0] === id)).filter(Boolean).map(([id, label, Icon]) => <button key={id} type="button" className={tab === id ? 'active' : ''} onClick={() => setTab(id)}><Icon size={14} />{label}</button>)}</div>)}</nav>
      <button type="button" className="cc-close" onClick={onClose} aria-label="Close command center"><X size={16} /></button></header>
    {TAB_INFO[tab] && <div className="cc-tab-hero" key={tab} data-testid="cc-tab-hero"><div><small>{TAB_GROUPS.find(g => g[1].includes(tab))?.[0]?.toUpperCase()}</small><h3>{TAB_INFO[tab][0]}</h3><p>{TAB_INFO[tab][1]}</p></div>{TAB_INFO[tab][2].length > 0 && <div className="cc-tab-does">{TAB_INFO[tab][2].map(x => <span key={x}>{x}</span>)}</div>}</div>}

    {tab === 'launch' && <LaunchRailAdmin call={call} isOwner={isOwner} />}
    {tab === 'verify' && <CoinVerifyPanel call={call} />}
    {tab === 'latency' && <><LagCatcher call={call} /><LatencyPanel call={call} /></>}
    {tab === 'numbers' && <NumbersPanel call={call} />}
    {tab === 'kols' && <KolAdmin call={call} />}
    {tab === 'traffic' && <TrafficPanel call={call} />}
    {tab === 'seasons' && <SeasonsAdmin call={call} />}
    {tab === 'access' && <AccessAdmin call={call} />}
    {tab === 'shield' && <BotShield call={call} />}
    {tab === 'ideas' && <IdeasAdmin call={call} />}
    {tab === 'pulse' && <PulsePanel call={call} />}
    {tab === 'mod' && <ModPanel call={call} />}
    {tab === 'broadcast' && <BroadcastPanel call={call} />}
    {tab === 'marketing' && <MarketingPanel call={call} />}
    {tab === 'money' && <section className="m-stack" data-testid="cc-money">
      <div className="m-seg" role="tablist" aria-label="Money">{[['treasury', '🏦 Treasury & splits'], ['reserve', '💰 Reserve & badge pools'], ['circle', '◎ Circle wallets']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={moneyView === k} className={moneyView === k ? 'active' : ''} onClick={() => setMoneyView(k)}>{l}</button>)}</div>
      {moneyView === 'treasury' && <><TreasuryHub call={call} prefill={prefill} /><TreasuryRoutes call={call} isOwner={isOwner} /></>}
      {moneyView === 'reserve' && <><ReservePool call={call} /><BadgePools call={call} /></>}
      {moneyView === 'circle' && (isOwner ? <CircleWallets call={call} /> : <p className="cc-empty">Only owner wallets can manage Circle wallets.</p>)}
    </section>}
    {tab === 'overview' && <Overview sec={sec} reload={loadSec} />}
    {tab === 'investigate' && <IntelDesk call={call} />}
    {tab === 'nfts' && (isOwner ? <Suspense fallback={<p className="cc-empty">Opening the studio…</p>}><FuseCardMint call={call} /><NftStudio call={call} /></Suspense> : <p className="cc-empty">Only owner wallets can create and drop NFT collections.</p>)}
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
    {tab === 'fuse' && <FuseDeck call={call} panels={[
      ['runners', '🏃 Runners', <RunnersPanel call={call} />, 'Coins come to it: every Pump.fun coin gated, scored and laned (scalp / runner / hold) as it arrives; rounds every 15 min; lights only when paper-proven.'],
      ['lab', '🧬 Breed & fuse', <FuseLab call={call} />, 'Build mega cards: up to 12 legs (pools, runners or any mix), load a champion, preview it, one-click it with no FEELESS fee, publish it or stage it on the Arena.'],
      ['hq', '💰 HQ · P&L', <FuseHQ call={call} />, 'Real money: every verified Fuse in, live. Arena = $5 runs that prove a strategy before you trust it.'],
      ['pub', '📣 Published', <FuseBuilder call={call} />, 'Fuses traders see on Trade and in chat (/fuse). Set the creator cut; self-buys and bots never earn it.'],
      ['vault', '🏦 Vault', <><VaultMath /><VaultDesigner call={call} /></>, 'Design only: a future on-chain vault (SOL in → shares, fees in SOL). Localnet v0.1 — never deployed or funded without you.']]} />}{tab === 'badges' && <><QuestEngineAdmin call={call} /><AwardBadges call={call} initial={[...selected]} /></>}
    {tab === 'feecat' && <FeeCatPanel call={call} />}
    {tab === 'pools' && <PoolsPanel call={call} />}
    {tab === 'fees' && <><MoneyFlows /><FeesPanel call={call} /><FeeBook call={call} /></>}
    {tab === 'ads' && <AdsPanel call={call} />}
    {tab === 'invites' && <InvitesPanel call={call} />}
    {tab === 'bugs' && <section className="cc-panel">{!bugs.length ? <p className="cc-empty">No reports yet. Anyone can file one from a profile's “Report a bug” button.</p>
      : <div className="cc-bugs">{sortBugs(bugs).map(b => <div key={b.id} className={`cc-bug k-${b.kind} s-${b.status}`}><div><em className={`sev sev-${SEVERITY[b.kind]?.[0] ?? 1}`}>{SEVERITY[b.kind]?.[1] || b.kind}</em><b>{b.text}</b><small>{b.page || '—'} · {new Date(b.at * 1000).toLocaleString()}{b.address ? ` · ${shortAddress(b.address)}` : ''}</small></div>
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
    <div className="cc-block cc-wide cc-audit-log"><h4>Audit log</h4>{!sec.audit.length ? <small className="cc-empty">No admin actions yet.</small> : sec.audit.map((a, i) => <div key={i} className="cc-audit"><small>{new Date(a.at * 1000).toLocaleString()}</small><b>{a.action}</b><span>{a.detail}</span></div>)}</div>
  </section>;
}

function Airdrops({ drops, call, reload }) {
  const [sigs, setSigs] = useState({});
  const { wallet, provider, connect } = useWallet() || {};
  const [sending, setSending] = useState({});
  const [top3, setTop3] = useState({ amount: '', asset: 'fee' });
  // Send the whole drop from the connected wallet, then record every signature (server re-verifies each).
  const sendNow = async d => {
    try {
      if (!wallet?.address || wallet.chain !== 'solana' || !provider?.signTransaction) { await connect?.('solana'); return; }
      const assets = (await (await fetch('/api/market/assets')).json()).assets || [];
      const mint = d.asset === 'sol' ? null : assets.find(a => a.id === d.asset)?.mint;
      if (d.asset !== 'sol' && !mint) throw new Error(`No mint known for ${d.asset.toUpperCase()}.`);
      const { batchSend } = await import('../../lib/batchSend');
      const txs = await batchSend({ provider, owner: wallet.address, mint, recipients: d.recipients, onStatus: m => setSending(x => ({ ...x, [d.id]: m })) });
      for (const sig of txs) await call(`/admin/airdrops/${d.id}`, { method: 'POST', body: JSON.stringify({ status: 'sent', txSig: sig }) });
      toast.success(`Sent in ${txs.length} transaction${txs.length > 1 ? 's' : ''} — receipts recorded.`); reload();
    } catch (e) { toast.error(e.message || 'Send failed'); } finally { setSending(x => ({ ...x, [d.id]: '' })); }
  };
  // Season reward: draft a drop to the current top 3 (review, then send from your wallet).
  const draftTop3 = async () => {
    try {
      const amt = Number(top3.amount); if (!(amt > 0)) throw new Error('Enter an amount per winner.');
      const top = ((await (await fetch('/api/reputation/season')).json()).top || []).slice(0, 3).filter(r => !r.address.startsWith('0x'));
      if (!top.length) throw new Error('No season players yet.');
      await call('/admin/airdrops', { method: 'POST', body: JSON.stringify({ name: `Season top ${top.length} reward`, asset: top3.asset, recipients: top.map(r => ({ address: r.address, amount: amt })), scheduledAt: Date.now() / 1000, note: 'Season leaderboard reward' }) });
      toast.success('Drafted — review below, then Send from wallet.'); reload();
    } catch (e) { toast.error(e.message); }
  };
  const mark = async (d, status) => {
    try { await call(`/admin/airdrops/${d.id}`, { method: 'POST', body: JSON.stringify({ status, txSig: sigs[d.id]?.trim() || null }) }); toast.success(status === 'sent' ? 'Verified on-chain — recipients got the 🪂 badge.' : `Marked ${status}.`); reload(); }
    catch (e) { toast.error(e.message); }
  };
  return <section className="cc-panel">
    <p className="cc-note">FEELESS never holds your keys. <b>Send from wallet</b> packs the transfers into a few transactions, dry-runs them, and your wallet approves them in one prompt; every signature is verified on-chain and kept as a receipt. You can still send elsewhere and paste the signature.</p>
    <div className="cc-block cc-top3"><h4>Season top-3 reward / holder fee-share</h4><div className="cc-toolbar"><input inputMode="decimal" placeholder="Amount per winner" value={top3.amount} onChange={e => setTop3(t => ({ ...t, amount: e.target.value.replace(/[^0-9.]/g, '') }))} /><select value={top3.asset} onChange={e => setTop3(t => ({ ...t, asset: e.target.value }))}>{['fee', 'sol', 'feecat', 'rfee'].map(a => <option key={a} value={a}>{a.toUpperCase()}</option>)}</select><button type="button" className="btn-primary" onClick={draftTop3}>Draft top-3 drop</button></div><small className="cc-empty">For a holder fee-share, pick holders on the Holders tab and schedule with SOL — then Send from wallet here.</small></div>
    {!drops.length ? <p className="cc-empty">No airdrops yet. Select holders on the Holders tab to schedule one.</p> : drops.map(d => { const due = d.scheduledAt * 1000 <= Date.now() && d.status === 'scheduled';
      return <div key={d.id} className={`cc-drop s-${d.status} ${due ? 'due' : ''}`}>
        <div className="cc-drop-top"><b>🪂 {d.name}</b><em>{due ? 'DUE NOW' : d.status}</em><small>{new Date(d.scheduledAt * 1000).toLocaleString()} · {d.recipients.length} wallets · {d.total.toLocaleString(undefined, { maximumFractionDigits: 4 })} {d.asset.toUpperCase()}</small></div>
        <div className="cc-drop-actions">
          <button type="button" onClick={() => download(`${d.name}.csv`, csv([['address', 'amount'], ...d.recipients.map(r => [r.address, r.amount])]))}><Download size={13} />CSV</button>
          {d.status === 'scheduled' && <button type="button" className="btn-primary" disabled={!!sending[d.id]} onClick={() => sendNow(d)}>{sending[d.id] || 'Send from wallet'}</button>}{d.status === 'scheduled' && <><input placeholder="Paste tx signature after sending" value={sigs[d.id] || ''} onChange={e => setSigs(s => ({ ...s, [d.id]: e.target.value }))} /><button type="button" className="btn-primary" onClick={() => mark(d, 'sent')}>Verify & mark sent</button><button type="button" onClick={() => mark(d, 'cancelled')}>Cancel</button></>}
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
  const [limits, setLimits] = useState({ profile: 3, chat: 3 });
  const [awards, setAwards] = useState({ rows: [], wallets: 0, awards: 0 });
  const [view, setView] = useState(initial.length ? 'award' : 'cards');
  const loadAwards = useCallback(() => call('/admin/badges').then(setAwards).catch(e => toast.error(e.message)), [call]);
  useEffect(() => { call('/admin/badges/limits').then(setLimits).catch(e => toast.error(e.message)); loadAwards(); }, [call, loadAwards]);
  const addrs = text.split(/[\s,]+/).filter(a => /^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$/.test(a));
  const award = async () => {
    try { const r = await call('/admin/badges', { method: 'POST', body: JSON.stringify({ addresses: addrs, label, icon, tone, why }) }); toast.success(`Awarded ${label} to ${r.awarded} wallet(s).`); setLabel(''); setWhy(''); loadAwards(); }
    catch (e) { toast.error(e.message); }
  };
  const saveLimits = async () => {
    try { setLimits(await call('/admin/badges/limits', { method: 'PUT', body: JSON.stringify({ profile: Number(limits.profile), chat: Number(limits.chat) }) })); toast.success('Badge limits saved and enforced site-wide.'); }
    catch (e) { toast.error(e.message); }
  };
  const revoke = async (address, bid) => { try { await call(`/admin/badges/${address}/${bid}`, { method: 'DELETE' }); toast.success('Badge revoked.'); loadAwards(); } catch (e) { toast.error(e.message); } };
  return <section className="cc-panel cc-award cc-badges-meta" data-testid="cc-badges">
    <div className="bdg-hero"><div><small>BADGE ENGINE</small><h3>Earned, displayed, <em>paid</em>.</h3><p>Season tiers earn a cut of the Fee Reserve. Custom awards flex on profiles and in chat.</p></div>
      <div className="bdg-kpis"><span><small>Wallets badged</small><b>{awards.wallets}</b></span><span><small>Awards</small><b>{awards.awards}</b></span><span><small>Profile / chat cap</small><b>{limits.profile} / {limits.chat}</b></span></div></div>
    <div className="bdg-seg" role="tablist">{[['cards', '🃏 Cards'], ['award', '🎖️ Award'], ['ledger', '📜 Ledger'], ['caps', '⚙ Caps']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={view === k} className={view === k ? 'active' : ''} onClick={() => setView(k)}>{l}</button>)}</div>
    {view === 'cards' && <CardStudio call={call} />}
    {view === 'caps' && <>
    <div className="cc-block"><h4>Badge mechanics</h4><p className="cc-note">Awards are earned inventory. The profile and chat caps only control how many a user may display; they do not delete awards. Only Command Center can issue or revoke them.</p><div className="cc-studio-grid"><label>Profile display cap<input type="number" min="0" max="12" value={limits.profile} onChange={e => setLimits(x => ({ ...x, profile: e.target.value }))} /></label><label>Chat display cap<input type="number" min="0" max="12" value={limits.chat} onChange={e => setLimits(x => ({ ...x, chat: e.target.value }))} /></label></div><button type="button" className="btn-primary" onClick={saveLimits}>Save display caps</button></div>
    </>}
    {view === 'award' && <div className="bdg-award">
    <div className="cc-award-preview"><span className={`badge-pill tone-${tone}`}>{icon} {label || 'Badge name'}</span><small>{why || 'Why they earned it'}</small></div>
    <div className="cc-award-form">
      <div className="cc-icons">{['⭐', '💎', '🔥', '🏆', '🧠', '🐞', '🛠️', '🎖️', '🦾', '🌙'].map(i => <button key={i} type="button" className={icon === i ? 'active' : ''} onClick={() => setIcon(i)}>{i}</button>)}</div>
      <input placeholder="Badge name (e.g. Bug Hunter)" maxLength={32} value={label} onChange={e => setLabel(e.target.value)} />
      <input placeholder="Why (shown on hover)" maxLength={140} value={why} onChange={e => setWhy(e.target.value)} />
      <div className="cc-icons">{['gold', 'mint', 'plain', 'bad'].map(t => <button key={t} type="button" className={`tone-${t} ${tone === t ? 'active' : ''}`} onClick={() => setTone(t)}>{t}</button>)}</div>
      <textarea rows={6} placeholder="Wallet addresses — one per line (select holders first to prefill)" value={text} onChange={e => setText(e.target.value)} />
      <button type="button" className="btn-primary" disabled={!addrs.length || label.length < 2} onClick={award}><Award size={14} />Award to {addrs.length} wallet{addrs.length === 1 ? '' : 's'}</button>
    </div>
    </div>}
    {view === 'ledger' && <>
    <div className="cc-block cc-badge-ledger"><h4>Issued badge ledger</h4>{!awards.rows.length ? <p className="cc-empty">No custom badges issued yet.</p> : awards.rows.map(row => <div className="cc-badge-wallet" key={row.address}><code>{shortAddress(row.address)}</code><div>{row.badges.map(b => <span key={b.id} className={`badge-pill tone-${b.tone}`} title={b.why}><i>{b.icon}</i>{b.label}<button type="button" aria-label={`Revoke ${b.label}`} onClick={() => revoke(row.address, b.id)}>×</button></span>)}</div></div>)}</div>
    </>}
  </section>;
}

const TIER_ICON = { Legend: '👑', Diamond: '💎', Gold: '🥇', Silver: '🥈', Bronze: '🥉' };

// Season badges earn a weighted cut of the Fee Reserve wallet. The reserve wallet signs the payout itself (no custody).
export function ReservePool({ call }) {
  const { wallet, provider, connect } = useWallet() || {};
  const px = useSolUsd();
  const [seasons, setSeasons] = useState([]);
  const [sid, setSid] = useState('');
  const [plan, setPlan] = useState(null);
  const [form, setForm] = useState({ reserveWallet: '', badgeRewardPct: '' });
  const [busy, setBusy] = useState('');
  useEffect(() => { call('/admin/seasons').then(d => { const list = [...(d.seasons || [])].sort((a, b) => b.start - a.start); setSeasons(list); const now = Date.now() / 1000; setSid((list.find(s => s.start <= now && now < s.end) || list[0])?.id || ''); }).catch(e => toast.error(e.message)); }, [call]);
  // Plans come from the shared money pulse; the direct call is only for seasons the pulse doesn't carry (no reserve wallet yet).
  const pulse = useMoneyPulse(call).data;
  const pulsed = pulse?.reserves?.[sid];
  const load = useCallback(() => { if (sid) call(`/admin/reserve/${sid}`).then(setPlan).catch(e => toast.error(e.message)); }, [call, sid]);
  const reload = () => { refreshPulse(true); load(); };
  useEffect(() => { setPlan(null); if (!pulsed) load(); }, [sid]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (pulsed) setPlan(pulsed); }, [pulsed]);
  useEffect(() => { if (plan?.season?.id === sid) setForm({ reserveWallet: plan.season.reserveWallet || '', badgeRewardPct: String(plan.season.badgeRewardPct || '') }); }, [sid, plan?.season?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const usd = v => (px && v != null ? money(v * px) : '');
  const save = async () => {
    try { setBusy('Saving…'); await call(`/admin/seasons/${sid}`, { method: 'PUT', body: JSON.stringify({ reserveWallet: form.reserveWallet.trim(), badgeRewardPct: Number(form.badgeRewardPct) || 0 }) }); toast.success('Reserve pool saved.'); reload(); }
    catch (e) { toast.error(errorText(e)); } finally { setBusy(''); }
  };
  const isReserve = wallet?.chain === 'solana' && wallet?.address === plan?.season.reserveWallet;
  const circleW = useCircleWallet(call, plan?.season.reserveWallet);
  const pay = async () => {
    try {
      if (!isReserve) { await connect?.('solana'); return; }
      const { batchSend } = await import('../../lib/batchSend');
      const sigs = await batchSend({ provider, owner: wallet.address, recipients: plan.rows.map(r => ({ address: r.address, amount: r.sol })), kind: 'reserve', onStatus: setBusy });
      await call(`/admin/reserve/${sid}/paid`, { method: 'POST', body: JSON.stringify({ sigs }) });
      toast.success(`Paid ${plan.paidSol} SOL to ${plan.rows.length} badge holders.`); reload();
    } catch (e) { toast.error(errorText(e)); } finally { setBusy(''); }
  };
  if (!seasons.length) return <div className="cc-block"><p className="cc-empty">Create a season first (Seasons tab). Its badges then earn from the reserve pool.</p></div>;
  return <div className="bdg-pool m-stack">
    <div className="m-seg">{seasons.slice(0, 5).map(s => <button key={s.id} type="button" className={sid === s.id ? 'active' : ''} onClick={() => setSid(s.id)}>{s.name}</button>)}</div>
    <div className="m-grid">
      <div className="m-card m-stack"><div className="m-row"><span className="m-label">RESERVE WALLET</span>{plan?.assigned ? <span className="m-chip ok">● assigned</span> : <span className="m-chip warn">● not assigned</span>}</div>
        {circleW && <span className="m-chip ok" data-testid="reserve-circle">◎ Circle wallet “{circleW.name || 'Circle'}” · {circleW.balances?.find(b => b.symbol === 'SOL')?.amount ?? 0} SOL · pays via Circle</span>}
        <label className="m-field"><span>Wallet (Solana address)</span><input className="m-input" placeholder="Fee Reserve wallet" value={form.reserveWallet} onChange={e => setForm(f => ({ ...f, reserveWallet: e.target.value }))} /></label>
        <label className="m-field"><span>% of the wallet to badge holders</span><input className="m-input" style={{ maxWidth: 110 }} inputMode="decimal" placeholder="0" value={form.badgeRewardPct} onChange={e => setForm(f => ({ ...f, badgeRewardPct: e.target.value.replace(/[^0-9.]/g, '') }))} /></label>
        <button type="button" className="m-btn primary" disabled={!!busy} onClick={save}>Save pool</button></div>
      <div className="m-card is-hot m-stat"><span className="m-label">POT THIS SEASON</span><b className="m-num">{plan ? `${plan.potSol} SOL` : '…'}</b><span className="m-dim">{plan && usd(plan.potSol)}</span>
        <span className="m-dim">{plan ? `${plan.pct}% of ${plan.poolSol} SOL${plan.balanceKnown ? '' : ' (balance unreadable)'}` : ''}</span><span className="m-dim">0.01 SOL always stays for rent + fees</span>
        {plan && plan.assigned && !plan.poolSol && <div className="m-note warn"><b>Why 0?</b>The reserve wallet holds no SOL yet. Send SOL to it (fees, or your own wallet) and the pot fills at {plan.pct}% of whatever it holds.</div>}</div>
      <div className="m-card m-stack"><span className="m-label">TIER WEIGHTS</span><div className="m-row">{Object.entries(plan?.weights || {}).filter(([, w]) => w).map(([t, w]) => <span key={t} className="m-chip ok">{TIER_ICON[t]} {t} {w}×</span>)}</div><span className="m-dim">Recruit, blocklisted and FEELESS wallets earn nothing.</span></div>
    </div>
    {plan?.payout ? <div className="bdg-paid">✅ {plan.payout.via === 'circle' ? 'Sent' : 'Paid'} {plan.payout.rows.reduce((a, r) => a + r.sol, 0).toFixed(4)} SOL to {plan.payout.rows.length} wallets · {plan.payout.via === 'circle' ? 'via Circle' : <a href={`https://solscan.io/tx/${plan.payout.sigs[0]}`} target="_blank" rel="noopener noreferrer">receipt</a>}
        {plan.payout.failed?.length > 0 && <><span className="bdg-warn"> · {plan.payout.failed.length} failed</span><CirclePay call={call} circle={circleW} rows={plan.payout.failed} path={`/admin/reserve/${sid}/pay-circle`} onDone={reload} label={`Retry ${plan.payout.failed.length} via Circle`} /></>}</div>
      : <div className="m-card m-row cs-bar"><span className="m-dim">{plan ? `${plan.rows.length} wallets · ${plan.paidSol} SOL${plan.droppedDust ? ` · ${plan.droppedDust} dust shares re-split` : ''}` : 'Loading…'}</span>
        {circleW ? <CirclePay call={call} circle={circleW} rows={plan?.rows || []} path={`/admin/reserve/${sid}/pay-circle`} onDone={reload} label={`Pay ${plan?.paidSol ?? ''} SOL via Circle`} /> : <button type="button" className="btn-primary" disabled={!!busy || !plan?.rows.length} title={plan?.ended ? '' : 'Season still live: shares will move until it ends'} onClick={pay}>{busy || (isReserve ? `Pay out ${plan?.paidSol ?? ''} SOL` : 'Connect the reserve wallet to pay')}</button>}</div>}
    <div className="bdg-table">{!plan?.rows.length ? <p className="cc-empty">{plan && !plan.pct ? 'Set a % to start paying badge holders.' : 'No tiered badge holders yet.'}</p> : plan.rows.slice(0, 60).map((r, i) => <div key={r.address} className="bdg-row"><i>#{i + 1}</i><span className={`bdg-tier t-${r.tier.toLowerCase()}`}>{TIER_ICON[r.tier]} {r.tier}</span><code>{shortAddress(r.address)}</code><small>{r.sharePct}%</small><b>{r.sol} SOL</b><em>{usd(r.sol)}</em></div>)}</div>
  </div>;
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
  const [test, setTest] = useState(null);
  const [testBusy, setTestBusy] = useState(false);
  const runTest = useCallback(async () => { setTestBusy(true); try { setTest(await call('/admin/fees/selftest')); } catch (e) { toast.error(e.message); } finally { setTestBusy(false); } }, [call]);
  useEffect(() => { runTest(); }, [runTest]);
  const [health, setHealth] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [savedCfg, setSavedCfg] = useState(null);   // what the server holds (status chips compare against it)
  const [routes, setRoutes] = useState([]);
  const [earnings, setEarnings] = useState(null);
  const [earningsBusy, setEarningsBusy] = useState(false);
  const [limits, setLimits] = useState({ minBps: 0, maxBps: 2000, ultraMaxBps: 255, priorityMaxLamports: 5000000 });
  const [promoDays, setPromoDays] = useState(0);
  useEffect(() => {
    call('/admin/fees/health').then(setHealth).catch(() => setHealth(null));
    call('/admin/fees').then(d => { setCfg(d.fees); setSavedCfg(d.fees); setLimits(d.limits); }).catch(e => toast.error(e.message));
    call('/admin/treasury/routes').then(d => setRoutes(d.routes || [])).catch(() => {});
  }, [call]);
  const solUsd = useSolUsd();
  if (!cfg) return <p className="cc-empty">Loading fee settings…</p>;
  const set = (k, v) => setCfg(c => ({ ...c, [k]: v }));
  const loadEarnings = async () => { setEarningsBusy(true); try { setEarnings(await call('/admin/fees/balances')); } catch (e) { toast.error(e.message); } finally { setEarningsBusy(false); } };
  const save = async (override) => {
    const cur = override && override.platformFeeBps !== undefined ? override : cfg;
    const body = { ...cur, platformFeeBps: Math.min(Number(cur.platformFeeBps) || 0, limits.maxBps), priorityMaxLamports: Number(cur.priorityMaxLamports) || 0, ultraFallback: Boolean(cur.ultraFallback), engine: cur.engine || 'swap',
      feeAccountSol: (cur.feeAccountSol || '').trim(), feeAccountUsdc: (cur.feeAccountUsdc || '').trim(), lifiFeeBps: Number(cur.lifiFeeBps) || 0, lifiIntegrator: cur.lifiIntegrator || '', vaultFeeWallet: (cur.vaultFeeWallet || '').trim(), zeroFeeMints: [],
      promo: { ...(cur.promo || {}), until: promoDays > 0 ? Date.now() / 1000 + promoDays * 86400 : cur.promo?.until || 0 } };
    try { const d = await call('/admin/fees', { method: 'POST', body: JSON.stringify(body) }); setCfg(d.fees); setSavedCfg(d.fees); toast.success('Fee settings saved — applied to the next quote.'); } catch (e) { toast.error(e.message); }
  };
  const TIERS = ['Trencher', 'Fee Friend', 'Fee Insider', 'Fee Whale'];
  const enabled = Number(cfg.platformFeeBps) > 0;
  const engine = cfg.engine || 'swap';
  const feeAcct = Boolean(cfg.feeAccountSol || cfg.feeAccountUsdc);
  const pct = v => `${((Number(v) || 0) / 100).toFixed(2)}%`;
  const status = [['Engine', engine === 'swap' ? 'Swap API' : 'Ultra', true], ['Ultra fallback', cfg.ultraFallback ? 'On' : 'Off', true],
    ['Fee', enabled ? pct(cfg.platformFeeBps) : 'Off', enabled], ['Fee account', engine === 'swap' ? (feeAcct ? 'Set' : 'Missing') : (cfg.referralAccount ? 'Referral set' : 'Missing'), engine === 'swap' ? feeAcct : Boolean(cfg.referralAccount)],
    ['Health', health ? (health.ok ? 'Collecting' : 'Not collecting') : 'Checking…', Boolean(health?.ok)]];
  return <section className="cc-panel cc-fees" data-testid="fees-panel">
    <LiveMoney call={call} solUsd={solUsd} />
    <div className="cc-status-strip" data-testid="fee-status">{status.map(([k, v, ok]) => <span key={k} className={ok ? 'ok' : 'bad'}><small>{k}</small><b>{v}</b></span>)}</div>
    {health && !health.ok && <div className="fee-health bad" data-testid="fee-health"><b>⚠ Fees are NOT being collected</b><span>{health.problem}</span>{health.fix && <small><b>Fix:</b> {health.fix}</small>}</div>}

    <div className="cc-block cc-rules" data-testid="fee-rules"><h4>Fee rules</h4><ul>
      <li><b>Every Solana trade pays {enabled ? pct(cfg.platformFeeBps) : 'the platform fee'}</b>, collected in SOL or USDC.</li>
      <li><b>Only exemption:</b> buying $FEE, FEECAT or rFEE with SOL, USDC or USDT is 0%. Selling them pays the fee.</li>
      <li><b>Coin → coin</b> trades have no SOL/USDC side to pay from, so they are refused: traders route coin → SOL → coin.</li>
      <li><b>Holder tiers and promos</b> lower the fee (max 90% off). They never make a trade free.</li>
      <li><b>Cards bought all at once</b> (Fuse / runners) pay the bundle price per coin (section 6). Cmd Ctr cards pay no FEELESS fee.</li>
      <li><b>EVM swaps, bridges and gas</b> pay the LI.FI fee below.</li></ul></div>

    <div className="cc-studio-grid">
      <div className="cc-block cc-engine" data-testid="trading-engine"><h4>1 · Trading engine</h4>
        <div className="cc-seg">{[['swap', 'Swap API · your fee'], ['ultra', 'Ultra only · 0.5–2.55%']].map(([id, label]) => <button key={id} type="button" className={engine === id ? 'active' : ''} onClick={() => set('engine', id)}>{label}</button>)}</div>
        <label className="cc-check"><input type="checkbox" checked={Boolean(cfg.ultraFallback)} disabled={engine === 'ultra'} onChange={e => set('ultraFallback', e.target.checked)} />Ultra fallback when the Swap API fails (fee capped at 2.55% on those trades). Off = trading pauses.</label>
        <FeeAccountMaker onDone={(a, created) => { const next = { ...cfg, feeAccountSol: a.sol, feeAccountUsdc: a.usdc }; setCfg(next); if (created) save(next); }} />
        <label>SOL fee account (wSOL token account)<input placeholder="Token account for So111…112 owned by your treasury" value={cfg.feeAccountSol || ''} onChange={e => set('feeAccountSol', e.target.value.trim())} /></label>
        <label>USDC fee account (optional)<input placeholder="Token account for USDC owned by your treasury" value={cfg.feeAccountUsdc || ''} onChange={e => set('feeAccountUsdc', e.target.value.trim())} /></label>
        <label>Speed tip per trade (lamports)<UnitInput min="0" max={limits.priorityMaxLamports} value={cfg.priorityMaxLamports ?? 200000} onChange={e => set('priorityMaxLamports', e.target.value)} suffix={[`= ${((Number(cfg.priorityMaxLamports ?? 200000) || 0) / 1e9).toFixed(6)} SOL`, solUsd && `= ${money(((Number(cfg.priorityMaxLamports ?? 200000) || 0) / 1e9) * solUsd)}`]} /></label>
        {Number(cfg.priorityMaxLamports) > limits.priorityMaxLamports
          ? <small className="cc-empty fee-over-cap">Too high: the max is {limits.priorityMaxLamports.toLocaleString('en-US')} ({(limits.priorityMaxLamports / 1e9).toFixed(3)} SOL). Saving will use that.</small>
          : <small className="cc-empty"><b>Paid by your traders, not to you.</b> A tip to Solana validators so swaps land faster in busy moments. Higher = faster, but pricier for traders. <b>200,000</b> (0.0002 SOL, about 3¢) is a good default; 1,000,000 for launch rushes.</small>}
      </div>
      <div className="cc-block"><h4>2 · Platform fee</h4>
        <label>Your cut of every trade (100 = 1% · max {Number(limits.maxBps).toLocaleString('en-US')} = {pct(limits.maxBps)})<UnitInput min="0" max={limits.maxBps} value={cfg.platformFeeBps} onChange={e => set('platformFeeBps', e.target.value)} suffix={[`= ${pct(cfg.platformFeeBps)}`, `= ${money((Number(cfg.platformFeeBps) || 0) / 100)} / $100`]} /></label>
        {Number(cfg.platformFeeBps) > limits.maxBps
          ? <small className="cc-empty fee-over-cap">Max is {pct(limits.maxBps)}. Saving will use {pct(limits.maxBps)}.</small>
          : <small className="cc-empty">{enabled ? `${pct(cfg.platformFeeBps)} per trade${engine === 'ultra' || cfg.ultraFallback ? ` · Ultra trades: ${pct(Math.min(Math.max(Number(cfg.platformFeeBps), limits.ultraMinBps || 50), limits.ultraMaxBps || 255))}` : ''}` : 'Fee off: every trade is free until you set one.'}</small>}
        <FeeTable feeBps={cfg.platformFeeBps} discounts={cfg.tierDiscountPct} />
        <TradePreview feeBps={cfg.platformFeeBps} tipLamports={cfg.priorityMaxLamports ?? 200000} solUsd={solUsd} />
        <h5>$FEE holder discounts (% off)</h5>
        <div className="cc-mini-grid">{TIERS.map((t, i) => <label key={t}>{t}<UnitInput min="0" max="90" value={cfg.tierDiscountPct?.[String(i)] ?? 0} onChange={e => set('tierDiscountPct', { ...cfg.tierDiscountPct, [String(i)]: Number(e.target.value) })} suffix="% off" /></label>)}</div>
        <h5>Promo</h5>
        <div className="cc-mini-grid"><label>Label<input value={cfg.promo?.label || ''} onChange={e => set('promo', { ...cfg.promo, label: e.target.value })} placeholder="Launch week" /></label>
          <label>% off<UnitInput min="0" max="90" value={cfg.promo?.discountPct || 0} onChange={e => set('promo', { ...cfg.promo, discountPct: Number(e.target.value) })} suffix="% off" /></label>
          <label>Days<UnitInput min="0" value={promoDays} onChange={e => setPromoDays(Number(e.target.value))} suffix="days" /></label></div>
        {cfg.promo?.until > Date.now() / 1000 && <small className="cc-empty">Promo live until {new Date(cfg.promo.until * 1000).toLocaleString()}</small>}
      </div>
      <div className="cc-block"><h4>3 · Ultra fallback (Jupiter referral)</h4>
        <label>Jupiter referral account<input placeholder="Create at referral.jup.ag, paste the account" value={cfg.referralAccount} onChange={e => set('referralAccount', e.target.value.trim())} /></label>
        <small className="cc-empty">Only used when Ultra is the engine or the fallback is on. Fees collect in the referral account's vaults; claim them at referral.jup.ag with the authority wallet.</small>
        <div className="cc-toolbar"><button type="button" className="btn-outline" onClick={loadEarnings} disabled={earningsBusy || !cfg.referralAccount}><RefreshCw size={13} />{earningsBusy ? 'Reading chain…' : 'Referral balances'}</button><a className="btn-outline" href="https://referral.jup.ag/" target="_blank" rel="noopener noreferrer">Claim ↗</a></div>
        {earnings?.accounts?.length > 0 && <ul className="fee-checks">{earnings.accounts.map(a => <li key={a.tokenAccount || a.mint} className="ok"><b>◎</b><span>{a.symbol || a.mint?.slice(0, 4)}</span><small>{a.amount ?? a.uiAmount}</small></li>)}</ul>}
      </div>
      <div className="cc-block fee-lifi"><h4>4 · EVM swaps &amp; bridges (LI.FI)</h4>
        <label>LI.FI integrator name<input placeholder="as registered at portal.li.fi" value={cfg.lifiIntegrator || ''} onChange={e => set('lifiIntegrator', e.target.value.trim())} /></label>
        <label>LI.FI fee (basis points)<UnitInput min="0" max="300" value={cfg.lifiFeeBps || 0} onChange={e => set('lifiFeeBps', e.target.value)} suffix={`= ${pct(cfg.lifiFeeBps)}`} /></label>
        <small className="cc-empty">{Number(cfg.lifiFeeBps) && cfg.lifiIntegrator ? `${pct(cfg.lifiFeeBps)} on EVM swaps, bridges and gas (LI.FI adds its own 0.25%).` : 'Register at portal.li.fi and set a fee to charge EVM routes.'}</small>
      </div>
      <div className="cc-block fee-vault"><h4>5 · FUSE Vault fees</h4>
        <label>Vault fee wallet<input placeholder="SOL wallet that receives vault management + performance fees" value={cfg.vaultFeeWallet || ''} onChange={e => set('vaultFeeWallet', e.target.value.trim())} data-testid="vault-fee-wallet" /></label>
        <VaultWalletStatus value={cfg.vaultFeeWallet} saved={savedCfg?.vaultFeeWallet} /></div>
      <BundlePricing call={call} initial={cfg.bundle} swapBps={Number(cfg.platformFeeBps) || 0} />
    </div>

    <div className="cc-block fee-selftest" data-testid="fee-selftest"><h4>5 · Prove it <Explain>Runs real quotes through the same endpoints the swap boxes use. Nothing is signed or sent. A pass means FEELESS is paid on real trades.</Explain></h4>
      <div className="cc-toolbar"><button type="button" className="btn-outline" onClick={runTest} disabled={testBusy}><RefreshCw size={13} className={testBusy ? 'spin' : ''} />{testBusy ? 'Testing live quotes…' : 'Run fee self-test'}</button>{test?.at && <small className="cc-empty">Last run {new Date(test.at * 1000).toLocaleTimeString()}</small>}{health?.ok && <small className="cc-empty">✓ {health.note}</small>}</div>
      {test && <ul className="fee-checks">{test.checks.map(c => <li key={c.label} className={c.ok ? 'ok' : 'bad'}><b>{c.ok ? '✓' : '✗'}</b><span>{c.label}</span><small>{c.detail}</small></li>)}
        {(test.lifiChecks || []).map(c => <li key={c.label} className={c.skipped ? 'skip' : c.ok ? 'ok' : 'bad'}><b>{c.skipped ? '–' : c.ok ? '✓' : '✗'}</b><span>LI.FI · {c.label}</span><small>{c.detail}</small></li>)}</ul>}
    </div>
    <div className="cc-savebar"><span>{routes.length || 0} treasury route{routes.length === 1 ? '' : 's'} saved</span><button type="button" className="btn-primary" onClick={save} data-testid="fees-save">Save trading &amp; fees</button></div>
  </section>;
}

// Vault fee wallet status: saved ✓ / unsaved edit / not a Solana address / missing.
export const vaultStatus = (v, saved) => (!v ? ['bad', 'Not set — vault fees have nowhere to go'] : !/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(v) ? ['bad', 'Not a Solana address']
  : v === saved ? ['ok', `✓ Saved · vault fees land in ${v.slice(0, 4)}…${v.slice(-4)}`] : ['warn', 'Not saved yet — press Save below']);
function VaultWalletStatus({ value, saved }) {
  const [tone, text] = vaultStatus(value, saved);
  return <small className={`vault-status is-${tone}`} data-testid="vault-status">{text}</small>;
}

// One-click fee accounts: the connected wallet pays ~0.004 SOL rent and signs once; the accounts belong to the fee wallet.
function FeeAccountMaker({ onDone }) {
  const { wallet, provider } = useWallet() || {};
  const [owner, setOwner] = useState('');
  const [status, setStatus] = useState('');
  const feeWallet = owner.trim() || wallet?.address || '';
  const run = async () => {
    if (wallet?.chain !== 'solana' || !provider?.signTransaction) { toast.error('Connect your Solana wallet (Phantom) first.'); return; }
    try {
      const { createFeeAccounts } = await import('../../lib/feeAccounts');
      const out = await createFeeAccounts({ provider, payer: wallet.address, owner: feeWallet, onStatus: setStatus });
      onDone(out, true); setStatus('');
    } catch (e) { setStatus(''); toast.error(e.code === 4001 ? 'Declined in wallet. Nothing was created.' : e.message); }
  };
  return <div className="fee-maker" data-testid="fee-account-maker">
    <label>Fee wallet (receives the fees)<input placeholder={wallet?.address ? `${wallet.address.slice(0, 6)}… (connected wallet)` : 'Your fee wallet address'} value={owner} onChange={e => setOwner(e.target.value.trim())} /></label>
    <div className="cc-toolbar"><button type="button" className="btn-primary" onClick={run} disabled={Boolean(status) || !feeWallet}>{status || 'Create fee accounts in Phantom'}</button>
      <button type="button" className="btn-outline" disabled={!feeWallet} onClick={async () => { try { const { findFeeAccounts } = await import('../../lib/feeAccounts'); onDone(await findFeeAccounts(feeWallet), false); toast.success('Fee accounts filled in (no transaction). Press Save.'); } catch { toast.error('That is not a valid Solana address.'); } }}>Already created? Find them (free)</button></div>
    <small className="cc-empty">Creates the wSOL + USDC fee accounts for that wallet in one approval (~0.004 SOL rent, paid by the connected wallet). Safe to repeat.</small>
  </div>;
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
  const [pct, setPct] = useState('');
  const load = useCallback(() => call('/admin/referrals').then(x => { setD(x); setPct(String(x.pct ?? 0)); }).catch(e => toast.error(e.message)), [call]);
  useEffect(() => { load(); fetch('/api/reputation/site').then(r => r.json()).then(x => setUrl(x.publicUrl || '')).catch(() => {}); }, [load]);
  const saveUrl = () => call('/admin/site', { method: 'POST', body: JSON.stringify({ publicUrl: url }) }).then(r => toast.success(`Invite links use ${url}${r.webhook?.ok ? ' · Helius webhook connected' : r.webhook?.reason ? ` · webhook: ${r.webhook.reason}` : ''}`)).catch(e => toast.error(e.message));
  const savePct = () => call('/admin/referrals/config', { method: 'PUT', body: JSON.stringify({ pct: Number(pct) || 0 }) }).then(r => { toast.success(`Every inviter now earns ${r.pct}% of their invitees' FEELESS fees.`); load(); }).catch(e => toast.error(errorText(e)));
  if (!d) return <p className="cc-empty">Loading invites…</p>;
  const usd = v => `$${Number(v || 0).toFixed(Number(v) >= 1 ? 2 : 4)}`;
  return <section className="cc-panel m-stack" data-testid="cc-invites">
    <div className="m-grid">
      <div className="m-card is-hot m-stack"><span className="m-label">INVITE REWARD · ALL USERS</span>
        <span className="m-dim">Every inviter earns this share of the FEELESS fees their invitees pay, on every confirmed trade. It accrues on their profile; you pay it out.</span>
        <div className="m-row"><input className="m-input" style={{ width: 100 }} inputMode="decimal" value={pct} onChange={e => setPct(e.target.value.replace(/[^0-9.]/g, ''))} aria-label="Invite reward percent" /><span className="m-dim">% of invitee fees (max 50)</span>
          <button type="button" className="m-btn primary" disabled={Number(pct) > 50 || String(d.pct) === pct} onClick={savePct}>Save</button></div></div>
      <div className="m-card m-stack"><span className="m-label">PUBLIC SITE DOMAIN <em>used in every invite link</em></span>
        <div className="m-row"><input className="m-input" style={{ flex: 1 }} placeholder="https://your-domain.com" value={url} onChange={e => setUrl(e.target.value)} /><button type="button" className="m-btn primary" onClick={saveUrl}>Save</button></div>
        <small className="m-dim">Links look like {url || 'https://your-domain.com'}/r/b26hhajg — one per wallet.</small></div>
      <div className="m-card m-grid"><div className="m-stat"><small>Wallets invited</small><b className="m-num">{d.total}</b></div><div className="m-stat"><small>Active inviters</small><b className="m-num">{d.top.length}</b></div><div className="m-stat"><small>Rewards owed</small><b className="m-num m-pos">{usd(d.owedUsd)}</b></div></div>
    </div>
    <div className="m-card"><span className="m-label">TOP INVITERS</span>{!d.top.length ? <p className="m-dim">No invites yet — every wallet has its link in its profile › Invites.</p>
      : <dl className="m-kv">{d.top.map((r, i) => <React.Fragment key={r.address}><dt>{i + 1}. <a href={`/terminal/profile/${r.address}`} target="_blank" rel="noopener noreferrer">@{r.handle}</a></dt><dd>{r.invited} invited · earned {usd(r.earnedUsd)}{r.earnedSol ? ` · ${r.earnedSol.toFixed(4)} SOL` : ''}</dd></React.Fragment>)}</dl>}</div>
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

const FEE_LABELS = {
  minLiquidity: ['Min liquidity ($)', 'Pool must hold at least this much, so she can always get out.'],
  minVolume24h: ['Min 24h volume ($)', 'Skip coins nobody is trading.'],
  minMarketCap: ['Min market cap ($)', 'Smallest coin she will touch.'],
  maxMarketCap: ['Max market cap ($)', 'Biggest coin she will touch.'],
  minAgeHours: ['Min pool age (h)', 'Let a coin prove itself for this long first (fresh-launch lane is separate, at half size).'],
  maxPositions: ['Max open coins', 'How many coins she can hold at once.'],
  maxTop10Pct: ['Max top-10 holders (%)', 'Skip coins where 10 wallets own more than this.'],
  maxSnipers: ['Max snipers', 'Skip coins sniped by more wallets than this at launch.'],
  maxBundled: ['Max bundled wallets', 'Skip coins with more bundled launch wallets than this.'],
  maxM5Chase: ['No chasing above (5m %)', 'Never buy a coin already up more than this in 5 minutes.'],
  add1At: ['First dip buy (%)', 'If price falls this far below her first buy and the thesis holds, she adds and lowers her average.'],
  add2At: ['Second dip buy (%)', 'Deeper dip, smaller add. Only if liquidity, volume and buyers still hold.'],
  hardStop: ['Hard stop (%)', 'Emergency exit this far below her average entry, no matter what.'],
  takeProfit1: ['First profit at (+%)', 'She sells part of the position here to lock in gains.'],
  takeProfit2: ['Second profit at (+%)', 'She sells more here; the rest keeps running.'],
  runnerTrail: ['Runner trailing stop (%)', 'After taking profit, sell the rest if it falls this far from its peak. It never sells below break-even.'],
  maxHoldHours: ['Max hold (h)', 'Give up on a coin that never reached a profit target after this long.'],
  maxExposure: ['Max capital at work (0–1)', 'Share of her balance allowed in open trades. 0.4 = 40%.'],
};
const FEE_PRESETS = {
  feecat: ['Trench Lord', 'Balanced: patient holds, two dip buys', { minLiquidity: 40000, minVolume24h: 100000, minMarketCap: 150000, minAgeHours: 3, maxPositions: 5, maxM5Chase: 8, add1At: -18, add2At: -32, hardStop: -45, takeProfit1: 50, takeProfit2: 120, runnerTrail: 35, maxHoldHours: 72, maxExposure: 0.4 }],
  trench: ['Trench', 'Earlier, smaller coins; wider dips', { minLiquidity: 25000, minVolume24h: 75000, minMarketCap: 75000, minAgeHours: 1, maxPositions: 5, maxM5Chase: 10, add1At: -22, add2At: -38, hardStop: -55, takeProfit1: 60, takeProfit2: 150, runnerTrail: 40, maxHoldHours: 48, maxExposure: 0.35 }],
  meme: ['Meme', 'Fresh narratives, let runners run', { minLiquidity: 15000, minVolume24h: 50000, minMarketCap: 50000, minAgeHours: 0.5, maxPositions: 4, maxM5Chase: 12, add1At: -25, add2At: -40, hardStop: -55, takeProfit1: 80, takeProfit2: 200, runnerTrail: 45, maxHoldHours: 48, maxExposure: 0.3 }],
  scalper: ['Trader / Scalper', 'Liquid coins, quick profits', { minLiquidity: 150000, minVolume24h: 500000, minMarketCap: 500000, minAgeHours: 1, maxPositions: 3, maxM5Chase: 6, add1At: -10, add2At: -18, hardStop: -25, takeProfit1: 20, takeProfit2: 50, runnerTrail: 15, maxHoldHours: 12, maxExposure: 0.5 }],
};
function FeeCatPanel({ call }) {
  const [d, setD] = useState(null);
  const [draft, setDraft] = useState({});
  const [size, setSize] = useState('');
  const [preset, setPreset] = useState('feecat');
  const [loadErr, setLoadErr] = useState('');
  const load = useCallback(() => { setLoadErr(''); return call('/admin/feecat').then(x => { setD(x); setDraft(x.rules); setSize(x.leader?.risk?.maxPositionSol ?? ''); setPreset(x.strategyPreset || 'feecat'); }).catch(e => { setLoadErr(e.message || 'Fee service did not answer.'); }); }, [call]);
  useEffect(() => { load(); }, [load]);
  if (!d) return <p className="cc-empty">{loadErr ? <>Couldn't load Fee: {loadErr} <button type="button" className="btn-outline" onClick={load}>Retry</button></> : 'Waking Fee up…'}</p>;
  const save = extra => call('/admin/feecat', { method: 'POST', body: JSON.stringify({ rules: draft, maxPositionSol: Number(size) || undefined, ...extra }) }).then(() => { toast.success(extra.action === 'run' ? 'Fee completed an intelligence cycle.' : 'Fee updated — applies on the next tick.'); load(); }).catch(e => toast.error(e.message));
  const running = d.leader?.status === 'running';
  const choosePreset = id => { setPreset(id); setDraft(current => ({ ...current, ...FEE_PRESETS[id][2] })); };
  const lastCycle = d.cat.lastTick ? Math.max(0, Math.round(Date.now() / 1000 - d.cat.lastTick)) : null;
  return <section className="cc-panel">
    <div className="cc-kpis cc-kpis-5"><span><small>Engine</small><b className={running && lastCycle != null && lastCycle < 90 ? 'positive' : 'negative'}>{running ? (lastCycle == null ? 'Starting' : `${lastCycle}s ago`) : 'Paused'}</b></span><span><small>Open</small><b>{d.cat.positions?.length || 0}</b></span><span><small>Balance</small><b>{Number(d.cat.balanceSol || 0).toFixed(2)} SOL</b></span><span><small>Realized</small><b>{Number(d.cat.realizedPnlSol || 0).toFixed(3)}</b></span><span><small>Win rate</small><b>{d.cat.winRate ?? '—'}%</b></span></div>
    <div className="cc-toolbar"><button type="button" className="btn-primary" onClick={() => save({ status: running ? 'paused' : 'running' })}>{running ? '⏸ Pause Fee' : '▶ Resume Fee'}</button><button type="button" disabled={!running} onClick={() => save({ action: 'run' })}>⚡ Run intelligence cycle</button><button type="button" onClick={() => window.confirm('Reset what Fee has learned? Exits go back to defaults.') && save({ resetLearning: true })}>Reset learning</button><a href="/terminal/feecat" target="_blank" rel="noopener noreferrer">Open Fee's profile ↗</a></div>
    <p className="cc-note">Tune Fee's brain. Every value is clamped to a safe range on the server — Fee can get more aggressive, never reckless. Changes are logged in the audit trail.</p>
    <FeeBrain />
    <div className="cc-block"><h4>How Fee trades <Explain>Fee is a paper agent: her balance and P/L are simulated, but every price, liquidity and market-cap number is read live. She cannot sign, spend or move real SOL. Every entry and exit pays a 1% fee each way so the results are honest.</Explain></h4>
      <ol className="fee-howto">
        <li><b>Pick.</b> Only coins that pass the entry and safety rules below: enough liquidity and volume, buyers in control, clean holders, not already vertical.</li>
        <li><b>Start small.</b> She buys a {Math.round((d.rules?.starterFraction ?? 0.5) * 100)}% starter of her planned size, and keeps at most {Math.round((draft.maxExposure ?? 0.4) * 100)}% of her balance in open trades.</li>
        <li><b>Buy the dip, with a plan.</b> If price drops {draft.add1At ?? -18}% (then {draft.add2At ?? -32}%) below her first buy <i>and</i> liquidity, volume and buyers still hold, she adds and lowers her average entry. Example: bought at $100K MC, adds at $80K, average entry ≈ $90K.</li>
        <li><b>Hold while the reason holds.</b> No knee-jerk stop. She exits early only if the thesis breaks: liquidity pulled, sellers dumping, or volume dying while she's red. Emergency stop at {draft.hardStop ?? -45}% from her average.</li>
        <li><b>Take profit in pieces.</b> Sells part at +{draft.takeProfit1 ?? 50}% and more at +{draft.takeProfit2 ?? 120}%. The rest rides with a {draft.runnerTrail ?? 35}% trailing stop that never sells below break-even.</li>
      </ol></div>
    <div className="cc-block"><h4>Trading style</h4><div className="fee-presets">{Object.entries(FEE_PRESETS).map(([id, [name, note]]) => <button type="button" key={id} className={preset === id ? 'active' : ''} onClick={() => choosePreset(id)}><b>{name}</b><small>{note}</small></button>)}</div><p className="cc-note">Picking a style fills the rules below. Nothing changes until you press Save.</p></div>
    <div className="cc-block"><h4>Rules</h4><div className="fee-rules">{Object.keys(d.bounds).map(k => { const [lo, hi] = d.bounds[k]; return <label key={k}><span>{FEE_LABELS[k]?.[0] || k}<em>{lo}–{hi}</em></span>{FEE_LABELS[k]?.[1] && <small className="fee-rule-help">{FEE_LABELS[k][1]}</small>}<input type="number" step="any" min={lo} max={hi} value={draft[k] ?? ''} onChange={e => setDraft(x => ({ ...x, [k]: e.target.value }))} /></label>; })}
      <label><span>Max SOL per trade<em>0.1–10</em></span><input type="number" step="0.1" value={size} onChange={e => setSize(e.target.value)} /></label></div>
      <button type="button" className="btn-primary" onClick={() => save({ strategyPreset: preset })}>Save {FEE_PRESETS[preset][0]} brain</button></div>
    {d.learning && <div className="cc-block"><h4>What Fee has learned <Explain>After every exit Fee watches the coin for 6 hours. If it kept running, she gives winners more room next time; if her exit was right, she drifts back to the defaults. Always within safe limits.</Explain></h4>{Object.entries(d.learning.params || {}).map(([key, v]) => <div key={key} className="cc-sig"><span>{({ runnerTrail: 'Runner trailing stop', takeProfit1: 'First profit target' })[key] || key}</span><b>{v}% <small className="cc-empty">(default {d.learning.defaults?.[key]}%)</small></b></div>)}</div>}
    <div className="cc-block"><h4>Recent paper audit</h4>{d.events?.length ? d.events.map(e => <div key={e.id} className="cc-sig"><span>{e.type} · {e.catName}</span><b>{e.type === 'SELL' ? `entry MC ${e.entryMarketCapUsd ? formatUSD(e.entryMarketCapUsd) : '—'} → exit ${e.marketCapUsd ? formatUSD(e.marketCapUsd) : '—'}` : e.marketCapUsd ? `entry MC ${formatUSD(e.marketCapUsd)}` : 'snapshot unavailable'}</b></div>) : <p className="cc-empty">No paper trade receipts yet.</p>}</div>
  </section>;
}

function PoolsPanel({ call }) {
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
    <div className="cc-toolbar"><select value={asset} onChange={e => setAsset(e.target.value)}>{Object.keys(mints).map(k => <option key={k} value={k}>{k.toUpperCase()}</option>)}</select>{mint && <><code className="pool-mint">{mint}</code><button type="button" onClick={() => copy(mint)}>Copy mint</button><button type="button" onClick={() => copy('So11111111111111111111111111111111111111112')}>Copy SOL mint</button></>}</div>
    <details className="tr-explain" open><summary>🔒 What does "lock" actually lock? (read this first)</summary>
      <ul><li><b>A pool can never be deleted by anyone</b> — once it exists on-chain, anyone can trade it or add to it. Locking is about <b>your deposit</b> (your liquidity position), not the pool.</li>
        <li><b>Locked forever:</b> you can never pull your tokens + SOL back out, but that position keeps earning swap fees and you can claim them anytime. Holders can verify it → rug-proof badge.</li>
        <li><b>Not locked:</b> you keep full control — withdraw your deposit whenever you want, plus the fees. Holders see it can be pulled, so no rug-proof badge and less trust.</li>
        <li><b>A pool can't peg the price.</b> Price is just the ratio of the two piles; buyers and sellers move it. To turn fees into price support: <b>buy back</b> the coin with fees (raises price), then burn or lock what you bought. That's the Buy &amp; burn setup, fed from Treasury › Split now.</li></ul></details>
    <details className="tr-explain"><summary>🌊 Which coins need a pool from here?</summary>
      <ul><li><b>Coins launched on a FEELESS config</b> get their pool automatically when the curve graduates (liquidity locked per the config). Don't make one yourself before that — it splits liquidity and gets arbitraged.</li>
        <li><b>Tokens that already exist</b> (e.g. $FEE) — create the TOKEN/SOL pool here. You deposit both sides; the ratio is the opening price.</li>
        <li><b>Your fee reserve coin:</b> use a separate Phantom account (Add account — same recovery phrase, new address) or a Squads multisig as the reserve wallet. Launch the coin from that wallet on a house config, or create its pool from that wallet here. That wallet owns the position and earns its fees; badge pools can pay holders from it.</li>
        <li><b>Platform swapping uses your pools automatically.</b> FEELESS trades route through Jupiter, which indexes Meteora pools within minutes — so a pool you create here becomes a route for every swap of that coin on the site (and everywhere else Jupiter is used). Deeper pool = better prices for your traders.</li>
        <li>One pool per token/SOL pair on this rail. Everything is simulated before you sign.</li></ul></details>
    <PoolCreator defaultMint={mint || ''} call={call} />
    <h4 className="cc-sub">Other DEXes (external, their own pool pages)</h4>
    <div className="cc-studio-grid">{DEXES.map(x => <div key={x.id} className="cc-block"><h4>{x.name}</h4><small className="cc-empty">{x.note}</small><a className="btn-primary" href={x.url} target="_blank" rel="noopener noreferrer">Create on {x.name.split(' ')[0]} ↗</a></div>)}</div>
    <div className="cc-block"><h4>Verify a new pool</h4><div className="cc-toolbar"><input placeholder="Paste the new pool / pair address" value={check} onChange={e => setCheck(e.target.value)} /><button type="button" className="btn-primary" onClick={verify}>Verify</button></div>
      {found === false && <small className="cc-empty">Not indexed yet — DexScreener usually picks up new pools within a few minutes.</small>}
      {found && <div className="cc-sig"><span>✅ {found.baseToken.symbol}/{found.quoteToken.symbol} on {found.dexId}</span><b>{formatUSD(found.liquidity?.usd)} liq</b></div>}</div>
    <div className="cc-block"><h4>Live pools for {asset.toUpperCase()}</h4>{!pools.length ? <small className="cc-empty">No pools indexed.</small> : pools.map(p => <div key={p.pairAddress} className="cc-sig"><a href={`/terminal/chat?chain=solana&pair=${p.pairAddress}&room=bulls`} target="_blank" rel="noopener noreferrer">{p.baseToken.symbol}/{p.quoteToken.symbol} · {p.dexId}</a><span>vol {formatUSD(p.volume?.h24)}</span><b>{formatUSD(p.liquidity?.usd)}</b></div>)}</div>
  </section>;
}

// Admins mark real KOL wallets; FEELESS tracks their actual trades and flags call-and-dump patterns.
function KolAdmin({ call }) {
  const [rows, setRows] = useState([]); const [f, setF] = useState({ address: '', name: '', x: '', chain: 'solana' });
  const load = () => fetch(apiUrl('/api/reputation/kols')).then(r => r.json()).then(d => setRows(d.kols || [])).catch(() => {});
  useEffect(() => { load(); }, []);
  const add = async e => { e.preventDefault(); try { await call('/admin/kols', { method: 'POST', body: JSON.stringify(f) }); toast.success('KOL added — trades load in a few seconds.'); setF({ address: '', name: '', x: '', chain: 'solana' }); load(); } catch (err) { toast.error(err.message); } };
  const remove = async a => { try { await call(`/admin/kols/${a}`, { method: 'DELETE' }); load(); } catch (err) { toast.error(err.message); } };
  return <section className="cc-card"><h3>KOL tracker</h3><p className="wp-bio">Add wallets you know belong to KOLs. FEELESS reads their real Solana trades and shows users hold times, quick-flip rate and call-and-dump flags on the Rep page.</p>
    <form className="cc-kol-form" onSubmit={add}><input required placeholder="Wallet address" value={f.address} onChange={e => setF({ ...f, address: e.target.value.trim() })} /><input required placeholder="Name" value={f.name} onChange={e => setF({ ...f, name: e.target.value })} /><input placeholder="X handle" value={f.x} onChange={e => setF({ ...f, x: e.target.value })} /><button className="btn-primary" type="submit">Track</button></form>
    <div className="cc-kol-list">{rows.map(k => <div key={k.address}><b>{k.name}</b><small>{k.x ? `@${k.x} · ` : ''}{k.chain} · {shortAddress(k.address)}</small><span>{k.stats ? `${k.stats.closed} closed · flips ${k.stats.quickFlipPct ?? '—'}% · ${k.stats.danger ? '⚠ call-and-dump' : 'no dump pattern'}` : '…'}</span><button type="button" className="btn-outline" onClick={() => remove(k.address)}>Remove</button></div>)}</div>
  </section>;
}

// Marketing view: what people actually look at, from privacy-light page-view counts.
function TrafficPanel({ call }) {
  const [d, setD] = useState(null);
  useEffect(() => { call('/admin/traffic').then(setD).catch(e => toast.error(e.message)); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (!d) return <p className="wp-bio">Loading traffic…</p>;
  const maxDay = Math.max(1, ...d.daily.map(x => x.views)); const maxHr = Math.max(1, ...d.hours);
  const list = (rows, k, v) => rows.length ? rows.map(r => <div key={r[k]} className="tr-row"><span>{r[k]}</span><b>{r[v].toLocaleString()}</b></div>) : <p className="wp-bio">No data yet.</p>;
  return <section className="cc-card tr">
    <h3>Traffic <small>no raw IPs stored · uniques are daily salted hashes</small></h3>
    <div className="tr-days">{d.daily.map(x => <div key={x.day} title={`${x.day}: ${x.views} views, ${x.uniques} visitors`}><i style={{ height: `${(x.views / maxDay) * 100}%` }} /><small>{x.day.slice(5)}</small></div>)}</div>
    <div className="tr-grid">
      <div><h4>Top pages · 24h</h4>{list(d.topPages24h, 'page', 'views')}</div>
      <div><h4>Top pages · 7d</h4>{list(d.topPages7d, 'page', 'views')}</div>
      <div><h4>Most-viewed coins</h4>{list(d.topCoins.map(c => ({ ...c, pair: shortAddress(c.pair) })), 'pair', 'views')}</div>
      <div><h4>Referrers</h4>{list(d.referrers, 'host', 'visits')}</div>
      <div><h4>Most-clicked in chat</h4>{list(d.topClicks.map(c => ({ ...c, label: `${c.kind}: ${c.value}` })), 'label', 'count')}</div>
      <div><h4>Busiest hours (UTC)</h4><div className="tr-hours">{d.hours.map((n, h) => <i key={h} title={`${h}:00 — ${n}`} style={{ opacity: 0.15 + (n / maxHr) * 0.85 }} />)}</div></div>
    </div>
  </section>;
}

// Monthly seasons: create the next one in two clicks (defaults to next calendar month).
function SeasonsAdmin({ call }) {
  const [d, setD] = useState(null);
  const [editing, setEditing] = useState(null);
  const next = () => { const n = new Date(); const s = new Date(Date.UTC(n.getUTCFullYear(), n.getUTCMonth() + 1, 1)); const e = new Date(Date.UTC(n.getUTCFullYear(), n.getUTCMonth() + 2, 1)); return { start: s.toISOString().slice(0, 10), end: e.toISOString().slice(0, 10) }; };
  const [f, setF] = useState({ name: '', theme: '', prize: '', multiplier: 1, accent: '#f5c542', ...next() });
  const load = () => call('/admin/seasons').then(setD).catch(e => toast.error(e.message));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async e => { e.preventDefault(); try { await call('/admin/seasons', { method: 'POST', body: JSON.stringify({ ...f, multiplier: Number(f.multiplier), start: Date.parse(f.start) / 1000, end: Date.parse(f.end) / 1000 }) }); toast.success('Season scheduled.'); load(); } catch (err) { toast.error(err.message); } };
  const set = k => e => setF({ ...f, [k]: e.target.value });
  return <section className="cc-card"><h3>Monthly seasons</h3>
    <div className="cc-kol-list">{(d?.seasons || []).map(s => <div key={s.id} style={{ borderLeft: `3px solid ${s.accent}` }}><b>{s.name}</b><small>{new Date(s.start * 1000).toLocaleDateString()} → {new Date(s.end * 1000).toLocaleDateString()} · {s.multiplier}×</small><span>{d.players[s.id] || 0} players</span><button type="button" className="btn-outline" onClick={() => setEditing(s)}>Edit</button></div>)}</div>
    {editing && <SeasonEditor season={editing} call={call} onDone={() => { setEditing(null); load(); }} />}
    <form className="cc-kol-form" onSubmit={save}><input required placeholder="Season name (e.g. Diamond Hands)" value={f.name} onChange={set('name')} /><input placeholder="Theme / story" value={f.theme} onChange={set('theme')} /><input placeholder="Prize" value={f.prize} onChange={set('prize')} />
      <input type="date" value={f.start} onChange={set('start')} /><input type="date" value={f.end} onChange={set('end')} /><input type="number" step="0.5" min="0.5" max="5" value={f.multiplier} onChange={set('multiplier')} title="Points multiplier" /><input type="color" value={f.accent} onChange={set('accent')} title="Season color" /><button className="btn-primary" type="submit">Schedule season</button></form>
  </section>;
}

// Command center access: only the owner wallet can grant or revoke.
function AccessAdmin({ call }) {
  const [d, setD] = useState(null); const [f, setF] = useState({ address: '', role: 'moderator' });
  const load = () => call('/admin/roles').then(setD).catch(e => toast.error(e.message));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const grant = async e => { e.preventDefault(); try { await call('/admin/roles', { method: 'POST', body: JSON.stringify(f) }); toast.success('Access granted.'); setF({ address: '', role: 'moderator' }); load(); } catch (err) { toast.error(err.message); } };
  const revoke = async a => { try { await call(`/admin/roles/${a}`, { method: 'DELETE' }); load(); } catch (err) { toast.error(err.message); } };
  if (!d) return <p className="wp-bio">Loading access…</p>;
  return <section className="cc-card"><h3>Command center access</h3><p className="wp-bio">Owner: {d.owners.map(shortAddress).join(', ')}. {d.youAreOwner ? 'You can grant and revoke.' : 'Only the owner can change access.'}</p>
    {d.youAreOwner && <form className="cc-kol-form" onSubmit={grant}><input required placeholder="Wallet address" value={f.address} onChange={e => setF({ ...f, address: e.target.value.trim() })} /><select value={f.role} onChange={e => setF({ ...f, role: e.target.value })}>{d.roles.map(r => <option key={r}>{r}</option>)}</select><button className="btn-primary" type="submit">Grant</button></form>}
    <div className="cc-kol-list">{Object.entries(d.grants).map(([a, g]) => <div key={a}><b>{shortAddress(a)}</b><small>{g.role}</small><span>since {new Date(g.at * 1000).toLocaleDateString()}</span>{d.youAreOwner && <button type="button" className="btn-outline" onClick={() => revoke(a)}>Revoke</button>}</div>)}{!Object.keys(d.grants).length && <p className="wp-bio">No one else has access yet.</p>}</div>
  </section>;
}

function IdeasAdmin({ call }) {
  const [rows, setRows] = useState([]); const [f, setF] = useState({ title: '', body: '' });
  const load = () => call('/admin/ideas').then(d => setRows(d.ideas || [])).catch(e => toast.error(e.message));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const add = async e => { e.preventDefault(); try { await call('/admin/ideas', { method: 'POST', body: JSON.stringify(f) }); setF({ title: '', body: '' }); load(); } catch (err) { toast.error(err.message); } };
  return <section className="cc-card"><h3>Ideas board</h3>
    <form className="cc-kol-form" onSubmit={add}><input required placeholder="Idea" value={f.title} onChange={e => setF({ ...f, title: e.target.value })} /><input placeholder="Details" value={f.body} onChange={e => setF({ ...f, body: e.target.value })} /><button className="btn-primary" type="submit">Save idea</button></form>
    <div className="cc-ideas">{rows.map(i => <article key={i.id}><b>{i.title}</b><small>{i.status}</small><p>{i.body}</p></article>)}</div>
  </section>;
}


// Where fee earnings go. Addresses only — FEELESS never creates, stores or sees private keys.
// Tip: point the main route at a multisig (Squads on Solana, Safe on Base) so no single key can drain it.
function TreasuryRoutes({ call, isOwner }) {
  const [rows, setRows] = useState([]);
  useEffect(() => { call('/admin/treasury/routes').then(d => setRows(d.routes?.length ? d.routes : [{ label: 'Treasury (multisig)', address: '', pct: 100 }])).catch(() => {}); }, [call]);
  const total = rows.reduce((a, r) => a + Number(r.pct || 0), 0);
  const set = (i, k, v) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const save = async () => { try { await call('/admin/treasury/routes', { method: 'PUT', body: JSON.stringify({ routes: rows.map(r => ({ ...r, pct: Number(r.pct) })) }) }); toast.success('Treasury routing saved.'); } catch (e) { toast.error(e.message); } };
  return <section className="cc-card"><h3>Split plan</h3>
    <p className="wp-bio">Where fees go when you press <b>Split now</b> above. Each split is signed by you and verified on-chain; nothing moves on its own.</p>
    <p className="wp-bio">Record wallets you control — e.g. 60% treasury multisig, 25% buybacks, 15% team. FEELESS stores addresses only, never keys. Use a <a href="https://squads.so" target="_blank" rel="noopener noreferrer">Squads</a> (Solana) or <a href="https://app.safe.global" target="_blank" rel="noopener noreferrer">Safe</a> (Base) multisig for the main destination.</p>
    <div className="routes">{rows.map((r, i) => <div key={i} className="route-row"><input placeholder="Label" value={r.label} disabled={!isOwner} onChange={e => set(i, 'label', e.target.value)} /><input placeholder="Wallet address" value={r.address} disabled={!isOwner} onChange={e => set(i, 'address', e.target.value.trim())} /><input type="number" min="0" max="100" value={r.pct} disabled={!isOwner} onChange={e => set(i, 'pct', e.target.value)} /><span>%</span>{isOwner && <button type="button" className="btn-outline" onClick={() => setRows(rows.filter((_, j) => j !== i))}>×</button>}</div>)}</div>
    <div className="routes-foot"><span className={Math.abs(total - 100) < 0.01 ? 'ok' : 'bad'}>Total {total}%</span>{isOwner ? <><button type="button" className="btn-outline" onClick={() => setRows([...rows, { label: '', address: '', pct: 0 }])}>+ Add destination</button><button type="button" className="btn-primary" disabled={Math.abs(total - 100) > 0.01} onClick={save}>Save allocation plan</button></> : <small>Only the owner wallet can change this plan.</small>}</div>
  </section>;
}
