import React, { useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { useSolPrice, usd } from '../../lib/solPrice';

const ASSETS = [['sol', 'SOL'], ['fee', '$FEE'], ['feecat', '$FEECAT'], ['rfee', '$RFEE']];

// Creator-wallet-only sender: move SOL or FEELESS coins to other wallets (team, multisig, winners)
// straight from the connected creator wallet. Batches, simulates, one approval. Nothing custodial.
export function TreasurySend({ ownerWallets = [] }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [asset, setAsset] = useState('sol');
  const [lines, setLines] = useState('');
  const [status, setStatus] = useState('');
  const solPx = useSolPrice();
  const isCreator = wallet?.chain === 'solana' && ownerWallets.includes(wallet.address);
  const rows = lines.split('\n').map(l => l.trim()).filter(Boolean).map(l => { const [address, amount] = l.split(/[\s,]+/); return { address, amount: Number(amount) }; });
  const bad = rows.filter(r => !/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(r.address || '') || !(r.amount > 0));
  const total = rows.reduce((s, r) => s + (r.amount > 0 ? r.amount : 0), 0);
  const send = async () => {
    try {
      if (!isCreator) { await connect?.('solana'); return; }
      if (!rows.length || bad.length) throw new Error('One "address amount" per line.');
      if (!window.confirm(`Send ${total} ${asset.toUpperCase()} to ${rows.length} wallet(s) from ${wallet.address.slice(0, 4)}…? This cannot be undone.`)) return;
      const assets = (await (await fetch('/api/market/assets')).json()).assets || [];
      const mint = asset === 'sol' ? null : assets.find(a => a.id === asset)?.mint;
      const { batchSend } = await import('../../lib/batchSend');
      const sigs = await batchSend({ provider, owner: wallet.address, mint, recipients: rows, onStatus: setStatus, kind: 'transfer' });
      toast.success(`Sent in ${sigs.length} transaction${sigs.length > 1 ? 's' : ''}.`); setLines(''); setStatus('');
    } catch (e) { setStatus(''); toast.error(e.message || 'Send failed'); }
  };
  return <div className="cc-block treasury-send"><h4>Send from the creator wallet</h4>
    {!isCreator ? <p className="cc-empty">Only works while the creator wallet ({ownerWallets[0]?.slice(0, 4)}…{ownerWallets[0]?.slice(-4)}) is connected. <button type="button" className="btn-outline" onClick={() => connect?.('solana')}>Connect it</button></p> : <>
      <div className="cc-toolbar"><select value={asset} onChange={e => setAsset(e.target.value)}>{ASSETS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select><small className="cc-empty">One per line: <code>address amount</code></small></div>
      <textarea rows={4} value={lines} onChange={e => setLines(e.target.value)} placeholder={'7xKX…gAsU 0.5\nGygj…BUpA 1.25'} />
      <small className="cc-empty">{rows.length} wallet(s) · total {total} {asset.toUpperCase()} {asset === 'sol' ? usd(total, solPx) : ''}{bad.length ? ` · ⚠ ${bad.length} line(s) invalid` : ''}</small>
      <button type="button" className="btn-primary" disabled={!!status || !rows.length || bad.length > 0} onClick={send}>{status || 'Review & send'}</button>
    </>}
  </div>;
}
