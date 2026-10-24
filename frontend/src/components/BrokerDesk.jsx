import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { readChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import { useGlide } from '../lib/useGlide';
import '../styles/brokerDesk.css';

// 🏦 THE BROKERAGE (docs/BROKERS.md, DECISIONS #9): YOUR own broker (Webull · Coinbase · Kraken · Alpaca · E*TRADE … via SnapTrade) linked to
// your Familia wallet — one tap opens SnapTrade's portal where you log in to your broker (FEELESS never sees the password); then your cash,
// buying power and positions live here, and BUY / SELL stocks · ETFs · crypto from $1 in your own account. 🔑 No SnapTrade needed: paste your
// own FREE Alpaca keys ($0 to start, no minimum, commission-free) — checked live, sealed to your wallet (`AlpacaKeys`).
const $ = v => (v == null ? '—' : `$${Math.abs(v) >= 1000 ? Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 }) : Math.abs(v).toFixed(2)}`);

export function BrokerDesk({ devAddress = '' }) {   // devAddress: the /dev/broker preview only
  const { wallet } = useWallet() || {}; const a = wallet?.address || devAddress; const s = a ? readChatSession(a) : '';
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
  if (!a || !s) return <section className="bk" data-testid="broker-desk"><b className="bk-t">🏦 YOUR BROKER</b><p className="bk-dim">Sign in to Familia with your wallet, then add your broker here.</p></section>;
  if (d && !d.linked) return <section className="bk" data-testid="broker-desk"><b className="bk-t">🏦 YOUR BROKER · STOCKS · ETFS · CRYPTO</b>
    <AlpacaKeys signup={d.signup} post={post} onSaved={load} />
    {d.snaptrade ? <button type="button" className="bk-sm bk-any" disabled={!!busy} onClick={link} data-tip="Log in to Webull · Coinbase · Kraken · E*TRADE … on SnapTrade's secure portal — FEELESS never sees your password" data-testid="bk-link">{busy || '🔗 OR LINK ANY BROKER'}</button> : null}</section>;
  return <section className="bk" data-testid="broker-desk">
    <header className="bk-h"><b className="bk-t">🏦 THE BROKERAGE</b><span className="bk-val"><em>ALL ACCOUNTS</em><b className="m-num">{$(val)}</b>
      <small className={`m-num ${(d?.pnl ?? 0) >= 0 ? 'is-up' : 'is-dn'}`}>{(d?.pnl ?? 0) >= 0 ? '+' : '−'}{$(d?.pnl)} open P&L</small></span>
      {d?.snaptrade ? <button type="button" className="bk-sm" onClick={link} data-tip="Add another broker">+ BROKER</button> : null}<button type="button" className="bk-sm" onClick={unlink} data-tip="Unlink every broker + delete your keys from FEELESS">UNLINK</button></header>
    {d?.alpacaError ? <p className="bk-err">⚠ {d.alpacaError}</p> : null}
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

// 🔑 the fastest $0 start: a free Alpaca account → its API keys → paste here (checked live against YOUR account, then sealed to your wallet)
function AlpacaKeys({ signup, post, onSaved }) {
  const [k, setK] = useState(''); const [sec, setSec] = useState(''); const [paper, setPaper] = useState(true); const [busy, setBusy] = useState(false);
  const save = async () => { setBusy(true); try { const r = await post('/api/reputation/familia/broker/keys', { key: k.trim(), secret: sec.trim(), paper }); toast.success(`🔑 ${r.account?.broker || 'Alpaca'} linked — cash ${$(r.account?.cash)}`); setK(''); setSec(''); onSaved(); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  return <div className="bk-keys" data-testid="bk-keys">
    <ol className="bk-steps">
      <li style={{ '--i': 0 }}><i>1</i><span><b>FREE ACCOUNT</b><small>Alpaca · $0 to start · no minimum · commission-free</small></span>
        <a className="bk-sm" href={signup || 'https://app.alpaca.markets/signup'} target="_blank" rel="noreferrer noopener" data-tip="Opens Alpaca's own sign-up in a new tab (PAPER works the same minute; LIVE after its ID check)" data-testid="bk-signup">OPEN ↗</a></li>
      <li style={{ '--i': 1 }}><i>2</i><span><b>GET YOUR KEYS</b><small>Alpaca dashboard → API Keys → Generate</small></span></li>
      <li style={{ '--i': 2 }}><i>3</i><span><b>PASTE + SAVE</b><small>checked live, sealed to your wallet</small></span></li>
    </ol>
    <span className="m-seg" role="radiogroup" aria-label="Account">{[[true, 'PAPER', 'Practice money — same API, nothing real'], [false, 'LIVE', 'Your real Alpaca account']].map(([v, l, tip]) =>
      <button key={l} type="button" role="radio" aria-checked={paper === v} className={paper === v ? 'active' : ''} onClick={() => setPaper(v)} data-tip={tip} data-testid={`bk-${l.toLowerCase()}`}>{l}</button>)}</span>
    <input value={k} onChange={e => setK(e.target.value)} placeholder="API Key ID" aria-label="Alpaca API Key ID" autoComplete="off" spellCheck="false" data-testid="bk-key" />
    <input value={sec} onChange={e => setSec(e.target.value)} placeholder="Secret Key" aria-label="Alpaca Secret Key" type="password" autoComplete="off" data-testid="bk-secret" />
    <button type="button" className="bk-go" disabled={busy || k.trim().length < 16 || sec.trim().length < 30} onClick={save} data-tip="FEELESS checks the keys against your Alpaca account, then seals them to your wallet — remove them any time" data-testid="bk-save">{busy ? 'Checking with Alpaca…' : '🔑 SAVE MY KEYS'}</button>
  </div>;
}
