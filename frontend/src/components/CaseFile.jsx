import React, { useEffect, useState } from 'react';
import { Search, X } from 'lucide-react';
import { WatchButton } from './WatchButton';
import { VerifyReport } from './VerifyReport';
import { ShareGifButton } from './ShareGif';

// A case file as a shareable GIF: verdict, score and the top cited findings, readable at a glance.
const cut = (t, n = 58) => (t && t.length > n ? `${t.slice(0, n - 1)}…` : t || '');
const money = v => (!(Number(v) > 0) ? '—' : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);
const pct = v => (v == null ? '—' : `${Number(v).toFixed(Number(v) >= 10 ? 0 : 1)}%`);
// The share GIF for a case: coin image + $SYMBOL, the score, the verdict, and a stats panel with the facts behind it.
export const caseCard = (c, coin) => {
  const bad = ['suspect', 'high', 'danger'].includes(c.level);
  const ev = (c.evidence || []).filter(e => e.weight > 0).slice(0, 2).map(e => `• ${cut(e.claim, 40)}`);
  const sym = coin?.baseToken?.symbol; const isCoin = c.kind === 'coin';
  const a = c.authorities || {}; const h = c.holders || {}; const l = c.launch || {};
  const stats = isCoin ? [
    { label: 'Mint authority', value: a.mintAuthority ? 'LIVE ⚠' : 'revoked ✓', tone: a.mintAuthority ? 'bad' : 'ok' },
    { label: 'Freeze authority', value: a.freezeAuthority ? 'LIVE ⚠' : 'revoked ✓', tone: a.freezeAuthority ? 'bad' : 'ok' },
    { label: 'Top 10 hold', value: pct(h.top10Pct), tone: h.top10Pct > 40 ? 'bad' : h.top10Pct > 25 ? 'warn' : 'ok' },
    { label: 'Dev holds', value: pct(h.devHoldingPct), tone: h.devHoldingPct > 10 ? 'bad' : 'ok' },
    { label: 'Snipers · bundled', value: `${l.snipers ?? 0} · ${l.bundled ?? 0}`, tone: (l.snipers || 0) + (l.bundled || 0) > 5 ? 'warn' : 'ok' },
    { label: 'Liq · MC', value: `${money(coin?.liquidity?.usd)} · ${money(coin?.marketCap || coin?.fdv)}` },
  ] : [
    { label: 'Risk level', value: String(c.level || 'clean'), tone: bad ? 'bad' : 'ok' },
    { label: 'Launches', value: String((c.launches || []).length ?? 0) },
    { label: 'Linked wallets', value: String((c.linked || []).length ?? 0) },
    { label: 'Calls', value: c.caller ? `${c.caller.calls ?? 0} · ${Math.round((c.caller.hitRate || 0) * 100)}% hit` : '—' },
  ];
  const name = isCoin ? (sym ? `$${sym}${coin?.baseToken?.name ? ` · ${coin.baseToken.name}` : ''}` : (c.label || 'Coin case'))
    : (c.identity?.name || c.identity?.handle ? `${c.identity?.name || ''} ${c.identity?.handle ? `@${c.identity.handle}` : ''}` : (c.label || 'Case file'));
  return { kicker: `FEELESS CASE FILE · ${isCoin ? 'COIN' : 'WALLET'} · ${String(c.address || '').slice(0, 4)}…${String(c.address || '').slice(-4)}`,
    title: cut(name, 26), tone: bad ? 'down' : 'up', big: `${c.score ?? 0}/100`, stats,
    // Same-origin logo proxy first: third-party image hosts block canvas use, which would drop the coin from the GIF.
    imageUrl: isCoin ? apiUrl(`/api/reputation/token-logo/${c.address}`) : (c.identity?.avatarUrl || undefined),
    lines: [cut(c.summary || (ev.length ? `${String(c.level || 'caution').toUpperCase()} — ${ev.length} red flag${ev.length === 1 ? '' : 's'} on record` : 'No red flags on record.'), 60), ...(ev.length ? ev : ['• Every point cited: forensics, funding graph, blocklist'])],
    footer: 'feeless · check any wallet or coin' };
};
import { apiUrl, errorText } from '../lib/api';
import { reportQuest } from '../lib/questEvents';
import { resolveCoin } from '../lib/resolveCoin';
import { useWallet } from '../hooks/useWallet';

const short = a => (a ? `${a.slice(0, 4)}…${a.slice(-4)}` : '—');
const LEVEL = { high: 'High risk', suspect: 'Suspect', watch: 'Watch', clean: 'No red flags', feeless: 'FEELESS wallet', danger: 'High risk', caution: 'Caution', ok: 'Clear' };

// Open a case file from anywhere: window.dispatchEvent(new CustomEvent('feeless:investigate', { detail: address }))
export const investigate = address => window.dispatchEvent(new CustomEvent('feeless:investigate', { detail: address }));

