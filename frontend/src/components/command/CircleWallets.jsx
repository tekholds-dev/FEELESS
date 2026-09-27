import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { CopyBtn } from '../CopyBtn';

const CHAINS = [['SOL-DEVNET', 'Solana devnet'], ['BASE-SEPOLIA', 'Base Sepolia'], ['ETH-SEPOLIA', 'Ethereum Sepolia'], ['ARB-SEPOLIA', 'Arbitrum Sepolia'], ['SOL', 'Solana mainnet'], ['BASE', 'Base mainnet']];

// Creator-only: wallets created and held by Circle (keys never touch FEELESS), listed with balances.
export function CircleWallets({ call }) {
  const [status, setStatus] = useState(null);
  const [wallets, setWallets] = useState([]);
  const [f, setF] = useState({ blockchain: 'SOL-DEVNET', name: '' });
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    call('/admin/circle/status').then(setStatus).catch(e => setStatus({ configured: false, reason: e.message }));
    call('/admin/circle/wallets').then(d => setWallets(d.wallets || [])).catch(() => {});
  }, [call]);
  useEffect(() => { load(); }, [load]);
  const create = async () => {
    const main = !f.blockchain.includes('-');
    if (main && !window.confirm(`Create a MAINNET ${f.blockchain} wallet? Real funds sent to it are real.`)) return;
    setBusy(true);
    try { await call('/admin/circle/wallets', { method: 'POST', body: JSON.stringify({ blockchain: f.blockchain, name: f.name || 'Creator wallet' }) }); toast.success('Wallet created'); setF(x => ({ ...x, name: '' })); load(); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return <div className="cc-block circle-wallets"><h4>Creator wallets <small className="chain-tag">Circle · {status?.testnet ? 'TESTNET' : 'LIVE'}</small></h4>
    {!status?.configured ? <div className="cc-empty"><p><b>Not active yet:</b> {status?.reason || 'checking…'}</p>
      <ol><li>In a terminal on this computer run <code>node circle/register-entity-secret.mjs</code> (once).</li><li>Back up <code>~/.circle/recovery-file.json</code> somewhere safe (password manager).</li><li>Paste the printed <code>ENTITY_SECRET=…</code> line into <code>backend/.env</code>.</li><li>Start the wallet service: <code>node circle/server.mjs</code>, then Re-check.</li></ol>
      <button type="button" className="btn-outline" onClick={load}>Re-check</button></div> : <>
      <div className="cc-toolbar"><select value={f.blockchain} onChange={e => setF(x => ({ ...x, blockchain: e.target.value }))}>{CHAINS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select><input placeholder="Wallet name (e.g. Treasury ops)" value={f.name} maxLength={40} onChange={e => setF(x => ({ ...x, name: e.target.value }))} /><button type="button" className="btn-primary" disabled={busy} onClick={create}>{busy ? 'Creating…' : 'Create wallet'}</button></div>
      <div className="cw-list">{!wallets.length ? <small className="cc-empty">No wallets yet.</small> : wallets.map(w => <div key={w.id} className="cw-row"><b>{w.name || 'Wallet'}</b><span className="chain-tag">{w.blockchain}</span><code>{w.address?.slice(0, 6)}…{w.address?.slice(-4)}</code><CopyBtn value={w.address} /><em>{(w.balances || []).map(b => `${Number(b.amount).toLocaleString()} ${b.symbol}`).join(' · ') || 'empty'}</em></div>)}</div>
      <small className="cc-empty">Keys are held by Circle and never touch FEELESS. Recovery lives in your ~/.circle recovery file. Fund EOA wallets with the chain's gas token before sending.</small>
    </>}
  </div>;
}
