import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { CopyBtn } from '../CopyBtn';

// Circle ties networks to the key: TEST keys only reach testnets, LIVE keys only mainnets.
const CHAINS = { test: [['SOL-DEVNET', 'Solana devnet'], ['BASE-SEPOLIA', 'Base Sepolia'], ['ETH-SEPOLIA', 'Ethereum Sepolia'], ['ARB-SEPOLIA', 'Arbitrum Sepolia']], live: [['SOL', 'Solana mainnet'], ['BASE', 'Base mainnet'], ['ETH', 'Ethereum mainnet'], ['ARB', 'Arbitrum mainnet'], ['MATIC', 'Polygon mainnet']] };

// Creator-only: wallets created and held by Circle (keys never touch FEELESS), listed with balances.
export function CircleWallets({ call }) {
  const [status, setStatus] = useState(null);
  const [wallets, setWallets] = useState([]);
  const [f, setF] = useState({ blockchain: '', name: '' });
  const [meta, setMeta] = useState({});
  const chains = CHAINS[status?.testnet ? 'test' : 'live'];
  const blockchain = chains.some(([k]) => k === f.blockchain) ? f.blockchain : chains[0][0];
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    call('/admin/circle/status').then(setStatus).catch(e => setStatus({ configured: false, reason: e.message }));
    call('/admin/circle/wallets').then(d => setWallets(d.wallets || [])).catch(() => {});
    call('/admin/circle/meta').then(setMeta).catch(() => {});
  }, [call]);
  useEffect(() => { load(); }, [load]);
  const create = async () => {
    const main = !blockchain.includes('-');
    if (main && !window.confirm(`Create a MAINNET ${blockchain} wallet? Real funds sent to it are real.`)) return;
    setBusy(true);
    try { await call('/admin/circle/wallets', { method: 'POST', body: JSON.stringify({ blockchain, name: f.name || 'Creator wallet' }) }); toast.success('Wallet created'); setF(x => ({ ...x, name: '' })); load(); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return <div className="cc-block circle-wallets"><h4>Creator wallets <small className="chain-tag">Circle · {status?.testnet ? 'TESTNET' : 'LIVE'}</small></h4>
    <p className="cc-note"><b>Gas funding:</b> Circle holds the keys, but these are normal on-chain wallets. Before an outbound transfer or contract call, fund each wallet with that network's native gas token (SOL on Solana, ETH on Base/Ethereum/Arbitrum, POL on Polygon). Receiving assets does not require the wallet to hold gas. Gas is separate from FEELESS/Jupiter platform fees.</p>
    {!status?.configured ? <div className="cc-empty"><p><b>Not active yet:</b> {status?.reason || 'checking…'}</p>
      <ol><li>Get an API key at <code>console.circle.com</code> (API &amp; Client Keys; a <code>TEST_</code> key = testnet) and add <code>CIRCLE_API_KEY=…</code> to <code>backend/.env</code>.</li><li>In the project folder run <code>cd circle &amp;&amp; npm install &amp;&amp; node setup.mjs</code> (once). It saves the secret to <code>backend/.env</code> for you.</li><li>Back up the recovery file in <code>~/.circle</code> (password manager). Without it a lost secret can't be recovered.</li><li>Run <code>bash scripts/start-backend.sh</code> (starts the wallet service too), then Re-check.</li></ol>
      <button type="button" className="btn-outline" onClick={load}>Re-check</button></div> : <>
      <div className="cc-toolbar"><select value={blockchain} onChange={e => setF(x => ({ ...x, blockchain: e.target.value }))}>{chains.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select><input placeholder="Wallet name (e.g. Treasury ops)" value={f.name} maxLength={40} onChange={e => setF(x => ({ ...x, name: e.target.value }))} /><button type="button" className="btn-primary" disabled={busy} onClick={create}>{busy ? 'Creating…' : 'Create wallet'}</button></div>
      <div className="cw-list">{!wallets.length ? <small className="cc-empty">No wallets yet.</small> : wallets.map(w => <CircleRow key={w.id} w={w} meta={meta[w.id]} call={call} onSaved={load} />)}</div>
      <small className="cc-empty">Keys are held by Circle and never touch FEELESS. Recovery lives in your ~/.circle recovery file. Check the estimated network fee and native-token balance before every outbound transaction.</small>
    </>}
  </div>;
}

// One Circle wallet: rename + describe it, and send from it (type the destination's last 4 to confirm).
function CircleRow({ w, meta, call, onSaved }) {
  const [mode, setMode] = useState('');
  const [m, setM] = useState({ name: meta?.name || w.name || '', description: meta?.description || '' });
  const [tx, setTx] = useState({ tokenId: w.balances?.[0]?.tokenId || '', to: '', amount: '', confirm: '' });
  const [busy, setBusy] = useState(false);
  const save = async () => { setBusy(true); try { await call(`/admin/circle/wallets/${w.id}`, { method: 'PUT', body: JSON.stringify(m) }); toast.success('Saved.'); setMode(''); onSaved?.(); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  const send = async () => { setBusy(true); try { const r = await call('/admin/circle/transfer', { method: 'POST', body: JSON.stringify({ walletId: w.id, ...tx }) }); toast.success(`Sent — Circle status ${r.state || 'submitted'}.`); setMode(''); onSaved?.(); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  const bal = (w.balances || []).find(b => b.tokenId === tx.tokenId);
  return <div className="cw-row cw-row-x">
    <div className="cw-top"><b>{meta?.name || w.name || 'Wallet'}</b><span className="chain-tag">{w.blockchain}</span><code>{w.address?.slice(0, 6)}…{w.address?.slice(-4)}</code><CopyBtn value={w.address} /><em>{(w.balances || []).map(b => `${Number(b.amount).toLocaleString()} ${b.symbol}`).join(' · ') || 'empty'}</em>
      <button type="button" className="btn-outline" onClick={() => setMode(mode === 'edit' ? '' : 'edit')}>✎ Edit</button><button type="button" className="btn-outline" disabled={!(w.balances || []).length} onClick={() => setMode(mode === 'send' ? '' : 'send')}>↗ Send</button></div>
    {meta?.description && mode !== 'edit' && <small className="cw-desc">{meta.description}</small>}
    {mode === 'edit' && <div className="bdg-form-row"><input maxLength={40} placeholder="Name" value={m.name} onChange={e => setM(x => ({ ...x, name: e.target.value }))} /><input maxLength={200} placeholder="What this wallet is for" value={m.description} onChange={e => setM(x => ({ ...x, description: e.target.value }))} /><button type="button" className="btn-primary" disabled={busy || m.name.length < 2} onClick={save}>Save</button></div>}
    {mode === 'send' && <div className="bdg-form-row"><select value={tx.tokenId} onChange={e => setTx(x => ({ ...x, tokenId: e.target.value }))}>{(w.balances || []).map(b => <option key={b.tokenId} value={b.tokenId}>{b.symbol} ({Number(b.amount).toLocaleString()})</option>)}</select>
      <input placeholder="Destination address" value={tx.to} onChange={e => setTx(x => ({ ...x, to: e.target.value.trim() }))} /><input inputMode="decimal" placeholder="Amount" value={tx.amount} onChange={e => setTx(x => ({ ...x, amount: e.target.value.replace(/[^0-9.]/g, '') }))} />
      <input placeholder={tx.to ? `Type ${tx.to.slice(-4)} to confirm` : 'Confirm'} maxLength={4} value={tx.confirm} onChange={e => setTx(x => ({ ...x, confirm: e.target.value }))} />
      <button type="button" className="btn-primary" disabled={busy || !tx.to || !Number(tx.amount) || tx.confirm !== tx.to.slice(-4) || (bal && Number(tx.amount) > Number(bal.amount))} onClick={send}>{busy ? 'Sending…' : 'Send'}</button>
      <small className="cc-empty">Circle signs and pays a small network fee from this wallet's native balance (SOL / ETH / MATIC…). Sends are logged in the audit trail.</small></div>}
  </div>;
}