function Evidence({ items }) {
  if (!items?.length) return <p className="cf-empty">Nothing on record.</p>;
  return <ul className="cf-evidence">{items.map((e, i) => <li key={i} className={e.weight < 0 ? 'good' : ''}>
    <b>{e.weight > 0 ? `+${e.weight}` : e.weight}</b><span>{e.claim}</span><small>{e.source}</small></li>)}</ul>;
}

function Gauge({ score, level }) {
  return <div className={`cf-gauge lvl-${level}`} style={{ '--p': `${score}%` }}><em>{score}</em><small>{LEVEL[level] || level}</small></div>;
}

const age = ts => { if (!ts) return '—'; const d = (Date.now() / 1000 - ts) / 86400; return d < 1 ? '<1d' : d < 365 ? `${Math.floor(d)}d` : `${(d / 365).toFixed(1)}y`; };
const usd = v => (v == null ? '—' : `${v < 0 ? '−' : '+'}$${Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 })}`);

function Vitals({ v, caller }) {
  const cells = [['SOL', v?.sol != null ? Number(v.sol).toFixed(3) : '—'], ['Tokens held', v?.tokensHeld ?? '—'], ['Transactions', v?.txCount != null ? `${v.txCount.toLocaleString('en-US')}${v.txCountCapped ? '+' : ''}` : '—'],
    ['Wallet age', v?.firstSeen ? age(v.firstSeen) : v?.txCountCapped ? 'veteran' : '—'], ['Swaps seen', caller?.tradesSeen ?? '—'], ['Coins traded', caller?.tokens ?? '—']];
  return <div className="cf-vitals" data-testid="case-vitals">{cells.map(([k, val]) => <span key={k}><small>{k}</small><b>{val}</b></span>)}</div>;
}

function Trader({ c }) {
  if (!c) return null;
  const judged = (c.closed || 0) >= 3;
  return <section><h5>As a trader</h5>
    {judged ? <p>Win rate {c.winPct}% · flips {c.quickFlipPct}% within 1h · dumps {c.dumpPct}% within 2h · median hold {c.medianHoldMin ?? '—'}m · net {usd(c.netUsd)}</p>
      : <p>Not enough closed trades to judge ({c.closed || 0} closed of {c.tokens || 0} coins traded). Holding, not flipping.</p>}
  </section>;
}

function WalletCase({ c }) {
  return <>
    <Vitals v={c.vitals} caller={c.caller} />
    {c.protected && <div className="cf-official">✓ Official FEELESS wallet: treasury, launches and fee accounts. Never blocklisted, never scored as a suspect.</div>}
    {!c.protected && <Evidence items={c.evidence} />}
    <div className="cf-grid">
      <section><h5>Funding trail</h5>
        <p>Funded by {c.trail?.fundedBy ? <button type="button" className="cf-link" onClick={() => investigate(c.trail.fundedBy)}>{short(c.trail.fundedBy)}</button> : 'self / unknown'}</p>
        {c.trail?.fundedWallets?.length > 0 && <p>Funded {c.trail.fundedWallets.length} flagged wallet(s): {c.trail.fundedWallets.slice(0, 6).map(w => <button key={w} type="button" className="cf-link" onClick={() => investigate(w)}>{short(w)}</button>)}</p>}
      </section>
      {c.launches && <section><h5>Launches</h5><p>{c.launches.tokenCount} coins · {c.launches.ruggedCount || 0} rugged · {c.launches.dumpedCount || 0} dumped · {c.launches.bigWinners || 0} winners</p></section>}
      <Trader c={c.caller} />
      {c.linked?.length > 0 && <section><h5>Linked wallets (same funder)</h5><p>{c.linked.map(l => <button key={l.address} type="button" className={`cf-link b-${l.badge}`} onClick={() => investigate(l.address)}>{short(l.address)}</button>)}</p></section>}
    </div>
  </>;
}

