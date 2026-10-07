import React, { useCallback, useEffect, useState } from 'react';
import NumInput from '../NumInput';
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
  const unit = asset === 'USDC' ? 'USDC' : 'SOL';
  return <section className="cc-panel treasury-hub m-stack" data-testid="treasury-hub">
    <MoneyFlows />
    <div className="m-grid">{[
      ['💸 Where do trading fees go?', <p key="a">Every FEELESS trade carries its own fee transfer inside the transaction the trader signs. Buys pay in SOL into the <b>SOL fee account</b>; USDC trades pay into the <b>USDC fee account</b>. The money lands the moment the trade confirms — no claiming, no middleman.</p>],
      ['🏦 Fee accounts vs treasury vs reserves vs Circle', <p key="b"><b>Fee accounts</b>: where fees arrive (your wallet owns them). <b>Treasury destinations</b>: where you send fees on (split plan). <b>Season reserve / badge pools</b>: SOL shared with badge holders. <b>Circle wallets</b>: custodial ops wallets, separate from fees.</p>],
      ['🔀 How a split works', <p key="c">Pick the asset and amount, review each cut, press Split. It's simulated first, you approve once, and the server re-reads every transaction on-chain and records only what moved. Auto-splitting would need a server-held key — FEELESS never has one.</p>],
    ].map(([t, body]) => <details key={t} className="m-card m-details"><summary className="m-label">{t}</summary>{body}</details>)}</div>
    <div className="m-card"><div className="m-label">READY TO SPLIT</div>
      <ul className="pulse-checks">{checks.map(([t, ok, how]) => <li key={t} className={ok ? 'ok' : 'bad'}><i>{ok ? '✓' : '!'}</i><span><b>{t}</b>{!ok && <small>{how}</small>}</span></li>)}</ul></div>
    <div className="m-grid">
      {d.feeAccounts.map(f => <div key={f.asset} className="m-card m-stat"><small>{f.label}</small><b className="m-num">{f.ok ? `${f.amount} ${f.asset === 'USDC' ? 'USDC' : 'SOL'}` : 'not set up'}</b>
        {f.ok && <span className="m-dim">{f.asset === 'USDC' ? money(f.amount) : px ? money(f.amount * px) : ''}</span>}{f.address && <code className="m-dim">{shortAddress(f.address)} <CopyBtn value={f.address} /></code>}{f.owner && <span className="m-dim">owner {shortAddress(f.owner)}</span>}</div>)}
      <div className="m-card m-stat"><small>Admin wallet (you)</small><b className="m-num">{d.adminSol != null ? `${d.adminSol.toFixed(3)} SOL` : '—'}</b><span className="m-dim">{px && d.adminSol ? money(d.adminSol * px) : ''}</span><code className="m-dim">{shortAddress(d.admin)} <CopyBtn value={d.admin} /></code></div>
      {d.reserves.map(r => <div key={r.address + r.label} className="m-card m-stat"><small>{r.label}</small><b className="m-num">{r.sol != null ? `${r.sol.toFixed(3)} SOL` : '—'}</b><span className="m-dim">{px && r.sol ? money(r.sol * px) : ''}</span><code className="m-dim">{shortAddress(r.address)} <CopyBtn value={r.address} /></code></div>)}
    </div>
    <div className="m-card is-hot m-stack"><div className="m-label">SPLIT NOW <em>signed by you · verified on-chain</em></div>
      {!routesOk ? <p className="m-dim">Set a split plan that adds to 100% below first.</p> : <>
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
