import React, { useEffect, useState } from 'react';
import { Crosshair, Layers, Users, UserRound, AlertTriangle, RefreshCw } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { shortAddress } from '../../lib/dexscreener';

const cache = new Map();

export function LaunchForensics({ pair }) {
  const mint = pair?.baseToken?.address;
  const chain = pair?.chainId;
  const [state, setState] = useState(() => ({ data: cache.get(mint) || null, error: '', loading: !cache.get(mint) }));
  const [open, setOpen] = useState('');
  const load = React.useCallback(() => {
    if (!mint || chain !== 'solana') { setState({ data: null, error: 'On-chain forensics cover Solana tokens.', loading: false }); return () => {}; }
    let alive = true;
    setState(s => ({ ...s, loading: !s.data }));
    fetch(apiUrl(`/api/reputation/intel/${chain}/${mint}`))
      .then(r => (r.ok ? r.json() : Promise.reject(new Error('Unavailable'))))
      .then(data => { cache.set(mint, data); if (alive) setState({ data, error: '', loading: false }); })
      .catch(() => { if (alive) setState(s => ({ ...s, error: 'Unavailable', loading: false })); });
    return () => { alive = false; };
  }, [mint, chain]);
  useEffect(() => load(), [load]);
  const d = state.data;
  const pct = v => (v == null ? '—' : `${Number(v).toFixed(v >= 10 ? 1 : 2)}%`);
  const cards = [
    ['snipers', Crosshair, 'Snipers', d ? String(d.sniperWallets.length) : state.loading ? '…' : 'Unavailable', 'Bought within ~1s of launch', d?.sniperWallets, d && d.sniperWallets.length >= 5],
    ['bundlers', Layers, 'Bundled', d ? String(d.bundledWallets.length) : state.loading ? '…' : 'Unavailable', 'Same block as the mint', d?.bundledWallets, d && d.bundledWallets.length >= 3],
    ['insiders', AlertTriangle, 'Insiders hold', d ? pct(d.insidersHoldingPct) : state.loading ? '…' : 'Unavailable', 'Snipers + bundlers still in top holders', null, d && d.insidersHoldingPct >= 10],
    ['holders', Users, 'Top 10 hold', d ? pct(d.top10Pct) : state.loading ? '…' : 'Unavailable', `Excl. pools${d?.poolPct != null ? ` · pool/curve ${pct(d.poolPct)}` : ''}`, null, d && d.top10Pct >= 35],
    ['dev', UserRound, 'Dev holds', d ? pct(d.devHoldingPct) : state.loading ? '…' : 'Unavailable', d?.creator ? `Creator ${shortAddress(d.creator)}` : 'Creator wallet', null, d && d.devHoldingPct >= 5],
  ];
  return <section className="token-analytics launch-forensics" data-testid="token-analytics">
    <div className="token-analytics-heading"><strong>Launch forensics</strong><span>Read from Solana on-chain · refreshed every 3 min</span>{d && <button type="button" className="icon-btn small-icon forensics-refresh" title="Refresh" onClick={() => { cache.delete(mint); load(); }}><RefreshCw size={12} /></button>}</div>
    <div className="token-analytics-grid forensics-grid">{cards.map(([id, Icon, label, value, sub, list, warn]) => <div key={id} className={`token-analytics-item ${warn ? 'is-warning' : ''} ${list?.length ? 'is-clickable' : ''}`} data-testid={`token-analytics-${id}`} role={list?.length ? 'button' : undefined} tabIndex={list?.length ? 0 : undefined} onClick={() => list?.length && setOpen(open === id ? '' : id)}>
      <span><Icon size={13} />{label}</span><b>{value}</b><small>{sub}</small>
    </div>)}</div>
    {open && <div className="forensics-wallets">{(open === 'snipers' ? d.sniperWallets : d.bundledWallets).map(w => <a key={w} href={`https://solscan.io/account/${w}`} target="_blank" rel="noreferrer"><code>{shortAddress(w)}</code></a>)}</div>}
    {d?.flags?.length > 0 && <ul className="forensics-flags">{d.flags.map(f => <li key={f}><AlertTriangle size={12} />{f}</li>)}</ul>}
    {d && !d.flags?.length && <p className="forensics-clean">No bundle, sniper, or concentration red flags detected in the launch window.</p>}
  </section>;
}