function CoinCase({ c }) {
  const a = c.authorities || {};
  return <>
    <VerifyReport mint={c.address} />
    <div className="cf-chips"><span className={a.mintAuthority ? 'bad' : 'ok'}>Mint {a.mintAuthority ? 'LIVE' : 'revoked'}</span><span className={a.freezeAuthority ? 'bad' : 'ok'}>Freeze {a.freezeAuthority ? 'LIVE' : 'revoked'}</span>
      <span>Top 10 {c.holders?.top10Pct ?? '—'}%</span><span>Dev {c.holders?.devHoldingPct ?? '—'}%</span><span>Insiders {c.holders?.insidersHoldingPct ?? '—'}%</span><span>{c.launch?.bundled} bundled · {c.launch?.snipers} snipers</span></div>
    <Evidence items={c.evidence} />
    <section className="cf-clusters"><h5>Holder clusters · linked by funder</h5>
      {!c.clusters?.clusters?.length ? <p className="cf-empty">No linked holder groups among the top wallets.</p>
        : c.clusters.clusters.map(cl => <div key={cl.funder} className="cf-cluster"><i style={{ width: `${Math.min(100, cl.pct * 2)}%` }} /><b>{cl.pct}%</b><span>{cl.wallets.length} wallets · funder <button type="button" className="cf-link" onClick={() => investigate(cl.funder)}>{short(cl.funder)}</button></span></div>)}
    </section>
    {c.creatorCase && <section className="cf-creator"><h5>Creator {short(c.creatorCase.address)} · <span className={`lvl-${c.creatorCase.level}`}>{c.creatorCase.label} {c.creatorCase.score}</span></h5><p>{c.creatorCase.summary}</p>
      <button type="button" className="cf-link" onClick={() => investigate(c.creatorCase.address)}>Open creator case →</button></section>}
  </>;
}

export function CaseFileView({ address }) {
  const [c, setC] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    if (!address) return undefined;
    let alive = true; setC(null); setErr('');
    fetch(apiUrl(`/api/reputation/case/${address}`)).then(async r => { const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(errorText(b, r.status)); return b; })
      .then(b => alive && setC(b)).catch(e => alive && setErr(e.message));
    return () => { alive = false; };
  }, [address]);
  const [coin, setCoin] = useState(null);   // coin name/image/market for the share GIF (coin cases)
  useEffect(() => { setCoin(null); if (c?.kind === 'coin') resolveCoin('solana', c.address).then(setCoin).catch(() => {}); }, [c?.kind, c?.address]);
  if (err) return <p className="cf-empty">{err}</p>;
  if (!c) return <p className="cf-empty cf-loading">Pulling the chain records…</p>;
  return <div className={`case-file lvl-${c.level}`} data-testid="case-file">
    <header><Gauge score={c.score} level={c.level} /><div><small>{c.kind === 'coin' ? 'COIN CASE' : 'WALLET CASE'} · {short(c.address)}</small>
      <h4>{c.identity?.name || c.identity?.handle ? `${c.identity.name || ''} ${c.identity.handle ? `@${c.identity.handle}` : ''}` : LEVEL[c.level]}</h4><p>{c.summary || (c.evidence?.[0]?.claim ?? 'No red flags on record.')}</p><div className="cf-actions">{c.kind === 'wallet' && <WatchButton target={c.address} />}<ShareGifButton className="btn-outline cf-share" label="🎞 Share case GIF" card={caseCard(c, coin)} /></div></div></header>
    {c.kind === 'coin' ? <CoinCase c={c} /> : <WalletCase c={c} />}
    <small className="cf-foot">Evidence from on-chain forensics, the FEELESS funding graph and blocklist. Every point is cited; nothing is guessed.</small>
  </div>;
}

// Global modal: mounted once, opened by investigate(address).
export function CaseFileModal() {
  const [address, setAddress] = useState(null);
  const me = (useWallet() || {}).wallet?.address;
  useEffect(() => {
    const open = e => { setAddress(e.detail); if (me && e.detail && e.detail !== me) reportQuest(me, 'case_open', e.detail); };   // quest: open case files
    const esc = e => e.key === 'Escape' && setAddress(null);
    window.addEventListener('feeless:investigate', open); window.addEventListener('keydown', esc);
    return () => { window.removeEventListener('feeless:investigate', open); window.removeEventListener('keydown', esc); };
  }, [me]);
  if (!address) return null;
  return <div className="cf-overlay" role="dialog" aria-label="Case file" onClick={e => e.target === e.currentTarget && setAddress(null)}>
    <div className="cf-modal"><button type="button" className="cf-close" aria-label="Close" onClick={() => setAddress(null)}><X size={16} /></button><CaseFileView address={address} /></div>
  </div>;
}

// Command Center tab: search any wallet or coin.
export function InvestigatePanel() {
  const [q, setQ] = useState('');
  const [address, setAddress] = useState('');
  return <section className="cc-panel" data-testid="investigate-panel">
    <div className="cc-block"><h4>Investigate</h4>
      <form className="cf-search" onSubmit={e => { e.preventDefault(); setAddress(q.trim()); }}><Search size={15} /><input placeholder="Paste any Solana wallet or coin address" value={q} onChange={e => setQ(e.target.value)} /><button type="submit" className="btn-primary">Open case</button></form>
      <small className="cc-empty">Wallets: funding trail, launches, snipes and bundles, caller dumps, linked wallets. Coins: 0-100 risk, mint/freeze authority, holder clusters, the creator's case.</small>
    </div>
    {address && <div className="cc-block"><CaseFileView address={address} /></div>}
  </section>;
}
