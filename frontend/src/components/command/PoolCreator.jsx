import { useSolPrice, usd } from '../../lib/solPrice';
import NumInput from '../NumInput';
import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { createSolPool, inspectPool } from '../../lib/poolBuilder';
import { CopyBtn } from '../CopyBtn';

import { tiny } from '../../lib/num';
// Owner-only: seed a TOKEN/SOL pool on Meteora DAMM v2 from the connected wallet.
// The wallet supplies both sides; the starting price is simply SOL ÷ tokens deposited.
export function PoolCreator({ defaultMint = '', call }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [f, setF] = useState({ mint: defaultMint, tokens: '', sol: '', feeBps: '100', launchFeeBps: '0', launchMinutes: '0', lock: true });
  const [meta, setMeta] = useState(null);
  const [status, setStatus] = useState('');
  const [done, setDone] = useState(null);
  const solPx = useSolPrice();
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
      // Record it so the coin can earn the rug-proof badge (server re-checks the tx on-chain).
      for (let i = 0; i < 4; i++) {
        try { await call('/admin/pools/register', { method: 'POST', body: JSON.stringify({ pool: r.pool, mint: f.mint, signature: r.signature, locked: f.lock }) }); break; }
        catch { await new Promise(res => setTimeout(res, 4000)); }
      }
    } catch (e) { setStatus(''); toast.error(e.message || 'Pool creation failed'); }
  };
  const share = meta?.supply && Number(f.tokens) > 0 ? (Number(f.tokens) / meta.supply) * 100 : null;
  return <div className="cc-block pool-creator"><h4>Create a pool <small className="chain-tag">Meteora DAMM v2 · Solana</small></h4>
    <details className="pool-explain"><summary>How these inputs work</summary>
      <p>A pool is two piles: your token and SOL. Traders swap against them, and the ratio between the piles is the price.</p>
      <ul>
        <li><b>Tokens + SOL to deposit</b> — both come from your wallet. Opening price = SOL ÷ tokens. Example: 100,000,000 tokens + 10 SOL opens at 0.0000001 SOL each. More of both = deeper pool, less slippage, same price.</li>
        <li><b>Swap fee</b> — charged on every trade, paid to your position in SOL. 100 bps = 1%. Most memecoin pools use 1%; majors use 0.25%.</li>
        <li><b>Anti-snipe</b> — optional. A high fee at open (e.g. 5000 = 50%) that decays to the swap fee over the window, so bots that buy the first block pay heavily. 0 turns it off.</li>
        <li><b>Lock forever</b> — the liquidity can never be withdrawn (you still collect fees). This is what makes a pool rug-proof and earns the badge.</li>
      </ul>
    </details>
    <div className="rail-form">
      <label className="wide"><span>Token mint</span><input value={f.mint} onChange={e => set('mint', e.target.value.trim())} placeholder="Token mint address" />
        <small>{!meta ? 'Paste a Solana token mint.' : meta.error ? `⚠ ${meta.error}` : meta.exists ? <>A pool for this token/SOL already exists: <code>{meta.pool.slice(0, 6)}…</code><CopyBtn value={meta.pool} /></> : `${meta.decimals} decimals · ${meta.program.startsWith('TokenzQd') ? 'Token-2022' : 'SPL token'}${meta.freeze ? ' · ⚠ freeze authority is still on' : ''}`}</small></label>
      <label><span>Tokens to deposit</span><NumInput inputMode="decimal" value={f.tokens} onChange={e => set('tokens', e.target.value.replace(/[^0-9.]/g, ''))} /><small>From your connected wallet.</small></label>
      <label><span>SOL to deposit</span><NumInput inputMode="decimal" value={f.sol} onChange={e => set('sol', e.target.value.replace(/[^0-9.]/g, ''))} /><small>{price ? `Opens at ${tiny(price, 4)} SOL per token${solPx ? ` (${usd(price, solPx).slice(2).replace(/^\$0$/, '<$0.01')})` : ''}.` : 'Sets the opening price.'} {usd(f.sol, solPx)}</small></label>
      <label><span>Swap fee (bps)</span><NumInput inputMode="numeric" value={f.feeBps} onChange={e => set('feeBps', e.target.value.replace(/\D/g, ''))} /><small>100 = 1%. Minimum 25. Fees accrue to your position in SOL.</small></label>
      <label><span>Anti-snipe start fee (bps)</span><NumInput inputMode="numeric" value={f.launchFeeBps} onChange={e => set('launchFeeBps', e.target.value.replace(/\D/g, ''))} /><small>0 = off. e.g. 5000 = 50% at open, decaying.</small></label>
      <label><span>Anti-snipe window (min)</span><NumInput inputMode="numeric" value={f.launchMinutes} onChange={e => set('launchMinutes', e.target.value.replace(/\D/g, ''))} /><small>How long the start fee takes to fall to the swap fee.</small></label>
      <label className="pool-lock"><input type="checkbox" checked={f.lock} onChange={e => set('lock', e.target.checked)} /><span>Lock this liquidity forever</span><small>Recommended. You keep earning fees but can never pull it — holders can verify it.</small></label>
    </div>
    {price && <div className="pool-summary"><span><small>Opening price</small><b>{tiny(price, 4)} SOL</b></span>{meta?.supply ? <span><small>Implied market cap</small><b>{(price * meta.supply).toLocaleString(undefined, { maximumFractionDigits: 2 })} SOL</b>{solPx && <em className="usd-hint">{usd(price * meta.supply, solPx)}</em>}</span> : null}{share != null && <span><small>Supply in pool</small><b>{share.toFixed(2)}%</b></span>}<span><small>Launch fee</small><b>{Number(f.launchFeeBps) > Number(f.feeBps) && Number(f.launchMinutes) > 0 ? `${Number(f.launchFeeBps) / 100}% → ${Number(f.feeBps) / 100}%` : `${Number(f.feeBps) / 100}% flat`}</b></span></div>}
    <button type="button" className="btn-primary" disabled={!!status || (wallet?.chain === 'solana' && !ready)} onClick={create}>{status || (wallet?.chain === 'solana' ? `Create pool · sign with ${wallet.address.slice(0, 4)}…` : 'Connect Solana wallet')}</button>
    <small className="cc-empty">Simulated before you sign. Any owner wallet works — switch accounts in Phantom and reconnect. One pool per token/SOL pair on this rail.</small>
    {done && <div className="cc-sig"><span>✅ Pool <code>{done.pool.slice(0, 6)}…</code><CopyBtn value={done.pool} /></span><a href={`/terminal/chat?chain=solana&pair=${done.pool}&room=bulls`}>Open chart →</a><a href={`https://solscan.io/tx/${done.signature}`} target="_blank" rel="noreferrer">Tx ↗</a></div>}
  </div>;
}
