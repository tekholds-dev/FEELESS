import React, { useEffect, useRef, useState } from 'react';
import { QuickTrade } from './QuickTrade';
import { DipRipTool } from './DipRipTool';
import { ShieldBadge } from '../Shield';
import { EdgeScore } from './EdgeScore';
import { LaunchForensics } from './LaunchForensics';
import { investigate } from '../CaseFile';
import { DeskPop } from '../desk/DeskLook';
import { Ic3 } from '../../lib/icon3d';
import '../../styles/deskLook.css';
import '../../styles/trenchFlip.css';

// 🔁 TRENCH DASH v2 (Slice 34, owner 2026-11-20: "quick trade on one side and chat on the other … keep it sort of one page").
// The right card flips between Quick trade (Market / Dip & rip — the very QuickTrade and DipRipTool the chart carried, so every order still
// goes through the wallet: it signs everything) and the coin chat, with an unread badge. Both faces stay mounted: flipping never loses a typed
// amount or the chat's place. The tools that don't fit one screen live in a Tools popover that opens each one in its own window.
const read = (k, d) => { try { return localStorage.getItem(k) || d; } catch { return d; } };
const keep = (k, v) => { try { localStorage.setItem(k, v); } catch { /* this visit only */ } };

/** counts chat messages that arrive while the chat face is hidden (real rendered rows, never a guess) */
export function useUnread(ref, watching) {
  const [n, setN] = useState(0); const seen = useRef(null);
  useEffect(() => {
    const el = ref.current; if (!el) return undefined;
    const ids = () => [...el.querySelectorAll('[data-testid^="chat-message-"]')].map(x => x.getAttribute('data-testid'));
    if (!watching) { seen.current = null; setN(0); return undefined; }
    seen.current = new Set(ids());
    const mo = new MutationObserver(() => { const fresh = ids().filter(id => !seen.current.has(id)); if (fresh.length) { fresh.forEach(id => seen.current.add(id)); setN(x => x + fresh.length); } });
    mo.observe(el, { childList: true, subtree: true }); return () => mo.disconnect();
  }, [ref, watching]);
  return n;
}

export function TradeChatFlip({ pair, chat }) {
  const [face, setFace] = useState(() => (read('feeless.trenchFlip', 'trade') === 'chat' ? 'chat' : 'trade'));
  const [kind, setKind] = useState(() => (read('feeless.trenchOrder', 'mkt') === 'dr' ? 'dr' : 'mkt'));
  const chatRef = useRef(null); const unread = useUnread(chatRef, face !== 'chat');
  const turn = f => { setFace(f); keep('feeless.trenchFlip', f); };
  const solana = pair?.chainId === 'solana';
  return <section className={`tfl is-${face}`} data-testid="trench-flip">
    <header className="tfl-h" role="tablist" aria-label="Trade or chat">
      <button type="button" role="tab" aria-selected={face === 'trade'} onClick={() => turn('trade')} data-testid="tfl-to-trade"><Ic3 e="⚡" /> Quick trade</button>
      <button type="button" role="tab" aria-selected={face === 'chat'} onClick={() => turn('chat')} data-testid="tfl-to-chat"><Ic3 e="💬" /> Chat{unread ? <em className="tfl-badge" data-testid="tfl-unread">{unread > 99 ? '99+' : unread}</em> : null}</button>
    </header>
    <div className="tfl-face tfl-trade" hidden={face !== 'trade'} data-testid="tfl-trade">
      {pair ? <>
        <div className="tfl-seg" role="group" aria-label="Order type">{[['mkt', 'Market'], ['dr', 'Dip & rip']].map(([k, l]) => <button key={k} type="button" aria-pressed={kind === k} onClick={() => { setKind(k); keep('feeless.trenchOrder', k); }} data-testid={`tfl-order-${k}`}>{l}</button>)}</div>
        <div hidden={kind !== 'mkt'}><QuickTrade pair={pair} /></div>
        <div hidden={kind !== 'dr'}><DipRipTool pair={pair} /></div>
        {solana ? <ShieldBadge mint={pair.baseToken?.address} /> : null}
      </> : <p className="tfl-empty">Pick a coin to trade it.</p>}
    </div>
    <div ref={chatRef} className="tfl-face tfl-chat" hidden={face !== 'chat'} data-testid="tfl-chat">{chat}</div>
  </section>;
}

/** the Tools popover: what no longer fits one screen, each one opening in its own window — nothing is lost */
export function TrenchTools({ pair, calls, wide, onWide }) {
  const [open, setOpen] = useState(false); const [win, setWin] = useState(null); const box = useRef(null);
  useEffect(() => { if (!open) return undefined; const off = e => { if (box.current && !box.current.contains(e.target)) setOpen(false); }; const esc = e => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', off); document.addEventListener('keydown', esc); return () => { document.removeEventListener('pointerdown', off); document.removeEventListener('keydown', esc); }; }, [open]);
  const mint = pair?.baseToken?.address;
  const items = [
    ['calls', '📣', 'Calls log', 'Hot calls, live calls and the caller board', () => setWin('calls')],
    ['why', '🧭', 'Why this read', 'The FEELESS Edge score and every reason behind it', () => setWin('why')],
    ['forensics', '🔬', 'Snipers + bundles · dev', 'Who got in early, bundled wallets and the creator', () => setWin('forensics')],
    ...(mint ? [['case', '🗂', 'Case file', "This coin's case file", () => investigate(mint)]] : []),
    ['wide', wide ? '🗗' : '🗖', wide ? 'Normal chart' : 'Wide chart', 'Give the chart the whole row', () => onWide?.()],
  ];
  const body = { calls, why: pair ? <EdgeScore pair={pair} /> : null, forensics: pair ? <LaunchForensics pair={pair} /> : null }[win];
  const title = (items.find(i => i[0] === win) || [])[2] || '';
  return <span className="tfl-tools" ref={box}>
    <button type="button" className="tfl-tools-btn" aria-expanded={open} onClick={() => setOpen(o => !o)} data-tip="Everything that doesn't fit one screen" data-testid="trench-tools"><Ic3 e="🧰" /> Tools <b className="m-num">{items.length}</b></button>
    {open ? <div className="tfl-pop" role="menu" data-testid="trench-tools-pop">{items.map(([k, e, l, tip, go]) => <button key={k} type="button" role="menuitem" onClick={() => { setOpen(false); go(); }} data-tip={tip} data-testid={`trench-tool-${k}`}><Ic3 e={e} size="20px" /><span>{l}</span></button>)}</div> : null}
    <span className="tfl-host"><DeskPop open={!!body} title={title} wide onClose={() => setWin(null)} testid="trench-win">{body}</DeskPop></span>
  </span>;
}
