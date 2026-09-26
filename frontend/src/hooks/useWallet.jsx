import React, { createContext, useContext, useEffect, useState } from 'react';
const WalletContext = createContext(null);
const solanaProvider = () => window.phantom?.solana || window.trustwallet?.solana || window.solflare || window.backpack?.solana || window.solana;
const evmProvider = () => window.trustwallet?.ethereum || window.ethereum || window.phantom?.ethereum;
// Same wallet, other chain: Trust Wallet 0x ↔ Trust Wallet Solana, Phantom ↔ Phantom, etc.
// Never jump to a different wallet extension just because it was injected first.
const brandOf = p => {
  if (!p) return null;
  const w = window;
  if (p.isTrust || p.isTrustWallet || p === w.trustwallet?.ethereum || p === w.trustwallet?.solana || p === w.trustwallet) return 'trust';
  if (p.isPhantom || p === w.phantom?.ethereum || p === w.phantom?.solana) return 'phantom';
  if (p.isBackpack || p === w.backpack?.solana || p === w.backpack?.ethereum) return 'backpack';
  if (p.isSolflare || p === w.solflare) return 'solflare';
  if (p.isCoinbaseWallet || p === w.coinbaseSolana) return 'coinbase';
  return null;
};
const pairedProvider = (brand, type) => {
  const w = window;
  const map = {
    trust: { solana: w.trustwallet?.solana, evm: w.trustwallet?.ethereum || (w.ethereum?.isTrust ? w.ethereum : null) },
    phantom: { solana: w.phantom?.solana, evm: w.phantom?.ethereum },
    backpack: { solana: w.backpack?.solana || (w.backpack?.isBackpack ? w.backpack : null), evm: w.backpack?.ethereum },
    solflare: { solana: w.solflare, evm: null },
    coinbase: { solana: w.coinbaseSolana, evm: w.coinbaseWalletExtension || (w.ethereum?.isCoinbaseWallet ? w.ethereum : null) },
  };
  return brand ? map[brand]?.[type] || null : null;
};
const walletName = (p, chain) => (brandOf(p) === 'trust' ? 'Trust Wallet' : p?.isPhantom ? 'Phantom' : p?.isSolflare ? 'Solflare' : p?.isBackpack ? 'Backpack' : p?.isCoinbaseWallet ? 'Coinbase Wallet' : p?.isRabby ? 'Rabby' : p?.isMetaMask ? 'MetaMask' : chain === 'solana' ? 'Solana wallet' : 'EVM wallet');
// EVM networks FEELESS trades on, keyed by DexScreener chain id.
export const EVM_CHAINS = {
  ethereum: { chainId: '0x1', chainName: 'Ethereum', nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 }, rpcUrls: ['https://eth.llamarpc.com'], blockExplorerUrls: ['https://etherscan.io'] },
  base: { chainId: '0x2105', chainName: 'Base', nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 }, rpcUrls: ['https://mainnet.base.org'], blockExplorerUrls: ['https://basescan.org'] },
  bsc: { chainId: '0x38', chainName: 'BNB Smart Chain', nativeCurrency: { name: 'BNB', symbol: 'BNB', decimals: 18 }, rpcUrls: ['https://bsc-dataseed.binance.org'], blockExplorerUrls: ['https://bscscan.com'] },
  arbitrum: { chainId: '0xa4b1', chainName: 'Arbitrum One', nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 }, rpcUrls: ['https://arb1.arbitrum.io/rpc'], blockExplorerUrls: ['https://arbiscan.io'] },
  avalanche: { chainId: '0xa86a', chainName: 'Avalanche C-Chain', nativeCurrency: { name: 'Avalanche', symbol: 'AVAX', decimals: 18 }, rpcUrls: ['https://api.avax.network/ext/bc/C/rpc'], blockExplorerUrls: ['https://snowtrace.io'] },
  polygon: { chainId: '0x89', chainName: 'Polygon', nativeCurrency: { name: 'POL', symbol: 'POL', decimals: 18 }, rpcUrls: ['https://polygon-rpc.com'], blockExplorerUrls: ['https://polygonscan.com'] },
};
export const ecoOf = chain => (chain === 'solana' ? 'solana' : EVM_CHAINS[chain] ? 'evm' : null);
export const networkLabel = hex => Object.entries(EVM_CHAINS).find(([, c]) => c.chainId === String(hex || '').toLowerCase())?.[1].chainName || (hex ? `Chain ${parseInt(hex, 16)}` : null);
const bytesToBase64 = bytes => {
  const value = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let binary = '';
  value.forEach(byte => { binary += String.fromCharCode(byte); });
  return window.btoa(binary);
};
const stringToHex = value => `0x${Array.from(new TextEncoder().encode(value), byte => byte.toString(16).padStart(2, '0')).join('')}`;
export async function signWith(prov, chain, address, message) {
  if (chain === 'solana') {
    const r = await prov.signMessage(new TextEncoder().encode(message), 'utf8');
    return bytesToBase64(r?.signature || r);
  }
  return prov.request({ method: 'personal_sign', params: [stringToHex(message), address] });
}

