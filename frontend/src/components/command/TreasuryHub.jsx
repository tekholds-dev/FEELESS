import React, { useCallback, useEffect, useState } from 'react';
import NumInput from '../NumInput';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { errorText } from '../../lib/api';
import { shortAddress } from '../../lib/dexscreener';
import { CopyBtn } from '../CopyBtn';
import { MoneyFlows } from './MoneyFlows';
import { useSolUsd, money } from './FeeInputs';
import { shaped } from '../../lib/shape';
import { Coins, DollarSign, ShieldCheck, Wallet as WalletIc } from 'lucide-react';
import { useCountUp } from '../../lib/useCountUp';
import '../../styles/treasuryHub.css';
const TREASURY = shaped({ feeAccounts: [], reserves: [], splits: [], routes: [], adminSol: 0 });

// Treasury: where FEELESS money sits right now, the split plan, and a real split you sign from your own wallet.
// Nothing moves automatically: that would need a hot key on the server, which FEELESS never holds.
const WSOL = 'So11111111111111111111111111111111111111112';
const USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const floor = (v, d) => Math.floor(v * 10 ** d + 1e-6) / 10 ** d;

// 💰 owner 2026-11-12 "the money folder ugh": the treasury reads like a desk, not a form — one live total with its mix, a readiness ring,
// a card per wallet with its share of the total, and the split plan drawn as one bar. Every number is the treasury read's own; nothing moves here.
const SEG = ['var(--m-accent)', 'var(--m-warn)', 'color-mix(in srgb, var(--m-accent) 45%, var(--m-text))', 'color-mix(in srgb, var(--m-warn) 50%, var(--m-danger))', 'var(--m-mute)', 'color-mix(in srgb, var(--m-accent) 30%, var(--m-bg))'];
export function walletRows(d, px) {
  const rows = [...(d.feeAccounts || []).map(f => ({ key: f.asset, ic: f.asset === 'USDC' ? DollarSign : Coins, label: f.label, ok: !!f.ok, amount: Number(f.amount) || 0, unit: f.asset === 'USDC' ? 'USDC' : 'SOL', usd: f.ok ? (f.asset === 'USDC' ? Number(f.amount) || 0 : px ? (Number(f.amount) || 0) * px : null) : null, address: f.address, owner: f.owner })),
    { key: 'admin', ic: WalletIc, label: 'Admin wallet (you)', ok: d.adminSol != null, amount: Number(d.adminSol) || 0, unit: 'SOL', usd: px && d.adminSol != null ? d.adminSol * px : null, address: d.admin },
    ...(d.reserves || []).map(r => ({ key: r.address + r.label, ic: ShieldCheck, label: r.label, ok: r.sol != null, amount: Number(r.sol) || 0, unit: 'SOL', usd: px && r.sol != null ? r.sol * px : null, address: r.address }))];
  const total = rows.reduce((a, r) => a + (r.usd || 0), 0);
  return { rows: rows.map((r, i) => ({ ...r, share: total > 0 && r.usd ? r.usd / total : 0, color: SEG[i % SEG.length] })), total };
}
function Total({ usd }) { const c = useCountUp(Math.round((usd || 0) * 100)); return <b className="trh-total m-num" data-testid="trh-total">{money(c / 100)}</b>; }
function Ring({ done, all }) {
  const r = 26; const C = 2 * Math.PI * r; const f = all ? done / all : 0;
  return <svg className={`trh-ring${done === all ? ' is-ok' : ''}`} viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r={r} className="trh-ring-bg" /><circle cx="32" cy="32" r={r} className="trh-ring-fg" strokeDasharray={`${C * f} ${C}`} transform="rotate(-90 32 32)" /><text x="32" y="37" textAnchor="middle">{done}/{all}</text></svg>;
}
export function TreasuryHub({ call, prefill }) {
  const { wallet, provider, connect } = useWallet() || {};
  const px = useSolUsd();
  const [d, setD] = useState(null);   // TREASURY: every list the hub reads exists, even on an empty reply
  const [asset, setAsset] = useState(prefill?.asset || 'SOL');
  const [amount, setAmount] = useState(prefill?.amount || '');
  useEffect(() => { if (prefill) { setAsset(prefill.asset); setAmount(prefill.amount); } }, [prefill]);
  const [busy, setBusy] = useState('');
  const load = useCallback(() => call('/admin/treasury/money').then(x => setD(TREASURY(x))).catch(e => toast.error(errorText(e))), [call]);
  useEffect(() => { load(); }, [load]);
  if (!d) return <p className="cc-empty">Reading every FEELESS wallet…</p>;
  const fee = k => d.feeAccounts.find(f => f.asset === k) || {};
  const routes = d.routes || [];
  const routesOk = routes.length > 0 && Math.abs(routes.reduce((a, r) => a + Number(r.pct), 0) - 100) < 0.01;
  const src = asset === 'SOL' ? null : fee(asset);
  const holderOk = asset === 'SOL' ? wallet?.chain === 'solana' : src?.owner && src.owner === wallet?.address;
  const dec = asset === 'USDC' ? 6 : 9;
  const avail = asset === 'SOL' ? null : src?.amount ?? 0;
  const amt = Number(amount) || 0;
  const rows = routes.map(r => ({ ...r, amount: floor((amt * Number(r.pct)) / 100, dec) })).filter(r => r.amount > 0);
  const usdOf = v => (asset === 'USDC' ? money(v) : px ? money(v * px) : '');
  const checks = [
    ['SOL fee account exists', fee('wSOL').ok, 'Trading & fees › create fee accounts. Buys pay the FEELESS fee in SOL here.'],
    ['USDC fee account exists', fee('USDC').ok, 'Trading & fees › create fee accounts. USDC-side trades pay here.'],
    ['Split plan adds to 100%', routesOk, 'Set destinations below (e.g. 60% multisig, 25% buy-back, 15% team).'],
    ['Owner wallet connected to split', holderOk, asset === 'SOL' ? 'Connect a Solana wallet.' : `Connect ${src?.owner ? shortAddress(src.owner) : 'the fee account owner'}.`],
  ];
  const mix = walletRows(d, px);
  const split = async () => {
    try {
      if (!holderOk) { await connect?.('solana'); return; }
      if (asset !== 'SOL' && amt > (avail || 0)) throw new Error(`Only ${avail} ${asset} in the fee account.`);
      const { batchSend } = await import('../../lib/batchSend');
      const sigs = await batchSend({ provider, owner: wallet.address, mint: asset === 'SOL' ? null : asset === 'USDC' ? USDC : WSOL, recipients: rows.map(r => ({ address: r.address, amount: r.amount })), source: asset === 'SOL' ? null : src.address, kind: 'treasury-split', onStatus: setBusy });
      const r = await call('/admin/treasury/split', { method: 'POST', body: JSON.stringify({ sigs, asset }) });
      toast.success(`Split ${r.total} ${asset} across ${r.transfers} transfers — verified on-chain.`); setAmount(''); load();
    } catch (e) { toast.error(errorText(e)); } finally { setBusy(''); }
  };
  const unit = asset === 'USDC' ? 'USDC' : 'SOL';
  return <section className="cc-panel treasury-hub m-stack" data-testid="treasury-hub">
    <div className="trh-hero m-card m-live" data-testid="trh-hero">
      <div className="trh-sum"><span className="m-label">EVERY FEELESS WALLET</span><Total usd={mix.total} /><small className="m-dim">{mix.rows.length} wallets{px ? ` · SOL ${money(px)}` : ' · reading the SOL price'}</small>
        <div className="trh-mix" role="img" aria-label={`Where the money sits: ${mix.rows.filter(r => r.share > 0).map(r => `${r.label} ${Math.round(r.share * 100)}%`).join(', ') || 'nothing held yet'}`}>{mix.rows.filter(r => r.share > 0).map((r, i) => <i key={r.key} style={{ '--w': r.share, '--c': r.color, '--i': i }} data-tip={`${r.label}: ${r.usd != null ? money(r.usd) : '—'} (${Math.round(r.share * 100)}%)`} />)}</div>
        <ul className="trh-legend">{mix.rows.filter(r => r.share > 0).map(r => <li key={r.key} style={{ '--c': r.color }}><i aria-hidden="true" />{r.label}<b className="m-num">{Math.round(r.share * 100)}%</b></li>)}</ul></div>
      <div className="trh-ready"><Ring done={checks.filter(c => c[1]).length} all={checks.length} /><div><span className="m-label">READY TO SPLIT</span>
        <ul className="trh-checks">{checks.map(([t, ok, how]) => <li key={t} className={ok ? 'is-ok' : 'is-bad'} data-tip={ok ? 'Done' : how} tabIndex={0}><i aria-hidden="true">{ok ? '✓' : '!'}</i>{t}</li>)}</ul></div></div>
    </div>
    <div className="trh-wallets" data-testid="trh-wallets">{mix.rows.map((r, i) => <article key={r.key} className={`trh-w${r.ok ? '' : ' is-off'}`} style={{ '--c': r.color, '--i': i }}>
      <header><r.ic size={16} aria-hidden="true" /><small>{r.label}</small></header>
      <b className="m-num">{r.ok ? `${r.unit === 'USDC' ? r.amount : r.amount.toFixed(r.amount >= 1 ? 3 : 4)} ${r.unit}` : 'not set up'}</b>
      <span className="trh-w-usd m-num">{r.usd != null ? money(r.usd) : r.ok ? 'reading price' : 'Trading & fees › create it'}</span>
      <span className="trh-w-bar" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, r.share)})` }} /></span>
      <footer>{r.address ? <code>{shortAddress(r.address)} <CopyBtn value={r.address} /></code> : <code>—</code>}<em className="m-num">{Math.round(r.share * 100)}%</em></footer>{r.owner ? <small className="trh-w-own">owner {shortAddress(r.owner)}</small> : null}</article>)}</div>
    <div className="m-card is-hot m-stack"><div className="m-label">SPLIT NOW <em>signed by you · verified on-chain</em></div>
      {!routesOk ? <p className="m-dim">Set a split plan that adds to 100% below first.</p> : <>
        <div className="trh-plan" role="img" aria-label={`Split plan: ${routes.map(r => `${r.label || shortAddress(r.address)} ${r.pct}%`).join(', ')}`}>{routes.map((r, i) => <span key={r.address} style={{ '--w': Number(r.pct) / 100, '--c': SEG[i % SEG.length], '--i': i }} data-tip={`${r.label || shortAddress(r.address)} gets ${r.pct}%${rows.find(x => x.address === r.address) ? ` · ${rows.find(x => x.address === r.address).amount} ${unit}` : ''}`}><b>{r.pct}%</b><small>{r.label || shortAddress(r.address)}</small></span>)}</div>
        <div className="m-seg">{['SOL', 'wSOL', 'USDC'].map(a => <button key={a} type="button" className={asset === a ? 'active' : ''} onClick={() => { setAsset(a); setAmount(''); }}>{a === 'SOL' ? 'SOL · from wallet' : `${a} · fee account`}</button>)}</div>
        <div className="m-row"><NumInput className="m-input" style={{ maxWidth: 200 }} inputMode="decimal" placeholder="0" value={amount} onChange={e => setAmount(e.target.value.replace(/[^0-9.]/g, ''))} aria-label="Amount to split" /><span className="m-dim">{unit}{amt ? ` · ${usdOf(amt)}` : ''}</span>
          {avail != null && <button type="button" className="m-btn" onClick={() => setAmount(String(avail))}>Max {avail}</button>}</div>
        {asset === 'wSOL' && <small className="m-dim">Destinations receive wrapped SOL (they can unwrap in Phantom). Your fee account stays open so fees keep landing.</small>}
        {rows.length > 0 && <dl className="m-kv">{rows.map(r => <React.Fragment key={r.address}><dt>{r.label || shortAddress(r.address)} · {r.pct}%</dt><dd>{r.amount} {unit}{usdOf(r.amount) ? ` · ${usdOf(r.amount)}` : ''} <code>{shortAddress(r.address)}</code></dd></React.Fragment>)}</dl>}
        {rows.length > 0 && (() => { const txs = Math.ceil(rows.length / (asset === 'SOL' ? 18 : 6)); const net = txs * 0.000005; const rent = asset === 'SOL' ? 0 : rows.length * 0.00204;
          return <div className="m-note"><b>Cost to split</b>{txs} transaction{txs > 1 ? 's' : ''} ≈ {net.toFixed(6)} SOL network fee{rent ? ` + up to ${rent.toFixed(4)} SOL one-time account rent for destinations that never held ${asset}` : ''}{px ? ` (≈ ${money((net + rent) * px)})` : ''}. FEELESS charges nothing.</div>; })()}
        <button type="button" className="m-btn primary wide" disabled={!!busy || (holderOk && !rows.length)} onClick={split}>{busy || (holderOk ? `Split ${amt || ''} ${asset} · sign once` : 'Connect the owner wallet')}</button></>}
    </div>
    {d.splits?.length > 0 && <div className="m-card"><div className="m-label">RECENT SPLITS</div><dl className="m-kv">{d.splits.map(s2 => <React.Fragment key={s2.sigs[0]}><dt>{new Date(s2.at * 1000).toLocaleString()}</dt><dd>{s2.total} {s2.asset} · {s2.moved.length} transfers · <a href={`https://solscan.io/tx/${s2.sigs[0]}`} target="_blank" rel="noopener noreferrer">receipt ↗</a></dd></React.Fragment>)}</dl></div>}
  </section>;
}
