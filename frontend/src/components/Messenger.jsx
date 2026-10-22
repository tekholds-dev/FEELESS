import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { MessageCircle, Send, Settings2 } from 'lucide-react';
import { toast } from 'sonner';
import { ChatFx, ChatThemePicker, chatTheme, useFeeUsd, useBadgeBgs } from './ChatFx';
import { useChatPrefs } from '../lib/chatPrefs';
import { usePresence } from '../lib/presence';
import { PresenceDot } from './PresenceDot';
import '../styles/messenger.css';

// 💬 THE INBOX = A MESSENGER (owner, 2026-10-20: "chat should expand more vertically and look exactly like Facebook Messenger but better, with
// features they forgot; fix overflow"): drawn on <body> (a portal — the profile's own layout can never sit on top of it or clip it), tall
// (up to 88vh), a searchable conversation list with avatars beside the open chat, bubbles grouped by sender with day separators, Enter sends /
// Shift+Enter new line, the box grows with what you type, one-tap trench replies, copy a message, paste a CA → a coin link. Esc closes.
const QUICK = ['gm ☀️', 'wagmi', '👀', '🚀', 'LFG', 'ser'];
// ⚙ INBOX SETTINGS (owner, 2026-10-20: "inbox can have settings with dope and clean UI — themes, spam"): one look per browser (localStorage
// feeless.dmLook): chat theme · bubble style · text size · enter-to-send · spam filter on/off · muted + pinned chats. The server's "who can message me"
// sits in the same panel. Spam = a stranger's first message that pushes a link / airdrop / "claim" / a contract with nothing else (pure, tested).
export const DM_THEMES = [['royal', '🌿 Royal'], ['noir', '🎩 Noir'], ['midnight', '🌌 Midnight'], ['aurora', '🌈 Aurora'], ['sunset', '🌅 Sunset'], ['matrix', '🟩 Matrix'], ['paper', '📄 Paper']];
export const DM_BUBBLES = [['round', 'Round'], ['sharp', 'Sharp'], ['glass', 'Glass']];
export const DM_SIZES = [['s', 'S'], ['m', 'M'], ['l', 'L']];
const DM_DEFAULT = { theme: 'royal', bubble: 'round', size: 'm', enter: true, spam: true, muted: [], pinned: [] };
export const readLook = () => { try { return { ...DM_DEFAULT, ...(JSON.parse(localStorage.getItem('feeless.dmLook') || '{}') || {}) }; } catch { return { ...DM_DEFAULT }; } };
const SPAM_RE = /(https?:\/\/|t\.me\/|discord\.gg|airdrop|claim (your|now)|free (sol|tokens?|nft)|giveaway|dm me|whitelist|presale|connect (your )?wallet|seed phrase|verify (your )?wallet)/i;
export const isSpam = t => Boolean(t && t.request && SPAM_RE.test(String(t.last?.text || '')));
export const folderOf = (t, look) => ((look.muted || []).includes(t.peer) ? 'muted' : look.spam && isSpam(t) ? 'spam' : t.request ? 'requests' : 'all');
export const dayWord = t => { const d = new Date(t * 1000); const n = new Date(); const y = new Date(n); y.setDate(n.getDate() - 1);
  return d.toDateString() === n.toDateString() ? 'Today' : d.toDateString() === y.toDateString() ? 'Yesterday' : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }); };
const hm = t => new Date(t * 1000).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
const ini = h => String(h || '?').replace('@', '').slice(0, 2).toUpperCase();
const hue = s => [...String(s || '')].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 360, 140);
// messages → [{day} | {group: me, from, items}] (a run by the same sender within 5 min = one group, like Messenger)
export function groupMsgs(msgs, peer) {
  const out = []; let lastDay = null; let g = null;
  for (const m of msgs || []) {
    const at = Number(m.at) || 0; const d = dayWord(at); const me = m.from !== peer;
    if (d !== lastDay) { out.push({ day: d, key: `d-${at}` }); lastDay = d; g = null; }
    if (g && g.me === me && at - g.last <= 300) { g.items.push(m); g.last = at; continue; }
    g = { me, from: m.from, items: [m], last: at, key: `g-${m.id || at}` }; out.push(g);
  }
  return out;
}
const CA = /\b[1-9A-HJ-NP-Za-km-z]{32,44}\b/;
function Text({ t }) {
  const m = String(t || '').match(CA);
  if (!m) return <>{t}</>;
  const [a, b] = [t.slice(0, m.index), t.slice(m.index + m[0].length)];
  return <>{a}<a className="msx-ca" href={`/terminal/coin/solana/${m[0]}`} onClick={e => e.stopPropagation()}>🪙 {m[0].slice(0, 4)}…{m[0].slice(-4)}</a>{b}</>;
}

