import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { errorText } from '../../lib/api';
import { shortAddress } from '../../lib/dexscreener';
import { CopyBtn } from '../CopyBtn';
import { MoneyFlows } from './MoneyFlows';
import { useSolUsd, money } from './FeeInputs';

// Treasury: where FEELESS money sits right now, the split plan, and a real split you sign from your own wallet.
// Nothing moves automatically: that would need a hot key on the server, which FEELESS never holds.
const WSOL = 'So11111111111111111111111111111111111111112';
const USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const floor = (v, d) => Math.floor(v * 10 ** d + 1e-6) / 10 ** d;

export function TreasuryHub({ call, prefill }) {
  const { wallet, provider, connect } = useWallet() || {};
  const px = useSolUsd();
  const [d, setD] = useState(null);
  const [asset, setAsset] = useState(prefill?.asset || 'SOL');
  const [amount, setAmount] = useState(prefill?.amount || '');
  useEffect(() => { if (prefill) { setAsset(prefill.asset); setAmount(prefill.amount); } }, [prefill]);
  const [busy, setBusy] = useState('');
  const load = useCallback(() => call('/admin/treasury/money').then(setD).catch(e => toast.error(errorText(e))), [call]);
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
  return <section className="cc-panel treasury-hub" data-testid="treasury-hub">
    <MoneyFlows />
    <div className="tr-explains">
      <details className="tr-explain"><summary>💸 Where do trading fees go?</summary>
        <p>Every FEELESS trade carries its own fee transfer inside the transaction the trader signs. Buys pay in SOL into the <b>SOL fee account</b> (a wrapped-SOL token account you own); USDC trades pay into the <b>USDC fee account</b>. The money lands the moment the trade confirms — no claiming, no middleman.</p></details>
      <details className="tr-explain"><summary>🏦 Fee accounts vs treasury vs reserves vs Circle</summary>
        <ul><li><b>Fee accounts</b> — where fees arrive. Owned by your wallet.</li>
          <li><b>Treasury destinations</b> — where you send fees on (multisig, buy-back, team). Set in the split plan.</li>
          <li><b>Season reserve / badge pools</b> — wallets whose SOL is shared with badge holders (Badges tab).</li>
          <li><b>Circle wallets</b> — custodial wallets run through Circle's API for ops; separate from fees.</li></ul></details>
      <details className="tr-explain"><summary>🔀 How a split works (and why it isn't automatic)</summary>
        <p>Pick the asset and amount, review each destination's cut, press Split. It's simulated first, you approve once in your wallet, and the server re-reads every transaction on-chain and records only what really moved. Auto-splitting would need the server to hold a private key — FEELESS never does. A Squads multisig as the main destination is the safe setup.</p></details>
    </div>
    <div className="tr-status">{checks.map(([t, ok, how]) => <div key={t} className={ok ? 'ok' : 'todo'}><i>{ok ? '✓' : '!'}</i><span><b>{t}</b>{!ok && <small>{how}</small>}</span></div>)}</div>
    <div className="tr-money">
      {d.feeAccounts.map(f => <div key={f.asset} className="tr-card"><small>{f.label}</small><b>{f.ok ? `${f.amount} ${f.asset === 'USDC' ? 'USDC' : 'SOL'}` : 'not set up'}</b>
        {f.ok && <em>{f.asset === 'USDC' ? money(f.amount) : px ? money(f.amount * px) : ''}</em>}{f.address && <code>{shortAddress(f.address)}<CopyBtn value={f.address} /></code>}{f.owner && <span>owner {shortAddress(f.owner)}</span>}</div>)}
      <div className="tr-card"><small>Admin wallet (you)</small><b>{d.adminSol != null ? `${d.adminSol.toFixed(3)} SOL` : '—'}</b><em>{px && d.adminSol ? money(d.adminSol * px) : ''}</em><code>{shortAddress(d.admin)}<CopyBtn value={d.admin} /></code></div>
      {d.reserves.map(r => <div key={r.address + r.label} className="tr-card tr-reserve"><small>{r.label}</small><b>{r.sol != null ? `${r.sol.toFixed(3)} SOL` : '—'}</b><em>{px && r.sol ? money(r.sol * px) : ''}</em><code>{shortAddress(r.address)}<CopyBtn value={r.address} /></code></div>)}
    </div>
    <div className="cc-block tr-split"><h4>Split now <small>signed by you · verified on-chain</small></h4>
      {!routesOk ? <p className="cc-empty">Set a split plan that adds to 100% below first.</p> : <>
        <div className="bdg-seg">{['SOL', 'wSOL', 'USDC'].map(a => <button key={a} type="button" className={asset === a ? 'active' : ''} onClick={() => { setAsset(a); setAmount(''); }}>{a === 'SOL' ? 'SOL · from wallet' : `${a} · fee account`}</button>)}</div>
        <div className="bdg-form-row"><label className="bdg-pct"><input inputMode="decimal" placeholder="0" value={amount} onChange={e => setAmount(e.target.value.replace(/[^0-9.]/g, ''))} /><span>{asset === 'USDC' ? 'USDC' : 'SOL'}{amt ? ` · ${usdOf(amt)}` : ''}</span></label>
          {avail != null && <button type="button" className="btn-outline" onClick={() => setAmount(String(avail))}>Max {avail}</button>}</div>
        {asset === 'wSOL' && <small className="cc-empty">Destinations receive wrapped SOL (they can unwrap in Phantom). Your fee account stays open so fees keep landing.</small>}
        <div className="tr-rows">{rows.map(r => <div key={r.address} className="tr-row"><b>{r.label || shortAddress(r.address)}</b><span>{r.pct}%</span><code>{shortAddress(r.address)}</code><em>{r.amount} {asset === 'USDC' ? 'USDC' : 'SOL'}{usdOf(r.amount) ? ` · ${usdOf(r.amount)}` : ''}</em></div>)}</div>
        {rows.length > 0 && (() => { const txs = Math.ceil(rows.length / (asset === 'SOL' ? 18 : 6)); const net = txs * 0.000005; const rent = asset === 'SOL' ? 0 : rows.length * 0.00204;
          return <small className="tr-cost">Cost to split: {txs} transaction{txs > 1 ? 's' : ''} ≈ {net.toFixed(6)} SOL network fee{rent ? ` + up to ${rent.toFixed(4)} SOL one-time account rent for destinations that never held ${asset}` : ''}{px ? ` (≈ ${money((net + rent) * px)})` : ''}. FEELESS charges nothing.</small>; })()}
        <button type="button" className="btn-primary" disabled={!!busy || (holderOk && !rows.length)} onClick={split}>{busy || (holderOk ? `Split ${amt || ''} ${asset} · sign once` : 'Connect the owner wallet')}</button></>}
    </div>
    {d.splits?.length > 0 && <div className="cc-block"><h4>Recent splits</h4>{d.splits.map(s => <div key={s.sigs[0]} className="cc-sig"><span>{new Date(s.at * 1000).toLocaleString()}</span><b>{s.total} {s.asset}</b><span>{s.moved.length} transfers</span><a href={`https://solscan.io/tx/${s.sigs[0]}`} target="_blank" rel="noopener noreferrer">receipt ↗</a></div>)}</div>}
  </section>;
}
