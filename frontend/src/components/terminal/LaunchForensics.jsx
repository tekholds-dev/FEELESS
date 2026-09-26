import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Crosshair, Layers, Users, UserRound, AlertTriangle, RefreshCw, Ban } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { shortAddress } from '../../lib/dexscreener';

const cache = new Map();

function OffenderPanel({ mint, intel, onChanged }) {
  const [sel, setSel] = useState(new Set());
  const [busy, setBusy] = useState(false);
  const rec = intel.walletRecords || {};
  const rows = [...intel.bundledWallets.map(w => [w, 'bundler']), ...intel.sniperWallets.map(w => [w, 'sniper'])];
  const toggle = w => setSel(s => { const n = new Set(s); n.has(w) ? n.delete(w) : n.add(w); return n; });
  const selectRole = role => setSel(new Set(rows.filter(([w, r]) => r === role && !rec[w]?.blocked).map(([w]) => w)));
  const submit = async () => {
    setBusy(true);
    try {
      const res = await fetch(apiUrl('/api/reputation/blocklist'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mint, wallets: [...sel] }) });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || 'Could not update the blocklist.');
      toast.success(`${body.accepted.length} wallet${body.accepted.length === 1 ? '' : 's'} added to the FEELESS blocklist${body.rejected.length ? ` · ${body.rejected.length} rejected (no on-chain evidence)` : ''}`);
      setSel(new Set()); onChanged();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return <div className="offender-panel" data-testid="offender-panel">
    <div className="offender-actions">
      <button type="button" className="sel-bundler" onClick={() => selectRole('bundler')}>Select all bundlers ({intel.bundledWallets.length})</button>
      <button type="button" className="sel-sniper" onClick={() => selectRole('sniper')}>Select all snipers ({intel.sniperWallets.length})</button>
      {sel.size > 0 && <button type="button" onClick={() => setSel(new Set())}>Clear</button>}
      <button type="button" className="offender-submit" disabled={!sel.size || busy} onClick={submit}><Ban size={12} />{busy ? 'Submitting…' : `Add ${sel.size || ''} to FEELESS blocklist`}</button>
    </div>
    <div className="offender-chips">{rows.map(([w, role]) => { const r = rec[w] || {}; return <label key={w} className={`offender-chip role-${role} ${r.blocked ? 'is-blocked' : ''} ${sel.has(w) ? 'is-selected' : ''}`} title={`${role} · ${r.strikes || 1} launch${(r.strikes || 1) === 1 ? '' : 'es'} caught${r.blocked ? ' · on FEELESS blocklist' : ''}`}>
      <input type="checkbox" checked={sel.has(w)} disabled={r.blocked} onChange={() => toggle(w)} />
      <i>{role === 'bundler' ? 'B' : 'S'}</i><code>{shortAddress(w)}</code>{(r.strikes || 1) > 1 && <em>×{r.strikes}</em>}{r.blocked && <span>⛔</span>}
      <a href={`https://solscan.io/account/${w}`} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}>↗</a>
    </label>; })}</div>
    <small className="offender-note">Only wallets FEELESS's own chain read proves bundled or sniped this launch can be added. Wallets caught on 3+ launches are blocklisted automatically.</small>
  </div>;
}

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
    {d && (d.bundledWallets.length > 0 || d.sniperWallets.length > 0) && <OffenderPanel mint={mint} intel={d} onChanged={() => { cache.delete(mint); load(); }} />}
    {d?.flags?.length > 0 && <ul className="forensics-flags">{d.flags.map(f => <li key={f}><AlertTriangle size={12} />{f}</li>)}</ul>}
    {d && !d.flags?.length && <p className="forensics-clean">No bundle, sniper, or concentration red flags detected in the launch window.</p>}
  </section>;
}
