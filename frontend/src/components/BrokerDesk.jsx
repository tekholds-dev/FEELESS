import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { readChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import { useGlide } from '../lib/useGlide';
import '../styles/brokerDesk.css';

// 🏦 THE BROKERAGE (docs/BROKERS.md, DECISIONS #9): YOUR own broker (Webull · Coinbase · Kraken · Alpaca · E*TRADE … via SnapTrade) linked to
// your Familia wallet — one tap opens SnapTrade's portal where you log in to your broker (FEELESS never sees the password); then your cash,
// buying power and positions live here, and BUY / SELL stocks · ETFs · crypto from $1 in your own account.
const $ = v => (v == null ? '—' : `$${Math.abs(v) >= 1000 ? Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 }) : Math.abs(v).toFixed(2)}`);

export function BrokerDesk() {
  const { wallet } = useWallet() || {}; const a = wallet?.address || ''; const s = a ? readChatSession(a) : '';
  const [d, setD] = useState(null); const [busy, setBusy] = useState(''); const [t, setT] = useState({ symbol: 'SPY', action: 'BUY', usd: 5, accountId: '' });
  const load = useCallback(() => fetch(apiUrl(`/api/reputation/familia/broker${a && s ? `?address=${a}&session=${encodeURIComponent(s)}` : ''}`)).then(r => (r.ok ? r.json() : null)).then(x => x && setD(x)).catch(() => {}), [a, s]);
  useEffect(() => { load(); const i = setInterval(() => { if (!document.hidden) load(); }, 20000); return () => clearInterval(i); }, [load]);
  const post = async (path, body) => { const r = await fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: a, session: s, ...body }) });
    const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'The broker said no.'); return b; };
  const link = async () => { setBusy('Opening your broker login…'); try { const { url } = await post('/api/reputation/familia/broker/link', { back: window.location.href }); window.open(url, '_blank', 'noopener'); }
    catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const order = async () => { const acct = t.accountId || d?.accounts?.[0]?.id;
    if (!window.confirm(`${t.action} $${t.usd} of ${t.symbol.toUpperCase()} in your ${d?.accounts?.find(x => x.id === acct)?.broker || 'broker'} account?`)) return;
    setBusy('Sending to your broker…'); try { const o = await post('/api/reputation/familia/broker/order', { ...t, accountId: acct }); toast.success(`✅ ${o.action} ${o.symbol} — ${o.status || 'sent'}`); load(); }
    catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const unlink = async () => { if (!window.confirm('Unlink your broker from FEELESS?')) return; try { await post('/api/reputation/familia/broker/unlink', {}); load(); } catch (e) { toast.error(e.message); } };
  const val = useGlide(d?.value ?? null, 600);
  if (!a || !s) return <section className="bk" data-testid="broker-desk"><b className="bk-t">🏦 THE BROKERAGE</b><p className="bk-dim">Sign in to Familia with your wallet, then link your broker here.</p></section>;
  if (d && !d.ready) return <section className="bk" data-testid="broker-desk"><b className="bk-t">🏦 THE BROKERAGE</b><span className="bk-lock">🔒 OPENS WHEN SNAPTRADE IS SET UP</span></section>;
  if (d && !d.linked) return <section className="bk" data-testid="broker-desk"><b className="bk-t">🏦 THE BROKERAGE</b>
    <button type="button" className="bk-go" disabled={!!busy} onClick={link} data-tip="Log in to YOUR broker on SnapTrade's secure portal — FEELESS never sees your password" data-testid="bk-link">{busy || '🔗 LINK MY BROKER'}</button>
    <small className="bk-dim">Webull · Coinbase · Kraken · Alpaca · E*TRADE · more — stocks, ETFs, crypto from $1</small></section>;
  return <section className="bk" data-testid="broker-desk">
    <header className="bk-h"><b className="bk-t">🏦 THE BROKERAGE</b><span className="bk-val"><em>ALL ACCOUNTS</em><b className="m-num">{$(val)}</b>
      <small className={`m-num ${(d?.pnl ?? 0) >= 0 ? 'is-up' : 'is-dn'}`}>{(d?.pnl ?? 0) >= 0 ? '+' : '−'}{$(d?.pnl)} open P&L</small></span>
      <button type="button" className="bk-sm" onClick={link} data-tip="Add another broker">+ BROKER</button><button type="button" className="bk-sm" onClick={unlink} data-tip="Unlink every broker">UNLINK</button></header>
    <div className="bk-ticket">
      <span className="m-seg">{['BUY', 'SELL'].map(x => <button key={x} type="button" className={t.action === x ? 'active' : ''} onClick={() => setT({ ...t, action: x })} data-testid={`bk-${x}`}>{x}</button>)}</span>
      <input value={t.symbol} onChange={e => setT({ ...t, symbol: e.target.value.toUpperCase() })} aria-label="Ticker" placeholder="SPY" data-testid="bk-sym" />
      <label className="bk-usd">$<input type="number" min="1" value={t.usd} onChange={e => setT({ ...t, usd: Number(e.target.value) })} aria-label="Dollars" data-testid="bk-usd" /></label>
      {(d?.accounts || []).length > 1 ? <select value={t.accountId} onChange={e => setT({ ...t, accountId: e.target.value })} aria-label="Account">{d.accounts.map(x => <option key={x.id} value={x.id}>{x.broker} ··{x.number}</option>)}</select> : null}
      <button type="button" className={`bk-go is-${t.action.toLowerCase()}`} disabled={!!busy || !(t.usd >= 1) || !t.symbol} onClick={order} data-testid="bk-order">{busy || `${t.action} $${t.usd} ${t.symbol}`}</button>
    </div>
    {(d?.accounts || []).map((x, i) => <div key={x.id} className="bk-acct" style={{ '--i': i }}>
      <div className="bk-ah"><b>{x.broker}</b><small>{x.name} ··{x.number}</small><span><em>CASH</em><b className="m-num">{$(x.cash)}</b></span><span><em>BUYING POWER</em><b className="m-num">{$(x.buyingPower)}</b></span><span><em>VALUE</em><b className="m-num">{$(x.value)}</b></span></div>
      <ol>{x.positions.map((p, j) => <li key={p.ticker + j} className={p.pnl >= 0 ? 'is-up' : 'is-dn'}><button type="button" onClick={() => setT({ ...t, symbol: p.ticker, accountId: x.id })} data-tip="Trade this">{p.ticker}</button>
        <small className="m-num">{p.units} @ {$(p.price)}</small><b className="m-num">{$(p.value)}</b><i className="m-num">{p.pnl >= 0 ? '+' : '−'}{$(p.pnl)}{p.pnlPct != null ? ` · ${p.pnlPct}%` : ''}</i></li>)}</ol>
    </div>)}
  </section>;
}