export const WalletProvider = ({ children }) => {
  const [wallet, setWallet] = useState(null);
  const [provider, setProvider] = useState(null);
  const connect = async (type, brand) => {
    const p = (brand && pairedProvider(brand, type)) || (type === 'solana' ? solanaProvider() : evmProvider());
    if (brand && !pairedProvider(brand, type)) throw new Error(`Your ${walletName(provider, wallet?.chain)} doesn't expose a ${type === 'solana' ? 'Solana' : 'EVM'} account in this browser — enable it in the wallet's settings.`);
    if (!p) throw new Error(type === 'solana' ? 'No Solana wallet found. Phantom, Trust Wallet, Solflare and Backpack all work — enable Solana in your wallet.' : 'No EVM wallet detected in this browser.');
    if (type === 'solana') {
      const result = await p.connect();
      if (!result.publicKey) throw new Error('No wallet account was returned.');
      const nextWallet = { name: walletName(p, 'solana'), chain: type, address: result.publicKey.toString() };
      setWallet(nextWallet);
      setProvider(p);
      return { wallet: nextWallet, provider: p };
    } else {
      const accounts = await p.request({ method: 'eth_requestAccounts' });
      if (!accounts?.[0]) throw new Error('No wallet account was returned.');
      const evmChainId = await p.request({ method: 'eth_chainId' }).catch(() => null);
      const nextWallet = { name: walletName(p, 'evm'), chain: type, address: accounts[0], evmChainId };
      setWallet(nextWallet);
      setProvider(p);
      return { wallet: nextWallet, provider: p };
    }
  };
  const disconnect = async () => {
    if (wallet?.chain === 'solana') await provider?.disconnect?.();
    setWallet(null); setProvider(null);
  };
  // Move the connected wallet onto the eco/network a coin lives on.
  // Same extension, other side (e.g. Trust Wallet 0x → its Solana account), or an EVM network switch.
  const [linkCandidate, setLinkCandidate] = useState(null);
  const switchTo = async chain => {
    const before = wallet && provider ? { wallet, provider } : null;
    const out = await switchToInner(chain);
    if (before && out?.wallet && before.wallet.chain !== out.wallet.chain) setLinkCandidate({ a: before, b: { wallet: out.wallet, provider: out.provider } });
    return out;
  };
  // Link the two accounts of one wallet (e.g. Trust 0x + Trust Solana): each signs, so posts,
  // profile and badges follow you on every network.
  const linkAccounts = async () => {
    if (!linkCandidate) throw new Error('Switch networks first.');
    const { a, b } = linkCandidate;
    const sol = a.wallet.chain === 'solana' ? a : b; const evm = a.wallet.chain === 'solana' ? b : a;
    const ts = Math.floor(Date.now() / 1000);
    const message = `FEELESS link wallets\nsolana:${sol.wallet.address}\nevm:${evm.wallet.address}\nts:${ts}`;
    const solSig = await signWith(sol.provider, 'solana', sol.wallet.address, message);
    const evmSig = await signWith(evm.provider, 'evm', evm.wallet.address, message);
    const res = await fetch('/api/reputation/identity/link', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ solana: sol.wallet.address, evm: evm.wallet.address, ts, solanaSig: solSig, evmSig }) });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || 'Link failed.');
    setLinkCandidate(null);
    return body;
  };
  const switchToInner = async chain => {
    const eco = ecoOf(chain);
    if (!eco) throw new Error(`FEELESS can't sign on ${chain} yet.`);
    const brand = brandOf(provider);
    if (eco === 'solana') return wallet?.chain === 'solana' ? { wallet, provider } : connect('solana', brand);
    let current = wallet?.chain === 'evm' ? { wallet, provider } : await connect('evm', brand);
    const target = EVM_CHAINS[chain];
    if (String(current.wallet.evmChainId || '').toLowerCase() === target.chainId) return current;
    try {
      await current.provider.request({ method: 'wallet_switchEthereumChain', params: [{ chainId: target.chainId }] });
    } catch (e) {
      if (e?.code !== 4902) throw e;
      await current.provider.request({ method: 'wallet_addEthereumChain', params: [target] });
    }
    const next = { ...current.wallet, evmChainId: target.chainId };
    setWallet(next);
    return { wallet: next, provider: current.provider };
  };
  const signMessage = async message => {
    if (!wallet || !provider) throw new Error('Connect a wallet before signing.');
    if (wallet.chain === 'solana') {
      if (!provider.signMessage) throw new Error('This Solana wallet cannot sign messages.');
      const result = await provider.signMessage(new TextEncoder().encode(message), 'utf8');
      return bytesToBase64(result?.signature || result);
    }
    if (!provider.request) throw new Error('This wallet cannot sign messages.');
    return provider.request({ method: 'personal_sign', params: [stringToHex(message), wallet.address] });
  };
  useEffect(() => {
    if (!provider || !wallet) return;
    const changed = value => {
      const address = wallet.chain === 'solana' ? value?.toString() : value?.[0];
      setWallet(current => address && current ? { ...current, address } : null);
    };
    const reset = () => setWallet(null);
    const chainChanged = evmChainId => setWallet(current => (current ? { ...current, evmChainId } : current));
    const event = wallet.chain === 'solana' ? 'accountChanged' : 'accountsChanged';
    provider.on?.(event, changed); provider.on?.('disconnect', reset); provider.on?.('chainChanged', chainChanged);
    return () => { provider.removeListener?.(event, changed); provider.removeListener?.('disconnect', reset); provider.removeListener?.('chainChanged', chainChanged); };
  }, [provider, wallet?.chain]); // eslint-disable-line react-hooks/exhaustive-deps
  return <WalletContext.Provider value={{ wallet, connect, disconnect, provider, signMessage, switchTo, linkCandidate, linkAccounts }}>{children}</WalletContext.Provider>;
};
export const useWallet = () => useContext(WalletContext);