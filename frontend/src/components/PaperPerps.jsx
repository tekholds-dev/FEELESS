import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { readChatSession, getChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import { useGlide } from '../lib/useGlide';
import { cash } from '../lib/earnStake';
import '../styles/paperPerps.css';

// 📉 THE PAPER DESK — the Perps building's own order ticket (docs/DECISIONS.md #1): long / short the market you picked with a margin and
// your leverage, at the REAL mark price; the position lives here with the real funding accruing and liquidates at the real distance. Paper
// dollars only — FEELESS never places, routes or holds a perps order. When the setup is right, "Take it real" opens the regulated venue.
const MARGINS = [25, 100, 500, 1000];
const pct = v => `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`;
const sgn = v => `${Number(v) < 0 ? '−' : '+'}${cash(Math.abs(Number(v) || 0))}`;   // −$20 · +$61, never $-20

export function PaperPerps({ row, lev, venues = {}, devAddress = '' }) {   // devAddress: the /dev/perps preview only
  const { wallet, signMessage } = useWallet() || {}; const addr = (wallet?.chain === 'solana' ? wallet.address : '') || devAddress;
  const [sess, setSess] = useState(() => (devAddress ? 'dev' : addr ? readChatSession(addr) : ''));
  useEffect(() => { setSess(devAddress ? 'dev' : addr ? readChatSession(addr) : ''); }, [addr, devAddress]);
  const [b, setB] = useState(null); const [margin, setMargin] = useState(100); const [busy, setBusy] = useState(false);
  const q = `address=${addr}&session=${encodeURIComponent(sess)}`;
  const load = useCallback(() => (addr && sess ? fetch(apiUrl(`/api/reputation/familia/paper-perps?${q}`)).then(r => (r.ok ? r.json() : null)).then(x => x && setB(x)).catch(() => {}) : Promise.resolve()), [addr, sess, q]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 10000); return () => clearInterval(t); }, [load]);
  useEffect(() => { (b?.liquidated || []).forEach(x => toast.error(`💥 Paper ${x.side} ${x.coin} ${x.lev}× liquidated — the margin ($${x.margin}) is gone`)); }, [b?.liquidated]);
  const equity = useGlide(b?.equity ?? 0);
  const act = async body => {
    setBusy(true);
    try { const r = await fetch(apiUrl('/api/reputation/familia/paper-perps'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: addr, session: sess, ...body }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || 'The paper desk said no'); setB(j); return true; }
    catch (e) { toast.error(e.message); return false; } finally { setBusy(false); }
  };
  if (!addr) return <p className="pp-gate" data-testid="pp-gate">Connect your wallet to open a paper perps book — $10,000 paper, the real prices.</p>;
  if (!sess) return <p className="pp-gate" data-testid="pp-gate">One signature keeps your paper book (no transaction, no fee). <button type="button" className="m-btn m-go"
    onClick={async () => { try { setSess(await getChatSession(addr, signMessage)); } catch (e) { toast.error(e.message); } }} data-testid="pp-signin">🔑 Sign in</button></p>;
  const maxLev = row?.maxLev || 1; const L = Math.min(lev, maxLev); const size = margin * L; const liqMove = Math.max(0, 100 / L - 0.5);
  return <div className="pp" data-testid="paper-perps">
    <header className="pp-head"><span><em>📉 THE PAPER DESK · LIVE PRICES · PAPER DOLLARS</em><b className="m-num" key={Math.round(b?.equity || 0)}>{cash(equity)}</b>
      <small>{b ? `${b.trades} closed${b.winPct != null ? ` · ${b.winPct}% won` : ''} · realized ${sgn(b.realized)} · cash ${cash(b.cash)}` : 'opening your book…'}</small></span>
      <u className="pp-eq" aria-hidden="true"><s className={(b?.equity ?? 1e4) >= (b?.start ?? 1e4) ? 'up' : 'dn'} style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, (b?.equity || 0) / ((b?.start || 1e4) * 2)))})` }} /></u></header>
    {row ? <div className="pp-ticket">
      <span className="pp-mkt"><b>{row.coin}-PERP</b><small>${Number(row.mark).toLocaleString('en-US', { maximumFractionDigits: row.mark >= 100 ? 0 : 4 })} · up to {maxLev}× · f {row.fundApr > 0 ? '+' : ''}{row.fundApr}%</small></span>
      <span className="m-seg pp-mg" role="radiogroup" aria-label="Margin">{MARGINS.map(m => <button key={m} type="button" role="radio" aria-checked={margin === m} className={margin === m ? 'active' : ''} onClick={() => setMargin(m)} data-testid={`pp-m-${m}`}>${m >= 1000 ? `${m / 1000}K` : m}</button>)}</span>
      <span className="pp-read"><em>{L}× · {cash(size)} position</em><small>wiped at {liqMove.toFixed(1)}% against you</small></span>
      <span className="pp-go"><button type="button" className="pp-long" disabled={busy} onClick={() => act({ act: 'open', coin: row.coin, side: 'long', margin, lev: L })} data-tip={`Paper LONG ${row.coin}: $${margin} margin × ${L}× at the live mark`} data-testid="pp-long">▲ LONG</button>
        <button type="button" className="pp-short" disabled={busy} onClick={() => act({ act: 'open', coin: row.coin, side: 'short', margin, lev: L })} data-tip={`Paper SHORT ${row.coin}: $${margin} margin × ${L}× at the live mark`} data-testid="pp-short">▼ SHORT</button></span>
      {(row.venues || []).length ? <span className="pp-real"><small>TAKE IT REAL — your account, their order ticket:</small>{row.venues.map(v => venues[v] ? <a key={v} className="m-btn" href={venues[v][1](row.coin)} target="_blank" rel="noopener noreferrer"
        data-tip={`Open ${venues[v][0]} — you place the real order there on your own account; FEELESS never routes it`} data-testid={`pp-real-${v}`}>{venues[v][0]} ↗</a> : null)}</span> : null}
    </div> : null}
    {(b?.open || []).length ? <ol className="pp-pos">{b.open.map((p, i) => <li key={p.id} className={p.pnl >= 0 ? 'is-up' : 'is-dn'} style={{ '--i': i }} data-testid={`pp-pos-${p.id}`}>
      <b className={`pp-side is-${p.side}`}>{p.side === 'long' ? '▲' : '▼'} {p.coin} {p.lev}×</b>
      <span className="pp-n"><em className="m-num">{sgn(p.pnl)}</em><small>{pct(p.pnlPct)} on {cash(p.margin)}{p.fund ? ` · funding ${sgn(p.fund)}` : ''}</small></span>
      <span className="pp-liq" data-tip={`Liquidation at $${Number(p.liq).toPrecision(5)} — ${p.toLiqPct}% away`}><u><s style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, (p.toLiqPct || 0) / (100 / p.lev)))})` }} /></u><small>{p.toLiqPct}% to liq</small></span>
      <button type="button" className="m-btn" disabled={busy} onClick={() => act({ act: 'close', id: p.id })} data-testid={`pp-close-${p.id}`} data-tip="Close at the live mark">Close</button></li>)}</ol>
      : <p className="pp-none">No paper position open — pick a market above, size it, long or short.</p>}
    {(b?.closed || []).length ? <p className="pp-tape">{b.closed.slice(0, 6).map(c => <span key={c.id} className={c.pnl >= 0 ? 'up' : 'dn'} title={`${c.side} ${c.coin} ${c.lev}× · ${c.why}`}>{c.coin} {c.side === 'long' ? '▲' : '▼'} {sgn(c.pnl)}{c.why === 'liquidated' ? ' 💥' : ''}</span>)}
      <button type="button" className="pp-reset" onClick={() => window.confirm('Reset your paper book to $10,000?') && act({ act: 'reset' })} data-testid="pp-reset">↺ reset</button></p> : null}
  </div>;
}
