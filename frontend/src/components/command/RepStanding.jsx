import { CopyBtn } from '../CopyBtn';
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useWallet } from '../../hooks/useWallet';
import { apiUrl } from '../../lib/api';

const short = a => (a ? `${a.slice(0, 4)}…${a.slice(-4)}` : '');
const ago = t => { if (!t) return ''; const s = Date.now() / 1000 - (typeof t === 'string' ? Date.parse(t) / 1000 : t); return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };

// Where the signed-in wallet stands in every category FEELESS scores — each with its evidence.
function MyStanding() {
  const { wallet, connect } = useWallet();
  const [d, setD] = useState(null);
  const address = wallet?.address;
  useEffect(() => {
    if (!address) { setD(null); return undefined; }
    let alive = true;
    fetch(apiUrl(`/api/reputation/standing/${address}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setD(x)).catch(() => {});
    return () => { alive = false; };
  }, [address]);
  if (!address) return <section className="rep-standing rep-standing-empty"><h3>Where do you stand?</h3><p>Connect a wallet to see your record in every category FEELESS scores — trust, creator, caller, sniper history, funding trail, community.</p><button type="button" className="btn-primary" onClick={() => connect?.()}>Connect wallet</button></section>;
  if (!d) return <section className="rep-standing"><h3>Reading your on-chain record…</h3></section>;
  return <section className="rep-standing" data-testid="rep-standing">
    <header><h3>Your standing</h3><Link to={`/terminal/profile/${address}`}>{short(address)} · full profile →</Link></header>
    <div className="rep-cats">{d.categories.map(c => <div key={c.id} className={`rep-cat ${c.good ? 'good' : c.score != null && c.score < 40 ? 'bad' : ''}`}>
      <small>{c.label}</small>
      <b>{c.score ?? '—'}</b>
      <i className="rep-bar"><i style={{ width: `${c.score ?? 0}%` }} /></i>
      <span>{c.detail}{c.percentile != null ? ` · top ${Math.max(1, 100 - c.percentile)}%` : ''}</span>
    </div>)}</div>
  </section>;
}

// The dark side: who snipes, who bankrolls them, who moves size, what just rugged.
function DarkSide() {
  const [d, setD] = useState(null);
  const [tab, setTab] = useState('offenders');
  const [kols, setKols] = useState(null);
  useEffect(() => { if (tab === 'kols' && !kols) fetch(apiUrl('/api/reputation/kols')).then(r => r.json()).then(x => setKols(x.kols || [])).catch(() => setKols([])); }, [tab, kols]);
  useEffect(() => {
    let alive = true;
    const load = () => fetch(apiUrl('/api/reputation/darkside?limit=12')).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(); const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  const tabs = [['offenders', '🎯 Snipers & bundlers'], ['funders', '💸 Who funds them'], ['whales', '🐋 Whales'], ['rugs', '🪦 Rugs & dumps'], ['kols', '🎙 KOL trades']];
  const rows = tab === 'kols' ? (kols || []) : (d?.[tab] || []);
  return <section className="rep-dark" data-testid="rep-darkside">
    <header><h3>The dark side</h3><small>Every entry is on-chain evidence FEELESS caught — click any wallet for its full record.</small></header>
    <nav>{tabs.map(([k, l]) => <button key={k} type="button" className={tab === k ? 'active' : ''} onClick={() => setTab(k)}>{l}<em>{d?.[k]?.length ?? ''}</em></button>)}</nav>
    <div className="rep-dark-list">
      {!rows.length && <p className="wp-bio">{d ? (tab === 'kols' ? (kols ? 'No KOL wallets tracked yet — admins add them in the command center.' : 'Loading KOL trades…') : tab === 'whales' || tab === 'rugs' ? 'Nothing yet — the radar fills this as it watches live pools.' : 'None caught yet.') : 'Loading…'}</p>}
      {tab === 'offenders' && rows.map(r => <Link key={r.wallet} to={`/terminal/profile/${r.wallet}`} className="rep-dark-row"><code>{short(r.wallet)}</code><CopyBtn value={r.wallet} /><span>{r.roles.join(' + ')} on <b>{r.strikes}</b> launch{r.strikes === 1 ? '' : 'es'}</span>{r.blocked && <em className="bad">⛔ blocklisted</em>}<small>{ago(r.lastSeen)}</small></Link>)}
      {tab === 'funders' && rows.map(r => <Link key={r.wallet} to={`/terminal/profile/${r.wallet}`} className="rep-dark-row"><code>{short(r.wallet)}</code><CopyBtn value={r.wallet} /><span>bankrolled <b>{r.walletsFunded}</b> sniper/bundler wallets · {r.launches} launch{r.launches === 1 ? '' : 'es'}</span>{r.flagged && <em className="bad">🚩 repeat funder</em>}<small>{ago(r.lastSeen)}</small></Link>)}
      {tab === 'whales' && rows.map(r => <Link key={r.tx} to={`/terminal/profile/${r.wallet}`} className="rep-dark-row"><code>{short(r.wallet)}</code><CopyBtn value={r.wallet} /><span className={r.kind === 'buy' ? 'positive' : 'negative'}>{r.kind} <b>${Number(r.usd).toLocaleString()}</b> of ${r.symbol}</span><small>{ago(r.at)}</small></Link>)}
      {tab === 'kols' && rows.map(k => <div key={k.address} className={`rep-kol ${k.stats?.danger ? 'danger' : ''}`}>
        <Link to={`/terminal/profile/${k.address}`} className="rep-dark-row"><code>{k.name}</code><span>{k.x ? `@${k.x} · ` : ''}{k.chain}{k.stats ? ` · ${k.stats.closed} closed trades · median hold ${k.stats.medianHoldMin ?? '—'}m · flips ${k.stats.quickFlipPct ?? '—'}% in 1h · win ${k.stats.winPct ?? '—'}%` : ' · stats unavailable'}</span>{k.stats?.danger && <em className="bad">⚠ call-and-dump</em>}</Link>
        {k.stats?.flags?.map(f => <p key={f} className="rep-kol-flag">{f}</p>)}
      </div>)}
      {tab === 'rugs' && rows.map(r => <a key={`${r.pair}-${r.at}`} href={`/?coin=solana:${r.pair}`} className="rep-dark-row"><code>${r.symbol}</code><span>{r.text}</span><small>{ago(r.at)}</small></a>)}
    </div>
  </section>;
}

export function RepStanding() {
  return <div className="rep-top"><MyStanding /><DarkSide /></div>;
}
