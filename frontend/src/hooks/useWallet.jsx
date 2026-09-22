import React, { createContext, useContext, useEffect, useState } from 'react';
const WalletContext = createContext(null);
const solanaProvider = () => window.phantom?.solana || window.solana;
const evmProvider = () => window.ethereum || window.phantom?.ethereum;
const bytesToBase64 = bytes => {
  const value = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let binary = '';
  value.forEach(byte => { binary += String.fromCharCode(byte); });
  return window.btoa(binary);
};
const stringToHex = value => `0x${Array.from(new TextEncoder().encode(value), byte => byte.toString(16).padStart(2, '0')).join('')}`;
export const WalletProvider = ({ children }) => {
  const [wallet, setWallet] = useState(null);
  const [provider, setProvider] = useState(null);
  const connect = async type => {
    const p = type === 'solana' ? solanaProvider() : evmProvider();
    if (!p) throw new Error(type === 'solana' ? 'Phantom is not installed in this browser.' : 'No EVM wallet detected in this browser.');
    if (type === 'solana') {
      const result = await p.connect();
      if (!result.publicKey) throw new Error('No wallet account was returned.');
      const nextWallet = { name: 'Phantom', chain: type, address: result.publicKey.toString() };
      setWallet(nextWallet);
      setProvider(p);
      return { wallet: nextWallet, provider: p };
    } else {
      const accounts = await p.request({ method: 'eth_requestAccounts' });
      if (!accounts?.[0]) throw new Error('No wallet account was returned.');
      const nextWallet = { name: 'EVM wallet', chain: type, address: accounts[0] };
      setWallet(nextWallet);
      setProvider(p);
      return { wallet: nextWallet, provider: p };
    }
  };
  const disconnect = async () => {
    if (wallet?.chain === 'solana') await provider?.disconnect?.();
    setWallet(null); setProvider(null);
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
    const event = wallet.chain === 'solana' ? 'accountChanged' : 'accountsChanged';
    provider.on?.(event, changed); provider.on?.('disconnect', reset); provider.on?.('chainChanged', reset);
    return () => { provider.removeListener?.(event, changed); provider.removeListener?.('disconnect', reset); provider.removeListener?.('chainChanged', reset); };
  }, [provider, wallet?.chain]); // eslint-disable-line react-hooks/exhaustive-deps
  return <WalletContext.Provider value={{ wallet, connect, disconnect, provider, signMessage }}>{children}</WalletContext.Provider>;
};
export const useWallet = () => useContext(WalletContext);