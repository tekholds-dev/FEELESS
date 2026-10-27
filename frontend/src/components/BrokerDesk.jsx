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

// 🔑 the key doors a user can open themselves (owner 2026-10-26: "enter my api once … always jump in and go") — US-legal, free to open
export const VENUES = {
  alpaca: { name: 'Alpaca', sub: 'US stocks · ETFs · crypto · $0 to start', signup: 'https://app.alpaca.markets/signup', where: 'Alpaca dashboard → API Keys → Generate', paper: true, keyMin: 16, secMin: 30 },
  cdc: { name: 'Crypto.com', sub: 'spot + perps in your own Crypto.com Exchange account', signup: 'https://crypto.com/exchange', where: 'Crypto.com Exchange → Settings → API Keys (trading ON, withdrawals OFF)', paper: false, keyMin: 16, secMin: 16 },
};
export function BrokerDesk({ devAddress = '', venue = null }) {   // devAddress: the /dev/broker preview only · venue: open on that key door / account
  const { wallet } = useWallet() || {}; const a = wallet?.address || devAddress; const s = a ? readChatSession(a) : '';
  const [d, setD] = useState(null); const [busy, setBusy] = useState(''); const [t, setT] = useState({ symbol: venue === 'cdc' ? 'BTC' : 'SPY', action: 'BUY', usd: 5, accountId: venue === 'cdc' ? 'cdc' : '', market: 'spot', lev: 5 });
  const load = useCallback(() => fetch(apiUrl(`/api/reputation/familia/broker${a && s ? `?address=${a}&session=${encodeURIComponent(s)}` : ''}`)).then(r => (r.ok ? r.json() : null)).then(x => x && setD(x)).catch(() => {}), [a, s]);
  useEffect(() => { load(); const i = setInterval(() => { if (!document.hidden) load(); }, 20000); return () => clearInterval(i); }, [load]);
  const post = async (path, body) => { const r = await fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: a, session: s, ...body }) });
    const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'The broker said no.'); return b; };
  const link = async () => { setBusy('Opening your broker login…'); try { const { url } = await post('/api/reputation/familia/broker/link', { back: window.location.href }); window.open(url, '_blank', 'noopener'); }
    catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const order = async () => { const acct = t.accountId || d?.accounts?.[0]?.id;
    const perp = acct === 'cdc' && t.market === 'perp';
    if (!window.confirm(perp ? `${t.action === 'BUY' ? 'LONG' : 'SHORT'} ${t.symbol.toUpperCase()}-PERP · $${t.usd} margin × ${t.lev}× = $${t.usd * t.lev} on Crypto.com?` : `${t.action} $${t.usd} of ${t.symbol.toUpperCase()} in your ${d?.accounts?.find(x => x.id === acct)?.broker || 'broker'} account?`)) return;
    setBusy('Sending to your broker…'); try { const o = await post('/api/reputation/familia/broker/order', { ...t, accountId: acct, market: perp ? 'perp' : 'spot' }); toast.success(`✅ ${o.action} ${o.symbol} — ${o.status || 'sent'}`); load(); }
    catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const unlink = async () => { if (!window.confirm('Unlink your broker from FEELESS?')) return; try { await post('/api/reputation/familia/broker/unlink', {}); load(); } catch (e) { toast.error(e.message); } };
  const val = useGlide(d?.value ?? null, 600);
  const title = venue ? `🔑 ${VENUES[venue]?.name || 'YOUR BROKER'}`.toUpperCase() : '🏦 YOUR BROKER';
  if (!a || !s) return <section className="bk" data-testid="broker-desk"><b className="bk-t">{title}</b><p className="bk-dim">Sign in to Familia with your wallet (one signature, 7 days), then paste your keys once — they stay sealed to your wallet.</p>
    {venue === 'cdc' ? <CdcCaps a="" s="" /> : null}
    {venue ? <AlpacaKeys venue={venue} post={async () => { throw new Error('Sign in to Familia with your wallet first.'); }} onSaved={() => {}} /> : null}</section>;
  if (d && !d.linked) return <section className="bk" data-testid="broker-desk"><b className="bk-t">🏦 YOUR BROKER · STOCKS · ETFS · CRYPTO</b>
    {d.snaptrade ? <button type="button" className="bk-go bk-any" disabled={!!busy} onClick={link} data-tip="Log in to YOUR broker (TradeStation · Webull · Coinbase · Kraken · E*TRADE …) on SnapTrade's secure portal — once; FEELESS never sees your password" data-testid="bk-link">{busy || '🔗 LINK MY BROKER · TRADESTATION · WEBULL · ANY'}</button> : null}
    {d.snaptrade ? <small className="bk-dim">— or paste free Alpaca keys —</small> : null}
    {venue === 'cdc' ? <CdcCaps a={a} s={s} /> : null}
    <AlpacaKeys venue={venue || 'alpaca'} post={post} onSaved={load} /></section>;
  return <section className="bk" data-testid="broker-desk">
    <header className="bk-h"><b className="bk-t">🏦 THE BROKERAGE</b><span className="bk-val"><em>ALL ACCOUNTS</em><b className="m-num">{$(val)}</b>
      <small className={`m-num ${(d?.pnl ?? 0) >= 0 ? 'is-up' : 'is-dn'}`}>{(d?.pnl ?? 0) >= 0 ? '+' : '−'}{$(d?.pnl)} open P&L</small></span>
      {d?.snaptrade ? <button type="button" className="bk-sm" onClick={link} data-tip="Add another broker">+ BROKER</button> : null}<button type="button" className="bk-sm" onClick={unlink} data-tip="Unlink every broker + delete your keys from FEELESS">UNLINK</button></header>
    {d?.alpacaError ? <p className="bk-err">⚠ {d.alpacaError}</p> : null}{d?.cdcError ? <p className="bk-err">⚠ {d.cdcError}</p> : null}
    {venue && !(d?.accounts || []).some(x => x.id === venue || (venue === 'alpaca' && x.id !== 'cdc')) ? <AlpacaKeys venue={venue} post={post} onSaved={load} /> : null}
    {venue === 'cdc' ? <CdcCaps a={a} s={s} onPick={(b, mk, lev) => setT(x => ({ ...x, symbol: b, market: mk, accountId: 'cdc', lev: lev ? Math.min(x.lev, lev) : x.lev }))} /> : null}
    <div className="bk-ticket">
      {(t.accountId || d?.accounts?.[0]?.id) === 'cdc' ? <span className="m-seg bk-mkt" role="radiogroup" aria-label="Market">{[['spot', 'SPOT', 'Buy / sell the coin itself'], ['perp', 'PERPS', 'Long / short with leverage in your Crypto.com account (Crypto.com decides if your account may)']].map(([k, l, tip]) =>
        <button key={k} type="button" role="radio" aria-checked={t.market === k} className={t.market === k ? 'active' : ''} onClick={() => setT({ ...t, market: k })} data-tip={tip} data-testid={`bk-m-${k}`}>{l}</button>)}</span> : null}
      {t.market === 'perp' && (t.accountId || d?.accounts?.[0]?.id) === 'cdc' ? <span className="m-seg bk-lev" role="radiogroup" aria-label="Leverage">{[2, 5, 10, 25, 50, 100].map(l => <button key={l} type="button" role="radio" aria-checked={t.lev === l} className={t.lev === l ? 'active' : ''} onClick={() => setT({ ...t, lev: l })} data-tip={`${l}×: a ${(100 / l).toFixed(1)}% move against you wipes the margin`}>{l}×</button>)}</span> : null}
      <span className="m-seg">{['BUY', 'SELL'].map(x => <button key={x} type="button" className={t.action === x ? 'active' : ''} onClick={() => setT({ ...t, action: x })} data-testid={`bk-${x}`}>{x}</button>)}</span>
      <input value={t.symbol} onChange={e => setT({ ...t, symbol: e.target.value.toUpperCase() })} aria-label="Ticker" placeholder="SPY" data-testid="bk-sym" />
      <label className="bk-usd">$<input type="number" min="1" value={t.usd} onChange={e => setT({ ...t, usd: Number(e.target.value) })} aria-label="Dollars" data-testid="bk-usd" /></label>
      {(d?.accounts || []).length > 1 ? <select value={t.accountId} onChange={e => setT({ ...t, accountId: e.target.value })} aria-label="Account">{d.accounts.map(x => <option key={x.id} value={x.id}>{x.broker} ··{x.number}</option>)}</select> : null}
      <button type="button" className={`bk-go is-${t.action.toLowerCase()}`} disabled={!!busy || !(t.usd >= 1) || !t.symbol} onClick={order} data-testid="bk-order">{busy || (t.market === 'perp' && (t.accountId || d?.accounts?.[0]?.id) === 'cdc' ? `${t.action === 'BUY' ? '▲ LONG' : '▼ SHORT'} ${t.symbol}-PERP $${t.usd} × ${t.lev}×` : `${t.action} $${t.usd} ${t.symbol}`)}</button>
    </div>
    {(d?.accounts || []).map((x, i) => <div key={x.id} className="bk-acct" style={{ '--i': i }}>
      <div className="bk-ah"><b>{x.broker}</b><small>{x.name} ··{x.number}</small><span><em>CASH</em><b className="m-num">{$(x.cash)}</b></span><span><em>BUYING POWER</em><b className="m-num">{$(x.buyingPower)}</b></span><span><em>VALUE</em><b className="m-num">{$(x.value)}</b></span></div>
      <ol>{x.positions.map((p, j) => <li key={p.ticker + j} className={p.pnl >= 0 ? 'is-up' : 'is-dn'}><button type="button" onClick={() => setT({ ...t, symbol: p.ticker, accountId: x.id })} data-tip="Trade this">{p.ticker}</button>
        <small className="m-num">{p.units} @ {$(p.price)}</small><b className="m-num">{$(p.value)}</b><i className="m-num">{p.pnl >= 0 ? '+' : '−'}{$(p.pnl)}{p.pnlPct != null ? ` · ${p.pnlPct}%` : ''}</i></li>)}</ol>
    </div>)}
  </section>;
}

// 🔑 the fastest $0 start: a free Alpaca account → its API keys → paste here (checked live against YOUR account, then sealed to your wallet)
function AlpacaKeys({ venue: v0 = 'alpaca', post, onSaved }) {
  const [venue, setVenue] = useState(v0); const V = VENUES[venue] || VENUES.alpaca;
  useEffect(() => { setVenue(v0); }, [v0]);
  const [k, setK] = useState(''); const [sec, setSec] = useState(''); const [paper, setPaper] = useState(true); const [busy, setBusy] = useState(false);
  const save = async () => { setBusy(true); try { const r = await post('/api/reputation/familia/broker/keys', { venue, key: k.trim(), secret: sec.trim(), paper: V.paper && paper }); toast.success(`🔑 ${r.account?.broker || V.name} linked — cash ${$(r.account?.cash)}`); setK(''); setSec(''); onSaved(); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  return <div className={`bk-keys is-${venue}`} data-testid="bk-keys">
    <span className="m-seg bk-venue" role="radiogroup" aria-label="Which account">{Object.entries(VENUES).map(([id, x]) => <button key={id} type="button" role="radio" aria-checked={venue === id} className={venue === id ? 'active' : ''} onClick={() => setVenue(id)} data-tip={x.sub} data-testid={`bk-v-${id}`}>{x.name}</button>)}</span>
    <ol className="bk-steps">
      <li style={{ '--i': 0 }}><i>1</i><span><b>YOUR ACCOUNT</b><small>{V.name} · {V.sub}</small></span>
        <a className="bk-sm" href={V.signup} target="_blank" rel="noreferrer noopener" data-tip={`Opens ${V.name}'s own sign-up in a new tab`} data-testid="bk-signup">OPEN ↗</a></li>
      <li style={{ '--i': 1 }}><i>2</i><span><b>GET YOUR KEYS</b><small>{V.where}</small></span></li>
      <li style={{ '--i': 2 }}><i>3</i><span><b>PASTE + SAVE ONCE</b><small>checked live, sealed to your wallet · jump in any time</small></span></li>
    </ol>
    {V.paper ? <span className="m-seg" role="radiogroup" aria-label="Account">{[[true, 'PAPER', 'Practice money — same API, nothing real'], [false, 'LIVE', `Your real ${V.name} account`]].map(([v, l, tip]) =>
      <button key={l} type="button" role="radio" aria-checked={paper === v} className={paper === v ? 'active' : ''} onClick={() => setPaper(v)} data-tip={tip} data-testid={`bk-${l.toLowerCase()}`}>{l}</button>)}</span> : null}
    <input value={k} onChange={e => setK(e.target.value)} placeholder="API Key" aria-label={`${V.name} API key`} autoComplete="off" spellCheck="false" data-testid="bk-key" />
    <input value={sec} onChange={e => setSec(e.target.value)} placeholder="Secret" aria-label={`${V.name} secret`} type="password" autoComplete="off" data-testid="bk-secret" />
    <button type="button" className="bk-go" disabled={busy || k.trim().length < V.keyMin || sec.trim().length < V.secMin} onClick={save} data-tip={`FEELESS checks the keys against your ${V.name} account, then seals them to your wallet — remove them any time`} data-testid="bk-save">{busy ? `Checking with ${V.name}…` : '🔑 SAVE MY KEYS'}</button>
  </div>;
}

// 🔑 WHAT YOUR CRYPTO.COM KEY DOES IN FEELESS: the exchange's own live list (spot · perpetuals · futures) + whether this wallet's key reads its
// account — so the trade station shows exactly what is wired before you type a ticker.
function CdcCaps({ a, s, onPick }) {
  const [c, setC] = useState(null);
  useEffect(() => { let on = true; fetch(apiUrl(`/api/reputation/familia/broker/cdc-caps${a && s ? `?address=${a}&session=${encodeURIComponent(s)}` : ''}`)).then(r => (r.ok ? r.json() : null)).then(x => on && setC(x)).catch(() => {}); return () => { on = false; }; }, [a, s]);
  const k = c?.key || {};
  const tiles = [['SPOT', c ? `${c.spot.n} pairs` : '…', 'BUY / SELL vs USD', true], ['PERPS', c ? `${c.perps.n} · to ${c.perps.maxLev}×` : '…', 'long / short · your account decides', true],
    ['FUTURES', c ? `${c.futures.n} dated` : '…', 'not wired in FEELESS yet', false], ['YOUR KEY', k.linked ? (k.reads ? `reads · $${Math.round(k.valueUsd || 0).toLocaleString()}` : 'refused') : 'not added', k.linked ? (k.reads ? 'balance read live' : (k.error || '')) : 'paste it below once', !!k.reads]];
  return <div className="bk-caps" data-testid="cdc-caps"><b className="bk-t">🔑 WHAT YOUR CRYPTO.COM KEY CAN DO HERE</b>
    <div className="bk-capg">{tiles.map(([l, v, sub, ok], i) => <span key={l} className={ok ? 'is-ok' : 'is-off'} style={{ '--i': i }}><em>{l}</em><b className="m-num">{v}</b><small>{ok ? '✓ ' : '○ '}{sub}</small></span>)}</div>
    {c?.devKey && !c?.envPair && !k.linked ? <p className="bk-err" data-testid="cdc-devkey">🔑 Your Crypto.com <b>Developer Platform</b> key is in .env — it reads Cronos chain data but can't trade. For trading add an <b>Exchange</b> key + secret (crypto.com/exchange → Settings → API Keys) below, or as CRYPTO_COM_API_KEY / CRYPTO_COM_API_SECRET in .env (rides your wallet automatically).</p> : null}
    {c?.perps?.all?.length || c?.spot?.all?.length ? <CdcMarkets c={c} onPick={onPick} /> : null}</div>;
}

// 📜 EVERY market Crypto.com lists (owner 2026-10-27: "full list of tradeables + trading options per provider"): PERPS (with each one's max
// leverage) | SPOT, a search box, one tap loads the coin into the ticket above.
function CdcMarkets({ c, onPick }) {
  const [m, setM] = useState('perp'); const [q, setQ] = useState('');
  const rows = m === 'perp' ? (c.perps.all || []).map(x => [x.base, x.lev]) : (c.spot.all || []).map(b => [b, null]);
  const hit = rows.filter(([b]) => !q || b.includes(q.toUpperCase()));
  return <div className="bk-mkts" data-testid="cdc-markets">
    <span className="m-seg" role="radiogroup" aria-label="Market list">{[['perp', `PERPS · ${c.perps.n}`, 'Perpetuals: long / short with leverage'], ['spot', `SPOT · ${c.spot.n}`, 'Buy / sell the coin itself vs USD']].map(([k, l, tip]) =>
      <button key={k} type="button" role="radio" aria-checked={m === k} className={m === k ? 'active' : ''} onClick={() => setM(k)} data-tip={tip} data-testid={`cdc-ml-${k}`}>{l}</button>)}</span>
    <input value={q} onChange={e => setQ(e.target.value.replace(/[^A-Za-z0-9]/g, '').slice(0, 12))} placeholder="Search a coin" aria-label="Search Crypto.com markets" data-testid="cdc-mq" />
    <div className="bk-mlist">{hit.slice(0, 160).map(([b, lev], i) => <button key={b + i} type="button" onClick={() => onPick?.(b, m, lev)} style={{ '--i': Math.min(i, 12) }}
      data-tip={lev ? `Long / short ${b}-PERP up to ${lev}× — loads it in the ticket` : `Buy / sell ${b} vs USD — loads it in the ticket`}><b>{b}</b>{lev ? <i className="m-num">{lev}×</i> : null}</button>)}
      {!hit.length ? <small className="bk-dim">No {m === 'perp' ? 'perp' : 'pair'} matches “{q}”.</small> : null}</div>
    {hit.length > 160 ? <small className="bk-dim">{hit.length - 160} more — search to narrow.</small> : null}
  </div>;
}