export function Messenger({ mine, wallet, session, start, threads, withPeer, setWith, msgs, text, setText, send, policy, prefs, pending, setThreads, endRef, onClose }) {
  const [q, setQ] = useState('');
  const [look, setLookS] = useState(readLook); const [gear, setGear] = useState(false); const [fold, setFold] = useState('all');
  const online = usePresence((threads || []).map(t => t.peer));   const [cprefs, setCprefs] = useChatPrefs(); const feeUsd = useFeeUsd(wallet?.address); const perkBgs = useBadgeBgs(wallet?.address);   // 🎨 the inbox's animated background (same themes as every chat)
  const setLook = patch => setLookS(l => { const n = { ...l, ...patch }; try { localStorage.setItem('feeless.dmLook', JSON.stringify(n)); } catch {} return n; });
  const toggle = (k, peer) => setLook({ [k]: (look[k] || []).includes(peer) ? look[k].filter(x => x !== peer) : [...(look[k] || []), peer] });
  const box = useRef(null);
  useEffect(() => { const k = e => { if (e.key === 'Escape') onClose(); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose]);
  useEffect(() => { const el = box.current; if (el) { el.style.height = 'auto'; el.style.height = `${Math.min(140, el.scrollHeight)}px`; } }, [text]);
  const counts = useMemo(() => (threads || []).reduce((a, t) => { const f = folderOf(t, look); a[f] = (a[f] || 0) + 1; return a; }, {}), [threads, look]);
  const list = useMemo(() => (threads || []).filter(t => folderOf(t, look) === fold && (!q || `${t.handle} ${t.last?.text || ''}`.toLowerCase().includes(q.toLowerCase())))
    .sort((a, b) => ((look.pinned || []).includes(b.peer) - (look.pinned || []).includes(a.peer)) || ((b.last?.at || 0) - (a.last?.at || 0))), [threads, q, fold, look]);
  const peer = (threads || []).find(t => t.peer === withPeer);
  const groups = useMemo(() => groupMsgs(msgs, withPeer), [msgs, withPeer]);
  const submit = e => { e?.preventDefault?.(); if (text.trim()) send({ preventDefault() {} }); };
  const quick = w => { setText(t => (t ? `${t} ${w}` : w)); box.current?.focus(); };
  const copy = t => (navigator.clipboard?.writeText(t) || Promise.reject()).then(() => toast.success('Copied')).catch(() => {});
  const title = withPeer ? `@${peer?.handle || `${withPeer.slice(0, 4)}…${withPeer.slice(-4)}`}` : mine ? 'Chats' : 'Private chat';
  return createPortal(<section className={`msx ${mine ? 'has-list' : ''} ${withPeer ? 'has-chat' : ''} msx-t-${look.theme} msx-b-${look.bubble} msx-s-${look.size}`} data-testid="profile-dm" role="dialog" aria-label="Messages">
    <header className="msx-head">
      {mine && withPeer ? <button type="button" className="msx-back" onClick={() => setWith(null)} aria-label="Back to chats">‹</button> : null}
      <span className="msx-ava is-head" style={{ '--h': hue(withPeer || 'inbox') }}>{withPeer ? ini(peer?.handle || withPeer) : <MessageCircle size={16} />}</span>
      <span className="msx-title"><b>{title}</b><small>{withPeer ? 'private · end to end between two wallets' : `${(threads || []).length} conversations`}</small></span>
      {withPeer ? <button type="button" className={`msx-ic ${(look.pinned || []).includes(withPeer) ? 'on' : ''}`} onClick={() => toggle('pinned', withPeer)} aria-label="Pin this chat" data-tip="Pin to the top">📌</button> : null}
      {withPeer ? <button type="button" className={`msx-ic ${(look.muted || []).includes(withPeer) ? 'on' : ''}`} onClick={() => toggle('muted', withPeer)} aria-label="Mute this chat" data-tip="Mute (moves to Muted)">🔕</button> : null}
      <button type="button" className={`msx-ic ${gear ? 'on' : ''}`} onClick={() => setGear(g => !g)} aria-label="Inbox settings" aria-expanded={gear} data-testid="dm-gear"><Settings2 size={15} /></button>
      <button type="button" className="msx-x" onClick={onClose} aria-label="Close" data-testid="dm-close">×</button>
    </header>
    {gear ? <div className="msx-gear" data-testid="dm-settings">
      <div className="msx-gr"><span>THEME</span><div className="msx-seg">{DM_THEMES.map(([k, l]) => <button key={k} type="button" className={look.theme === k ? 'on' : ''} onClick={() => setLook({ theme: k })} data-testid={`dm-theme-${k}`}><i className={`msx-sw msx-t-${k}`} />{l}</button>)}</div></div>
      <div className="msx-gr"><span>BUBBLES</span><div className="msx-seg">{DM_BUBBLES.map(([k, l]) => <button key={k} type="button" className={look.bubble === k ? 'on' : ''} onClick={() => setLook({ bubble: k })}>{l}</button>)}</div>
        <span>TEXT</span><div className="msx-seg">{DM_SIZES.map(([k, l]) => <button key={k} type="button" className={look.size === k ? 'on' : ''} onClick={() => setLook({ size: k })}>{l}</button>)}</div></div>
      <div className="msx-gr"><label className="msx-tg"><input type="checkbox" checked={!!look.spam} onChange={e => setLook({ spam: e.target.checked })} /><span>🛡 Spam filter — strangers pushing links, airdrops, "claim" or wallet verifies go to Spam</span></label>
        <label className="msx-tg"><input type="checkbox" checked={!!look.enter} onChange={e => setLook({ enter: e.target.checked })} /><span>⏎ Enter sends (Shift+Enter = new line)</span></label></div>
      {policy ? <div className="msx-gr"><span>WHO CAN MESSAGE ME</span><div className="msx-seg">{[['everyone', 'Everyone'], ['requests', 'Requests first'], ['nobody', 'Nobody']].map(([k, l]) => <button key={k} type="button" className={policy === k ? 'on' : ''} onClick={() => prefs({ policy: k })}>{l}</button>)}</div></div> : null}
      <div className="msx-gr msx-motion"><span>MOTION · behind your chats</span><ChatThemePicker prefs={cprefs} setPrefs={setCprefs} room="inbox" feeUsd={feeUsd} unlocked={perkBgs} /></div>
      <small className="msx-gnote">Looks and filters live in this browser. Your messages stay between the two wallets.</small>
    </div> : null}
    {!wallet || !session ? <div className="msx-gate"><MessageCircle size={28} /><p>{wallet ? 'Sign once to chat privately (free, 7 days).' : 'Connect a wallet to chat.'}</p>
      <button type="button" className="m-btn m-go" onClick={start}>{wallet ? 'Sign in' : 'Connect'}</button></div>
      : <div className="msx-body">
        {mine ? <aside className="msx-list">
          <input className="msx-search" value={q} onChange={e => setQ(e.target.value)} placeholder="Search chats" aria-label="Search chats" />
          <div className="msx-folds" role="tablist">{[['all', 'All'], ['requests', 'Requests'], ['spam', 'Spam'], ['muted', 'Muted']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={fold === k} className={fold === k ? 'on' : ''} onClick={() => setFold(k)} data-testid={`dm-fold-${k}`}>{l}{counts[k] ? <b>{counts[k]}</b> : null}</button>)}</div>
          {!list.length ? <p className="msx-empty">{q ? 'No chat matches.' : 'No conversations yet.'}</p> : list.map(t => <button key={t.peer} type="button" className={`msx-row ${withPeer === t.peer ? 'on' : ''}`} onClick={() => setWith(t.peer)}>
            <span className="msx-ava" style={{ '--h': hue(t.peer) }}>{ini(t.handle)}<PresenceDot status={online[t.peer] || 'offline'} /></span>
            <span className="msx-rowtx"><b>{(look.pinned || []).includes(t.peer) ? '📌 ' : ''}@{t.handle}{t.request ? <em className="msx-req">request</em> : null}{isSpam(t) && look.spam ? <em className="msx-req is-spam">spam?</em> : null}</b><small>{t.last?.text || ''}</small></span>
            {t.last?.at ? <i className="msx-when">{hm(t.last.at)}</i> : null}</button>)}
        </aside> : null}
        {withPeer ? <div className="msx-chat has-cfx"><ChatFx theme={chatTheme(cprefs, 'inbox', feeUsd, perkBgs)} room="inbox" />
          <div className="msx-msgs">{groups.map(g => g.day ? <p key={g.key} className="msx-day"><span>{g.day}</span></p>
            : <div key={g.key} className={`msx-grp ${g.me ? 'me' : 'them'}`}>{!g.me ? <span className="msx-ava is-sm" style={{ '--h': hue(g.from) }}>{ini(peer?.handle)}</span> : null}
              <div className="msx-bubs">{g.items.map((m, i) => <p key={m.id || i} className="msx-bub" onDoubleClick={() => copy(m.text)} title="Double-click to copy"><Text t={m.text} /></p>)}
                <small>{hm(g.last)}</small></div></div>)}
            {!msgs?.length ? <p className="msx-empty">Say gm 👋</p> : null}<i ref={endRef} /></div>
          {pending ? <div className="msx-request"><span>@{peer?.handle} wants to message you.</span><button type="button" className="m-btn m-go"
            onClick={() => prefs({ accept: withPeer }).then(() => setThreads(ts => ts.map(t => (t.peer === withPeer ? { ...t, request: false } : t))))}>Accept</button></div> : null}
          <div className="msx-quick">{QUICK.map(w => <button key={w} type="button" onClick={() => quick(w)}>{w}</button>)}</div>
          <form className="msx-compose" onSubmit={submit}>
            <textarea ref={box} rows={1} value={text} maxLength={1000} onChange={e => setText(e.target.value)} placeholder="Aa" aria-label="Message"
              onKeyDown={e => { if (look.enter && e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } }} data-testid="dm-input" />
            <button type="submit" className="msx-send" disabled={!text.trim()} aria-label="Send" data-testid="dm-send"><Send size={17} /></button>
          </form>
        </div> : mine ? <div className="msx-pick"><MessageCircle size={34} /><p>Pick a chat on the left.</p></div> : null}
      </div>}
  </section>, document.body);
}
