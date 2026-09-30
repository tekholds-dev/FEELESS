import React, { useState } from 'react';
import { Wallet, ArrowUpRight, ShieldCheck, LogOut, ChevronDown, Download } from 'lucide-react';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from './ui/dialog';
import { useWallet, EVM_CHAINS, networkLabel, signWith, detectWallets } from '../hooks/useWallet';
import { WalletIcon } from './WalletIcon';
import { getChatSession } from '../lib/chatSession';

// Featured: Phantom + Trust Wallet. Four more widely used wallets live under "More wallets".
// Installed wallets connect (Solana first, EVM as a secondary chip); missing ones link to the official install page.
const FEATURED = [
  { brand: 'phantom', label: 'Phantom', types: ['solana', 'evm'], url: 'https://phantom.com/download', tag: 'Most popular on Solana' },
  { brand: 'trust', label: 'Trust Wallet', types: ['solana', 'evm'], url: 'https://trustwallet.com/download', tag: 'Solana + 100 chains' },
];
const MORE = [
  { brand: 'solflare', label: 'Solflare', types: ['solana'], url: 'https://solflare.com/download' },
  { brand: 'backpack', label: 'Backpack', types: ['solana', 'evm'], url: 'https://backpack.app/download' },
  { brand: 'coinbase', label: 'Coinbase Wallet', types: ['solana', 'evm'], url: 'https://www.coinbase.com/wallet/downloads' },
  { brand: 'metamask', label: 'MetaMask', types: ['evm'], url: 'https://metamask.io/download/' },
  { brand: 'cryptocom', label: 'Crypto.com Onchain', types: ['evm'], url: 'https://crypto.com/onchain' },
  { brand: 'okx', label: 'OKX Wallet', types: ['solana', 'evm'], url: 'https://www.okx.com/web3' },
];
const WalletMark = ({ w, size }) => (w.icon && /^data:image\/(svg\+xml|png|webp)|^https:\/\//.test(w.icon) ? <img className="wallet-icon" src={w.icon} alt="" width={size} height={size} /> : <WalletIcon brand={w.iconBrand || w.brand} size={size} />);

function WalletChooser({ busy, onPick }) {
  const found = detectWallets();
  const installed = brand => brand === 'metamask'
    ? found.find(w => /metamask/i.test(w.label) && (!w.brand || w.brand.startsWith('eip6963:')))
    : found.find(w => w.brand === brand);
  const listed = new Set([...FEATURED, ...MORE].map(w => installed(w.brand)).filter(Boolean));
  const [more, setMore] = useState(() => MORE.some(w => installed(w.brand)) && !FEATURED.some(w => installed(w.brand)));
  const pickBrand = w => (w.brand === 'metamask' ? installed('metamask')?.brand || null : w.brand);
  const row = (w, featured) => {
    const hit = installed(w.brand);
    const types = hit ? hit.types : [];
    const primary = types.includes('solana') ? 'solana' : types[0];
    const testId = w.brand === 'phantom' ? 'wallet-connect-phantom' : w.brand === 'metamask' ? 'wallet-connect-evm' : `wallet-connect-${w.brand}`;
    return <div key={w.brand} className={`wallet-choice ${featured ? 'is-featured' : ''} ${hit ? 'is-installed' : ''}`}>
      {hit
        ? <button type="button" className="wallet-choice-main" data-testid={testId} disabled={busy} onClick={() => onPick(primary, pickBrand(w))}>
            <WalletMark w={{ ...w, icon: hit.icon }} size={featured ? 40 : 30} /><span><b>{w.label}</b><small>{featured ? w.tag : primary === 'solana' ? 'Solana' : 'Ethereum & EVM'}</small></span>
            <em className="wallet-choice-state">Detected</em><ArrowUpRight size={16} /></button>
        : <a className="wallet-choice-main" href={w.url} target="_blank" rel="noopener noreferrer" data-testid={`wallet-install-${w.brand}`}>
            <WalletIcon brand={w.brand} size={featured ? 40 : 30} /><span><b>{w.label}</b><small>{featured ? w.tag : 'Not installed'}</small></span>
            <em className="wallet-choice-state is-get"><Download size={12} />Install</em></a>}
      {hit && types.length > 1 && <button type="button" className="wallet-choice-alt" disabled={busy} onClick={() => onPick('evm', pickBrand(w))} data-testid={`wallet-connect-${w.brand}-evm`}>EVM</button>}
    </div>;
  };
  const others = found.filter(w => !listed.has(w));   // every other wallet the browser announced (Rabby, Zerion, …)
  const evmWallets = found.filter(w => w.types.includes('evm'));
  const cronosPick = installed('cryptocom') || evmWallets[0];
  return <div className="wallet-chooser">
    <div className="wallet-featured">{FEATURED.map(w => row(w, true))}</div>
    <button type="button" className={`wallet-more-toggle ${more ? 'open' : ''}`} aria-expanded={more} onClick={() => setMore(v => !v)} data-testid="wallet-more">
      More wallets<small>Solflare · Backpack · Coinbase · MetaMask · Crypto.com · OKX{others.length ? ` · +${others.length} detected` : ''}</small><ChevronDown size={16} /></button>
    {more && <div className="wallet-more-list">{MORE.map(w => row(w, false))}{others.map(w => <div key={w.brand || w.label} className="wallet-choice is-installed"><button type="button" className="wallet-choice-main" disabled={busy} onClick={() => onPick('evm', w.brand || null)}><WalletMark w={{ ...w, iconBrand: w.label === 'Rabby' ? 'rabby' : 'evm' }} size={30} /><span><b>{w.label}</b><small>Ethereum & EVM</small></span><em className="wallet-choice-state">Detected</em><ArrowUpRight size={16} /></button></div>)}</div>}
    <div className="wallet-cronos" data-testid="wallet-cronos">
      <span><b>Cronos on-chain</b><small>{cronosPick ? `Connects ${cronosPick.label} straight onto Cronos (CRO), adding the network if needed.` : 'Needs an EVM wallet: Crypto.com Onchain, MetaMask, Trust or Rabby.'}</small></span>
      {cronosPick
        ? <button type="button" className="btn-outline" disabled={busy} onClick={() => onPick('evm', cronosPick.brand || null, 'cronos')} data-testid="wallet-connect-cronos">Connect on Cronos</button>
        : <a className="btn-outline" href="https://crypto.com/onchain" target="_blank" rel="noopener noreferrer">Get Crypto.com Onchain</a>}
    </div>
  </div>;
}

export default function WalletModal({ open, onClose }) {
  const { wallet, connect, disconnect, switchTo, linkCandidate, linkAccounts } = useWallet();
  const [switching, setSwitching] = useState('');
  const [linked, setLinked] = useState(false);
  const hop = async chain => { setSwitching(chain); setError(''); try { await switchTo(chain); } catch (e) { setError(e.code === 4001 ? 'Switch declined in your wallet.' : e.message || 'Could not switch.'); } finally { setSwitching(''); } };
  const link = async () => { setBusy(true); setError(''); try { await linkAccounts(); setLinked(true); } catch (e) { setError(e.code === 4001 ? 'Signature declined.' : e.message); } finally { setBusy(false); } };
  const current = wallet?.chain === 'solana' ? 'solana' : Object.entries(EVM_CHAINS).find(([, c]) => c.chainId === String(wallet?.evmChainId || '').toLowerCase())?.[0];
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const handle = async (type, brand, chain) => {
    setBusy(true); setError('');
    try { const r = await connect(type, brand, chain ? { chain } : undefined); onClose(); try { await getChatSession(r.wallet.address, msg => signWith(r.provider, r.wallet.chain, r.wallet.address, msg)); } catch { /* declined: they'll be asked once when they first post/follow */ } } catch (e) { setError(e.code === 4001 ? 'Connection declined. Your wallet is unchanged.' : e.message || 'Connection failed.'); } finally { setBusy(false); }
  };
  return <Dialog open={open} onOpenChange={value => { if (!value) { onClose(); setError(''); } }}><DialogContent className="feeless-dialog" data-testid="wallet-dialog"><span className="dialog-icon"><Wallet size={26} /></span><DialogTitle>{wallet ? 'Connected wallet' : 'Your wallet. Your keys.'}</DialogTitle><DialogDescription>Connecting exposes your public account. Swap signing is a separate action requiring your wallet approval.</DialogDescription>
    {wallet ? <><code className="wallet-address" data-testid="connected-wallet-address">{wallet.address}</code>
      <div className="wallet-networks" data-testid="wallet-networks"><small>{wallet.name} · {wallet.chain === 'solana' ? 'Solana' : networkLabel(wallet.evmChainId) || 'EVM'} — switch network (same wallet)</small>
        <div>{[['solana', 'Solana'], ...Object.entries(EVM_CHAINS).map(([k, c]) => [k, c.chainName.replace(' Smart Chain', '').replace(' C-Chain', '').replace(' One', '')])].map(([k, l]) => <button key={k} type="button" className={current === k ? 'active' : ''} disabled={Boolean(switching)} onClick={() => hop(k)}>{switching === k ? '…' : l}</button>)}</div></div>
      {linkCandidate && !linked && <div className="wallet-link"><span>Link your {linkCandidate.a.wallet.chain === 'solana' ? 'Solana' : 'EVM'} and {linkCandidate.b.wallet.chain === 'solana' ? 'Solana' : 'EVM'} accounts so your profile, posts and badges show on every network.</span><button type="button" className="btn-outline" disabled={busy} onClick={link}>Link accounts (2 signatures)</button></div>}
      {linked && <div className="wallet-link ok">✓ Linked — you're one identity on every network.</div>}<button className="btn-primary" data-testid="wallet-disconnect" onClick={async () => { await disconnect(); onClose(); }}><LogOut size={16} />Disconnect from FEELESS</button></> : <WalletChooser busy={busy} onPick={handle} />}
    {error && <div data-testid="wallet-error" role="alert" className="market-error">{error}</div>}{busy && <p data-testid="wallet-connecting" className="muted">Waiting for wallet approval…</p>}<div className="wallet-note"><ShieldCheck size={16} />Non-custodial. Always.</div>
  </DialogContent></Dialog>;
}