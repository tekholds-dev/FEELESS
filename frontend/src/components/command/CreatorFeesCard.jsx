import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { claimCreatorFees, creatorFees } from '../../lib/launchRail';
import { useSolPrice, usd } from '../../lib/solPrice';

// Shown to a coin's creator only: trading fees earned on its FEELESS curve, claimable to their wallet.
export function CreatorFeesCard({ mint, creator }) {
  const { wallet, provider } = useWallet() || {};
  const solPx = useSolPrice();
  const [fees, setFees] = useState(null);
  const [status, setStatus] = useState('');
  const mine = !!wallet?.address && wallet.address === creator;
  const load = useCallback(() => { if (mine) creatorFees(mint).then(setFees).catch(() => setFees(null)); }, [mint, mine]);
  useEffect(load, [load]);
  if (!mine || !fees || fees.creator !== wallet.address) return null;
  const claim = async () => {
    try {
      setStatus('Building and dry-running the claim…');
      const sig = await claimCreatorFees({ provider, creator: wallet.address, mint, onStatus: setStatus });
      toast.success(`Claimed — ${sig.slice(0, 8)}… on Solscan`);
      load();
    } catch (e) { toast.error(e.message || 'Claim failed'); } finally { setStatus(''); }
  };
  return <div className="creator-fees" data-testid="creator-fees">
    <div className="cp-kv"><span>Your unclaimed creator fees</span><b>{fees.sol.toFixed(4)} SOL {usd(fees.sol, solPx)}</b></div>
    <button type="button" className="btn-primary" disabled={!!status || fees.sol <= 0 || !provider?.signTransaction} onClick={claim}>{status || (fees.sol > 0 ? 'Claim to my wallet' : 'Nothing to claim yet')}</button>
    <small className="wp-bio">Paid straight from the on-chain pool to your wallet. Simulated before you sign.</small>
  </div>;
}
