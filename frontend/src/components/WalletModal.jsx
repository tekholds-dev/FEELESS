import React, { useState } from 'react';
import { Wallet, ArrowUpRight, ShieldCheck, LogOut } from 'lucide-react';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from './ui/dialog';
import { useWallet } from '../hooks/useWallet';

export default function WalletModal({ open, onClose }) {
  const { wallet, connect, disconnect } = useWallet();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const handle = async type => {
    setBusy(true); setError('');
    try { await connect(type); onClose(); } catch (e) { setError(e.code === 4001 ? 'Connection declined. Your wallet is unchanged.' : e.message || 'Connection failed.'); } finally { setBusy(false); }
  };
  return <Dialog open={open} onOpenChange={value => { if (!value) { onClose(); setError(''); } }}><DialogContent className="feeless-dialog" data-testid="wallet-dialog"><span className="dialog-icon"><Wallet size={26} /></span><DialogTitle>{wallet ? 'Connected wallet' : 'Your wallet. Your keys.'}</DialogTitle><DialogDescription>Connecting exposes your public account. Swap signing is a separate action requiring your wallet approval.</DialogDescription>
    {wallet ? <><code className="wallet-address" data-testid="connected-wallet-address">{wallet.address}</code><button className="btn-primary" data-testid="wallet-disconnect" onClick={async () => { await disconnect(); onClose(); }}><LogOut size={16} />Disconnect from FEELESS</button></> : <div className="wallet-options"><button data-testid="wallet-connect-phantom" disabled={busy} onClick={() => handle('solana')}><span className="wallet-letter">P</span><span>Phantom<small>Solana</small></span><ArrowUpRight size={18} /></button><button data-testid="wallet-connect-evm" disabled={busy} onClick={() => handle('evm')}><span className="wallet-letter evm">E</span><span>Browser wallet<small>Ethereum & EVM networks</small></span><ArrowUpRight size={18} /></button></div>}
    {error && <div data-testid="wallet-error" role="alert" className="market-error">{error}</div>}{busy && <p data-testid="wallet-connecting" className="muted">Waiting for wallet approval…</p>}<div className="wallet-note"><ShieldCheck size={16} />Non-custodial. Always.</div>
  </DialogContent></Dialog>;
}