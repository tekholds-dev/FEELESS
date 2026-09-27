import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { WalletSwaps, tradeHref } from './WalletSwaps';

const KEY = 'feeless:copy-wallets';
const read = () => { try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch { return []; } };
const short = a => `${a.slice(0, 4)}…${a.slice(-4)}`;

// Copy trading with reputation built in: follow proven wallets, see every swap, mirror in one tap.
// Nothing auto-trades — each mirror opens the trade desk for you to review and sign. If a followed
// wallet turns bad (blocklisted, funds snipers, dumps on followers, low trust) mirroring pauses.
function Followed({ address, onRemove }) {
  const [chk, setChk] = useState(null);
  const navigate = useNavigate();
  useEffect(() => { fetch(apiUrl(`/api/reputation/copy/check/${address}`)).then(r => r.json()).then(setChk).catch(() => {}); }, [address]);
  const safe = chk?.safe;
  return <div className={`copy-wallet ${chk ? (safe ? 'safe' : 'paused') : ''}`}>
    <header><b>{short(address)}</b>{chk && <span className="copy-trust">trust {chk.trust ?? '—'}</span>}{chk && (safe ? <em className="ok">✓ safe to mirror</em> : <em className="bad">⏸ paused — {chk.reasons.join(', ')}</em>)}<button type="button" className="btn-outline" onClick={onRemove}>Unfollow</button></header>
    <WalletSwaps address={address} title="Latest swaps" limit={5} onMirror={{ disabled: !safe, fn: t => { if (!safe) { toast.error('Mirroring paused for this wallet.'); return; } navigate(tradeHref(t)); } }} />
  </div>;
}

export function CopyTrading() {
  const [list, setList] = useState(read);
  const [input, setInput] = useState('');
  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify(list)); } catch { /* ignore */ } }, [list]);
  const add = e => { e.preventDefault(); const a = input.trim(); if (!/^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$/.test(a)) { toast.error('Paste a Solana or 0x wallet address.'); return; } if (!list.includes(a)) setList([a, ...list].slice(0, 12)); setInput(''); };
  return <section className="copy-trading" data-testid="copy-trading">
    <header><h3>Copy trading</h3><small>Follow proven wallets. Every mirror opens your trade desk — you sign, FEELESS never trades for you. Bad wallets auto-pause.</small></header>
    <form onSubmit={add}><input placeholder="Paste a wallet to follow (tip: grab one from Rep or a profile)" value={input} onChange={e => setInput(e.target.value)} /><button className="btn-primary" type="submit">Follow</button></form>
    {!list.length && <p className="wp-bio">Not following anyone yet.</p>}
    <div className="copy-list">{list.map(a => <Followed key={a} address={a} onRemove={() => setList(list.filter(x => x !== a))} />)}</div>
  </section>;
}
