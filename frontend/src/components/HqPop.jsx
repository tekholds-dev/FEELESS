import React, { lazy, Suspense, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useWallet } from '../hooks/useWallet';
import { sharedJson } from '../lib/sharedJson';
import { useHqBusy } from '../lib/hqBusy';
import { pairedAddress } from '../lib/hqPaired';
import '../styles/hqPop.css';

// ⚡ HQ POP-OUT (owner, 2026-10-13: "in my lil mini cat bottom right make a one click big HQ popout … so I don't have to keep running to
// HQ in profile"). CREATOR WALLET ONLY: the button exists only when the server's yes / no check says this connected wallet is the
// creator (`whoami.isOwner`, a bool — never a role or an address). One click = the whole HQ in a full-window pop-out on ANY page; the
// HQ chunk itself is loaded only then, and every action inside still needs the signed HQ session exactly as before.
// The header reacts to what HQ is doing (hqBusy — the same counter every HQ button uses): 🟢 idle · ⚡ working · ⏳ still cooking.
const HqDeck = lazy(() => import('./command/HqDeck').then(m => ({ default: m.HqDeck })));
const OPEN_KEY = 'feeless.hqPop';
// one tap to the places the creator runs to most (HqDeck listens for feeless:hq-go)
export const HQ_JUMPS = [['agents', '🎩', "Sicario's", { tab: 'agents' }], ['wallet', '👛', 'Fuse wallet', { tab: 'fuse', panel: 'wallet' }], ['fuse', '⚛', 'Fuse', { tab: 'fuse' }],
  ['money', '💰', 'Money', { view: 'treasury' }], ['lag', '🩺', 'Lag catcher', { tab: 'latency' }], ['fees', '💲', 'Fees', { tab: 'fees' }]];
// the header's word for what HQ is doing right now — trench talk, read from real requests in flight (never a canned ticker)
export function hqMood(b) {
  if (!b?.n) return { key: 'idle', icon: '🟢', word: 'LOCKED IN', line: 'standing by' };
  if (b.slow) return { key: 'slow', icon: '⏳', word: 'STILL COOKING', line: b.label ? `${b.label} — waiting on the keeper's pass` : "waiting on the keeper's pass" };
  return { key: 'work', icon: '⚡', word: 'SENDING IT', line: b.label || `${b.n} move${b.n === 1 ? '' : 's'} in flight` };
}

export function useIsCreator() {
  const { wallet } = useWallet() || {};
  const addr = (wallet?.chain === 'solana' || !wallet?.chain ? wallet?.address : null) || pairedAddress();   // 📱 or the wallet that signed HQ from the phone (HqLink)
  const [yes, setYes] = useState(false);
  useEffect(() => {
    let alive = true; setYes(false);
    if (!addr) return undefined;
    sharedJson(`/api/reputation/admin/whoami?address=${addr}`, { maxAge: 300000 }).then(d => { if (alive) setYes(d?.isOwner === true); }).catch(() => {});
    return () => { alive = false; };
  }, [addr]);
  return yes ? addr : null;
}

function HqPopWindow({ address, signMessage, onClose }) {
  const busy = useHqBusy(); const mood = hqMood(busy);
  const [at, setAt] = useState('agents');
  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape' && !e.defaultPrevented && !['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target?.tagName)) onClose(); };
    document.addEventListener('keydown', onKey); document.body.classList.add('hqp-open');
    return () => { document.removeEventListener('keydown', onKey); document.body.classList.remove('hqp-open'); };
  }, [onClose]);
  const go = (k, detail) => { setAt(k); window.dispatchEvent(new CustomEvent('feeless:hq-go', { detail })); };
  return createPortal(<div className={`hqp is-${mood.key}`} data-testid="hq-pop" role="dialog" aria-label="HQ">
    <div className="hqp-fx" aria-hidden="true"><i /><i /><i /></div>
    <header className="hqp-bar">
      <span className="hqp-mark" aria-hidden="true"><i /><i /><b>HQ</b></span>
      <span className="hqp-mood" data-testid="hq-pop-mood" data-mood={mood.key}><b>{mood.icon} {mood.word}</b><small>{mood.line}</small></span>
      <nav className="hqp-jumps" aria-label="HQ shortcuts">{HQ_JUMPS.map(([k, ic, label, detail]) => <button key={k} type="button" className={at === k ? 'active' : ''} onClick={() => go(k, detail)} data-testid={`hq-pop-go-${k}`}><i>{ic}</i>{label}</button>)}</nav>
      <button type="button" className="hqp-x" onClick={onClose} aria-label="Close HQ" data-testid="hq-pop-close" data-tip="Close (Esc)">✕</button>
    </header>
    <div className="hqp-body"><Suspense fallback={<div className="hqp-load" data-testid="hq-pop-loading"><span className="hqp-mark is-big" aria-hidden="true"><i /><i /><b>HQ</b></span><small>opening HQ…</small></div>}>
      <HqDeck address={address} signMessage={signMessage} onClose={onClose} startTab="agents" /></Suspense></div>
  </div>, document.body);
}

// the launcher that sits on the mini cat — nothing renders (and no HQ code loads) for anyone but the creator's wallet
export default function HqPop() {
  const addr = useIsCreator();
  const { signMessage } = useWallet() || {};
  const [open, setOpen] = useState(() => { try { return sessionStorage.getItem(OPEN_KEY) === '1'; } catch { return false; } });
  const busy = useHqBusy();
  const set = v => { setOpen(v); try { if (v) sessionStorage.setItem(OPEN_KEY, '1'); else sessionStorage.removeItem(OPEN_KEY); } catch { /* private mode */ } };
  if (!addr) return null;
  return <>
    <button type="button" className={`hqp-fab ${open ? 'on' : ''} ${busy.n ? 'is-work' : ''}`} onClick={() => set(!open)} data-testid="hq-pop-open" aria-label="Open HQ" aria-pressed={open} data-tip="HQ — one click, any page (creator wallet only)">
      <i aria-hidden="true" /><b>HQ</b></button>
    {open && <HqPopWindow address={addr} signMessage={signMessage} onClose={() => set(false)} />}
  </>;
}
