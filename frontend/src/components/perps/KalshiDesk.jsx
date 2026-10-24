import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../../lib/api';
import { useGlide } from '../../lib/useGlide';
import { post, signTx } from '../../lib/perps';

// ⏱ KALSHI 15-MIN UP / DOWN — the US-legal (CFTC-regulated) side of the perps desk, tokenized on Solana by DFlow (backend/kalshi_trade.py).
// Live odds on the picked coin (the window's target vs the true price, its countdown, what $1 pays) and — once DFlow's production key is in
// (`tradable`) — the trade: 🪪 Proof (DFlow's free KYC, once per person; FEELESS never sees ID data) → UP / DOWN from $1 → the wallet signs
// DFlow's transaction → FEELESS sends only what it built → the fill is followed → settled winners redeem to USDC.
const STAKES = [1, 5, 10, 25];
const px = v => (v == null || !Number.isFinite(v) ? '—' : v >= 1000 ? `$${v.toLocaleString('en-US', { maximumFractionDigits: 2 })}` : `$${Number(v).toFixed(v >= 10 ? 2 : 4)}`);

export function kalshiRead(k, mark, now) {
  const m = k?.m15; if (!m || (m.yes == null && m.no == null)) return null;
  const end = Date.parse(m.closes || ''); const left = Number.isFinite(end) ? Math.max(0, Math.round((end - now) / 1000)) : null;
  const up = m.yes != null ? m.yes : 1 - m.no;
  return { up, left, frac: left == null ? 0 : Math.min(1, left / 900), above: m.target > 0 && mark > 0 ? mark - m.target : null, target: m.target,
    payUp: m.yes > 0 ? 1 / m.yes : null, payDn: m.no > 0 ? 1 / m.no : null, day: k?.day || null };
}
const dayWord = iso => { const d = new Date(iso); return Number.isFinite(d.getTime()) ? d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric' }).toUpperCase() : 'CLOSE'; };

export function KalshiDesk({ asset, k, mark, now, tradable, addr, wallet, provider, connect }) {
  const r = kalshiRead(k, mark, now); const g = useGlide(r ? Math.round(r.up * 1000) / 10 : 50, 600);
  const [usd, setUsd] = useState(5); const [busy, setBusy] = useState(''); const [proof, setProof] = useState(null); const [pos, setPos] = useState([]);
  const loadProof = useCallback(() => { if (!tradable || !addr) return; fetch(apiUrl(`/api/reputation/familia/kalshi/proof?address=${addr}`)).then(x => (x.ok ? x.json() : null)).then(x => x && setProof(!!x.verified)).catch(() => {}); }, [tradable, addr]);
  const loadPos = useCallback(() => { if (!tradable || !addr) return; fetch(apiUrl(`/api/reputation/familia/kalshi/positions?address=${addr}`)).then(x => (x.ok ? x.json() : null)).then(x => x && setPos(x.positions || [])).catch(() => {}); }, [tradable, addr]);
  useEffect(() => { loadProof(); loadPos(); const t = setInterval(() => { if (!document.hidden) { if (!proof) loadProof(); loadPos(); } }, 8000); return () => clearInterval(t); }, [loadProof, loadPos, proof]);
  const need = async () => { if (!wallet?.address || !provider) { await connect?.('solana'); return false; } return true; };
  const verify = async () => { if (!(await need())) return;
    try { const ts = Date.now(); const sig = await provider.signMessage(new TextEncoder().encode(`Proof KYC verification: ${ts}`));
      const bs58 = (await import('bs58')).default; const s58 = bs58.encode(sig?.signature || sig);
      window.open(`https://dflow.net/proof?wallet=${addr}&signature=${s58}&timestamp=${ts}&redirect_uri=${encodeURIComponent(window.location.href)}`, '_blank', 'noopener'); }
    catch (e) { toast.error(e.message || 'Signature declined.'); } };
  const send = async (label, body) => { if (!(await need())) return; setBusy(label);
    try { const b = await post('/api/reputation/familia/kalshi/order', { address: addr, ...body }); const signed = await signTx(provider, addr, b.transaction);
      const { signature } = await post('/api/reputation/familia/kalshi/send', { signed });
      let st = 'pending';
      for (let i = 0; i < 30 && !['closed', 'failed', 'expired'].includes(st); i += 1) { await new Promise(res => setTimeout(res, 2000));
        st = (await (await fetch(apiUrl(`/api/reputation/familia/kalshi/status?signature=${signature}&lastValidBlockHeight=${b.lastValidBlockHeight || 0}`))).json()).status; }
      if (st === 'closed') toast.success(`✅ ${label} — filled`); else if (st === 'failed' || st === 'expired') toast.error(`${label} — ${st}, your USDC stays`); else toast(`${label} — sent, still filling`);
      loadPos(); }
    catch (e) { if (String(e.message).startsWith('PROOF')) setProof(false); toast.error(e.message); } finally { setBusy(''); } };
  if (!r) return <div className="kd is-off" data-testid="kalshi-desk"><b>⏱ KALSHI</b><small>no live 15-minute window on {asset} right now</small></div>;
  const mm = r.left == null ? '—' : `${Math.floor(r.left / 60)}:${String(r.left % 60).padStart(2, '0')}`;
  return <div className={`kd ${r.up >= 0.5 ? 'is-up' : 'is-dn'}`} data-testid="kalshi-desk">
    <div className="kd-odds" data-testid="pd-odds" data-tip={`Kalshi (CFTC-regulated, US-legal): "${asset} price up in the next 15 mins?" — UP pays $1 a contract if ${asset} ends the window at or above the target`}>
      <span className="kd-hero"><em>⏱ {asset} UP IN 15 MIN?</em><b className="m-num">{g.toFixed(0)}%</b><small>KALSHI · US · CFTC</small></span>
      <span className="kd-k"><em>TARGET</em><b className="m-num">{px(r.target)}</b><small className={`m-num ${(r.above ?? 0) >= 0 ? 'is-up' : 'is-dn'}`}>{r.above == null ? '' : `live ${r.above >= 0 ? '▲ +' : '▼ −'}${px(Math.abs(r.above))}`}</small></span>
      <span className="kd-k kd-clock"><em>CLOSES IN</em><b className="m-num">{mm}</b><u aria-hidden="true"><s style={{ transform: `scaleX(${r.frac})` }} /></u></span>
      <span className="kd-k"><em>$1 PAYS</em><b className="m-num is-up">{r.payUp ? `$${r.payUp.toFixed(2)}` : '—'} <i>UP</i></b><b className="m-num is-dn">{r.payDn ? `$${r.payDn.toFixed(2)}` : '—'} <i>DOWN</i></b></span>
      {r.day ? <span className="kd-k"><em>{dayWord(r.day.closes)} · ABOVE {px(r.day.strike)}</em><b className="m-num">{Math.round(r.day.yes * 100)}%</b><u aria-hidden="true"><s style={{ transform: `scaleX(${r.day.yes})` }} /></u></span> : null}
      <div className="kd-split" aria-hidden="true"><s className="is-up" style={{ transform: `scaleX(${g / 100})` }} /><s className="is-dn" style={{ transform: `scaleX(${1 - g / 100})` }} /></div>
    </div>
    {tradable ? <div className="kd-trade">
      {proof === false ? <button type="button" className="kd-proof" onClick={verify} data-tip="DFlow Proof: a one-time free ID check (Stripe) linked to this wallet — Kalshi is a regulated market. FEELESS never sees your ID." data-testid="kd-proof">🪪 VERIFY WALLET · ONE TIME</button> : <>
        <span className="pt-chips">{STAKES.map(s => <button key={s} type="button" className={usd === s ? 'is-on' : ''} onClick={() => setUsd(s)} data-tip={`Spend $${s}`} data-testid={`kd-u-${s}`}>${s}</button>)}</span>
        <button type="button" className="kd-buy is-up" disabled={!!busy} onClick={() => send(`UP $${usd} on ${asset}`, { coin: asset, side: 'up', usd })} data-tip={`$${usd} on ${asset} ending this window above the target`} data-testid="kd-up">▲ UP · ${usd} → {r.payUp ? `$${(usd * r.payUp).toFixed(2)}` : '—'}</button>
        <button type="button" className="kd-buy is-dn" disabled={!!busy} onClick={() => send(`DOWN $${usd} on ${asset}`, { coin: asset, side: 'down', usd })} data-tip={`$${usd} on ${asset} ending this window below the target`} data-testid="kd-down">▼ DOWN · ${usd} → {r.payDn ? `$${(usd * r.payDn).toFixed(2)}` : '—'}</button></>}
      {busy ? <small className="kd-busy">{busy}…</small> : null}
    </div> : <span className="kd-lock" data-tip="Trading turns on when DFlow's production API key is in backend/.env (DFLOW_API_KEY)">🔒 TRADING WITH THE DFLOW KEY</span>}
    {tradable && pos.length ? <ol className="kd-pos">{pos.map(p => <li key={p.mint} className={p.won === false ? 'is-dn' : p.won ? 'is-up' : ''}>
      <b>{p.side === 'UP' ? '▲' : '▼'} {p.contracts} {p.side}</b><small>{p.title || p.ticker} · {p.status}</small>
      {p.redeemable ? <button type="button" disabled={!!busy} onClick={() => send(`Redeem ${p.contracts} ${p.side}`, { act: 'redeem', mint: p.mint, amount: p.raw })} data-tip="Cash the winning contracts into USDC">REDEEM ${p.contracts.toFixed(2)}</button> : null}</li>)}</ol> : null}
  </div>;
}
