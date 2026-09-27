import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { createSolPool, inspectPool } from '../../lib/poolBuilder';
import { CopyBtn } from '../CopyBtn';

// Owner-only: seed a TOKEN/SOL pool on Meteora DAMM v2 from the connected wallet.
// The wallet supplies both sides; the starting price is simply SOL ÷ tokens deposited.
export function PoolCreator({ defaultMint = '' }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [f, setF] = useState({ mint: defaultMint, tokens: '', sol: '', feeBps: '100', launchFeeBps: '0', launchMinutes: '0', lock: true });
  const [meta, setMeta] = useState(null);
  const [status, setStatus] = useState('');
  const [done, setDone] = useState(null);
  const set = (k, v) => setF(x => ({ ...x, [k]: v }));
  useEffect(() => { if (defaultMint) setF(x => ({ ...x, mint: defaultMint })); }, [defaultMint]);
  useEffect(() => {
    setMeta(null);
    if (!/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(f.mint)) return undefined;
    let alive = true;
    inspectPool(f.mint).then(m => alive && setMeta(m)).catch(e => alive && setMeta({ error: e.message }));
    return () => { alive = false; };
  }, [f.mint]);
  const price = Number(f.sol) > 0 && Number(f.tokens) > 0 ? Number(f.sol) / Number(f.tokens) : null;
  const ready = meta && !meta.error && !meta.exists && price && Number(f.feeBps) >= 25;
  const create = async () => {
    try {
      if (!wallet?.address || wallet.chain !== 'solana' || !provider?.signTransaction) { await connect?.('solana'); return; }
      setStatus('Building and dry-running…');
      const r = await createSolPool({ provider, owner: wallet.address, mint: f.mint, tokenAmount: f.tokens, solAmount: f.sol, feeBps: f.feeBps, launchFeeBps: f.launchFeeBps, launchMinutes: f.launchMinutes, lock: f.lock, onStatus: setStatus });
      setDone(r); setStatus(''); toast.success('Pool is live');
    } catch (e) { setStatus(''); toast.error(e.message || 'Pool creation failed'); }
  };
  return <div className="cc-block pool-creator"><h4>Create a pool <small className="chain-tag">Meteora DAMM v2 · Solana</small></h4>
    <div className="rail-form">
      <label className="wide"><span>Token mint</span><input value={f.mint} onChange={e => set('mint', e.target.value.trim())} placeholder="Token mint address" />
        <small>{!meta ? 'Paste a Solana token mint.' : meta.error ? `⚠ ${meta.error}` : meta.exists ? <>A pool for this token/SOL already exists: <code>{meta.pool.slice(0, 6)}…</code><CopyBtn value={meta.pool} /></> : `${meta.decimals} decimals · ${meta.program.startsWith('TokenzQd') ? 'Token-2022' : 'SPL token'}${meta.freeze ? ' · ⚠ freeze authority is still on' : ''}`}</small></label>
      <label><span>Tokens to deposit</span><input inputMode="decimal" value={f.tokens} onChange={e => set('tokens', e.target.value.replace(/[^0-9.]/g, ''))} /><small>From your connected wallet.</small></label>
      <label><span>SOL to deposit</span><input inputMode="decimal" value={f.sol} onChange={e => set('sol', e.target.value.replace(/[^0-9.]/g, ''))} /><small>{price ? `Opens at ${price.toPrecision(4)} SOL per token.` : 'Sets the opening price.'}</small></label>
      <label><span>Swap fee (bps)</span><input inputMode="numeric" value={f.feeBps} onChange={e => set('feeBps', e.target.value.replace(/\D/g, ''))} /><small>100 = 1%. Minimum 25. Fees accrue to your position in SOL.</small></label>
      <label><span>Anti-snipe start fee (bps)</span><input inputMode="numeric" value={f.launchFeeBps} onChange={e => set('launchFeeBps', e.target.value.replace(/\D/g, ''))} /><small>0 = off. e.g. 5000 = 50% at open, decaying.</small></label>
      <label><span>Anti-snipe window (min)</span><input inputMode="numeric" value={f.launchMinutes} onChange={e => set('launchMinutes', e.target.value.replace(/\D/g, ''))} /><small>How long the start fee takes to fall to the swap fee.</small></label>
      <label className="pool-lock"><input type="checkbox" checked={f.lock} onChange={e => set('lock', e.target.checked)} /><span>Lock this liquidity forever</span><small>Recommended. You keep earning fees but can never pull it — holders can verify it.</small></label>
    </div>
    <button type="button" className="btn-primary" disabled={!!status || (wallet?.chain === 'solana' && !ready)} onClick={create}>{status || (wallet?.chain === 'solana' ? `Create pool · sign with ${wallet.address.slice(0, 4)}…` : 'Connect Solana wallet')}</button>
    <small className="cc-empty">Simulated before you sign. Any owner wallet works — switch accounts in Phantom and reconnect. One pool per token/SOL pair on this rail.</small>
    {done && <div className="cc-sig"><span>✅ Pool <code>{done.pool.slice(0, 6)}…</code><CopyBtn value={done.pool} /></span><a href={`/terminal/coin/solana/${done.pool}`}>Open chart →</a><a href={`https://solscan.io/tx/${done.signature}`} target="_blank" rel="noreferrer">Tx ↗</a></div>}
  </div>;
}
