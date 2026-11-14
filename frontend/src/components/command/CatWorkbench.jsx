import { useOnScreen } from '../../lib/fxPause';
import ProofLive, { proofOf } from './ProofLive';
import { KalshiDoor, KalshiTicket } from './KalshiDoor';
import { priceWord, useProofPrices } from '../../lib/proofPrice';
import { Creations, PreviewButton } from './AgentStudio';
import React, { Suspense, lazy, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { boxRef } from '../../lib/boxRef';
const screenBox = boxRef([], { vars: true });   // 📐 --box-w/--box-h for the cursor, drop and SL/TP dot (cqw/cqh with no container froze HQ)
const poiBox = boxRef([620]);
import { createPortal } from 'react-dom';
import { apiUrl } from '../../lib/api';
import { ProofMonitorBody } from './ProofMonitor';
import { TestBench } from './TestBench';
import { startOpenRouterConnect, takeConnectResult } from '../../lib/openrouterConnect';
import { AgentLog, MindVitals, PowCard, SafeGate, safeOk } from './CatCockpit';
import { HeadCloud, McapChart, asModel } from './AgentLive';
import { useStickToBottom } from '../../lib/useStickToBottom';
import { ApiDrawer, Bubble } from './LaunchCat';
import '../../styles/agentDemo.css';
import '../../styles/catWorkbench.css';
import '../../styles/hive.css';
import { agentAuth, agentAuthQuery, revealMessage, shareMessage, getChatSession } from '../../lib/chatSession';
import { svgPngBlob } from '../../lib/svgPng';
import { useWallet } from '../../hooks/useWallet';
import { useSolPrice } from '../../lib/solPrice';
import '../../styles/collective.css';
import { ProofTools } from './ProofTools';
import { KernelCard, PoiFolder, PoiMinds } from './PoiFolder';
import { PopDesk, Calls, Live, ProposalCard } from './PopDesk';
import { CardSites, BidSites, BID_SITES } from './BidSites';
import { CostTicket, FolderRidge, PrintLines, PrintSeed, ProofHead, ProofKit, ProofSubmit, ProofTile as Tile, SitesRead, shortCost } from './ProofKit';
import { GitFolder } from './GitFolder';
import { EcoFolder } from './EcoFolder';
import { EngineFolder } from './EngineFolder';
import { CommandCenter } from './CommandCenter';
import { DatabaseFolder } from './DatabaseFolder';
import { DebateFolder } from './DebateFolder';
import { WatchWall } from './ProofRooms';
import { linesOf, printOf } from '../../lib/proofprint';
import { proofRows } from './ProofsFolder';
import { MailApp, SiteDoor, SignInFrame, SignInView, SiteTradeCard, TopupCard, TypeBar, WatchFolders } from './SiteDoor';
import { ProofsFolder, visitorProofs } from './ProofsFolder';
import ProofPicker from './ProofPicker';
import { ChatGrip, ChatSizeSeg, useChatSize } from './ChatSize';
import { ProofsList } from './ProofStamp';
import { SetupDeck, TermsFolder } from './SetupDeck';
import { LiveCount, useAgentPool } from './BoostFolder';
import { DeskWidgets } from './DeskWidgets';
import { SplitFlow, money } from './SplitFlow';
import { AgentStage, ChatStylePicker, chatClass, useChatStyle } from './ChatStyles';
import { ChatAttach, ChatComposer, ChatInput, ChatSend, ChatSettings, ChatStop } from '../chat/ChatKit';
import { DeskPrint } from './Proofprint';
import { BackToDesk, BoostCoin, DeskBell, DeskSettings, deskSet, useDeskPrefs, useDeskIcons, useDeskOverPage, DeskExtras, DeskIcon, DeskGrid, DeskTour, DeskWin, SetupDot, VitalsWall, PerfDiagram, PerfGlass, ShaderWall, glassOf, perfSeries, placeFor, tourSeen } from './DeskShell';
import { Ic3, Ic3Text, IconLook } from '../../lib/icon3d';
import { AgentManual } from './AgentManual';
import { SnapStack, cleanShots, cleanFolderShots } from './SnapStack';
import { useLivePrice } from '../../lib/livePriceHub';
import { FirstTips } from '../FirstTips';
import { twoTap } from '../ActBtn';

// 🧠🧠 THE GENERAL CAT'S WORKBENCH (owner 2026-10-29, P2 — backend cat_agent.py + cat_browser.py). Two browser windows, one per model, running in
// the cloud (Steel → Browserbase → the reader: never on this device). Each window: its model, its provider, the page it is on, a bubble top-right
// with what it is doing right now, and — when a sign-in / sign-up / CAPTCHA needs a person — a centred ✋ card (you act in the live window, then
// CONTINUE). Under them ONE chat: Enter → a fast answer from memory, or both models research their halves and merge. The $ bars: the agent's credit
// left and THIS task's spend against its cap (you set it; the task stops at it). Live views run only while on screen; polling pauses when hidden.
const CAPS = [0.02, 0.05, 0.25, 1];
const PROV = { kernel: ['KERNEL', 'is-steel'], anchor: ['ANCHOR', 'is-steel'], steel: ['STEEL', 'is-steel'], browserless: ['BROWSERLESS', 'is-bl'], browserbase: ['BROWSERBASE', 'is-bb'], reader: ['READER', 'is-reader'] };
const usd = v => (v == null ? '—' : `$${Number(v) < 1 ? Number(v).toFixed(4) : Number(v).toFixed(2)}`);
const LIVE_STATES = ['planning', 'working', 'merging'];
// 🧭 its two ways (cat_agent.MODES): plan together → one answer · each mind its own job
const WAYS = [['plan', '🧠🤝 ONE ANSWER', 'They plan it in a sentence each, split it, research in their own windows, merge into one answer'], ['jobs', '🎯🎯 TWO JOBS', 'Give each mind its own job — both run at once, two results']];

// 🛟 the agent service not answering (a restart, a 502 / 503 / 504 from the proxy) says so in plain words — never a bare "HTTP 504"
const DOWN = 'The agent service is not answering right now (it may be restarting) — nothing was sent. Try again in a few seconds.';
export async function work(id, body) {
  let r;
  try { r = await fetch(apiUrl(`/api/cats/${id}/work`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), ...body }) }); } catch { throw Object.assign(new Error(DOWN), { down: true }); }
  const j = await r.json().catch(() => ({}));
  if (r.status >= 502 && r.status <= 504) throw Object.assign(new Error(DOWN), { down: true });
  if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`);
  return j;
}


// 🃏 ONE OWNER DESK for every agent (owner 2026-10-31: "both trader and general desks should be the same, slightly different for what's needed"):
// [mind A vitals | head cloud + the chat card | mind B vitals] — the Files button flips the WHOLE desk over to its file cabinet, Esc / Chat flips back
const FILES_ICON = <svg viewBox="0 0 20 20" aria-hidden="true"><rect x="3" y="3" width="14" height="5" rx="1.5" /><rect x="3" y="10" width="14" height="7" rx="1.5" /><path d="M8 5.5h4M8 13.5h4" /></svg>;
// 🐝 COLONIZE (owner 2026-10-31: "a popout explaining it; users must stake FEECAT to colonize"): on = it files a graded coin call every N minutes on its
// own AND its trades are graded (entry, then an hour on; exit, then an hour on) — honey decides its share of the colony pot's growth. Off any time.
const PACES = [[120, '2 min'], [300, '5 min'], [900, '15 min'], [3600, '1 h']];
const COLONY_STEPS = [['🔎', 'It works in the Collective', 'One coin at a time, one small model call each, inside its $ limits, until you turn it off.'],
  ['📈', 'Every move is graded, before and after', 'Its calls, entries and exits are each judged an hour on against what the coin really did.'],
  ['⚡', 'Boosts come three ways', 'A winning proof of +50% or more sent to the Pool with its transaction, a convo call the market later proves, or a Debate room with a stake on both sides, which raises what a stake may earn. Nothing else earns one.'],
  ['👛', 'Your money is never pooled', 'It keeps trading from its own wallet. Only the % you sign below ever goes to the Pool.']];
const SHARE_PCTS = [5, 10, 15, 20, 25];
// 🤝 the owner's signed share of each WIN to the colony pot — one hook for the Colonize popout and the PoW folder (sharing never needs colonizing)
function useColonyShare(cat) {
  const { signMessage } = useWallet() || {}; const [share, setShare] = useState(cat?.colonyShare || { on: false, pct: 10 });
  const sign = async (on, pct = share.pct) => { let x;
    if (on) { const ts = Math.floor(Date.now() / 1000); const sig = await signMessage(shareMessage(cat.id, pct, ts)); x = await work(cat.id, { op: 'share', on: true, cap: pct, ts, sig }); }
    else x = await work(cat.id, { op: 'share', on: false });
    setShare(x.colonyShare); return x.colonyShare; };
  return [share, setShare, sign, !!signMessage];
}
export function HiveSwitch({ cat }) {
  const [share, setShare, signShare, canSign] = useColonyShare(cat); const [meta, setMeta] = useState(null);
  const [h, setH] = useState(cat?.hive || { on: false, every: 300 }); const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [pop, setPop] = useState(false); const [pace, setPace] = useState(cat?.hive?.every || 300);
  const set = async (on, every) => { setBusy(true); setErr(''); try { const r = await work(cat.id, { op: 'hive', on, cap: every }); setH(r.hive); setPop(false); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  useEffect(() => { if (pop) fetch(apiUrl(`/api/cats/colony?ids=${cat.id}`)).then(r => (r.ok ? r.json() : null)).then(x => x && setMeta(x)).catch(() => {}); }, [pop, cat?.id]);   // the pool + the airdrop clock
  const [convo, setConvo] = useState(!!cat?.convo?.on);
  const toggleConvo = async () => { setBusy(true); setErr(''); try { const r = await work(cat.id, { op: 'convo', on: !convo }); setConvo(!!r.convo?.on); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const sign = async on => { setBusy(true); setErr(''); try { await signShare(on); } catch (e) { setErr(e.message || 'Not signed'); } finally { setBusy(false); } };
  useEffect(() => { if (!pop) return undefined; const k = e => e.key === 'Escape' && setPop(false); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [pop]);
  const every = PACES.find(p => p[0] === h.every)?.[1] || `${Math.round(h.every / 60)} min`; const collecting = !!(share.on && share.auto); const noWallet = !cat?.agentWallet?.address && !cat?.realWallet;
  return <span className="hv-sw" data-testid="hive-sw">
    <button type="button" className={h.on ? 'is-on' : ''} aria-pressed={!!h.on} disabled={busy} onClick={() => (h.on && collecting ? set(false, h.every) : (setErr(''), setPop(true)))} data-testid="hive-toggle"
      data-tip={h.on && collecting ? `💎 In the Collective, and wins of +50% or more pay the Pool. It files a graded call every ${every}. Click to leave` : h.on ? '💎 In the Collective, but wins do not pay the Pool yet. Click to sign Auto-collect' : '💎 What the Collective is and the ways to earn, then you confirm'}><i aria-hidden="true"><Ic3 e="💎" /></i> {h.on && collecting ? 'AUTO-COLLECT ON' : h.on ? 'IN THE COLLECTIVE' : 'AUTO-COLLECT'}</button>
    {h.on ? <select value={h.every} disabled={busy} onChange={e => set(true, Number(e.target.value))} aria-label="How often it files a call" data-testid="hive-pace">{PACES.map(([v, l]) => <option key={v} value={v}>every {l}</option>)}</select> : null}
    {pop ? createPortal(<div className="hv-shade" onClick={e => e.target === e.currentTarget && setPop(false)}>
      <section className="hv-pop m-pop" role="dialog" aria-modal="true" aria-labelledby="hv-pop-h" data-testid="colonize-pop">
        <header><span className="hv-pop-orb" aria-hidden="true"><i /><i /><i /></span><div><small>THE COLLECTIVE</small><h3 id="hv-pop-h">Auto-collect for {cat?.name || 'this agent'}</h3></div>
          <button type="button" className="hv-pop-x" onClick={() => setPop(false)} aria-label="Close" data-tip="Close (Esc)">✕</button></header>
        <ol className="hv-pop-steps">{COLONY_STEPS.map(([ic, h3, p], k) => <li key={h3} style={{ '--i': k }}><b aria-hidden="true"><Ic3 e={ic} /></b><span><strong>{h3}</strong><small>{p}</small></span></li>)}</ol>
        <div className="hv-opps"><small>WAYS TO EARN IN THE COLLECTIVE</small>
          <article className={`hv-opp${convo ? ' is-on' : ''}`} data-testid="colony-opp-convo"><b className="hv-opp-n">3</b><span><strong>💬 Collective convos</strong><small>Once a day it talks with an agent of another owner: two short model calls on its own credit, at most 3 proofs. They make one joint call. If the market proves it in 24 hours, both earn a boost.</small><button type="button" className={`m-btn${convo ? ' m-go' : ''}`} disabled={busy} aria-pressed={convo} onClick={toggleConvo} data-testid="colony-convo">{convo ? 'Convos on' : 'Turn on convos'}</button></span></article>
          <article className="hv-opp" data-testid="colony-opp-stake"><b className="hv-opp-n">1</b><span><strong>🌊 Stake FEECAT or SOL in the Collective LP</strong>
            <small>The pool lives on its own platform and pays on its own epochs.</small>
            <em className={meta?.pool ? 'is-on' : ''}>{meta?.pool ? `OPEN on ${meta.pool.platform} · ${meta.pool.address.slice(0, 4)}…${meta.pool.address.slice(-4)} — staking from here isn't wired yet` : 'NOT OPEN YET — FEELESS opens it with the Pool wallet'}</em></span></article>
          <article className={`hv-opp${share.on ? ' is-on' : ''}`} data-testid="colony-opp-share"><b className="hv-opp-n">2</b><span><strong>🤝 Auto-collect: send a % of big wins</strong>
            <small>Sign once: each real proof that wins +50% or more sends the % you pick of its profit to the Collective, with its receipt in the folder. It stays there and earns points. Only send what you are willing to wait on. Losses send nothing.</small>
            <SplitFlow testid="colony-split" />
            {cat?.handle === 'sicarios' ? <em data-testid="colony-sicario">Join and it runs PoWs until the card's 4 seats are full. Card wins do not pay the Pool yet: that send is not built.</em> : noWallet ? <em data-testid="colony-no-wallet">Auto-collect sends from the agent's own wallet, and this one has none, so a win cannot pay the Pool yet.</em> : null}
            {collecting ? <span className="hv-opp-row"><em className="is-on">SHARING {share.pct}% · signed</em><button type="button" className="m-btn" disabled={busy} onClick={() => sign(false)} data-testid="colony-share-off">Stop sharing</button></span>
              : <span className="hv-opp-row"><span className="m-seg" role="group" aria-label="Share of each winning trade">{SHARE_PCTS.map(v => <button key={v} type="button" className={share.pct === v ? 'active' : ''} aria-pressed={share.pct === v} onClick={() => setShare(x => ({ ...x, pct: v }))} data-testid={`colony-share-${v}`}>{v}%</button>)}</span>
                <button type="button" className="m-btn m-go" disabled={busy || !canSign} onClick={() => sign(true)} data-testid="colony-share-sign" data-tip={canSign ? 'One wallet signature, no transaction' : 'Connect your wallet first'}><Ic3 e="✍" /> {share.on ? 'Sign again to turn it on' : 'Sign to share'}</button>{share.on ? <small data-testid="colony-share-old">Your last signature was for the old share, so nothing sends until you sign this one.</small> : null}</span>}</span></article></div>
        <label className="hv-pop-pace"><span>FILES A CALL</span><span className="m-seg" role="group" aria-label="How often it files a call">{PACES.map(([v, l]) => <button key={v} type="button" className={pace === v ? 'active' : ''} aria-pressed={pace === v} onClick={() => setPace(v)} data-testid={`colonize-pace-${v}`}>{l}</button>)}</span></label>
        {err ? <p className="lct-err" role="alert" data-testid="colonize-err">⚠ {err}</p> : null}
        <footer><button type="button" className="m-btn" onClick={() => setPop(false)}>Not now</button>{h.on ? <button type="button" className="m-btn" disabled={busy} onClick={() => set(false, h.every)} data-testid="colonize-leave">Leave the Collective</button> : null}<button type="button" className="m-btn m-go" disabled={busy} onClick={() => set(true, pace)} data-testid="colonize-go">{busy ? 'Joining…' : '💎 Colonize'}</button></footer>
      </section></div>, document.body) : null}</span>;
}

// 🕶 incognito (owner 2026-10-31): its screens hidden from visitors — $5 once per agent from its model credit (staff free), then on / off any time
export function IncognitoSwitch({ cat }) {
  const [on, setOn] = useState(!!cat?.incognito); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const flip = async () => { if (!on && !cat?.incognitoPaid && !twoTap('Incognito hides this agent\'s screens from everyone but you. It costs $5 once, from its model credit. Go incognito?')) return;
    setBusy(true); setErr(''); try { const r = await work(cat.id, { op: 'incognito', on: !on }); setOn(!!r.incognito); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  return <button type="button" className={`cwb-flip-btn cwb-incog${on ? ' is-on' : ''}`} aria-pressed={on} disabled={busy} onClick={flip} data-testid="incog-toggle"
    data-tip={err || (on ? '🕶 Incognito ON: visitors see no screens — only that it is working' : `🕶 Visitors watch its live screens (never its steps or what it types). Incognito hides them${cat?.incognitoPaid ? '' : ' — $5 once'}.`)}>🕶<span>{on ? 'Private' : 'Public'}</span></button>;
}

export function DeskFlip({ flip, setFlip, name, live, count, left, right, cloud, back, children, cat, size = null }) {
  const flipIn = useRef(null); const talk = useRef(null);   // ↕ AGX-3: the box a drag sizes (the talk column below 1100 px, the whole deck above)
  const measure = () => ((window.innerWidth <= 1100 ? talk.current : flipIn.current)?.offsetHeight || 0);   // ↕ layout px: the desk may be drawn scaled (0.9), a drag must not shrink it
  useEffect(() => { if (!flip) return undefined; const k = e => { if (e.key === 'Escape') setFlip(false); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [flip, setFlip]);
  return <div className={`cwb-under cwb-flip${flip ? ' is-back' : ''}`} data-testid="desk-flip"><div ref={flipIn} className="cwb-flip-in">
    <div className="cwb-face ck-cockpit cwb-deck" inert={flip}>
      {left}
      <div className="ck-center cwb-mid">
        <div ref={talk} className="cwb-talk" data-testid="cwb-cockpit">{size ? <ChatGrip measure={measure} onDrag={size.drag} /> : null}
          <header className="cwb-talk-h" onDoubleClick={e => { if (size && !e.target.closest('button, input, select, a')) size.toggleFocus(); }} data-tip={size ? 'Double-click: focus the chat (again: back)' : undefined}><span className={`cwb-status${live ? ' is-live' : ''}`}><i aria-hidden="true" />{live ? 'Working' : 'Ready'}</span>
            <b>Chat with {name || 'its minds'}</b>
            {size ? <ChatSizeSeg size={size.size} pick={size.pick} /> : null}{cat ? <HiveSwitch cat={cat} /> : null}{cat ? <IncognitoSwitch cat={cat} /> : null}
            <button type="button" className="cwb-flip-btn" onClick={() => setFlip(true)} aria-label="Flip to its file cabinet" data-tip="Flip to its file cabinet — every file, logins, sealed recovery files, API keys" data-testid="cwb-flip">
              {FILES_ICON}<span>Files</span><b className="m-num">{count}</b></button></header>
          {children}</div></div>
      {right}
    </div>
    <aside className="cwb-face cwb-back cwb-tools-rail" aria-label="Its file cabinet" inert={!flip} data-testid="cwb-sheet">
      <header className="cwb-talk-h"><b>Its file cabinet</b>
        <button type="button" className="cwb-flip-btn" onClick={() => setFlip(false)} aria-label="Flip back to the chat" data-tip="Back to the chat (Esc)" data-testid="cwb-flip-back">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 5h12v8H9l-4 3v-3H4z" /></svg><span>Chat</span></button></header>
      {cloud}{back}</aside>
  </div></div>;
}
// a general mind's vitals: what its window is doing right now
const host = u => String(u || '').replace(/^https?:\/\//, '').split(/[/?#]/)[0];
// ⛏ a research window whose round ended: its cloud browser is closed, so nothing may still say it works there
const roundIsOver = (w, f) => /^PROOF OF WORK/.test(w?.goal || '') && !!f?.coins?.length && !['scout', 'research'].includes(f.phase);
// ⛏ what this mind is doing right now, in its card: the proof it is on and its live step. Nothing running shows its last PoW, short. It never breaks out of the card.
const PH_ORDER = ['propose', 'split', 'scout', 'choose', 'buy', 'watch', 'research', 'sell'];
function MindNow({ d, w, p }) {
  const f = d?.powFolder; const pop = d?.popFolder; const pob = d?.pobRun || d?.pobRead; const trade = d?.task?.siteTrade; const working = w?.status === 'working' || w?.status === 'human';
  const kind = f ? 'PROOFING · PoW' : pop ? 'PROOFING · PoP' : pob ? 'PROOFING · PoB' : trade ? 'TRADING ON ITS ACCOUNT' : working ? 'WORKING' : null;
  if (!kind) return <PowCard p={p} compact />;
  const on = f ? (f.sym ? `$${f.sym}` : `${(f.coins || []).length} coins`) : pop ? `${pop.market || ''} ${pop.side || ''}`.trim() || 'Reading markets' : pob ? pob.topic || pob.q || 'Reading markets' : trade ? `$${trade.sym} on ${trade.site}` : (w?.url ? String(w.url).replace(/^https?:\/\//, '').split('/')[0] : 'Reading');
  const phase = f ? (PH[f.phase] || f.phase) : pop ? `Paper trade ${Number(pop.roePct || 0) >= 0 ? '+' : ''}${Number(pop.roePct || 0).toFixed(1)}%` : '';
  const at = f ? PH_ORDER.indexOf(f.phase) : -1;
  return <div className="ck-now" data-testid="ck-now"><span className="ck-now-h"><i aria-hidden="true" />{kind}</span><b>{on}</b>
    {at >= 0 ? <span className="ck-now-steps" role="img" aria-label={phase}>{PH_ORDER.map((x, n) => <u key={x} className={n < at ? 'is-done' : n === at ? 'is-at' : ''} />)}</span> : null}
    {phase ? <em className="ck-v-row"><b className="m-num is-pow">{phase}</b></em> : null}
    {w?.bubble ? <small data-testid="ck-now-step">{w.bubble}</small> : null}</div>;
}
function WinVitals({ w, f = null, i = 0, model = '' }) {   // ⛏ while a PoW folder runs, its role in it (owner: "it says IDLE while they work")
  if (f && (roundIsOver(w, f) || !(w?.status === 'working' || w?.status === 'human'))) {
    const me = String(i + (f.base || 0)); const name = String(model || '').split('/').pop().replace(':free', '');
    const said = [...(f.talk || [])].reverse().find(t => name && String(t.by).includes(name.slice(0, 12)));
    const rM = f.rPair ? f.rPair[i] : f.rMint && Number(f.rMind) === i ? f.rMint : null;
    const doing = rM ? `RESEARCHING $${(f.coins || []).find(c => c.mint === rM)?.sym || ''}` : (PH[f.phase] || f.phase || 'PoW').split(' ').slice(0, 3).join(' ');
    return <><span className="ck-v-row"><em>STATUS</em><b className="m-num is-pow">{doing}</b></span>
      <span className="ck-v-row"><em>FOLDER</em><b className="m-num">{String(f.name || '').split(' · ')[0]}</b></span>
      <span className="ck-v-row"><em>SPENT</em><b className="m-num">{usd(f.spend?.[me] || 0)}</b></span>
      <span className="ck-v-row"><em>ON</em><b className="m-num">{f.sym ? `$${f.sym}` : `${(f.coins || []).length} coins`}</b></span>
      <p className="ck-v-last">{said ? said.text : 'its turn comes next'}</p></>;
  }
  return <><span className="ck-v-row"><em>STATUS</em><b className="m-num">{String(w?.status || 'idle').toUpperCase()}</b></span>
    <span className="ck-v-row"><em>STEPS</em><b className="m-num" key={(w?.steps || []).length}>{(w?.steps || []).length}</b></span>
    <span className="ck-v-row"><em>SPENT</em><b className="m-num">{usd(w?.cost || 0)}</b></span>
    <span className="ck-v-row"><em>ON</em><b className="m-num">{host(w?.url) || '—'}</b></span>
    <p className="ck-v-last">{w?.bubble || (w?.goal ? 'waiting' : 'no job yet')}</p></>;
}

// 🖱 the AI's own cursor over its live window (owner 2026-10-31: "make sure the cursor actually shows and is controlled by the AI") — it glides to
// where the model clicks / types, measured in the real browser; the style is the viewer's pick in ⚙ (kept on this device only)
export const CURSORS = [['arrow', '➤ Arrow'], ['paw', '🐾 Paw'], ['dot', '◉ Neon dot'], ['cross', '✛ Crosshair']];
const CURSOR_KEY = 'feeless:ai-cursor';
export const readCursor = () => { try { return localStorage.getItem(CURSOR_KEY) || 'arrow'; } catch { return 'arrow'; } };
// 🖱 ALWAYS on (owner 2026-10-31): before its first move the cursor rests mid-screen, dimmed; then it glides to every real move
const REST = { x: 0.5, y: 0.55, act: 'move' };
export function AiCursor({ c, kind, think, page }) {   // think = its mind is working between moves → a 'reading' ring pulses at the cursor
  // 🖱 AGT-19: over a page-only screenshot (page) use the PAGE shares (px / py); x / y are shares of the whole window, chrome included (the live view)
  if (page && c?.px != null) c = { ...c, x: c.px, y: c.py };
  const rest = !c || c.x == null; if (rest) c = REST;
  return <span className={`cwb-cursor c-${kind}${rest ? ' is-rest' : ''}${think ? ' is-think' : ''}`} style={{ transform: `translate(calc(var(--box-w, 0px) * ${c.x}), calc(var(--box-h, 0px) * ${c.y}))` }} data-testid="cwb-cursor" aria-hidden="true">
    <i /><u key={c.at} className={`at-${c.act || 'click'}`} /></span>;
}

// 📥 when a mind keeps something (a note, a FEELESS read, media, a draft, a handoff) the named data drops from where it was on screen — its cursor —
// down into its files (owner 2026-10-31: "named data dropped down from wherever the info came from on screen, like Crawl but better")
const KEEPS = { note: '🗒', feeless: '📈', media: '🖼', draft: '✍', build: '🛠', handoff: '📦', pull: '⛏' };
const TRAY_MS = 8000;
// 📥 what it grabbed flies from its cursor to the BOTTOM of its monitor and sits in a tray (last 3) before it fades (owner 2026-11-01)
export function useDrop(w) {
  const [drop, setDrop] = useState(null); const [tray, setTray] = useState([]); const last = useRef(null);
  useEffect(() => { const s = (w?.steps || []).at(-1); if (!s || !KEEPS[s.action]) return undefined; const k = `${s.at}-${s.action}`;
    if (last.current === null) { last.current = k; return undefined; } if (last.current === k) return undefined; last.current = k;
    const it = { k, icon: KEEPS[s.action], label: String(s.detail || s.thought || s.action).slice(0, 56), x: w?.cursor?.x ?? 0.5, y: w?.cursor?.y ?? 0.35 };
    setDrop(it);
    const t1 = setTimeout(() => { setDrop(null); setTray(x => [...x, it].slice(-3)); }, 1100);
    const t2 = setTimeout(() => setTray(x => x.filter(y => y.k !== k)), 1100 + TRAY_MS);
    return () => { clearTimeout(t1); clearTimeout(t2); }; }, [w?.steps, w?.cursor]);
  return { drop, tray };
}

// 🖍 What it boxed on the page runs down a wire to the bottom of its monitor, and what it got sits there for a few seconds (owner 2026-11-07).
const FIND_MS = 7000;
// the wire shows for 7 s with a slim tray on the monitor: the last 3 finds, newest bright (owner 2026-11-07: "smaller for if they grab multiple info")
function useFinds(m) {
  const [wire, setWire] = useState(null); const [list, setList] = useState([]);
  useEffect(() => { if (!m?.at || !(m.pts || []).length) return undefined; setWire(m); setList(l => [m, ...l.filter(x => x.at !== m.at)].slice(0, 3));
    const t = setTimeout(() => setWire(x => (x === m ? null : x)), FIND_MS); return () => clearTimeout(t); }, [m?.at]);   // eslint-disable-line react-hooks/exhaustive-deps
  return [wire, list];
}
export function FindWires({ m }) {
  const [on, list] = useFinds(m);
  if (!on) return null; const pts = on.pts.slice(0, 8); const slot = i => 8 + (84 * (i + 0.5)) / pts.length;
  return <div className={`cwb-find${on.hunt ? ' is-hunt' : ''}`} key={on.at} data-testid="cwb-find" aria-live="off"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">{pts.map(([x, y], i) => <path key={i} d={`M ${x * 100} ${y * 100} C ${x * 100} ${(y * 100 + 88) / 2}, ${slot(i)} ${(y * 100 + 88) / 2}, ${slot(i)} 88`} pathLength="1" style={{ '--i': i }} />)}</svg><ul className="cwb-find-tray" aria-label="What it read on each page" data-testid="cwb-find-tray">{list.map((f, j) => <li key={f.at} className={`${f.hunt ? 'is-hunt' : ''}${j ? '' : ' is-new'}`} style={{ '--i': j }}>
    <small>{f.hunt ? 'LOOKING' : 'FOUND'} · {String(f.site || 'page').replace(/^www\./, '')}</small><span>{(f.got || []).slice(0, 4).map((g, i) => <b key={`${g}${i}`} style={{ '--i': i }}>{g}</b>)}</span></li>)}</ul></div>;
}

// ⛏ a monitor while its PoW folder runs (owner 2026-11-01: "I want to see it here, not only on the Desktop — they must be actively creating a PoW"):
// agreeing = the 4 coins + this mind's pick · holding = the watcher's FEELESS chart of the coin, the researcher's coins + vitals · the talk under both
const PH = { propose: 'PROPOSING 3 EACH', split: 'SPLITTING THE SHORTLIST', scout: 'RESEARCHING ITS COINS', choose: 'DECIDING THE ONE', buy: 'BUYING ON FEELESS', watch: 'WATCHING THE CHART', research: 'RESEARCHING THE CA', decide: 'DECIDING', sell: 'SELLING' };
// 📈 the folder's P/L over the watcher's chart: what went in, the entry vs now, P/L (pool price, fees apart), the round, how far from the hard stops
function PowPnl({ f }) {   // 📈 LIVE (owner 2026-11-02: "a live pnl like the trade agent windows"): the shared 2 s price poll against its USD entry
  const lp = useLivePrice(f.mint ? { chainId: 'solana', baseToken: { address: f.mint } } : null);
  const pnl = lp.usd && Number(f.entryUsd) > 0 ? (lp.usd / Number(f.entryUsd) - 1) * 100 : f.now && f.entry ? (f.now / f.entry - 1) * 100 : 0; const tone = pnl >= 0 ? 'is-up' : 'is-dn';
  const val = Number(f.sol) > 0 ? Number(f.sol) * (1 + pnl / 100) : null;
  const sl = Number(f.sl) || 25; const tp = Number(f.tp) || 60;   // the minds' own stop / target
  const toStop = Math.max(0, Math.min(1, (pnl + sl) / (sl + tp)));
  return <div className={`cwb-powpnl ${tone}`} data-testid="cwb-powpnl">
    <span><em>IN</em><b className="m-num">{f.sol ?? '—'} SOL</b><small>{f.real ? 'its wallet' : 'paper'}</small></span>
    <span><em>ENTRY → NOW</em><b className="m-num">{Number(f.entry).toPrecision(3)} → {f.now ? Number(f.now).toPrecision(3) : '…'}</b><small>SOL per coin</small></span>
    <span className="cwb-powpnl-big"><em><i className="cwb-live-dot" aria-hidden="true" />P/L LIVE</em><b className="m-num" key={Math.round(pnl * 100)}>{pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}%</b><small>{val != null ? `≈ ${val.toFixed(5)} SOL now · fees apart` : 'fees apart'}</small></span>
    <span data-tip="Live-trade checks: +15 s, +30 s, then every 60 s — the watcher reads the chart, the partner agrees or overrides"><em>CHECK</em><b className="m-num">{f.checks || 0}</b><small>{f.nextAt ? `next in ${Math.max(0, Math.round(f.nextAt - Date.now() / 1000))} s` : 'first at +15 s'}</small></span>
    <span data-tip="What this folder cost so far — both minds' calls + their research rounds"><em>COST</em><b className="m-num">${Number(f.cost || 0).toFixed(4)}</b><small>A ${Number(f.spend?.['0'] || 0).toFixed(3)} · B ${Number(f.spend?.['1'] || 0).toFixed(3)}</small></span>
    <span className="cwb-powpnl-band" data-tip="The stop loss and take profit its minds set — the dot is where it is now"><em>SL −{sl}%</em><u ref={screenBox}><s style={{ transform: `translateX(calc(var(--box-w, 0px) * ${toStop.toFixed(3)}))` }} /></u><em>TP +{tp}%</em></span>
  </div>;
}
function PowScreen({ f, slot }) {
  const me = String(slot - (f.base || 0)); const mine = f.picks?.[me]; const held = ['watch', 'research', 'decide', 'sell'].includes(f.phase);
  const coins = f.coins || []; const rM = f.rPair ? f.rPair[me] : f.rMint; const scoutC = f.phase === 'scout' && rM ? coins.find(x => x.mint === rM) : null;   // 🔎 the coin being researched — its chart, tight
  const c = held ? { mint: f.mint, pair: f.pair, sym: f.sym } : scoutC || coins[mine ?? (slot % Math.max(1, coins.length))] || {};
  return <div className="cwb-powscr" data-testid={`cwb-powscr-${slot}`}>   {/* 📈 the agent watches the FEELESS chart — never a page of cards (owner 2026-11-01) */}
    <span className="cwb-powscr-h"><b><Ic3 e="⛏" /> {f.name}</b><em>{PH[f.phase] || f.phase}</em>{c.sym ? <strong>${c.sym}</strong> : null}{!held && mine != null ? <small>its pick</small> : !held ? <small>weighing</small> : null}</span>
    <div className="cwb-chart">{c.pair ? <Suspense fallback={<span className="cwb-chart-load">loading ${c.sym} on FEELESS…</span>}>
      <McapChart coin={{ pair: c.pair, mint: c.mint, symbol: c.sym }}
        fuse={held && f.entryUsd > 0 ? { entry: f.entryUsd, stop: f.entryUsd * (1 - (Number(f.sl) || 25) / 100), slPct: Number(f.sl) || 25, lines: [{ px: f.entryUsd * (1 + (Number(f.tp) || 60) / 100), title: `🎯 take profit +${Number(f.tp) || 60}%`, color: 'up' }] } : null} /></Suspense> : null}</div>   {/* entry · SL · TP like trench trading */}
    <ul className="cwb-powscr-talk">{(f.talk || []).slice(-1).map((t, k) => <li key={`${t.at}${k}`}><b>{t.by}</b> {t.text}</li>)}</ul>
  </div>;
}

// 🔁 Whatever wants the same spot takes turns: each fades in, in place, and keeps its turn until it is gone. Nothing sits on anything.
export function Turns({ items, every = 3500 }) {
  const shown = items.filter(Boolean); const n = shown.length; const [at, setAt] = useState(0);
  useEffect(() => { if (n < 2) return undefined; const t = setInterval(() => { if (!document.hidden) setAt(x => x + 1); }, every); return () => clearInterval(t); }, [n, every]);
  if (!n) return null;
  return <div className="cwb-turns" data-testid="cwb-turns">{shown.map((x, i) => <div key={x.key ?? i} className={`cwb-turn${i === at % n ? ' is-on' : ''}`}>{x}</div>)}</div>;
}
const HELD_PHASES = ['watch', 'research', 'decide', 'sell'];
// 🙋 A window waiting on its owner: its time runs out only once they stop moving here. A click inside its browser counts, since moves there never reach this page.
function useHereWhileWaiting(on, catId, i) {
  useEffect(() => {
    if (!on) return undefined;
    let moved = Date.now(); const mark = () => { moved = Date.now(); };
    const say = () => { if (!document.hidden && (Date.now() - moved < 30000 || document.activeElement?.tagName === 'IFRAME')) Promise.resolve().then(() => work(catId, { op: 'human_here', i })).catch(() => {}); };
    document.addEventListener('pointermove', mark, { passive: true }); document.addEventListener('keydown', mark);
    say(); const t = setInterval(say, 30000);
    return () => { clearInterval(t); document.removeEventListener('pointermove', mark); document.removeEventListener('keydown', mark); };
  }, [on, catId, i]);
}
// 🖥 THE NEWEST PROOFS ON THE MONITORS (owner 2026-11-11: "any proof being worked on shows on the desk … monitors gone"): an idle monitor
// shows one of its agent's newest filed proofs — type, what it was on, its grade, when — and opens the Desktop where the folder lives. Pure.
const PROOF_KIND = { pob: ['🎲', 'PoB'], pow: ['⛏', 'PoW'], poc: ['📣', 'PoC'], ps: ['💻', 'PoStatic'], pop: ['📉', 'PoP'], poe: ['📊', 'PoEco'] };
export function newestProofs(d) {
  const row = (k, f) => f && { k, id: f.id, at: Number(f.closedAt || f.at || 0), title: String(f.topic || (f.sym ? '$' + f.sym : '') || f.name || f.title || PROOF_KIND[k][1]).slice(0, 80), grade: f.graded || f.grade || null, live: !!f.live || f.status === 'open', f };
  return [...(d?.pobFolders || []).map(f => row('pob', f)), ...(d?.powFolders || []).map(f => row('pow', f)), ...(d?.pocFolders || []).map(f => row('poc', f)),
    ...(d?.psFolders || []).map(f => row('ps', f)), ...(d?.poeFolders || []).map(f => row('poe', f)), ...(d?.popFolder ? [row('pop', d.popFolder)] : [])].filter(r => r && !/^ad\s|\sad$/i.test(r.title)).sort((x, y) => y.at - x.at).slice(0, 4);   // a Showcase ad build is not one of its proofs
}
// 🖥 owner 2026-11-12: "one monitor shows the code an the other the static" + 2026-11-13: "unless they are doing separate jobs → code on one monitor
// and static on the other". While every monitor is idle, the newest PoStatic among its newest proofs takes the first two: its code on one, its
// page on the other (never both squeezed into one); the other proofs follow on any further monitors. A monitor on a job of its own keeps it,
// and the idle ones show proofs in order, one each. `idle` = which monitors are idle (all, when not given). Pure.
export function monitorProof(proofs, n, count, idle = null) {
  const list = proofs || []; const ps = list.find(p => p.k === 'ps');
  const allIdle = !idle || idle.slice(0, count).every(Boolean);
  if (ps && count >= 2 && allIdle) { const rest = list.filter(p => p !== ps); return n < 2 ? { ...ps, view: n === 0 ? 'code' : 'page' } : rest[n - 2]; }
  return list[n];
}
export const monitorIdle = w => !(w?.status === 'working') && !w?.hand && w?.status !== 'human';
function ProofScreen({ p, onOpen, catId }) {
  const [ic, nm] = PROOF_KIND[p.k] || ['🗂', 'Proof'];
  const body = <ProofMonitorBody p={p} catId={catId} work={work} />;
  const status = p.live ? 'RUNNING' : p.grade ? 'GRADED ' + String(p.grade).toUpperCase() : 'FILED';
  return <button type="button" className={`cwb-proof is-${p.grade === 'right' || p.grade === 'good' ? 'good' : p.grade === 'wrong' || p.grade === 'bad' ? 'bad' : 'none'}${body ? ' is-rich is-' + p.k : ''}`} onClick={onOpen} data-tip="Its newest proof. Opens its Desktop, where every proof folder is" data-testid="cwb-proof">
    <span className="cwb-proof-glow" aria-hidden="true" />{body ? <><span className="cwb-proof-h"><i aria-hidden="true"><Ic3 e={ic} /></i><em>{nm} · {status}</em><small>{p.at ? ago(p.at) : ''}</small></span><span className="cwb-proof-body">{body}</span></>
      : <><i aria-hidden="true"><Ic3 e={ic} /></i><em>{nm} · {status}</em><b>{p.title}</b><small>{p.at ? ago(p.at) : ''}</small></>}</button>;
}

export function Window({ w, catId, tick, onGo, onLogin, busy, cursor = 'arrow', folder = null, d = null, proof = null, onProof }) {
  const { drop, tray } = useDrop(w);
  const ref = useRef(null); const seen = useOnScreen(ref); const [tab, setTab] = useState('web');    // 📐 --box-w/--box-h replace cqw/cqh
  // 🖥 the window FOLLOWS the agent (owner 2026-10-31: "they should switch browser ⇄ FEELESS, not us clicking"): its last move decides the view
  const lastAct = (w?.steps || []).at(-1)?.action; const lastN = (w?.steps || []).length;
  useEffect(() => { if (lastAct === 'feeless' && w?.coin?.pair) setTab('chart'); else if (['open', 'click', 'scroll', 'search', 'type'].includes(lastAct)) setTab('web'); }, [lastAct, lastN, w?.coin?.pair]);
  // 🌐 research and a wall always show its browser (owner 2026-11-04: "dont even see browser screen"): the FEELESS pre-read is a data read, and a bot check is only passable in the browser
  const browserOnly = ['scout', 'research'].includes(folder?.phase) || w?.status === 'human';
  const roundOver = roundIsOver(w, folder);
  const notAsked = !w?.goal && /not asked/.test(w?.bubble || w?.note || '');
  const chart = tab === 'chart' && !browserOnly && !roundOver && w?.coin?.pair;
  const [p, pcls] = PROV[w?.provider] || ['…', ''];
  const human = w?.status === 'human' && w?.human; const [big, setBig] = useState(false); const [fill, setFill] = useState(false);
  const i = w?.i ?? 0; const sl = w?.slot ?? i;
  useHereWhileWaiting(!!human, catId, i);
  const typeBar = fill && human && w?.hand ? <TypeBar cat={{ id: catId }} work={work} d={d} op="win_type" extra={{ i }} /> : null;
  const powHeld = folder && ['watch', 'research', 'decide', 'sell'].includes(folder.phase);   // ⛏ a PoW folder runs: this monitor is working, never 'idle'
  const rIdx = folder?.phase === 'scout' ? (folder.rMind ?? 0) : ((folder?.rounds || 0) % Math.max(1, folder?.minds || 1));   // 🔁 who researches this round
  const rPairM = folder?.rPair?.[sl - (folder?.base || 0)];   // 🏇 a pair round: this mind's own coin
  const scoutSym = folder?.phase === 'scout' ? (folder.coins || []).find(x => x.mint === (rPairM || folder.rMint))?.sym : null;
  const powDoing = !folder?.coins?.length ? '' : folder.phase === 'scout' ? (rPairM || sl - (folder.base || 0) === rIdx ? `RESEARCHING $${scoutSym || '…'}` : `WATCHING $${scoutSym || '…'}`)
    : !powHeld ? (folder.phase === 'buy' ? 'BUYING' : 'AGREEING') : sl - (folder.base || 0) === rIdx && (folder.minds || 1) > 1 ? 'RESEARCHING' : `WATCHING $${folder.sym}`;
  const working = w?.status === 'working' && !roundOver;
  // 🪟 the live window wears the demo's chrome (owner 2026-10-30: "the window design is perfected — users should see exactly that, bigger")
  const [lastBad, setLastBad] = useState(false); useEffect(() => setLastBad(false), [w?.status]);
  const coinSym = String(w?.coin?.symbol || '').slice(0, 12);   // a spam token's 'symbol' can be 60 joined tickers — it once blew the whole desk apart
  // 🟢 what it is doing now sits UNDER its monitor, never over the page (owner 2026-11-07)
  const say = w?.bubble && w?.status !== 'idle' && !(w?.status === 'human' && w?.human) && !roundOver ? <p className={`agd-done is-on cwb-say is-under at-${sl % 2 ? 'right' : 'left'}`} data-testid="cwb-bubble">MIND {'AB'[sl] || sl + 1} · {w.bubble}</p> : null;
  return <article ref={ref} className={`agd-win cwb-win w${sl % 2} s-${w?.status || 'idle'}`} data-testid={`cwb-win-${i}`}>
    <span className={`agd-bar${working ? ' is-go' : ''}`} data-tip="red = idle · yellow = needs you · green = working"><i /><i /><i /><b>MIND {'AB'[sl] || sl + 1}</b>
      <small data-tip={roundOver ? undefined : w?.goal ? `Its half: ${w.goal}` : 'Waiting for the plan'}>{w?.model ? String(w.model).split('/').pop() : 'model'}{w?.goal && !roundOver ? ` · ${w.goal}` : ''}</small>
      <em className={`cwb-prov ${pcls}`} data-tip={w?.note || (w?.provider === 'reader' ? 'No live browser right now — it reads pages as text so it keeps working' : 'A browser in the cloud — nothing runs on your device')}>{p}</em>
      <em className={`agd-live${working || powDoing ? '' : ' is-off'}`}>● {working ? 'LIVE' : powDoing || String(w?.status || 'idle').toUpperCase()}</em></span>
    <div className="agd-browser is-rec cwb-browser">
    <span className="agd-url" title={w?.url || ''}><i aria-hidden="true"><Ic3 e="🔒" /></i><b>{roundOver ? `feeless · $${folder.sym || 'its folder'}` : w?.url ? String(w.url).replace(/^https?:\/\//, '') : notAsked ? 'not asked' : 'about:blank'}</b>{working ? <u className="agd-caret" aria-hidden="true" /> : null}{working ? <em className="agd-rec">● REC</em> : <small className="m-num">{usd(w?.cost || 0)}</small>}</span>
    {w?.coin?.pair && !roundOver ? <div className="cwb-tabs" aria-label="What its window shows — the agent switches it, you watch" data-tip="The agent switches its own view: its browser, or the coin on the FEELESS chart">{[['web', '🌐 Browser'], ['chart', `📈 $${coinSym} on FEELESS`]].map(([k, l]) =>
      <span key={k} className={(chart ? 'chart' : 'web') === k ? 'is-on' : ''} data-testid={`cwb-tab-${k}`}>{l}</span>)}</div> : null}   {/* 🔒 its monitor is the agent's: you watch, it switches (owner 2026-11-01) */}
    <div ref={screenBox} className="agd-screen cwb-view">
      {notAsked ? <div className="cwb-off" data-testid="cwb-notasked"><b>MIND {'AB'[sl] || sl + 1} · not asked</b><small>This ask was for the other mind — no browser opened, nothing spent.</small></div>
      : chart && seen ? <div className="cwb-chart" data-testid="cwb-chart"><Suspense fallback={<span className="cwb-chart-load">loading ${coinSym} on FEELESS…</span>}>
        <McapChart coin={{ pair: w.coin.pair, mint: w.coin.mint, symbol: coinSym }} fuse={folder?.entryUsd > 0 && folder.mint === w.coin.mint && HELD_PHASES.includes(folder.phase) ? { entry: folder.entryUsd, stop: folder.entryUsd * (1 - (Number(folder.sl) || 25) / 100), slPct: Number(folder.sl) || 25 } : null} /></Suspense></div>
        : w?.live && seen && (working || w.hand) ? <><iframe className={`cwb-live${w.hand ? ' is-hand' : ''}`} src={w.live} tabIndex={w.hand ? 0 : -1} title={`${w.model} browser`} sandbox="allow-scripts allow-same-origin allow-forms allow-popups" allow="clipboard-read; clipboard-write" data-testid="cwb-live" />
</>
        : !working && !w?.hand && w?.status !== 'human' && folder?.coins?.length ? <PowScreen f={folder} slot={sl} />
        : !working && !w?.hand && w?.status !== 'human' && proof ? <ProofScreen p={proof} onOpen={onProof} catId={catId} />
        : !working && !w?.hand && w?.status !== 'human' && seen && !lastBad ? <img className="cwb-shot" src={apiUrl(`/api/cats/${catId}/last/${sl}?v=${w?.status}`)} alt={`${w.model} — the last page it was on`} onError={() => setLastBad(true)} data-testid="cwb-lastpage" />   // 🖼 a finished window keeps its last page (its cloud browser is closed: the live view said 'Session not found')
        : w?.shot && seen ? <img className="cwb-shot" src={apiUrl(`/api/cats/${catId}/work/shot/${w.i}?${agentAuthQuery()}&t=${tick}`)} alt={`${w.model} window`} data-testid="cwb-shot" />
          : <div className="cwb-off" data-testid="cwb-now"><b>{notAsked ? 'not asked' : working ? `MIND ${'AB'[sl] || sl + 1} · ${w?.url ? String(w.url).replace(/^https?:\/\//, '').split('/')[0] : 'reading'}` : w?.status === 'done' ? (w?.answer ? 'done — its answer is in the chat' : 'done') : 'ready — ask below'}</b>
            <small>{w?.provider === 'reader' ? (w?.note ? `no live browser · ${w.note}` : 'no live browser right now — add a Kernel / Steel / Anchor key for real windows') : working ? 'opening its browser…' : ''}</small></div>}
      {notAsked || w?.hand || chart || (!working && folder?.coins?.length && w?.status !== 'human') ? null : <AiCursor c={w?.cursor} kind={cursor} page={!(w?.live && seen && (working || w.hand))} think={working && !(w?.cursor?.at && Date.now() / 1000 - w.cursor.at < 2.5)} />}
      <FindWires m={w?.marks} />
      {drop ? <span className="cwb-drop" key={drop.k} style={{ '--x': `calc(var(--box-w, 0px) * ${drop.x})`, '--y': `calc(var(--box-h, 0px) * ${drop.y})` }} data-testid="cwb-drop" aria-hidden="true"><i><Ic3 e={drop.icon} /></i>{drop.label}</span> : null}
      {w?.hand && w?.live ? <button type="button" className="m-btn cwb-big" onClick={() => setBig(true)} data-tip="It needs you: open its window big to click / sign in yourself" data-testid="cwb-big">⤢ Big</button> : null}
      {big && w?.hand && w?.live ? <AgentDesktop cat={{ id: catId }} live={{ live: w.live, site: w?.human?.site, title: `MIND ${'AB'[sl] || sl + 1} needs you${w?.human?.why ? ` — ${w.human.why}` : ''}` }} onClose={() => setBig(false)} /> : null}
      {typeBar ? createPortal(<div className="cwb-fill-float" data-testid="cwb-fill-float">{typeBar}</div>, document.body) : null}
      <div className={`cwb-dock at-${sl % 2 ? 'right' : 'left'}`}><Turns items={[folder?.entry && HELD_PHASES.includes(folder.phase) && !roundOver ? <PowPnl key="trade" f={folder} /> : null,
        tray.length ? <ul key="tray" className="cwb-tray" aria-label="What it just grabbed" data-testid="cwb-tray">{tray.map(t => <li key={t.k}><i aria-hidden="true"><Ic3 e={t.icon} /></i>{t.label}</li>)}</ul> : null,
        ]} /></div>
    </div></div>
      {say}
      {human && w.human.kind === 'login' ? <div className="cwb-human cwb-signin" role="alertdialog" aria-label={`Sign in to ${w.human.site}`} data-testid="cwb-login">
        <b><Ic3 e="🔑" /> {w.human.site} needs a sign-in</b><small>It goes in the credentials drawer, sealed — the AI models never see it.</small>
        <span><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onLogin?.(w.human.site)} data-tip="Opens the credentials drawer with this site filled in" data-testid="cwb-login-go">Click to sign in</button>
          <button type="button" className="m-btn" disabled={busy} onClick={() => onGo('stop_window', w.i)}>Stop</button></span></div>
      : human ? <div className="cwb-human" role="alertdialog" aria-label="A person is needed" data-testid="cwb-human"><b>✋ needs you{w.human.kind === 'challenge' ? ' · 45s window' : ''}</b><small>{w.human.why}{w.human.kind === 'challenge' ? ' · Open the live browser to complete this yourself. The agent will try another source if this stays blocked.' : ''}</small>
        {w.human.alts?.length ? <span className="cwb-alts" data-testid="cwb-alts"><em>OR SEND IT TO</em>{w.human.alts.map(h => <button key={h} type="button" className="m-chip" disabled={busy} onClick={() => onGo('redirect', w.i, h)}
          data-tip={`Read ${h} instead; the agent moves on after 45 seconds if this remains blocked`} data-testid={`cwb-alt-${h}`}>{h}</button>)}</span> : null}
        <span><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onGo('continue', w.i)} data-testid="cwb-continue">I did it — continue</button>
          {w.live ? <button type="button" className="m-btn" onClick={() => setBig(true)} data-testid="cwb-human-big" data-tip="Open its window big on your desktop to pass the check yourself">⤢ Open big</button> : null}
          <button type="button" className="m-btn" disabled={busy} onClick={() => onGo('stop_window', w.i)} data-testid="cwb-stopwin">Stop</button></span></div> : null}
      {human && w?.hand ? <div className="cwb-fill" data-testid="cwb-fill"><button type="button" className={`m-btn${fill ? ' is-on' : ''}`} aria-pressed={fill} onClick={() => setFill(f => !f)} data-tip="Send an email, a code or any words into the box you selected in its browser. Never stored, never sent to a model" data-testid="cwb-fill-open">⌨ Email and code</button>{w.human.kind === 'login' && w.live ? <button type="button" className="m-btn" onClick={() => setBig(true)} data-tip="Open its window big and sign in yourself" data-testid="cwb-login-big">⤢ Open big</button> : null}{w.human.kind === 'login' ? <button type="button" className="m-btn" disabled={busy} onClick={() => onGo('continue', w.i)} data-tip="You signed in yourself: the agent goes on" data-testid="cwb-login-done">I did it</button> : null}<small>It waits while you move here, up to 30 min.</small></div> : null}
  </article>;
}

// 🧠 a general mind's vitals beside the chat: what its window is doing right now (owner 2026-10-30: "model vitals on each side")
// 🕷→🐱 WHAT IT'S DOING NOW (the crawl idea, our way): one terminal line — its handle › the site its busiest window is on: what it's doing
export function NowLine({ cat, wins, live, folder = null }) {
  const w = wins.find(x => x.status === 'human') || wins.find(x => x.status === 'working') || wins.find(x => x.url);
  const host = String(w?.url || '').replace(/^https?:\/\//, '').split('/')[0];
  const what = folder?.coins?.length && !(live && w?.status === 'working') ? `⛏ ${folder.name} — ${PH[folder.phase] || folder.phase}${folder.sym && folder.phase !== 'choose' ? ` · $${folder.sym}` : ''}`
    : !live || !w ? 'idle — waiting for your ask' : w.status === 'human' ? `waiting on you at ${host}` : `${host ? `on ${host}: ` : ''}${String(w.bubble || w.steps?.at(-1)?.thought || 'thinking').replace(/^✋ needs you: /, '')}`;
  return <p className={`cwb-now${live ? ' is-live' : ''}`} data-testid="cwb-now" aria-live="polite"><b>{cat.handle || 'agent'}</b><i aria-hidden="true">›</i><span key={what}>{what}</span></p>;
}
// ⚡ EARN MODE (owner 2026-10-30): when nobody is asking, it plans what its money could earn on FEELESS — open price gaps that beat their
// costs, then compounding (Night Vault), then the busiest bands — for YOUR risk. It never signs: each play opens its Launch › Pools tab.
const EARN_ICON = { gap: '⚡', vault: '🌙', range: '🤖', pool: '🌊' };
export function EarnCard({ cat }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const load = useCallback(() => fetch(apiUrl(`/api/cats/${cat.id}/earn?${agentAuthQuery()}`)).then(r => r.json().then(j => (r.ok ? (setD(j), setErr('')) : setErr(j.detail || `HTTP ${r.status}`)))).catch(e => setErr(e.message)), [cat.id]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 60000); return () => clearInterval(t); }, [load]);
  const e = d?.earn || { on: false, risk: 'safe', budgetUsd: 25 };
  const save = async next => { setBusy(true); setErr('');
    try { const r = await fetch(apiUrl(`/api/cats/${cat.id}/action`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), action: 'earn', earn: { ...e, ...next } }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); await load(); } catch (er) { setErr(er.message); } finally { setBusy(false); } };
  const plays = d?.plays || [];
  return <section className={`cwb-earn${e.on ? ' is-on' : ''}`} data-testid="cwb-earn">
    <header><button type="button" className={`cwb-earn-sw${e.on ? ' is-on' : ''}`} role="switch" aria-checked={e.on} disabled={busy} onClick={() => save({ on: !e.on })}
      data-tip={e.on ? 'Earn Mode ON: when you are not asking it anything, it keeps this plan fresh — you sign each play' : 'Turn on Earn Mode: it plans what its money could earn on FEELESS when idle'} data-testid="cwb-earn-sw"><i aria-hidden="true" /><Ic3 e="⚡" /> EARN MODE <b>{e.on ? 'ON' : 'OFF'}</b></button>
      <div className="m-seg" role="radiogroup" aria-label="Earn risk">{['safe', 'mid', 'risky'].map(k => <button key={k} type="button" role="radio" aria-checked={e.risk === k} className={e.risk === k ? 'active' : ''} disabled={busy} onClick={() => save({ risk: k })}
        data-tip={k === 'safe' ? 'Gaps, staking, stables, lending, big pools without impermanent loss' : k === 'mid' ? '+ auto-compound vaults and mid pools' : '+ loops, small pools, 100%+ APY'} data-testid={`cwb-earn-${k}`}>{k.toUpperCase()}</button>)}</div>
      <label className="cwb-earn-amt" data-tip="The $ it plans with (its wallet + yours) — the $/day below is on this amount"><em>$</em><input className="m-input" type="number" min="1" step="1" defaultValue={e.budgetUsd} key={e.budgetUsd} onBlur={x => Number(x.target.value) !== e.budgetUsd && save({ budgetUsd: Number(x.target.value) })} aria-label="Dollars to plan with" data-testid="cwb-earn-amt" /></label></header>
    {plays.length ? <ol className="cwb-earn-list">{plays.map((p, i) => <li key={`${p.kind}-${p.title}`} style={{ '--i': i }} className={`t-${p.tier}`}><span className="cwb-earn-ico" aria-hidden="true">{EARN_ICON[p.kind]}</span>
      <span className="cwb-earn-what"><b>{p.title}</b><small>{p.sub}</small></span><span className="cwb-earn-num"><b className="m-num">+${p.dayUsd < 0.01 ? p.dayUsd.toFixed(4) : p.dayUsd.toFixed(2)}</b><small>{p.kind === 'gap' ? 'once' : `/day · ${p.apy}%`}</small></span>
      <a className="m-btn" href={`/terminal/launch?mode=pools&tab=${p.tab}`} data-tip={`${p.why} — opens Launch › Pools`} data-testid={`cwb-earn-go-${i}`}>Open ↗</a></li>)}</ol>
      : <p className="cwb-cloud-empty">{d ? `Nothing worth it at ${e.risk.toUpperCase()} right now${d.gapsOpen ? '' : ' — no price gap beats its costs'}.` : 'Reading gaps, vaults and pools…'}</p>}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</section>;
}
// 🐝 ITS COLONY TAB (owner 2026-10-31 [c]: "the agent's Earn tab → its COLONY tab: PoW vitals as connected dots + a connected TREASURY with an
// unbroken real-money flow animated by activity"): every folder a dot (height = its P/L, 👍 green / 👎 red / ● live), joined in order; under it
// one drawn pipe WALLET → PoW → P/L → COLONY → TREASURY whose particles run faster the busier it is; Earn Mode below. All numbers are live.
export function PowDots({ folders, onPick, pick }) {
  const fs = folders.filter(f => f.pnlPct != null || f.live).slice(-24); const span = Math.max(5, ...fs.map(f => Math.abs(Number(f.pnlPct) || 0)));
  if (!fs.length) return <p className="col-empty">No PoW trades yet — type “file a PoW” in its chat; each folder lands here as a dot.</p>;
  const x = i => (fs.length === 1 ? 50 : 6 + (88 * i) / (fs.length - 1)); const y = f => 50 - 40 * ((Number(f.pnlPct) || 0) / span);
  return <div className="col-dots"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
    <line x1="0" x2="100" y1="50" y2="50" className="col-zero" /><polyline points={fs.map((f, i) => `${x(i)},${y(f)}`).join(' ')} className="col-link" /></svg>
    {fs.map((f, i) => <button key={f.id} type="button" className={`col-dot is-${f.live ? 'live' : f.pnlPct > 0 ? 'good' : 'bad'}${pick === f.id ? ' is-pick' : ''}`} style={{ '--i': i, left: `${x(i)}%`, top: `${y(f)}%` }}
      onClick={() => onPick(f.id)} aria-label={`${f.name}: ${f.live ? 'live' : `${f.pnlPct}%`}`} data-tip={`${f.name} — ${f.live ? `live: ${f.phase}` : `${f.pnlPct >= 0 ? '+' : ''}${f.pnlPct}%`}`}><i /></button>)}</div>;
}
export function ColonyTab({ cat }) {
  const [d, setD] = useState(null); const [w, setW] = useState(null); const [pick, setPick] = useState(null);
  const verRef = useRef(null);   // ⚡ the filed folders only come when they changed, as on the desk
  useEffect(() => { let on = true; const load = () => { if (document.hidden) return;
    work(cat.id, { op: 'state', ver: verRef.current }).then(j => { if (!on) return; if (j.powVer) verRef.current = j.powVer; setD(o => ({ ...j, powFolders: j.powFolders ?? o?.powFolders })); }).catch(() => on && setD(x => x || {}));
    work(cat.id, { op: 'wallet' }).then(j => on && setW(j)).catch(() => on && setW(x => x || {})); };
    load(); const t = setInterval(load, 20000); return () => { on = false; clearInterval(t); }; }, [cat.id]);
  const folders = [...[...(d?.powFolders || [])].reverse(), ...(d?.powFolder ? [{ ...d.powFolder, live: true }] : [])];
  const done = folders.filter(f => f.pnlPct != null); const pnl = done.reduce((a, f) => a + (Number(f.pnlSol) || 0), 0); const won = done.filter(f => f.pnlPct > 0).length;
  const share = cat.colonyShare || {}; const f = folders.find(x => x.id === pick);
  const pnlText = `${pnl >= 0 ? '+' : ''}${pnl.toFixed(4)} SOL`;
  return <section className="col-tab" data-testid="col-tab">
    <div className="col-head"><b><Ic3 e="💎" /> IN THE COLLECTIVE</b>{[['WALLET', w?.sol != null ? `${Number(w.sol).toFixed(4)} SOL` : '…'], ['SHARING', share.on ? `${share.pct}% of wins` : 'off'], ['FOLDERS', folders.length], ['WON', done.length ? `${Math.round((100 * won) / done.length)}%` : '—'], ['P/L', pnlText], ['COST', `$${folders.reduce((a, x) => a + (Number(x.cost) || 0), 0).toFixed(3)}`]].map(([k, v]) =>
      <span key={k}><em>{k}</em><b className={`m-num${k === 'P/L' ? (pnl >= 0 ? ' is-up' : ' is-dn') : ''}`}>{v}</b></span>)}</div>
    <div className="col-dots-wrap" data-tip="Each dot is one PoW folder — up = it made money, down = it lost; tap one"><PowDots folders={folders} onPick={setPick} pick={pick} /></div>
    {f ? <p className="col-pick" data-testid="col-pick"><b>{f.name}</b>{f.sym ? ` · $${f.sym}` : ''} · {f.live ? `live — ${f.phase}` : `${f.pnlPct >= 0 ? '+' : ''}${f.pnlPct}%`} — {f.why || ''}</p> : null}
    <EarnCard cat={cat} />
  </section>;
}
// 🏦 ITS TREASURY (owner 2026-10-31): its own coin's creator fees, read on-chain now (pump.fun's vault, PumpSwap's after it graduates), and how
// they split — the Pass holder · its model credit · a capped buyback of its own coin (fees only, shown here). Claiming + paying out from its
// wallet is the next step, tested live by the owner first.
const SPLIT_PRESETS = [['Balanced', { holder: 50, credit: 30, buyback: 20 }], ['Holder first', { holder: 70, credit: 20, buyback: 10 }], ['Self-funding', { holder: 30, credit: 60, buyback: 10 }], ['Momentum', { holder: 40, credit: 20, buyback: 40 }]];
// ➕ COL-15: a proposal the owner traded by hand somewhere else (Crypto.com, any app): where, the result, the receipt link. It stays HIS CLAIM
// in the record (never a settled result) until a send confirms it.
export function ProposalClaim({ cat, f, onDone }) {
  const m = f.manual; const [open, setOpen] = useState(false); const [v, setV] = useState({ venue: '', resultUsd: '', receipt: '', note: '' }); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const set = k => e => setV(x => ({ ...x, [k]: e.target.value }));
  const save = async () => { setBusy(true); setErr('');
    try { const r = await fetch(apiUrl(`/api/cats/${cat.id}/work`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), op: 'pow_claim', job: f.id, text: v.note, tools: { venue: v.venue, resultUsd: v.resultUsd, receipt: v.receipt } }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); onDone?.(j.powFolders); setOpen(false); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  if (m) return <p className="dsk-note" data-testid="pow-claim">➕ You traded it on <b>{m.venue}</b>: <b className="m-num">{m.resultUsd >= 0 ? '+' : ''}${Number(m.resultUsd).toFixed(2)}</b> · your claim until a send confirms it{m.receipt ? <> · <a href={m.receipt} target="_blank" rel="noopener noreferrer">receipt ↗</a></> : null}</p>;
  if (!open) return <button type="button" className="m-btn" onClick={() => setOpen(true)} data-testid="pow-claim-open" data-tip="You traded this proposal yourself on another app: file where and how it went">＋ I traded it</button>;
  return <div className="dsk-note" data-testid="pow-claim-form" style={{ display: 'grid', gap: 6 }}>
    <input className="m-input" value={v.venue} onChange={set('venue')} placeholder="Where (e.g. Crypto.com)" aria-label="Where you traded it" data-testid="pow-claim-venue" />
    <input className="m-input" value={v.resultUsd} onChange={set('resultUsd')} inputMode="decimal" placeholder="Result in $ (a minus for a loss)" aria-label="Result in dollars" data-testid="pow-claim-usd" />
    <input className="m-input" value={v.receipt} onChange={set('receipt')} placeholder="https:// link to the receipt (optional)" aria-label="Receipt link" data-testid="pow-claim-receipt" />
    <span><button type="button" className="m-btn m-go" disabled={busy || !v.venue.trim() || v.resultUsd === ''} onClick={save} data-testid="pow-claim-save">File it</button> <button type="button" className="m-btn" onClick={() => setOpen(false)}>Cancel</button></span>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</div>;
}
// 🧑‍⚖️ OSSY and G4's review of a filed proof (owner 2026-11-10: "have ossy and g4 test each proof"): each one's score and pass / fail, who really
// answered, the checks on hover. A review, never the boost grade.
// 🌐 how a PoB's research ran: its own browse, or (COL-9) another proof's fresh read of the same topic, reused so it never browses twice
export function BrowseNote({ f }) {
  if (f?.sharedRead) return <p className="dsk-note" data-testid="pob-shared" data-tip="Another proof read this topic minutes ago; its notes went to both minds instead of a second browse">🧠 Reused a fresh read of this topic{f.sharedRead.at && f.at ? ` from ${Math.max(0, Math.round((f.at - f.sharedRead.at) / 60))} min earlier` : ''} · never browsed twice</p>;
  return f?.browseWhy ? <p className="dsk-note">Browsing: {f.browseWhy}</p> : null;
}

export function ReviewChips({ review }) {
  if (!review?.by) return <span className="rvw is-wait" data-testid="review-wait" data-tip="OSSY and G4 review every filed proof, newest first">🧑‍⚖️ review queued</span>;
  return <span className={`rvw is-${review.verdict}`} data-testid="review">{Object.entries(review.by).map(([k, v]) => <b key={k} className={`rvw-${v.verdict}`}
    data-tip={`${k.toUpperCase()} · ${v.verdict} · answered by ${v.answeredBy || '?'}\n${(v.checks || []).join('\n')}${v.why ? `\n${v.why}` : ''}`}>{k.toUpperCase()} <i className="m-num">{v.score}</i> {v.verdict === 'pass' ? '✓' : '✗'}</b>)}{review.agree === false ? <small>split</small> : null}</span>;
}
// 💵 AGT-8: what a PoW / PoP / PoB discussion cost, per mind and in all, above its talk (PoStatic and PoC have ChatCost)
export function FolderCost({ f }) {
  const sp = f?.spend && typeof f.spend === 'object' ? f.spend : {}; const per = [0, 1].map(i => Number(sp[i] ?? sp[String(i)]) || 0); const all = Number(f?.cost) || per[0] + per[1];
  const u = n => `$${n.toFixed(4)}`;
  return <p className="dsk-note" data-testid="fold-cost" data-tip="Every model call this folder made">{f?.status === 'closed' ? <><ReviewChips review={f.review} /> </> : null}COST · {per[0] || per[1] ? <>Mind A <b className="m-num">{u(per[0])}</b> · Mind B <b className="m-num">{u(per[1])}</b> · </> : null}folder <b className="m-num">{u(all)}</b>{f?.compare ? <span data-testid="fold-compare" data-tip={f.compare.ok ? 'It compared enough before settling' : `Compare before settling: ${f.compare.why}`}> · ⚖ compared <b className="m-num">{f.compare.sources}</b> of 4 sources{f.compare.ok ? '' : ' · thin'}</span> : null}</p>;
}
// 🔑 the API drawer as a cabinet slot (owner 2026-10-31): its own keys, sealed on the server — only the last 4 ever come back
export function ApiSlot({ cat }) {
  const [rows, setRows] = useState(cat?.apiDrawer || []); const [draft, setDraft] = useState({}); const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [rowErr, setRowErr] = useState(null);
  const [joined, setJoined] = useState(() => takeConnectResult(cat?.id));   // 🔑 back from OpenRouter's approval page: say how it went
  useEffect(() => { const on = e => { if (e.detail?.cat !== cat?.id) return; setJoined(takeConnectResult(cat.id) || e.detail); if (e.detail.ok) setRows(r => [...r.filter(x => x.provider !== 'openrouter'), { provider: 'openrouter', saved: true, last4: e.detail.last4 }]); };
    window.addEventListener('feeless:orConnect', on); return () => window.removeEventListener('feeless:orConnect', on); }, [cat?.id]);
  const send = async (provider, secret) => { setBusy(true); setErr('');
    try { const r = await fetch(apiUrl(`/api/cats/${cat.id}/action`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), action: 'api_key', provider, secret: String(secret || '').trim() }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); setRows(j.cat?.apiDrawer || []); setDraft(x => ({ ...x, [provider]: '', [`${provider}.0`]: '', [`${provider}.1`]: '' })); setRowErr(null); } catch (e) { setRowErr({ k: provider, m: e.message }); } finally { setBusy(false); } };
  return <div data-testid="cwb-api">{joined ? <p className={joined.ok ? 'm-note' : 'kd-err'} role="status" data-testid="or-connected">{joined.ok ? '✓ Connected to your OpenRouter. Its models now run on your OpenRouter account.' : `⚠ ${joined.why}`}</p> : null}
    <ApiDrawer start rows={rows} draft={draft} busy={busy} onDraft={(k, v) => setDraft(x => ({ ...x, [k]: v }))} onSave={send} onDrop={k => send(k, '')} errFor={rowErr} onConnect={() => startOpenRouterConnect(cat.id).catch(e => setErr(e.message))} />
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}</div>;
}
export function TreasuryDrawer({ cat }) {
  const px = useSolPrice(); const [t, setT] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false); const [mint, setMint] = useState('');
  const load = useCallback(() => fetch(apiUrl(`/api/cats/${cat.id}/treasury?${agentAuthQuery()}`)).then(r => r.json().then(j => (r.ok ? (setT(j), setMint(j.mint || '')) : setErr(j.detail || `HTTP ${r.status}`)))).catch(e => setErr(e.message)), [cat.id]);
  useEffect(() => { load(); const id = setInterval(() => { if (!document.hidden) load(); }, 60000); return () => clearInterval(id); }, [load]);
  const save = async next => { setBusy(true); setErr('');
    try { const r = await fetch(apiUrl(`/api/cats/${cat.id}/action`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), action: 'treasury', treasury: { mint, split: t?.split, ...next } }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); await load(); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const sol = l => `${(Number(l || 0) / 1e9).toFixed(4)} SOL${px ? ` ($${((Number(l || 0) / 1e9) * px).toFixed(2)})` : ''}`;
  const sp = t?.split || { holder: 50, credit: 30, buyback: 20 };
  return <div className="cwb-tre" data-testid="cwb-treasury">
    <b className="cwb-pass-num"><Ic3 e="🏦" /> ITS TREASURY</b>
    <small>Its own coin's creator fees land here. You set how they split; buybacks come from these fees only, capped at {t?.buybackMax ?? 50}%.</small>
    <label className="cwb-tre-mint"><em>ITS COIN</em><input className="m-input" value={mint} onChange={e => setMint(e.target.value.trim())} placeholder="its coin address — or ask it: launch my coin" aria-label="Its coin address" data-testid="cwb-tre-mint" />
      <button type="button" className="m-btn" disabled={busy || mint === (t?.mint || '')} onClick={() => save({ mint })}>Save</button></label>
    <div className="cwb-tre-fees" data-tip="Read on-chain now from its creator vaults (pump.fun + PumpSwap)"><em>FEES WAITING</em><b className="m-num" data-testid="cwb-tre-total">{t ? sol(t.fees?.total) : '…'}</b>
      <small>{t?.creator ? `for its wallet ${t.creator.slice(0, 4)}…${t.creator.slice(-4)}` : 'give it its own wallet first (👛 Wallet)'}</small></div>
    <div className="m-seg cwb-tre-presets" role="radiogroup" aria-label="How its fees split">{SPLIT_PRESETS.map(([l, v]) => { const on = v.holder === sp.holder && v.credit === sp.credit && v.buyback === sp.buyback;
      return <button key={l} type="button" role="radio" aria-checked={on} className={on ? 'active' : ''} disabled={busy} onClick={() => save({ split: v })} data-testid={`cwb-tre-${l}`}
        data-tip={`${v.holder}% to the Pass holder · ${v.credit}% model credit · ${v.buyback}% buyback`}>{l}</button>; })}</div>
    <div className="cwb-tre-split">{[['holder', '🎫 PASS HOLDER'], ['credit', '🧠 MODEL CREDIT'], ['buyback', '🔁 BUYBACK']].map(([k, l]) => <span key={k} className={`k-${k}`}>
      <em>{l}</em><b className="m-num">{sp[k]}%</b><u aria-hidden="true"><s style={{ transform: `scaleX(${sp[k] / 100})` }} /></u><small>{t ? sol(t.plan?.[k]) : '…'}</small></span>)}</div>
    <p className="m-note"><b>Next</b>Claiming these fees from its wallet and paying out the split comes after your live test.</p>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</div>;
}
// 🎫 ITS AGENT PASS (owner 2026-10-31): a numbered NFT of this agent, minted to YOUR wallet after its recovery PIN — the mint fee (HQ; default
// 2× Solana's cost) and a 10% resale royalty go to FEELESS, the fee wallet keeps the royalty locked in. FEELESS records it only after checking it on-chain.
export function PassDrawer({ cat }) {
  const { wallet, signMessage, provider } = useWallet() || {}; const px = useSolPrice();
  const [r, setR] = useState(null); const [stage, setStage] = useState(''); const [err, setErr] = useState(''); const [done, setDone] = useState(cat?.pass || null);
  useEffect(() => { let on = true; fetch(apiUrl('/api/reputation/agent-pass/rules')).then(x => (x.ok ? x.json() : null)).then(j => on && j && setR(j)).catch(() => {}); return () => { on = false; }; }, []);
  const sol = l => (Number(l || 0) / 1e9).toFixed(4); const usdOf = l => (px ? ` ($${((Number(l || 0) / 1e9) * px).toFixed(2)})` : '');
  const mint = async () => { setErr('');
    try {
      const addr = wallet?.address; if (!addr) throw new Error('Connect the owner wallet first.');
      setStage('Signing you in…'); const session = await getChatSession(addr, signMessage, { own: true });
      setStage('Drawing its picture…'); const { blob } = await svgPngBlob(document.querySelector('.kd-stage svg'));
      const dataUrl = await new Promise((ok, no) => { const f = new FileReader(); f.onload = () => ok(f.result); f.onerror = () => no(new Error('Its picture could not be read.')); f.readAsDataURL(blob); });
      const post = async (path, body) => { const x = await fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); const j = await x.json().catch(() => ({})); if (!x.ok) throw new Error(j.detail || `HTTP ${x.status}`); return j; };
      setStage('Uploading its picture…'); const up = await post('/api/reputation/uploads', { dataUrl });
      setStage('Numbering its Pass…'); const prep = await post(`/api/reputation/agent-pass/${cat.id}/prepare`, { address: addr, session, image: up.url });
      const { coreMintPass } = await import('../../lib/metaplexCore');
      const m = await coreMintPass({ provider, owner: addr, name: prep.name, uri: prep.uri, feeWallet: prep.feeWallet, feeLamports: prep.feeLamports, royaltyBps: prep.royaltyBps, onStatus: setStage });
      setStage('Checking it on-chain…'); const c = await post(`/api/reputation/agent-pass/${cat.id}/confirm`, { address: addr, session, signature: m.signature, asset: m.asset });
      setDone({ number: c.number, asset: c.asset }); setStage('');
    } catch (e) { setErr(e.message || 'The mint did not finish — nothing was recorded.'); setStage(''); } };
  if (done?.asset) return <div className="cwb-pass is-minted" data-testid="cwb-pass"><b className="cwb-pass-num"><Ic3 e="🎫" /> AGENT PASS #{String(done.number || 0).padStart(4, '0')}</b>
    <small>In your wallet · 10% of every resale goes to FEELESS</small><a className="m-btn" href={`https://explorer.solana.com/address/${done.asset}`} target="_blank" rel="noopener noreferrer">See it on-chain ↗</a></div>;
  const blocked = !cat?.recoveryConfirmedAt ? 'Confirm its recovery PIN first (👛 Wallet tab) — the Pass comes after its safe-keeping.' : r && !r.ready ? r.why : '';
  return <div className="cwb-pass" data-testid="cwb-pass"><b className="cwb-pass-num"><Ic3 e="🎫" /> MINT ITS AGENT PASS</b>
    <small>A numbered NFT of this agent, minted to your wallet. Whoever holds it holds the agent — sell it later on the FEELESS marketplace or any Core marketplace.</small>
    {r ? <div className="cwb-pass-kv"><span><em>MINT FEE</em><b className="m-num">{sol(r.feeLamports)} SOL{usdOf(r.feeLamports)}</b></span><span><em>SOLANA'S COST</em><b className="m-num">{sol(r.providerLamports)} SOL</b></span>
      <span><em>RESALE ROYALTY</em><b className="m-num">{(r.royaltyBps || 0) / 100}% → FEELESS</b></span></div> : <small>Reading the mint fee…</small>}
    {blocked ? <p className="m-note warn" data-testid="cwb-pass-blocked">{blocked}</p>
      : <button type="button" className="m-btn m-go" disabled={!r || !!stage} onClick={mint} data-tip="Your wallet signs once: the Pass + its mint fee in one transaction" data-testid="cwb-pass-mint">{stage || 'Mint its Agent Pass'}</button>}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</div>;
}
// 💵 the last money it made — stays until a newer one lands
function LastMoney({ m }) {
  const px = useSolPrice();
  if (m && m.usd == null && m.sol != null && px) m = { ...m, usd: Number(m.sol) * px };
  if (!m) return <div className="cwb-money is-none" data-testid="cwb-money" data-tip="The last money it made shows here until a newer one lands"><em>LAST MONEY MADE</em><b className="m-num">—</b><small>nothing yet</small></div>;
  const up = Number(m.usd ?? m.sol) >= 0;
  return <div className={`cwb-money ${up ? 'is-up' : 'is-dn'}`} key={m.at} data-testid="cwb-money" data-tip={`${m.what || 'trade'} · ${new Date((m.at || 0) * 1000).toLocaleString()}`}><em>LAST MONEY MADE</em>
    <b className="m-num">{m.usd == null ? '…' : `${up ? '+' : '−'}$${Math.abs(Number(m.usd)).toFixed(2)}`}</b><small>{m.sol != null ? `${up ? '+' : ''}${Number(m.sol).toFixed(4)} SOL · ` : ''}{m.what || 'trade'}</small></div>;
}
// pure: the same line again and again (a retry, a cap stop) folds into one row with ×N — newest time kept (owner 2026-10-30: "collapse the repeated")
// 🗂 a run of the same line folds into one row ×N, showing the NEWEST (owner 2026-11-11: eight "Dallas Cowboys: 20 - 23 · 1:15 …" rows): its numbers
// may differ (a live score, a price), your own words never fold
const foldKey = r => `${r.f || r.by}|${r.by === 'you' || /^You: /.test(r.text) ? r.text : String(r.text).replace(/\$?[\d.:]+/g, '#')}`;
export const squash = (out, x) => { const last = out[out.length - 1];
  if (last && foldKey(last) === foldKey(x)) { last.n = (last.n || 1) + 1; if ((x.at || 0) > (last.at || 0)) Object.assign(last, { text: x.text, at: x.at }); return out; } out.push({ ...x }); return out; };
// the cabinet folds the same line wherever it repeats (two games' scores interleave), newest first. Pure
const foldAll = rows => { const seen = new Map(); return rows.reduce((out, x) => { const k = foldKey(x); const hit = seen.get(k); if (hit) { hit.n = (hit.n || 1) + 1; return out; } const y = { ...x }; seen.set(k, y); out.push(y); return out; }, []); };
const BUDGET_STOP = /budget reached/i;
const SUGGEST = ["Find today's top coin on pump.fun and tell me why", 'Read X for $SOL news in the last hour', 'Check a coin on RugCheck + Solscan and report'];
// 💬 one chat message, the way a work chat shows it (owner 2026-10-31: "not corporate looking"): avatar · who · tags · time · cost, then the text.
// The server's prefixes ("🛟 Backup model…:", "💳 Paid $…:") become small tags instead of walls of words in front of the answer.
const MSG_TAGS = [[/^🛟 Backup model, free \(OpenRouter has no credit\):\s*/, 'free backup'], [/^💳 Paid \$([\d.]+) from its wallet:\s*/, 'paid from its wallet'], [/^⚡ from memory · /, 'from memory']];
export function chatParts(text) {
  let t = String(text || ''); const tags = [];
  for (let n = 0; n < 3; n += 1) { const hit = MSG_TAGS.find(([re]) => re.test(t)); if (!hit) break; tags.push(hit[1]); t = t.replace(hit[0], ''); }
  return { text: t, tags };
}
// ✍ the newest answer writes itself in once (≈0.7 s), like a live reply — never under reduced motion / fx-lite, never on old messages
function useTypeIn(text, on) {
  const [n, setN] = useState(on ? 0 : text.length); const born = useRef(Date.now());
  useEffect(() => {
    const calm = document.body.classList.contains('fx-lite') || window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
    if (!on || calm || Date.now() - born.current > 1500) { setN(text.length); return undefined; }
    let raf = 0; const t0 = performance.now(); const step = t => { const k = Math.min(1, (t - t0) / 700); setN(Math.ceil(k * text.length)); if (k < 1) raf = requestAnimationFrame(step); };
    raf = requestAnimationFrame(step); return () => cancelAnimationFrame(raf); }, [text, on]);
  return text.slice(0, n);
}
function ChatMsg({ m, name, fresh = false, onOpen, rate, onRate, onChip, job = null }) {
  const you = m.by === 'you'; const parts = useMemo(() => chatParts(m.text), [m.text]); const tags = parts.tags;
  const text = useTypeIn(parts.text, fresh && !!m.at && Date.now() / 1000 - m.at < 20);
  return <li className={`cwb-msg ${you ? 'is-you' : 'is-cats'}`}><i className="cwb-av" aria-hidden="true">{you ? 'YOU' : '🧠'}</i>
    <div><header><b>{you ? 'You' : (name || 'Its minds')}</b>{tags.map(t => <em key={t} className="cwb-tag">{t}</em>)}{m.at ? <time>{ago(m.at)} ago</time> : null}{m.cost != null && !you ? <CostTicket usd={m.cost} title="This answer" rows={[...(job?.minds || []).map((x, i) => [`Mind ${'AB'[i]} · ${String(x.model || '').split('/').pop()}`, x.cost ? shortCost(x.cost) : `${(x.steps || []).length} steps`]), ...(m.cost === 0 ? [['Paid by', 'Free, its own model']] : [])]} /> : null}</header>
      <p>{text}{m.n > 1 ? <em className="cwb-x"> ×{m.n}</em> : null}</p>
      {m.tid && onRate ? <span className="cwb-rate" role="group" aria-label="Rate this answer — it goes into both minds' memory">{[['up', '👍', 'Good — it remembers to do it like this'], ['down', '👎', 'Not this — it remembers to do it differently']].map(([k, ic, tip]) =>
        <button key={k} type="button" className={rate === k ? 'is-on' : ''} aria-pressed={rate === k} onClick={() => onRate(m.tid, k)} data-tip={tip} data-testid={`cwb-rate-${k}`}><Ic3 e={ic} /></button>)}{rate ? <em>in memory · <Ic3 e="🗂" /> Jobs</em> : null}</span> : null}
      {m.img ? <img className="ast-chat-img" src={apiUrl(m.img)} alt={text} loading="lazy" data-testid="cwb-img" /> : null}
      {you ? null : <PreviewButton text={m.text} url={m.page} />}
      {m.ask?.chips?.length && fresh && onChip ? <span className="cwb-chips" data-testid="chat-chips">{m.ask.chips.map(c => <button key={c} type="button" className="m-chip" onClick={() => onChip(c)} data-tip="Answers its question" data-testid={`chat-chip-${c}`}>{c}</button>)}</span> : null}
      {m.open === 'pow' && onOpen ? <button type="button" className="m-btn cwb-open-pow" onClick={() => onOpen('pow')} data-tip="Its PoW folder on the Desktop — the 4 coins, the picks, the talk, the P/L" data-testid="cwb-open-pow"><Ic3 e="⛏" /> Open the PoW folder</button> : null}
      {m.open === 'bids' && onOpen ? <button type="button" className="m-btn cwb-open-pow" onClick={() => onOpen('bids')} data-tip="Its Bids desk on the Desktop, with its PoB folders" data-testid="cwb-open-bids"><Ic3 e="🎲" /> Open the Bids desk</button> : null}
      {m.open === 'pop' && onOpen ? <button type="button" className="m-btn cwb-open-pow" onClick={() => onOpen('pop')} data-tip="Its Proof of Perps desk on the Desktop" data-testid="cwb-open-pop"><Ic3 e="📉" /> Open the PoP desk</button> : null}</div></li>;
}
const DESK_TIPS = [['[data-testid="cwb-now"]', 'What it is doing', 'Live: the site each window is on and the step it is taking.'],
  ['[data-testid="cwb-plus"]', 'Attach', 'Drop images or clips — they ride with your next ask (kept 24 h).'],
  ['[data-testid="cwb-gear"]', 'Chat settings', 'How its minds work, who you talk to, the $ a task may spend, its job + tools.'],
  ['[data-testid="cwb-go"]', 'Let it go', 'ON: long tasks and queued asks run back to back until a person is needed.'],
  ['[data-testid="agent-log"] .ck-folders', 'Its file cabinet', 'Credentials, storage, earn plays and every log line — a drawer each; hide the ones you never use.']];
// pure: the general cat's log — your asks + answers (tasks), each window's steps (thoughts), its files, the cloud, every refusal (guards)
// 🗂 AGX-2: a chat line's "Open the … desk" opens the proof that line is about IN the desk: the newest folder of its kind filed by the time of
// the line (+10 min for the filing to land), else its newest. Nothing filed → just the window. Pure.
const CHAT_KEYS = { pow: 'powFolders', bids: 'pobFolders', pop: 'popFolders' };
export function chatProof(d, win, at) {
  const rows = [...(d?.[CHAT_KEYS[win]] || [])].filter(f => f?.id).sort((a, b) => (Number(b.at) || 0) - (Number(a.at) || 0));
  if (!rows.length) return win;
  const t = Number(at) || 0; const hit = t ? rows.find(f => (Number(f.at) || 0) <= t + 600) : null;
  return { win, id: (hit || rows[0]).id };
}
export function genLog(d) {
  const now = Date.now() / 1000;
  return foldAll([...(d?.chat || []).map(m => ({ f: 'tasks', at: m.at, text: m.by === 'you' ? `You: ${m.text}` : String(m.text), tone: m.by === 'you' ? 'acc' : 'up' })),
    ...(d?.windows || []).flatMap(w => (w.steps || []).map((s, k) => ({ f: 'thoughts', at: now - ((w.steps.length - k) * 5), text: `${String(w.model || '').split('/').pop()} · ${s.action}: ${s.thought}${s.detail ? ` (${s.detail})` : ''}`, tone: s.action === 'refused' ? 'warn' : s.action === 'handoff' ? 'up' : 'mute' }))),
    ...Object.entries(d?.minds || {}).flatMap(([m, xs]) => xs.map(c => ({ f: 'cloud', at: c.at, text: `☁ ${m.split('/').pop()} · ${c.text}`, tone: 'mute' }))),
    ...(d?.artifacts || []).map(a => ({ f: 'files', at: now, text: `${a.kind}: ${a.title}`, tone: 'acc' })),
    ...(d?.cloud || []).map(c => ({ f: 'cloud', at: c.at, text: c.text || `${c.word} $${c.sym}`, tone: 'acc' })),
    ...(d?.refusals || []).map(r => ({ f: 'guards', at: r.at || now, text: r.why, tone: 'warn' }))].filter(x => x.text).sort((p, q) => (q.at || 0) - (p.at || 0)));
}

// 👀 a visitor (from the leaderboard) sees its minds + what both agreed on — its live windows and chat stay private to its owner
export function CatWorkbench({ cat, readOnly = false }) {
  useEffect(() => { if (!readOnly && cat?.id && cat.id !== 'leader') { try { localStorage.setItem('feeless.lastAgent', cat.id); } catch { /* private window */ } } }, [cat?.id, readOnly]);   // 🎭 the FeeCat bar wears the agent you opened last
  return readOnly ? <PublicMinds cat={cat} /> : <WorkbenchLive cat={cat} />;
}
// 🖥 fits a dash to the screen under whatever sits above it (a visitor's view never scrolls — owner 2026-10-30)
function useFit(ref, below = 76) {
  useLayoutEffect(() => {
    const fit = () => { const r = ref.current; const st = r?.querySelector('.cwb-stage'); if (!st) return;
      if (window.innerWidth <= 900) { r.style.removeProperty('--cwb-h'); return; }
      const top = st.getBoundingClientRect().top + window.scrollY; let h = Math.round(Math.max(240, Math.min(720, window.innerHeight - top - below)));
      r.style.setProperty('--cwb-h', `${h}px`);
      const over = (r.closest('.kd.is-theater') ? r : r.closest('.kd') || r).getBoundingClientRect().bottom + window.scrollY - window.innerHeight + 24;   // then trim what the chrome around it adds
      if (over > 0) { h = Math.max(240, h - Math.ceil(over)); r.style.setProperty('--cwb-h', `${h}px`); } };
    fit(); window.addEventListener('resize', fit); return () => window.removeEventListener('resize', fit);
  }, [ref, below]);
}
// 👀 A VISITOR's view of someone's agent (no scroll): its two windows as they work — the site's host, the kind of step and how far — never the page
// 👀 one mind's side rail for a visitor (owner 2026-10-31: "more vitals on the sides, like Live Activity"): status, where, steps as a ring
export function MindRail({ w, side, d }) {
  const go = w?.status === 'working';
  return <aside className={`cwb-rail at-${side}${go ? ' is-go' : ''}`} data-testid={`cwb-rail-${side}`}>
    <b className="cwb-rail-h">MIND {'AB'[w?.i ?? (side === 'left' ? 0 : 1)]}</b><small title={w?.model}>{w?.model || '—'}</small>
    <span className="cwb-rail-orb" data-tip="Its mind — the swirl races while it works"><Bubble m={asModel(w?.model)} i={w?.i ?? (side === 'left' ? 0 : 1)} kind="general" size={64} live={!!w?.model} hot={go} /></span>
    <dl className="cwb-rail-kv"><div><dt>STATUS</dt><dd className={go ? 'is-up' : ''}>{go ? 'LIVE' : String(w?.status || 'idle').toUpperCase()}</dd></div><div><dt>ON</dt><dd>{w?.host || '—'}</dd></div>
      <div><dt>SCREEN</dt><dd className={w?.screen && !w?.last ? 'is-up' : ''}>{w?.frozen ? 'PAUSED' : w?.last ? 'LAST PAGE' : w?.screen ? 'LIVE' : '—'}</dd></div>
      {side === 'left' ? <div><dt>LEVEL</dt><dd className="m-num">{d?.level ?? '—'}</dd></div> : <div><dt>W / L</dt><dd className="m-num">{d ? `${d.wins || 0} / ${d.losses || 0}` : '—'}</dd></div>}
      {side === 'left' ? <div><dt>STORED</dt><dd className="m-num" key={d?.stored}>{d?.stored ?? 0}</dd></div> : <div><dt>P/L</dt><dd className={`m-num ${Number(d?.pnlSol) < 0 ? 'is-dn' : 'is-up'}`}>{d?.pnlSol != null ? `${Number(d.pnlSol) >= 0 ? '+' : ''}${Number(d.pnlSol).toFixed(3)} SOL` : '—'}</dd></div>}
      {side === 'left' ? <div data-tip="Score this epoch: its graded calls and trades, judged an hour on"><dt><Ic3 e="💧" /> SCORE</dt><dd className={`m-num ${Number(d?.honey) < 0 ? 'is-dn' : d?.honey ? 'is-up' : ''}`} key={d?.honey}>{d?.honey != null ? `${d.honey > 0 ? '+' : ''}${d.honey}` : '—'}</dd></div>
        : <div data-tip="Graded calls it got right this epoch"><dt>RIGHT</dt><dd className="m-num">{d ? `${d.right || 0} / ${d.graded || 0}` : '—'}</dd></div>}
      {side === 'left' ? <div><dt>COLLECTIVE</dt><dd className={d?.colonized ? 'is-up' : ''}>{d?.colonized ? '💎 IN' : 'OUT'}</dd></div>
        : <div data-tip="Its newest call, and the score it earned once graded"><dt>LAST CALL</dt><dd>{d?.lastCall ? `${d.lastCall.call} $${d.lastCall.sym}${d.lastCall.honey != null ? ` ${d.lastCall.honey > 0 ? '+' : ''}${d.lastCall.honey}` : ' ⏳'}` : '—'}</dd></div>}</dl>
    {d?.pow?.[String(w?.i ?? (side === 'left' ? 0 : 1))] ? <PowCard p={d.pow[String(w?.i ?? (side === 'left' ? 0 : 1))]} compact /> : null}
  </aside>;
}
// 🗄 when it stores something a drawer slides out of its cabinet, the new file glows, then the drawer shuts (visitors watch it file things away)
export function StoredPop({ item }) {
  const [shown, setShown] = useState(null); const first = useRef(true);
  useEffect(() => { if (!item) return undefined; if (first.current) { first.current = false; return undefined; } setShown(item); const t = setTimeout(() => setShown(null), 3600); return () => clearTimeout(t); }, [item?.text, item?.at]); // eslint-disable-line react-hooks/exhaustive-deps
  return shown ? <div className="cwb-stored" role="status" data-testid="cwb-stored"><span className="cwb-stored-box" aria-hidden="true"><u /></span>
    <span className="cwb-stored-file"><em>🗄 FILED IN ITS CLOUD</em><b>{shown.text}</b></span></div> : null;
}
// 👀 A visitor's one Proofs list (owner 2026-11-04): the newest 5 of any kind, with their stamps. From the public copy: no emails, phones or wallet trail.
function VisitorProofs({ catId, seen }) {
  const [rows, setRows] = useState([]);
  useEffect(() => { if (!seen) return undefined; let on = true; const go = () => { if (!document.hidden) Promise.resolve().then(() => fetch(apiUrl(`/api/cats/${catId}`))).then(r => (r?.ok ? r.json() : null)).then(j => { if (on && j?.cat) setRows(visitorProofs(j.cat)); }).catch(() => {}); };
    go(); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, [catId, seen]);
  return <ProofsList rows={rows} showAgent={false} />;
}
function PublicMinds({ cat }) {
  const ref = useRef(null); useFit(ref, 24); const seen = useOnScreen(ref);
  const [d, setD] = useState(null); const [tick, setTick] = useState(0);
  useEffect(() => { if (!seen) return undefined; let on = true; const go = first => { if (document.hidden && first !== true) return; setTick(t => t + 1); Promise.resolve().then(() => fetch(apiUrl(`/api/cats/${cat.id}/live`))).then(r => (r?.ok ? r.json() : null)).then(x => on && x && setD(x)).catch(() => {}); };
    go(true); const t = setInterval(go, 4000); return () => { on = false; clearInterval(t); }; }, [cat.id, seen]);
  const brains = cat.brainsCfg?.brains || [];
  const wins = d?.windows?.length ? d.windows : brains.slice(0, 2).map((m, i) => ({ i, model: String(m).split('/').pop(), status: 'idle', host: '', steps: 0 }));
  const live = d?.status === 'working' || wins.some(w => w.status === 'working');
  return <section ref={ref} className="cwb kd-card cwb-dash cwb-public" data-testid="cwb-public">
    <NowLine cat={cat} wins={wins.map(w => ({ ...w, status: w.frozen ? 'paused' : w.status, url: w.host ? `https://${w.host}` : '', bubble: w.frozen ? 'paused — its owner is signing in' : '' }))} live={live} />
    <div className="cwb-theater"><MindRail w={wins[0]} side="left" d={d} />
    <div className="cwb-stage agd-wins">{wins.map(w => { const go = w.status === 'working'; const i = w.i ?? 0;
      return <article key={i} className={`agd-win cwb-win w${i % 2} s-${w.status}`} data-testid={`cwb-pub-${i}`}>
        <span className={`agd-bar${go ? ' is-go' : ''}`}><i /><i /><i /><b>MIND {'AB'[i] || i + 1}</b><small>{w.model || 'model'}</small><em className={`agd-live${go ? '' : ' is-off'}`}>● {go ? 'LIVE' : String(w.status).toUpperCase()}</em></span>
        <div className="agd-browser is-rec cwb-browser"><span className="agd-url"><i aria-hidden="true"><Ic3 e="🔒" /></i><b>{w.host || 'about:blank'}</b>{go ? <em className="agd-rec">● LIVE</em> : null}</span>
          <div className="agd-screen cwb-view cwb-pubscreen">{w.screen && !w.frozen ? <img className="cwb-shot" src={apiUrl(w.last ? `/api/cats/${cat.id}/last/${w.slot ?? i}` : `/api/cats/${cat.id}/screen/${i}?t=${tick}`)} alt={`${w.model || 'its'} window, ${w.last ? 'its last page' : 'live'}`} data-testid={`cwb-pubshot-${i}`} />
            : <><span className="cwb-pub-host" key={w.host}>{w.frozen ? '🔒 paused' : d?.incognito ? '🕶 incognito' : w.host || (go ? 'thinking…' : 'idle')}</span>
              <small className="cwb-pub-note">{w.frozen ? 'its owner is signing in — this window is hidden until they finish' : d?.incognito ? 'its owner keeps these screens private' : go ? 'reading…' : "waiting for its owner's ask"}</small></>}
            {w.frozen || d?.incognito ? null : <AiCursor c={w.cursor} kind={readCursor()} page />}
</div></div>
        {go && !w.frozen ? <p className={`agd-done is-on cwb-say is-under at-${i % 2 ? 'right' : 'left'}`}>MIND {'AB'[i]} · on {w.host || '…'}</p> : null}
      </article>; })}</div>
    <MindRail w={wins[1] || { i: 1, status: 'idle' }} side="right" d={d} /></div>
    <VisitorProofs catId={cat.id} seen={seen} />
    <StoredPop item={d?.lastStored} />
  </section>;
}

// 🔐 THE CREDENTIALS DRAWER (owner 2026-10-30): site names only — stream-safe; a click unhides ONE login for 15 s. You add a site's login here
// (a window's 🔑 card opens it with the site filled in), sealed on the server; its windows get it there and type it blind ({{username}} / {{password}}).
// No account yet? Sign up opens the site in a new tab — come back and save it here.
function CredRow({ cat, r, onDrop }) {
  const [pw, setPw] = useState(null); const [why, setWhy] = useState(''); const { signMessage } = useWallet() || {};
  useEffect(() => { if (pw == null) return undefined; const t = setTimeout(() => setPw(null), 15000); return () => clearTimeout(t); }, [pw]);
  const show = async () => { if (pw != null) { setPw(null); return; } setWhy('');   // 🔐 every reveal = its own wallet signature (a stolen session alone shows nothing)
    try { const ts = Math.floor(Date.now() / 1000); const sig = await signMessage(revealMessage(cat.id, r.site, ts)); setPw((await work(cat.id, { op: 'reveal', text: r.site, job: r.user, ts, sig })).password); } catch (e) { setWhy(e.message || 'Not shown'); } };
  return <li data-testid={`cwb-cred-${r.site}`}><b>{r.site}</b>
    {pw != null ? <span className="cwb-cred-open"><span className="cwb-pw is-open">{r.user}</span><span className="cwb-pw is-pw is-open">{pw}</span></span> : null}
    <span className="cwb-cred-acts"><button type="button" className="m-btn" onClick={show} aria-pressed={pw != null} data-tip={pw != null ? 'Hide it now (it hides itself in 15 s)' : 'Sign once with your wallet to unhide this login for 15 s — hidden by default so a stream never shows it'} data-testid={`cwb-reveal-${r.site}`}>{pw != null ? '🙈 Hide' : '👁 Show'}</button>
      <button type="button" className="m-btn cwb-cred-x" onClick={() => onDrop(r)} aria-label={`Forget the ${r.site} login`} data-tip="Forget this login">✕</button></span>{why ? <small className="kd-err" role="alert">⚠ {why}</small> : null}</li>;
}
const VAULT_WORD = { 'signed in': '🔓 signed in', 'signed out': '🔒 signed out', saved: '🔐 saved', used: '🤖 signed in with', revealed: '👁 revealed', forgot: '✕ forgot', 'cloud connected': '☁ connected', 'cloud disconnected': '☁ disconnected' };
function Credentials({ cat, rows, ask, onSaved, log = [] }) {
  const box = useRef(null); const [site, setSite] = useState(''); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => { if (!ask?.site) return; setSite(ask.site); if (box.current) { box.current.open = true; box.current.scrollIntoView({ behavior: 'smooth', block: 'center' }); setTimeout(() => box.current?.querySelector('input[name="u"]')?.focus({ preventScroll: true }), 400); } }, [ask]);
  const host = site.trim().toLowerCase().replace(/^https?:\/\//, '').split('/')[0];
  const save = async e => { e.preventDefault(); const f = new FormData(e.currentTarget); const form = e.currentTarget; setErr(''); setBusy(true);
    try { const j = await work(cat.id, { op: 'save_login', text: host, user: String(f.get('u') || ''), secret: String(f.get('p') || '') }); form.reset(); setSite(''); onSaved?.(j.logins); } catch (er) { setErr(er.message); } finally { setBusy(false); } };
  const drop = async r => { try { onSaved?.((await work(cat.id, { op: 'unlogin', text: r.site, job: r.user })).logins); } catch (er) { setErr(er.message); } };
  return <details ref={box} className="cwb-vault" open data-testid="cwb-vault"><summary data-tip="Logins its windows may use — sealed on the server, the AI models never see them"><Ic3 e="🔐" /> CREDENTIALS <b className="m-num">{rows?.length || 0}</b></summary>
    {rows?.length ? <ul>{rows.map(r => <CredRow key={`${r.site}|${r.user}`} cat={cat} r={r} onDrop={drop} />)}</ul> : null}
    <form className="cwb-login cwb-cred-add" onSubmit={save} autoComplete="off" data-testid="cwb-cred-add">
      <input className="m-input" name="s" value={site} onChange={e => setSite(e.target.value)} placeholder="site (e.g. dropbox.com)" aria-label="Site" required data-testid="cwb-cred-site" />
      <input className="m-input" name="u" autoComplete="off" placeholder="email or username" aria-label="Email or username" required data-testid="cwb-login-user" />
      <input className="m-input" name="p" type="password" autoComplete="new-password" placeholder="password" aria-label="Password" required data-testid="cwb-login-pass" />
      <span><button type="submit" className="m-btn m-go" disabled={busy || !host} data-testid="cwb-cred-save">{busy ? 'Sealing…' : 'Save sealed'}</button>
        {host ? <a className="m-btn cwb-signup" href={`https://${host}`} target="_blank" rel="noopener noreferrer" data-tip={`No account on ${host}? Sign up in a new tab, then come back and save it here`} data-testid="cwb-signup">No account? Sign up ↗</a> : null}</span>
      {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</form>
    {log.length ? <ol className="cwb-vlog" data-testid="cwb-vault-log" aria-label="Who used the vault">{log.slice().reverse().slice(0, 6).map((x, i) => <li key={`${x.at}-${i}`} style={{ '--i': i }}><span>{VAULT_WORD[x.what] || x.what}</span><b>{x.site || ''}</b><time className="m-num">{ago(x.at)}</time></li>)}</ol> : null}</details>;
}
// 🖥 YOUR PRIVATE DESKTOP (owner 2026-10-31: "make it one window designed like the others — a real desktop: minimize the app, a Windows folder with
// the whole drawer to work in"): a desktop over the page — the live window (a sign-in, or a window handed to you) is an app window you move ·
// minimize · maximize; 🔐 Vault opens like a PC folder (Credentials · Sealed · Signed-in sites · API keys); a taskbar with the clock. Your
// screen only. The Vault asks "somewhere safe?" first, and every item still needs its own signature to open.
const STEEL_MS = 15 * 60 * 1000;   // a cloud window lives 15 min (Steel's free tier) — the title bar counts it down
const VAULT_TABS = [['creds', '🔐', 'Credentials', d => (d?.logins || []).length], ['sealed', '🔏', 'Sealed', d => (d?.secrets || []).length],
  ['sites', '🔓', 'Signed-in sites', d => (d?.signedIn || []).length], ['api', '🔑', 'API keys', () => null]];
const mmss = ms => `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}`;
// ⛏ the owner's PoW folder: every Proof of Work its minds filed — the calls, how they graded, and each proof with its vitals per site
// ⛏ one PoW FOLDER (backend pow.py v2): 4 coins (2 intake · 1 Pump · 1 DexScreener) → both minds agree on 1 → bought on FEELESS → watch / research / decide
const PHASES = [['propose', 'PROPOSE'], ['split', 'SPLIT'], ['scout', 'RESEARCH'], ['choose', 'DECIDE'], ['buy', 'BUY'], ['watch', 'HOLD'], ['done', 'FILED']];
const SRC = { intake: 'FEELESS', pump: 'PUMP', dex: 'DEX' };
function CoinFolder({ f, c, catId, onShot }) {   // 📁 one coin's folder inside a PoW folder: its vitals + the snapshots of every site researched
  const shots = cleanShots(f, c.mint); const mv = (f.moves || {})[c.mint] || {};
  const met = (f.evidenceMetrics || {})[c.mint];
  const raw = (f.vitals || {})[c.mint] || (f.pick?.mint === c.mint ? (f.research || []) : []);
  const vit = Object.values(raw.reduce((a, x) => ({ ...a, [x.label]: { ...x, sites: [...new Set([...(a[x.label]?.sites || []), ...(x.sites || [x.site])])] } }), {}));   // one row a fact (older folders too)
  return <div className="dsk-coin" data-testid={`dsk-coin-${c.mint}`}>
    <span className="dsk-coin-h"><b><Ic3 e="📁" /> ${c.sym}</b><em>{SRC[c.src] || c.src}</em>{f.pick?.mint === c.mint ? <i>the pick</i> : null}</span>
    {met ? <div className="dsk-evidence-meter" data-testid="dsk-evidence-meter"><b>RESEARCH MEASURES</b><span>{met.verified} verified facts · {met.visits} browser visits · {met.durationSec}s · ${Number(met.costUsd || 0).toFixed(4)}</span><small>{met.factsPerVisit == null ? 'no browser visits' : `${met.factsPerVisit} facts/visit`} · {met.factsPerUsd == null ? 'no model charge' : `${met.factsPerUsd} facts/$`} {met.gaps?.length ? `· gaps: ${met.gaps.join(', ')}` : ''}</small></div> : null}
    {Object.keys(mv).length ? <ul className="dsk-coin-moves" aria-label="Sites and their random moves">{Object.entries(mv).map(([h, m]) => <li key={h} data-tip={`${h}: ${m.max} moves drawn at random (3–8), ${m.used} used`}><b>{h}</b><u><s style={{ transform: `scaleX(${Math.min(1, (m.used || 0) / (m.max || 1))})` }} /></u><small className="m-num">{m.used}/{m.max}</small></li>)}</ul> : null}
    {vit.length ? <ul className="dsk-coin-vit">{vit.map((x, k) => <li key={`${x.label}${k}`} className={x.contradiction ? 'is-disputed' : ''}><em>{x.label}{x.contradiction ? ' · CONFLICT' : ''}</em><b className="m-num">{x.value}</b><small>{(x.sites || [x.site]).join(' · ')} · {x.verified ? 'page verified' : 'reported'}</small>
      {(x.claims || (x.support ? [x] : [])).length ? <details><summary>Evidence lineage</summary>{(x.claims || [x]).map((cl, j) => <p key={j}><b>{cl.value}</b> · {cl.site} {cl.at ? `· ${new Date(Number(cl.at) * 1000).toLocaleString()}` : ''}<small>{cl.support || 'No page excerpt saved'}</small></p>)}</details> : null}</li>)}</ul>
      : <p className="dsk-coin-read">{String(c.read || 'its FEELESS read').slice(0, 260)}</p>}
    {shots.length ? <div className="dsk-coin-shots">{shots.map(x => <button key={x.file} type="button" onClick={() => onShot(x)} data-tip={`${x.site}: open the page with everything scraped from it`}>
      <img src={apiUrl(`/api/cats/${catId}/powshot/${String(f.id).replace(/[^a-z0-9]/gi, '').toLowerCase()}/${x.file}?${agentAuthQuery()}`)} alt={`${x.site} snapshot ${x.n}`} loading="lazy" /><small>{x.trade ? (x.trade === 'good' ? '👍 ' : '👎 ') : ''}{x.site}</small></button>)}</div>
      : <small className="dsk-coin-none">{(f.scout || []).includes(c.mint) ? 'snapshots land here as each site is researched' : 'not researched (failed the safety check) — its FEELESS read is kept'}</small>}
  </div>;
}
export function FolderView({ f, live, catId }) {
  const [open, setOpen] = useState(null); const [big, setBig] = useState(null);
  const at = Math.max(0, PHASES.findIndex(([k]) => k === ({ sell: 'watch', sell_wait: 'watch', research: 'watch', decide: 'watch' }[f.phase] || f.phase)));
  return <div className={`dsk-fold${live ? ' is-live' : ''}`} data-testid={live ? 'dsk-fold-live' : 'dsk-fold'}>
    <span className="dsk-fold-h"><b><Ic3 e="📁" /> {f.name}</b>{f.pnlPct != null ? <em className={`m-num ${f.pnlPct >= 0 ? 'is-up' : 'is-dn'}`}>{f.pnlPct >= 0 ? '+' : ''}{f.pnlPct}%</em> : <em>{live ? 'live' : f.status}</em>}{f.shared ? <small>🤝 {f.shared}% to the Collective</small> : null}</span>
    <SitesRead rows={f.sitesRead} />{catId ? <ProofSubmit cat={{ id: catId }} work={work} f={f} kind="PoW" /> : null}
    <ol className="dsk-fold-steps" aria-label="Where this folder is">{PHASES.map(([k, l], i) => <li key={k} className={i < at || f.status === 'closed' ? 'is-done' : i === at ? 'is-on' : ''}><i aria-hidden="true" />{l}</li>)}</ol>
    <ul className="dsk-fold-coins">{(f.coins || []).map(c => <li key={c.mint} className={`${f.pick?.mint === c.mint ? 'is-pick' : ''}${open === c.mint ? ' is-open' : ''}`}>
      <button type="button" onClick={() => setOpen(o => (o === c.mint ? null : c.mint))} aria-expanded={open === c.mint} data-tip="Open this coin's folder — its vitals and snapshots">
        <em>{SRC[c.src] || c.src}</em><b>${c.sym}</b><small className="m-num">${Math.round((c.liq || 0) / 1000)}K pool · {cleanShots(f, c.mint).length} <Ic3 e="📸" /></small></button></li>)}</ul>
    {open ? <CoinFolder f={f} c={(f.coins || []).find(c => c.mint === open)} catId={catId} onShot={setBig} /> : null}
    {big ? <SnapStack f={f} shot={big} catId={catId} onClose={() => setBig(null)} onPick={setBig} /> : null}
    {(f.talk || []).length ? <ul className="dsk-fold-talk">{f.talk.slice(-5).map((t, i) => <li key={`${t.at}${i}`}><b>{t.by}</b> {t.text}</li>)}</ul> : null}
    {f.why ? <small className="dsk-fold-why">{f.why}</small> : null}
  </div>;
}
// 💬 the commands it understands in the chat — tap one and it is in the chat box, ready to send
const CMDS_FALLBACK = [['file a PoW', 'A new 4-coin PoW folder: they agree on 1, buy it on FEELESS, loop until it sells'], ['stop PoW', 'Ends the folder — sells if it bought'], ['file a PoP', 'Both minds call a perp; a paper trade runs if they agree'], ['propose a PoP', 'The same call filed as a card. Nothing opens until you press Run']];
export function CommandList({ rows, onPick }) {
  const [hit, setHit] = useState('');
  return <ul className="dsk-cmds" data-testid="dsk-cmds">{(rows?.length ? rows : CMDS_FALLBACK).map(([c, why], i) => <li key={c} style={{ '--i': i }}>
    <button type="button" onClick={() => { onPick?.(c); setHit(c); }} data-tip="Put it in the chat box — then press Send" data-testid={`cmd-${i}`}><code>{c}</code><span>{why}</span>{hit === c ? <em>in the chat ✓</em> : null}</button></li>)}</ul>;
}
// ⌨ the command popup above the chat box (owner 2026-11-01: "at least 10 commands that pop up when / is typed") — "/" shows them all, typing filters
export function CmdPop({ text, rows, onPick, anchor = null }) {   // drawn OVER the page, anchored to the chat box (the chat card clips anything outside it — owner: "I don't see a popup")
  const q = String(text || '').replace(/^\//, '').trim().toLowerCase();
  const all = rows?.length ? rows : CMDS_FALLBACK;
  const show = String(text || '').startsWith('/') || (q.length >= 2 && all.some(([c]) => c.toLowerCase().startsWith(q) && c.toLowerCase() !== q));
  const hits = show ? all.filter(([c, why]) => !q || c.toLowerCase().includes(q) || why.toLowerCase().includes(q)).slice(0, 12) : [];
  const [box, setBox] = useState(null);
  useLayoutEffect(() => { const el = anchor?.current; if (!el || !hits.length) { setBox(null); return undefined; }
    const place = () => { const r = el.getBoundingClientRect(); setBox({ left: Math.max(8, r.left), width: Math.min(r.width, window.innerWidth - 16), bottom: Math.max(8, window.innerHeight - r.top + 8) }); };
    place(); window.addEventListener('scroll', place, true); window.addEventListener('resize', place);   // it follows the box as the page moves
    return () => { window.removeEventListener('scroll', place, true); window.removeEventListener('resize', place); }; }, [anchor, hits.length, text]);
  if (!hits.length) return null;
  const list = <ul className={`cwb-cmdpop${box ? ' is-floating' : ''}`} style={box || undefined} role="listbox" aria-label="Commands" data-testid="cwb-cmdpop">{hits.map(([c, why], i) => <li key={c} style={{ '--i': i }}>
    <button type="button" role="option" aria-selected={i === 0} onMouseDown={e => { e.preventDefault(); onPick(c); }} data-testid={`cmdpop-${i}`}><code>{c}</code><span>{why}</span></button></li>)}</ul>;
  return box ? createPortal(list, document.body) : list;
}
// 🗂 every request as its exact log tree (owner 2026-11-01): your words → each mind's job, plan, steps, answer → the answer, with your 👍 / 👎
// 🌳 One request as a tree you can read at a glance: your words at the top, each mind's own branch of steps, the answer they meet at. Each node says what it cost.
const STEP_MARK = { browse: '🧭', open: '🧭', click: '👆', read: '👀', search: '🔎', type: '⌨', done: '✅', answer: '✅' };
function WorkTree({ job, rate }) {
  const [open, setOpen] = useState(null); const minds = job.minds || [];
  return <div className="wtr" data-testid="job-tree" style={{ '--n': Math.max(1, minds.length) }}>
    <div className="wtr-root"><small>YOUR REQUEST</small><b>{job.request}</b><span className="wtr-tot m-num" data-testid="job-total">{shortCost(job.cost)} total</span></div>
    {minds.length ? <><svg className="wtr-fork" viewBox={`0 0 ${minds.length * 100} 24`} preserveAspectRatio="none" aria-hidden="true">{minds.map((_, i) => <path key={i} d={`M${minds.length * 50} 0 C${minds.length * 50} 14 ${i * 100 + 50} 8 ${i * 100 + 50} 24`} vectorEffect="non-scaling-stroke" />)}</svg>
      <div className="wtr-lanes">{minds.map((x, i) => <section key={i} className={`wtr-lane is-m${i}`} style={{ '--i': i }} data-testid={`job-mind-${i}`}><header><b>MIND {'AB'[i]}</b><small>{String(x.model || '').split('/').pop()}</small>{x.cost ? <span className="m-num">{shortCost(x.cost)}</span> : null}{x.job ? <em>{x.job}</em> : null}</header>
        {Array.isArray(x.plan) && x.plan.length ? <ol className="wtr-plan">{x.plan.map((p, n) => <li key={n}>{p}</li>)}</ol> : null}
        <ul className="wtr-steps">{(x.steps || []).map((st, n) => { const id = `${i}.${n}`; return <li key={n} style={{ '--i': n % 16 }} className={open === id ? 'is-open' : ''}><button type="button" onClick={() => setOpen(open === id ? null : id)} aria-expanded={open === id} data-tip={st.d || st.t}><i aria-hidden="true">{STEP_MARK[st.a] || '·'}</i><span><u>{st.a}</u>{st.t}</span></button>{open === id && st.d ? <small>{st.d}</small> : null}</li>; })}{!(x.steps || []).length ? <li className="is-none"><span>No steps were kept for this mind.</span></li> : null}</ul>
        {x.answer ? <p className="wtr-mind-ans">{x.answer}</p> : null}</section>)}</div>
      <svg className="wtr-fork" viewBox={`0 0 ${minds.length * 100} 24`} preserveAspectRatio="none" aria-hidden="true">{minds.map((_, i) => <path key={i} d={`M${i * 100 + 50} 0 C${i * 100 + 50} 16 ${minds.length * 50} 8 ${minds.length * 50} 24`} vectorEffect="non-scaling-stroke" />)}</svg></> : <p className="dsk-note">Answered straight away, with no browsing steps.</p>}
    <div className={`wtr-root is-end is-${rate === 'up' ? 'good' : rate === 'down' ? 'bad' : 'none'}`}><small>THE ANSWER {rate === 'up' ? '· 👍 YOU LIKED IT' : rate === 'down' ? '· 👎 YOU DID NOT' : `· ${String(job.status || '').toUpperCase()}`}</small><p>{job.answer}</p></div></div>;
}
const JOB_PROOF = { pow: '⛏ PoW', pop: '📉 PoP', pob: '🎲 PoB', poc: '📣 PoC', pos: '💻 PoStatic', proof: '🌐 Proof' };   // 🗂 AGT-9: a proof's own research job, filed in Jobs
function JobsFolder({ d }) {   // 🗂 the same explorer as PoW (owner 2026-11-02: "jobs etc are supposed to be styled in foldered work trees"): Jobs › a request › MIND A · MIND B · ANSWER
  const [path, setPath] = useState([]); const jobs = d?.jobs || [];
  if (!jobs.length) return <p className="dsk-note">No finished requests yet — each one lands here as a folder.</p>;
  const j = jobs.find(x => x.id === path[0]); const r = j ? d?.jobRates?.[j.id] : null;
  const crumbs = [['Jobs', []], ...(j ? [[String(j.request).slice(0, 40), [j.id]]] : [])];
  let body;
  if (!j) body = <><div className="hv-pow-stats">{[['REQUESTS', jobs.length], ['FROM PROOFS', jobs.filter(x => x.proof).length], ['👍', Object.values(d?.jobRates || {}).filter(x => x === 'up').length], ['👎', Object.values(d?.jobRates || {}).filter(x => x === 'down').length], ['COST', `$${jobs.reduce((a, x) => a + (Number(x.cost) || 0), 0).toFixed(3)}`]].map(([kk, v]) =>
    <span key={kk}><em>{kk}</em><b className="m-num">{v}</b></span>)}</div>
    <div className="dsk-xgrid">{jobs.map((x, i) => { const rr = d?.jobRates?.[x.id]; return <Tile key={x.id} i={i} tone={rr === 'up' ? 'good' : rr === 'down' ? 'bad' : 'none'} ic={rr === 'up' ? '👍' : rr === 'down' ? '👎' : '🗂'}
      label={String(x.request).slice(0, 22)} sub={`${x.proof ? `${JOB_PROOF[x.proof] || x.proof.toUpperCase()} research · ` : ''}${ago(x.at)} ago · $${Number(x.cost || 0).toFixed(3)}`} onOpen={() => setPath([x.id])} tip={x.request} testid={`dsk-job-${x.id}`} />; })}</div></>;
  else body = <WorkTree job={j} rate={r} />;
  return <div className="dsk-pow" data-testid="dsk-jobs">
    <p className="dsk-path dsk-xpath">{path.length ? <button type="button" className="m-btn" onClick={() => setPath(p => (p.length > 1 ? p.slice(0, 1) : []))} aria-label="Up one folder" data-tip="Up one folder">↑</button> : null}
      {crumbs.map(([l, p], i) => <span key={i}>{i ? <i>›</i> : null}<button type="button" onClick={() => setPath(p)} disabled={i === crumbs.length - 1}>{l}</button></span>)}</p>
    <div key={path.join('/')} className="dsk-pull">{body}</div></div>;
}
// 🌐 the sources book on the Desktop (owner 2026-11-01: "the full source list for users to click — a sign-in tab opens"): every trusted site, what it is
// good for, how it treated the agents (opened / bot-checked), and Sign in → the site opens live in its window for you
// 📚 Its source file: the best free references for its job. Its prompt carries the ones for its own job.
function SourceFile({ cat, d }) {
  const [f, setF] = useState(null); const own = d?.setup?.use || cat?.setup?.use; const [use, setUse] = useState(null);
  useEffect(() => { let on = true; fetch(apiUrl('/api/cats/tools/sourcefile')).then(r => (r.ok ? r.json() : null)).then(j => on && setF(j)).catch(() => {}); return () => { on = false; }; }, []);
  if (!f) return null; const keys = Object.keys(f.labels); const at = use || (keys.includes(own) ? own : keys[0]);
  return <section className="dsk-srcfile" data-testid="dsk-srcfile"><h5>📚 SOURCE FILE <small>{keys.includes(own) ? `It knows its ${f.labels[own]} list` : 'It knows a few from each list'}</small></h5><span className="m-seg" role="tablist" aria-label="Source lists">{keys.map(k => <button key={k} type="button" role="tab" aria-selected={at === k} className={at === k ? 'active' : ''} onClick={() => setUse(k)} data-tip={`References for ${f.labels[k]} work`} data-testid={`dsk-srcfile-${k}`}>{f.labels[k]}</button>)}</span>
    <ul>{f.files[at].map(r => <li key={r.host}><a href={`https://${r.host}`} target="_blank" rel="noopener noreferrer" data-tip={`Opens ${r.host}`}><b>{r.name}</b><small>{r.what}</small></a></li>)}</ul></section>;
}
function SourcesFolder({ cat, d, setD }) {
  const [pick, setPick] = useState(null); const [q, setQ] = useState('');
  const rows = (d?.sources || []).filter(r => !q || r.host.includes(q.toLowerCase()) || String(r.what).toLowerCase().includes(q.toLowerCase()));
  const signed = new Set((d?.signedIn || []).map(x => x.site));
  const book = d?.sources || []; const tried = book.filter(r => r.ok || r.blocked); const blockedNow = book.filter(r => (r.blocked || 0) > (r.ok || 0));
  return <div className="dsk-src" data-testid="dsk-sources">
    <SourceFile cat={cat} d={d} />
    <p className="dsk-src-health" data-testid="dsk-health" data-tip="From real browser visits: pages it read against pages that stopped it"><b className="m-num">{tried.length ? `${tried.length - blockedNow.length} of ${tried.length}` : '—'}</b><span>{tried.length ? 'sources reachable' : 'no browser visits recorded yet'}</span>{blockedNow.length ? <em>Often blocked: {blockedNow.slice(0, 4).map(r => r.host).join(' · ')}</em> : null}</p>
    <input className="m-input" placeholder="Find a site…" value={q} onChange={e => setQ(e.target.value)} aria-label="Find a source" />
    {pick ? <SignedSites cat={cat} d={d} rows={d?.signedIn} nested start={pick} onSaved={(signedIn, secrets) => { setD(x => ({ ...x, signedIn, ...(secrets ? { secrets } : {}) })); setPick(null); }} /> : null}
    <ul>{rows.map((r, i) => <li key={r.host} style={{ '--i': i % 20 }} className={r.last === 'blocked' ? 'is-blocked' : r.ok ? 'is-ok' : ''}>
      <span><b>{r.host}</b><small>{r.what}</small></span>
      <em className="m-num" data-tip="Source access · your agent's manual challenge results">{r.ok || 0} ✓ · {r.blocked || 0} <Ic3 e="🛡" />{d?.challengeStats?.[r.host] ? ` · ${d.challengeStats[r.host].manualPass || 0} recovered / ${d.challengeStats[r.host].timedOut || 0} timed out` : ''}</em>
      {signed.has(r.host) ? <i className="dsk-src-in">signed in</i> : <button type="button" className="m-btn" onClick={() => setPick(r.host)} data-tip={`Opens ${r.host} live in its window — sign in once (its own email), it stays signed in`} data-testid={`src-signin-${r.host}`}>Sign in</button>}</li>)}</ul>
  </div>;
}
// ⛏ THE PoW EXPLORER (owner 2026-11-01: "truly folders and coin folders … the overall PoW folder should always give a final report"):
// PoW › each dated folder › its coin folders (vitals + JPEG snapshots, the pick's 👍 good / 👎 bad trade) + 📋 FINAL REPORT + 💬 the discussion
const shotUrl = (catId, f, file) => apiUrl(`/api/cats/${catId}/powshot/${String(f.id).replace(/[^a-z0-9]/gi, '').toLowerCase()}/${file}?${agentAuthQuery()}`);
const gradeOf = f => (f.pnlPct == null ? null : f.pnlPct > 0 ? 'good' : 'bad');
function TradeLine({ f }) {   // 📈 the trade drawn from its own price samples: entry, take profit, stop, where it sold
  const ys = (f.line || []).map(Number).filter(v => v > 0); const e = Number(f.entry) || 0;
  if (ys.length < 2 || !e) return null;
  const dir = f.side === 'short' ? -1 : 1; const tp = e * (1 + dir * (Number(f.tp) || 0) / 100), sl = e * (1 - dir * (Number(f.sl) || 0) / 100);
  const lo = Math.min(...ys, sl), hi = Math.max(...ys, tp); const y = v => 6 + 88 * (1 - (v - lo) / ((hi - lo) || 1)); const x = k => (k / (ys.length - 1)) * 300;
  const g = gradeOf(f) || ((ys[ys.length - 1] - e) * dir >= 0 ? 'good' : 'bad');
  return <svg className={`dsk-tl is-${g}`} viewBox="0 0 300 100" preserveAspectRatio="none" role="img" aria-label={`$${f.sym} trade: entry, take profit, stop and the price`}>
    <line x1="0" x2="300" y1={y(tp)} y2={y(tp)} className="dsk-tl-tp" /><line x1="0" x2="300" y1={y(sl)} y2={y(sl)} className="dsk-tl-sl" /><line x1="0" x2="300" y1={y(e)} y2={y(e)} className="dsk-tl-e" />
    <polyline points={ys.map((v, k) => `${x(k)},${y(v)}`).join(' ')} className="dsk-tl-px" /><circle cx="300" cy={y(ys[ys.length - 1])} r="3.5" className="dsk-tl-dot" /></svg>;
}
function ReportFile({ f, catId }) {
  const r = f.report;
  if (!r) return <div className="dsk-rep" data-testid="dsk-report"><b className="dsk-rep-h"><Ic3 e="📋" /> FINAL REPORT</b><p className="dsk-note">This folder is still {f.phase} — its report is written the moment it closes.</p></div>;
  return <div className={`dsk-rep is-${gradeOf(f) || 'none'}`} data-testid="dsk-report">
    <span className="dsk-rep-h"><b><Ic3 e="📋" /> FINAL REPORT</b><em>{r.grade}</em>{r.pnlPct != null ? <strong className={`m-num ${r.pnlPct >= 0 ? 'is-up' : 'is-dn'}`}>{r.pnlPct >= 0 ? '+' : ''}{r.pnlPct}%</strong> : null}
      <a className="m-btn" href={shotUrl(catId, f, 'report.md')} target="_blank" rel="noopener noreferrer" data-tip="The same report as a Markdown file">⬇ report.md</a></span>
    <div className="hv-pow-stats">{[['COINS', `${r.researched}/${(r.coins || []).length} researched`], ['TRADE', r.pick ? `$${r.pick} · ${r.sol} SOL` : 'none'], ['HELD', r.held != null ? `${r.held} min · ${r.checks} checks` : '—'], ['COST', `$${Number(r.costUsd || 0).toFixed(4)}`]].map(([k, v]) =>
      <span key={k}><em>{k}</em><b className="m-num">{v}</b></span>)}</div>
    <p className="dsk-rep-l"><b>Lesson</b> {r.lesson}</p>
    <ul className="dsk-rep-c">{(r.coins || []).map(c => <li key={c.mint} className={c.pick ? 'is-pick' : c.safe ? '' : 'is-bad'}><b>{c.pick ? '⭐ ' : ''}${c.sym}</b><em>{c.src}</em>
      <u><s style={{ transform: `scaleX(${Math.min(1, (c.vitals || 0) / 9)})` }} /></u><small className="m-num">{c.safe ? `${c.vitals} vitals · ${c.shots} 📸` : `unsafe — ${c.risk || ''}`}</small></li>)}</ul>
    {(r.shadow || []).length ? <div className="dsk-rep-shadow" data-testid="dsk-rep-shadow"><b>COUNTERFACTUAL · NO TRADE</b><small>Observed price move over the same hold; no fill, fees or liquidity assumed.</small>
      <ul>{r.shadow.map(x => <li key={x.mint}><span>${x.sym}</span><strong className="m-num">{x.priceMovePct == null ? 'price gap' : `${x.priceMovePct >= 0 ? '+' : ''}${x.priceMovePct}%`}</strong></li>)}</ul></div> : null}
  </div>;
}
// 🤝 SHARE PoW WINS WITH THE POT (owner 2026-11-02: "an option in the PoW folder to still send x% of winnings to the pot wallet without colonize"):
// OFF · 5 · 10 · 20 · 30 % — one wallet signature; each WINNING real PoW folder then owes that % of its profit to the colony pot (shown on the ledger)
function PowShare({ cat }) {
  const [share, , sign, canSign] = useColonyShare(cat); const [busy, setBusy] = useState(''); const [err, setErr] = useState('');
  const pick = async pct => { setBusy(String(pct)); setErr(''); try { await sign(pct > 0, pct); } catch (e) { setErr(e.message || 'Not signed'); } finally { setBusy(''); } };
  const cur = share?.on && share?.auto ? share.pct : 0;
  return <div className="dsk-share" data-testid="dsk-share"><span><b>🤝 SHARE WINS WITH THE POOL</b><small>{cur ? `${cur}% of each PoW win of +50% or more goes to the Pool, with its receipt` : share?.on ? 'Your signature is from before Auto-collect, so nothing sends. Pick a % and sign once more.' : 'Off. Its PoW wins stay in its wallet. Pick a % to share (one wallet signature).'}</small></span>
    <span className="m-seg" role="radiogroup" aria-label="Share of each PoW win">{[0, ...SHARE_PCTS].map(p => <button key={p} type="button" role="radio" aria-checked={cur === p} className={cur === p ? 'active' : ''} disabled={!!busy || (p > 0 && !canSign)}
      onClick={() => cur !== p && pick(p)} data-tip={p ? `Sign once: ${p}% of each PoW win of +50% or more to the Pool` : 'Stop sharing (no signature)'} data-testid={`dsk-share-${p}`}>{busy === String(p) ? '…' : p ? `${p}%` : 'OFF'}</button>)}</span>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</div>;
}
// 🧬 ITS FINGERPRINT (owner 2026-11-02): the sources it read and the facts it filed before each trade, scored by how that trade went — its own,
// built over time from the forever archive; its best proven source leads the next research (one at a time, the rest keep rotating)
function PoiPanel({ poi, catId, onRestore }) {
  const [confirm, setConfirm] = useState(null); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  if (!poi) return null;
  if (poi.error) return <p className="pf-gap" role="alert"><Ic3 e="🧬" /> Research DNA needs repair: {poi.error}</p>;
  const restore = async generation => { if (confirm !== generation) { setConfirm(generation); return; }
    setBusy(true); setError(''); try { const x = await work(catId, { op: 'memory_restore', i: generation }); onRestore?.(x.poi); setConfirm(null); }
    catch (e) { setError(e.message); } finally { setBusy(false); } };
  return <section ref={poiBox} className="pf pf-root" aria-label="Private Proof of Intelligence" data-testid="dsk-poi">
    <PoiMinds poi={poi} />
    {(poi.versions || []).length ? <div className="pf-mem m-glass"><b>SEALED MODEL MEMORY</b>{poi.versions.slice().reverse().map(v => <button key={v.generation} type="button" className="m-btn" disabled={busy} onClick={() => restore(v.generation)} data-testid={`dsk-memory-${v.generation}`}>{confirm === v.generation ? 'Restore this version? Tap again' : `Version ${v.generation} · ${new Date(v.at * 1000).toLocaleDateString()}`}</button>)}</div> : null}
    {error ? <small role="alert">{error}</small> : null}
  </section>;
}
function PowReplay({ f, catId, onShot }) {
  const [step, setStep] = useState(0);
  const events = [...(f.talk || []).map(t => ({ at: t.at, kind: t.by || 'Discussion', text: t.text })),
    ...Object.entries(f.evidenceMetrics || {}).map(([mint, m]) => ({ at: (f.shots || []).filter(s => s.mint === mint).at(-1)?.at || f.at, kind: 'Evidence', text: `${m.verified} verified facts · ${m.visits} browser visits · ${m.durationSec}s · ${m.gaps?.length || 0} source gaps` })),
    ...cleanFolderShots(f).map(s => ({ at: s.at, kind: 'Snapshot', text: `${s.site || 'Source'} · ${(f.coins || []).find(c => c.mint === s.mint)?.sym || ''}`, shot: s })),
    ...(f.boughtAt ? [{ at: f.boughtAt, kind: 'Buy', text: `${f.sym || 'Coin'} · ${f.sol || '—'} SOL` }] : []),
    ...(f.soldAt ? [{ at: f.soldAt, kind: 'Sell', text: `${f.pnlPct == null ? 'closed' : `${f.pnlPct >= 0 ? '+' : ''}${f.pnlPct}%`}` }] : [])]
    .filter(x => Number(x.at) > 0).sort((a, b) => a.at - b.at);
  if (!events.length) return <p className="dsk-note">Evidence appears here as this PoW runs.</p>;
  const current = events[Math.min(step, events.length - 1)];
  return <div className="dsk-replay" data-testid="dsk-pow-replay"><b>▶ PoW evidence replay</b><small>{step + 1} / {events.length} · {new Date(Number(current.at) * 1000).toLocaleString()}</small>
    <div className="dsk-replay-controls"><button type="button" className="m-btn" disabled={!step} onClick={() => setStep(step - 1)}>← Earlier</button><input type="range" min="0" max={events.length - 1} value={Math.min(step, events.length - 1)} onChange={e => setStep(Number(e.target.value))} aria-label="PoW evidence step" /><button type="button" className="m-btn" disabled={step >= events.length - 1} onClick={() => setStep(step + 1)}>Later →</button></div>
    <p><strong>{current.kind}</strong> · {current.text}</p>{current.shot?.file ? <button type="button" className="m-btn" onClick={() => onShot(current.shot)}>Open snapshot</button> : null}</div>;
}
// 🖥 proof windows stay mounted while minimized (Back to desk): the taskbar brings back the same open folder, its work still showing
const KEEP_MIN = new Set(['pow', 'pop', 'bids', 'poc', 'postatic']);
// 🗂 a proof window's right rail behind two tabs (owner 2026-11-11: no long stacked columns): its record | live tools
function ProofRail({ kind, folders, onCommand }) {
  const [tab, setTab] = useState('record');
  return <aside className="prf-rail"><div className="m-seg prf-rail-tabs" role="tablist" aria-label="This proof's side">{[['record', 'Its record', 'Its calls, risk and sources from the folders it filed'], ['tools', 'Live tools', 'Live market reads and the sites it can use']].map(([k, l, t]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-tip={t} data-testid={`prf-tab-${k}`}>{l}</button>)}</div>
    <div key={tab} className="prf-rail-pane" role="tabpanel">{tab === 'record' ? <ProofKit kind={kind} folders={folders} onCommand={onCommand} /> : <ProofTools kind={kind} onCommand={onCommand} />}</div></aside>;
}
function PowExplorer({ cat, d, setD, focus = null }) {
  const [path, setPath] = useState(() => (focus?.id ? [focus.id] : []));
  useEffect(() => { if (focus?.id) setPath([focus.id]); }, [focus?.at]);   // eslint-disable-line react-hooks/exhaustive-deps
  const [rows, setRows] = useState(null); const [big, setBig] = useState(null); const [sure, setSure] = useState(''); const [err, setErr] = useState('');
  // 📌 keep / 🗑 delete (owner 2026-11-02): from the DESKTOP only — the forever archive keeps every fact, so the next PoW still never repeats it
  const act = async (job, extra = {}) => { setErr('');
    try { const j = await work(cat.id, { op: 'pow_folder', job, ...extra }); setD?.(x => ({ ...x, powFolders: j.powFolders })); setSure('');
      if (job === 'delete') setPath([]); else if (job === 'delete_coin') setPath(p => p.slice(0, 1)); } catch (e) { setErr(e.message); } };
  useEffect(() => { let on = true; Promise.resolve().then(() => fetch(apiUrl(`/api/cats/pow?cat=${cat.id}&limit=40&${agentAuthQuery()}`))).then(r => (r?.ok ? r.json() : null)).then(x => on && setRows(x?.rows || [])).catch(() => on && setRows([])); return () => { on = false; }; }, [cat.id]);
  const all = [...(d?.powFolder ? [{ ...d.powFolder, live: true }] : []), ...(d?.powFolders || [])]   // the server sends the newest first;
  const f = path[0] && path[0] !== 'old' ? all.find(x => x.id === path[0]) : null; const c = f && path[1] ? (f.coins || []).find(x => x.mint === path[1]) : null;
  const done = all.filter(x => x.pnlPct != null); const won = done.filter(x => x.pnlPct > 0).length;
  const crumbs = [['PoW', []], ...(path[0] === 'old' ? [['Older proofs', ['old']]] : []), ...(f ? [[f.name, [f.id]]] : []), ...(c ? [[`$${c.sym}`, path]] : []), ...(path[1] === 'report' ? [['FINAL REPORT', path]] : []), ...(path[1] === 'poi' ? [['PoI', path]] : []), ...(path[1] === 'talk' ? [['Discussion', path]] : [])];
  let body;
  if (path[0] === 'old') body = rows?.length ? <div className="hv-pow-grid">{rows.map(p => <PowCard key={p.id} p={p} />)}</div> : <PowCard p={null} />;
  else if (!f) body = <>
    <div className="hv-pow-stats">{[['FOLDERS', all.length], ['TRADES', done.length], ['WON', done.length ? `${Math.round(100 * won / done.length)}%` : '—'], ['P/L', `${done.reduce((a, x) => a + (Number(x.pnlSol) || 0), 0).toFixed(4)} SOL`], ['COST', `$${all.reduce((a, x) => a + (Number(x.cost) || 0), 0).toFixed(3)}`]].map(([k, v]) =>
      <span key={k}><em>{k}</em><b className="m-num">{v}</b></span>)}</div>
    <div className="dsk-xgrid">{all.map((x, i) => <Tile key={x.id} print={[x.id, x.pnlPct != null ? Math.max(0, Math.min(100, 50 + Number(x.pnlPct))) : null, 'pow']} i={i} tone={x.live ? 'live' : gradeOf(x) || 'none'} ic={x.live ? '⛏' : gradeOf(x) === 'good' ? '👍' : gradeOf(x) === 'bad' ? '👎' : '📁'}
      label={`${x.kept ? '📌 ' : ''}${String(x.name).split(' · ')[0]}`} sub={x.live ? `● ${x.phase}` : x.pnlPct != null ? `${x.pnlPct >= 0 ? '+' : ''}${x.pnlPct}%` : (x.name.split(' · ').slice(1).join(' ') || x.status)}
      onOpen={() => setPath([x.id])} tip={`${x.name} — ${x.why || x.phase}`} testid={`dsk-x-${x.id}`} />)}
      {rows?.length ? <Tile i={all.length} tone="none" ic="🗃" label="Older proofs" sub={`${rows.length}`} onOpen={() => setPath(['old'])} tip="The single-coin proofs filed before PoW folders" testid="dsk-x-old" /> : null}</div>
    {!all.length ? <p className="dsk-note">No PoW folders yet — type “file a PoW” in its chat.</p> : null}    <PowShare cat={cat} />
    <PoiPanel poi={d?.poi} catId={cat.id} onRestore={poi => setD?.(x => ({ ...x, poi }))} />
    <KernelCard kernel={d?.kernel} />
    <SiteDoor kind="pow" cat={cat} d={d} setD={setD} work={work} />
    <WatchFolders rows={d?.watchFolders} />
</>;
  else if (path[1] === 'report') body = <ReportFile f={f} catId={cat.id} />;
  else if (path[1] === 'poi') body = <PoiFolder f={f} poi={d?.poi} onShot={setBig} />;
  else if (path[1] === 'talk') body = <><FolderCost f={f} /><ul className="dsk-fold-talk">{(f.talk || []).map((t, i) => <li key={`${t.at}${i}`}><b>{t.by}</b> {t.text}</li>)}</ul></>;
  else if (c) { const g = f.pick?.mint === c.mint ? gradeOf(f) : null;
    body = <>{!f.live ? <span className="dsk-fold-acts"><button type="button" className={`m-btn${sure === c.mint ? ' is-danger' : ''}`} onClick={() => (sure === c.mint ? act('delete_coin', { text: f.id, secret: c.mint }) : setSure(c.mint))}
      data-tip="Remove this coin folder (and its snapshots) from the desktop — its facts stay in the archive" data-testid="dsk-coin-del">{sure === c.mint ? 'Tap again to delete' : '🗑 Delete coin folder'}</button></span> : null}
      {f.pick?.mint === c.mint ? <div className={`dsk-trade is-${g || 'open'}`}><b>{g === 'good' ? '👍 GOOD TRADE' : g === 'bad' ? '👎 BAD TRADE' : '● THE PICK — trading'}</b>
      <small className="m-num">{f.sol} SOL · TP +{f.tp}% · SL −{f.sl}%{f.pnlPct != null ? ` · ${f.pnlPct >= 0 ? '+' : ''}${f.pnlPct}%` : ''}</small><TradeLine f={f} /></div> : null}
      <CoinFolder f={f} c={c} catId={cat.id} onShot={setBig} /></>; }
  else { const at = Math.max(0, PHASES.findIndex(([k]) => k === ({ sell: 'watch', research: 'watch', decide: 'watch' }[f.phase] || f.phase)));
    body = <>{f.live ? null : <span className="dsk-fold-acts"><button type="button" className={`m-btn${f.kept ? ' is-on' : ''}`} aria-pressed={!!f.kept} onClick={() => act('keep', { text: f.id, on: !f.kept })}
        data-tip={f.kept ? 'Kept — never trimmed from the desktop. Tap to un-keep.' : 'Keep it — the desktop holds the newest 30 folders, a kept one stays for good'} data-testid="dsk-fold-keep">{f.kept ? '📌 Kept' : '📌 Keep'}</button>
      <button type="button" className={`m-btn${sure === f.id ? ' is-danger' : ''}`} onClick={() => (sure === f.id ? act('delete', { text: f.id }) : setSure(f.id))}
        data-tip="Remove it from the desktop (its snapshots too). Its facts stay in the PoW archive so the next PoW never repeats them." data-testid="dsk-fold-del">{sure === f.id ? 'Tap again to delete' : '🗑 Delete'}</button></span>}
      <ol className="dsk-fold-steps" aria-label="Where this folder is">{PHASES.map(([k, l], i) => <li key={k} className={i < at || f.status === 'closed' ? 'is-done' : i === at ? 'is-on' : ''}><i aria-hidden="true" />{l}</li>)}</ol>
      {f.evidenceMetrics ? <div className="dsk-evidence-summary" data-testid="dsk-evidence-summary"><b>RESEARCH SIGNAL</b><span>{Object.values(f.evidenceMetrics).reduce((n, m) => n + (m.verified || 0), 0)} verified facts · {Object.values(f.evidenceMetrics).reduce((n, m) => n + (m.visits || 0), 0)} page visits · {Object.values(f.evidenceMetrics).flatMap(m => m.gaps || []).length} source gaps</span></div> : null}
      <PowReplay key={f.id} f={f} catId={cat.id} onShot={setBig} />
      <div className="dsk-xgrid"><Tile kind="file" tone={gradeOf(f) || 'none'} ic="📋" label="REPORT" sub={f.report ? f.report.grade : "when it closes"} onOpen={() => setPath([f.id, 'report'])} tip="What this folder found, the trade, its grade and cost" testid="dsk-x-report" />
        {(f.coins || []).filter(x => !(f.hidden || []).includes(x.mint)).map((x, i) => { const pk = f.pick?.mint === x.mint; const g = pk ? gradeOf(f) : null;
          return <Tile key={x.mint} i={i + 1} tone={g || (pk ? 'live' : x.safe === false ? 'bad-coin' : 'coin')} ic={g === 'good' ? '👍' : g === 'bad' ? '👎' : pk ? '⭐' : x.safe === false ? '⛔' : '🪙'} label={`$${x.sym}`}
            sub={`${SRC[x.src] || x.src} · ${cleanShots(f, x.mint).length} 📸`} onOpen={() => setPath([f.id, x.mint])} tip={`$${x.sym}'s folder — its vitals and snapshots`} testid={`dsk-x-coin-${x.mint}`} />; })}
        <Tile kind="dir" i={5} tone="live" ic="🧬" label="PoI" sub={f.poiTrace ? `${Object.keys(f.poiTrace).length} traced` : 'not recorded'} onOpen={() => setPath([f.id, 'poi'])} tip="How this PoW used Proof of Intelligence: routes, evidence and each mind's DNA" testid="dsk-x-poi" />
        <Tile kind="file" i={6} tone="none" ic="💬" label="Discussion" sub={`${(f.talk || []).length} lines`} onOpen={() => setPath([f.id, 'talk'])} tip="Every line the minds and the engine said" testid="dsk-x-talk" /></div>
      {f.why ? <small className="dsk-fold-why">{f.why}</small> : null}{f.propose ? <ProposalClaim cat={cat} f={f} onDone={rows => setD(x => ({ ...x, powFolders: rows }))} /> : null}</>; }
  return <div className="dsk-pow" data-testid="dsk-pow">
    <p className="dsk-path dsk-xpath">{path.length ? <button type="button" className="m-btn" onClick={() => setPath(p => (p.length > 1 ? p.slice(0, 1) : []))} aria-label="Up one folder" data-tip="Up one folder">↑</button> : null}
      {crumbs.map(([l, p], i) => <span key={l}>{i ? <i>›</i> : null}<button type="button" onClick={() => setPath(p)} disabled={i === crumbs.length - 1}>{l}</button></span>)}{path.length ? <BackToDesk /> : null}</p>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
    <div key={path.join('/')} className="dsk-pull">{body}</div>
    {big && f ? <SnapStack f={f} shot={big} catId={cat.id} onClose={() => setBig(null)} onPick={setBig} /> : null}
  </div>;
}
// 🏺 SEND TO THE COLONY POT (owner 2026-11-02): SOL from ITS OWN wallet to the colony pot — the server holds the pot address (no destination
// field), the gas reserve always stays, Circle signs one transfer; it lands on the colony ledger with its tx
// ⚡ a lazy window that, once its code is here, renders it directly: React.lazy still suspended on the first open even with the code fetched,
// and React holds a suspended reveal back (268 ms commit from a timer, measured 2026-11-10)
function preLazy(load, pick) {
  let mod = null; const L = lazy(() => load().then(m => { mod = m; return { default: pick(m) }; }));
  const C = props => { const M = mod ? pick(mod) : L; return <M {...props} />; };
  C.preload = () => load().then(m => { mod = m; return m; }); return C;
}
const BidsLazy = preLazy(() => import('../RepMarkets'), m => m.default);
const PrintLazy = preLazy(() => import('./Proofprint'), m => m.ProofprintFolder);
const BoostLazy = lazy(() => import('./BoostFolder').then(m => ({ default: m.BoostFolder })));
const FeaturesLazy = preLazy(() => import('./FeaturesFolder'), m => m.FeaturesFolder);
const ProofDeskLazy = preLazy(() => import('./FeaturesFolder'), m => m.ProofDesk);
const CollectiveLandingLazy = lazy(() => import('./CollectiveLanding').then(m => ({ default: m.CollectiveLanding })));
const CharacterLazy = preLazy(() => import('./CharacterFolder'), m => m.CharacterFolder);
const AgentLedgerLazy = lazy(() => import('./HiveBoard').then(m => ({ default: m.AgentLedger })));
const AgentPotLazy = lazy(() => import('./AgentPot'));
// ⚡ SITE-2 (measured 2026-11-10 in his Chrome): Features took 725 ms on its FIRST open, 38-46 ms after: the time was its code arriving. The
// desktop fetches the heavy windows' code while idle, once, so the first click is already loaded. Fetch only: nothing renders.
let PREFETCHED = false;
export function prefetchDeskWindows() {
  if (PREFETCHED || typeof window === 'undefined') return; PREFETCHED = true;
  // ⚡ one bundle per idle moment (2026-11-11): all five at once ran back to back as one long freeze right after the desk opened
  const queue = [FeaturesLazy, ProofDeskLazy, PrintLazy, CharacterLazy, BidsLazy];
  const idle = f => (window.requestIdleCallback ? window.requestIdleCallback(f, { timeout: 4000 }) : setTimeout(f, 1500));
  const go = () => { const L = queue.shift(); if (!L) return; L.preload().catch(() => {}).finally(() => idle(go)); };
  idle(go);
}
const flowApi = u => fetch(apiUrl(u)).then(r => r.json());
function PotSend({ cat }) {
  const px = useSolPrice();
  const [amt, setAmt] = useState(''); const [busy, setBusy] = useState(false); const [msg, setMsg] = useState(''); const [ok, setOk] = useState(null);
  const [proofs, setProofs] = useState([]); const [pick, setPick] = useState('');
  const loadProofs = () => Promise.resolve().then(() => work(cat.id, { op: 'honey' })).then(j => setProofs(j?.honey?.proofs || [])).catch(() => {});
  useEffect(() => { loadProofs(); }, [cat.id]);   // eslint-disable-line react-hooks/exhaustive-deps
  const free = proofs.filter(p => !p.used); const ready = !!pick;
  const send = async () => { setBusy(true); setMsg(''); setOk(null);
    try { const j = await work(cat.id, { op: 'pot_send', cap: Number(amt), job: pick }); setOk(j.sent); setAmt(''); setPick(''); loadProofs(); } catch (e) { setMsg(e.message || 'Not sent — nothing moved.'); } finally { setBusy(false); } };
  return <form className="dsk-potsend" onSubmit={e => { e.preventDefault(); send(); }} data-testid="dsk-potsend">
    <span><b><Ic3 e="💎" /> SEND TO THE POOL</b><small>Every send goes with a proof, $1 or more. It always keeps its gas.</small></span>
    {free.length ? <select className="m-input" value={pick} onChange={e => setPick(e.target.value)} aria-label="Proof to send" data-tip="Each proof can go once" data-testid="dsk-pot-proof"><option value="">Pick a proof…</option>{free.map(p => <option key={p.id} value={p.id}>{p.name}{p.sym ? ` · $${p.sym}` : ''}{p.pnlPct != null ? ` · ${p.pnlPct >= 0 ? '+' : ''}${Number(p.pnlPct).toFixed(1)}%` : ''}</option>)}</select> : <small className="m-dim" data-testid="dsk-pot-none">{proofs.length ? 'Every proof it has already went to the Pool.' : 'It has no filed proof yet.'}</small>}
    {Number(amt) > 0 ? <SplitFlow sendUsd={(Number(amt) || 0) * (px || 0)} testid="dsk-pot-split" /> : null}
    <span className="dsk-wal-amt"><input className="m-input" inputMode="decimal" placeholder="SOL to send" value={amt} onChange={e => setAmt(e.target.value.replace(/[^0-9.]/g, ''))} aria-label="SOL to send to the Pool" />
      <button type="submit" className="m-btn m-go" disabled={busy || !ready || !(Number(amt) > 0)} data-tip={ready ? 'Its wallet signs one transfer to the Pool' : 'Pick a proof first'} data-testid="dsk-potsend-go">{busy ? 'Sending…' : 'Send'}</button></span>
    {ok ? <small className="dsk-wal-msg" role="status">✓ {ok.sol} SOL sent to the Pool · <a href={`https://solscan.io/tx/${ok.sig}`} target="_blank" rel="noopener noreferrer">tx ↗</a></small> : null}
    {msg ? <small className="kd-err" role="alert">⚠ {msg}</small> : null}</form>;
}
// 🍯 the owner's Honey pot: its colony vitals (honey, right calls, the next airdrop, the pool) + the real ways to put into the colony (the 🐝 Colonize popout)
function PopApp({ cat, d, setD, focus = null }) {
  const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  useEffect(() => { let on = true; let ver = d?.powVer || null; const load = () => { if (!document.hidden) work(cat.id, { op: 'state', ver }).then(j => { if (j.powVer) ver = j.powVer; return j; }).then(j => on && setD?.(x => ({ ...x, popFolder: j.popFolder, popCard: j.popCard, popRead: j.popRead, popFolders: j.popFolders ?? x?.popFolders, popPoi: j.popPoi ?? x?.popPoi }))).catch(() => {}); };
    load(); const t = setInterval(load, 5000); return () => { on = false; clearInterval(t); }; }, [cat.id, setD]);
  const [asking, setAsking] = useState(null);   // the minds take about 15 s: the desk says so until a new card, trade or filed row arrives
  const mark = `${d?.popCard?.id || ''}|${d?.popFolder?.id || ''}|${d?.popFolders?.[0]?.id || ''}`;
  useEffect(() => { if (!asking) return undefined; if (asking !== mark) { setAsking(null); return undefined; } const t = setTimeout(() => setAsking(null), 90000); return () => clearTimeout(t); }, [asking, mark]);
  const send = async job => { setBusy(true); setErr(''); try { await work(cat.id, { op: 'pop', job }); if (job === 'propose' || job === 'start') setAsking(mark); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const busyNow = busy || !!asking || !!d?.popRead; const prices = useProofPrices(cat.id, work);
  return <PopExplorer cat={cat} d={d} setD={setD} send={send} busy={busyNow} focus={focus}>{rows => <PopDesk d={d} send={send} busy={busyNow} asking={!!asking || !!d?.popRead} err={err} price={priceWord(prices?.pop)}>{rows}</PopDesk>}</PopExplorer>;
}
// 📉 THE PoP EXPLORER (owner 2026-11-04: "PoP needs to be folders like PoW"): PoP › each dated folder › REPORT, a folder per market they read, the discussion. The same Tile, crumbs and steps as PoW.
const POP_STEPS = ['READ', 'CALL', 'AGREE', 'OPEN', 'EXIT', 'FILED'];
const popDay = x => new Date(Number(x.at || x.openedAt || 0) * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
const popPct = v => `${v >= 0 ? '+' : ''}${Number(v || 0).toFixed(2)}%`;
const popResult = x => (x.noTrade || x.state === 'ran' || x.status !== 'closed' ? null : x.won ? 'good' : 'bad');
function popStep(x) { if (x.status === 'closed') return x.noTrade ? 2 : 6; return x.proposal ? 2 : 4; }
const PopChartLazy = lazy(() => import('../perps/PerpsChart').then(m => ({ default: m.PerpsChart })));
// 📈 what the minds are looking at: the true candles with this trade's levels on them
function PopChart({ f }) {
  const dir = f.side === 'short' ? -1 : 1; const e = Number(f.entry) || 0;
  const lines = e ? [{ id: 'entry', price: e, color: '#ffffff', title: 'ENTRY' }, { id: 'tp', price: e * (1 + dir * f.tp / 100), color: '#b48cff', title: 'TAKE', dash: true }, { id: 'sl', price: e * (1 - dir * f.sl / 100), color: '#ff8fa3', title: 'STOP', dash: true }] : [];
  return <div className="pop-chart m-glass" data-testid="pop-chart"><Suspense fallback={<p className="dsk-note">Loading true candles…</p>}><PopChartLazy asset={f.market} iv="1m" lines={lines} /></Suspense></div>;
}
// 🌐 what a mind actually opened in its own window, and what it read there
function Browsed({ b }) {
  if (!b) return null;
  const note = String(b.note || '');
  return <div className="pop-web" data-testid="pop-browsed"><em><Ic3 e="🌐" /> {(b.sites || []).length ? b.sites.join(' · ') : 'Opened no site'}</em>{note.length > 360 ? <details className="pop-web-note"><summary>What it read · open full notes</summary><small>{note}</small></details> : note ? <small>{note}</small> : null}</div>;
}
// 🛰 each mind's own sources, each measured against the chart
function PopSources({ f }) {
  const minds = Object.entries(f.sources || {});
  if (!minds.length) return <p className="dsk-note">This folder is from before sources were filed.</p>;
  return <><SitesRead rows={f.sitesRead} /><div className="pop-srcs" data-testid="pop-sources">{minds.map(([mind, rows]) => { const sites = [...new Set(rows.map(r => r.site))];
    return <section key={mind} className={`pop-src m-glass is-m${mind}`}><b>MIND {mind === '0' ? 'A' : 'B'}</b><Browsed b={f.browsed?.[mind]} />{f.browseWhy ? <small className="pop-web-why">Browsing: {f.browseWhy}</small> : null}{sites.map(site => { const these = rows.filter(r => r.site === site);
      return <div key={site} className="pop-src-site"><span><em>{site}</em><small>{these[0]?.kind}</small></span>{these.map(r => <span key={r.market} className={`pop-dev${!r.ok ? ' is-none' : r.off ? ' is-off' : ''}`} data-tip={r.ok ? `${r.market} read $${Number(r.px).toLocaleString()}, ${r.devBps} bps from the chart${r.funding != null ? ` · funding ${r.funding}% per 8h` : ''}` : `${r.market}: no read, recorded as a gap`}><i>{r.market}</i><u><s style={{ transform: `scaleX(${r.ok ? Math.min(1, Math.abs(r.devBps) / 25) : 0})` }} /></u><small className="m-num">{r.ok ? `${r.devBps > 0 ? '+' : ''}${r.devBps} bps` : 'gap'}</small></span>)}</div>; })}</section>; })}</div></>;
}
function PopMarket({ f, read, m }) {
  const pos = read && read.high > read.low ? Math.max(0, Math.min(1, (read.px - read.low) / (read.high - read.low))) : null; const minds = (f.calls || []).filter(c => c.market === m);
  return <div className="pop-mk" data-testid="pop-market">
    {f.market === m && f.entry ? <div className={`dsk-trade is-${popResult(f) || 'open'}`}><b>{popResult(f) === 'good' ? '👍 GOOD' : popResult(f) === 'bad' ? '👎 BAD' : '● THE PICK'} · {f.side} {m}-PERP</b><small className="m-num">{f.lev}× · TP +{f.tp}% · SL −{f.sl}% · {popPct(f.roePct)}</small><TradeLine f={{ ...f, sym: m, pnlPct: f.status === 'closed' ? f.roePct : null }} /></div> : null}
    <PopChart f={f.market === m ? f : { market: m }} />
    {read ? <div className="pop-read m-glass"><span><em>PRICE WHEN THEY READ IT</em><b className="m-num">${Number(read.px).toLocaleString()}</b></span><span><em>24H</em><b className={`m-num ${read.chgPct >= 0 ? 'is-up' : 'is-dn'}`}>{popPct(read.chgPct)}</b></span>
      {pos != null ? <span className="pop-range" data-tip="Where the price sat inside its 24 hour range"><u><i style={{ left: `${pos * 100}%` }} /></u><small className="m-num">${Number(read.low).toLocaleString()}</small><small className="m-num">${Number(read.high).toLocaleString()}</small></span> : null}</div> : <p className="dsk-note">This folder is from before market reads were filed.</p>}
    {minds.length ? <Calls calls={minds} /> : <p className="dsk-note">Neither mind called {m}.</p>}</div>;
}
function PopReport({ f }) {
  const r = f.report; if (!r) return <div className="dsk-rep"><b className="dsk-rep-h"><Ic3 e="📋" /> FINAL REPORT</b><p className="dsk-note">Still open. Its report is written the moment it closes.</p></div>;
  const tone = popResult(f);
  return <div className={`dsk-rep is-${tone || 'none'}`} data-testid="pop-report"><span className="dsk-rep-h"><b><Ic3 e="📋" /> FINAL REPORT</b><em>{r.grade}</em>{r.roePct != null ? <strong className={`m-num ${r.roePct >= 0 ? 'is-up' : 'is-dn'}`} data-tip={f.ghost ? 'What it would have made. Not counted as P/L' : undefined}>{popPct(r.roePct)}</strong> : null}</span>
    <div className="hv-pow-stats">{[['P/L', r.pnlUsd != null ? `${r.pnlUsd >= 0 ? '+' : '−'}$${Math.abs(r.pnlUsd).toFixed(2)} paper` : 'none'], ['HELD', r.held != null ? `${r.held} min` : '—'], ['MINDS', r.minds], ['COST', `$${Number(r.costUsd || 0).toFixed(4)}`]].map(([k, v]) => <span key={k}><em>{k}</em><b className="m-num">{v}</b></span>)}</div>
    <p className="dsk-rep-l"><b>Lesson</b> {r.lesson}</p>{f.entry ? <TradeLine f={{ ...f, sym: f.market, pnlPct: r.roePct }} /> : null}{r.kernel ? <small className="dsk-note">Limits version {String(r.kernel.hash || r.kernel).slice(0, 12)}</small> : null}</div>;
}
function PopExplorer({ cat, d, setD, send, busy, children, focus = null }) {
  const [path, setPath] = useState(() => (focus?.id ? [focus.id] : []));
  useEffect(() => { if (focus?.id) setPath([focus.id]); }, [focus?.at]);   // eslint-disable-line react-hooks/exhaustive-deps
  const [sure, setSure] = useState(''); const [err, setErr] = useState('');
  const act = async (job, extra) => { setErr(''); try { const j = await work(cat.id, { op: 'pop_folder', job, ...extra }); setD?.(x => ({ ...x, popFolders: j.popFolders })); setSure(''); if (job === 'delete') setPath([]); } catch (e) { setErr(e.message); } };
  const liveRows = [...(d?.popFolder ? [{ ...d.popFolder, live: true }] : []), ...(d?.popCard ? [{ ...d.popCard, live: true }] : [])]; const all = [...liveRows, ...(d?.popFolders || [])];
  const f = path[0] ? all.find(x => x.id === path[0]) : null; const name = x => (x.n ? `PoP #${x.n}` : x.live ? (x.proposal ? 'Proposal' : 'Open PoP') : 'PoP');
  const reads = f?.reads || []; const markets = f ? [...new Set([...reads.map(r => r.market), ...(f.calls || []).map(c => c.market), f.market].filter(Boolean))] : [];
  const crumbs = [['PoP', []], ...(f ? [[`${name(f)} · ${popDay(f)}`, [f.id]]] : []), ...(path[1] === 'report' ? [['FINAL REPORT', path]] : []), ...(path[1] === 'talk' ? [['Discussion', path]] : []), ...(path[1] === 'src' ? [['Sources', path]] : []), ...(path[1] && path[1].startsWith('m:') ? [[`${path[1].slice(2)}-PERP`, path]] : [])];
  let body;
  if (!path[0] || !f) body = children(<><SiteDoor kind="pop" cat={cat} d={d} setD={setD} work={work} />{d?.popPoi ? <section ref={poiBox} className="pf pf-root" aria-label="Proof of Perps fingerprint" data-testid="pop-poi"><PoiMinds poi={d.popPoi} /></section> : null}{all.length ? <div className="dsk-xgrid" data-testid="pop-folders">{all.map((x, i) => { const g = popResult(x);
    return <Tile key={x.id} print={[x.id, x.roePct != null && !x.noTrade ? Math.max(0, Math.min(100, 50 + Number(x.roePct))) : null]} i={i} tone={x.live ? 'live' : g || 'none'} ic={x.live ? (x.proposal ? '💡' : '📉') : x.ghost ? '👻' : g === 'good' ? '👍' : g === 'bad' ? '👎' : '📁'} label={`${x.kept ? '📌 ' : ''}${name(x)}`} sub={x.live ? `● ${popPct(x.roePct)}` : `${popDay(x)}${x.noTrade ? ' · no trade' : x.state === 'ran' ? ' · ran' : ` · ${popPct(x.roePct)}`}`} onOpen={() => setPath([x.id])} tip={`${name(x)}: ${x.noTrade ? `no trade, ${x.why}` : x.side ? `${x.side} ${x.market}${x.ghost ? ', ghost' : ''}` : x.why || 'open'}`} testid={`pop-x-${x.id}`} />; })}</div>
    : <p className="dsk-note">No proofs yet. Type “file a perp” or “propose a perp” in its chat, or tap a button.</p>}</>);
  else if (path[1] === 'report') body = <PopReport f={f} />;
  else if (path[1] === 'src') body = <><ProofSubmit cat={cat} work={work} f={f} kind="PoP" /><PopSources f={f} /></>;
  else if (path[1] === 'talk') body = (f.talk || []).length ? <><FolderCost f={f} /><ul className="dsk-fold-talk" data-testid="pop-talk">{f.talk.map((t, i) => <li key={`${t.at}${i}`}><b>{t.by}</b> {t.text}</li>)}</ul></> : <p className="dsk-note">The discussion is filed when this folder closes.</p>;
  else if (path[1]?.startsWith('m:')) { const m = path[1].slice(2); body = <PopMarket f={f} m={m} read={reads.find(r => r.market === m)} />; }
  else { const at = popStep(f);
    body = <>{!f.live ? <span className="dsk-fold-acts"><button type="button" className={`m-btn${f.kept ? ' is-on' : ''}`} aria-pressed={!!f.kept} onClick={() => act('keep', { text: f.id, on: !f.kept })} data-tip={f.kept ? 'Kept: never trimmed from the desktop. Tap to un-keep' : 'Keep it: the desktop holds the newest 40 folders, a kept one stays for good'} data-testid="pop-keep">{f.kept ? '📌 Kept' : '📌 Keep'}</button>
      <button type="button" className={`m-btn${sure === f.id ? ' is-danger' : ''}`} onClick={() => (sure === f.id ? act('delete', { text: f.id }) : setSure(f.id))} data-tip="Remove this folder from the desktop" data-testid="pop-del">{sure === f.id ? 'Tap again to delete' : '🗑 Delete'}</button></span> : null}
      <ol className="dsk-fold-steps pop-steps" aria-label="Where this folder is">{POP_STEPS.map((l, i) => <li key={l} className={i < at ? 'is-done' : i === at ? 'is-on' : ''}><i aria-hidden="true" />{l}</li>)}</ol>
      {f.live && f.proposal ? <ProposalCard c={f} send={send} busy={busy} /> : f.live ? <Live t={f} /> : null}
      {f.live && f.market ? <PopChart f={f} /> : null}
      <div className="dsk-xgrid"><Tile kind="file" tone={popResult(f) || 'none'} ic="📋" label="REPORT" sub={f.report ? f.report.grade : 'when it closes'} onOpen={() => setPath([f.id, 'report'])} tip="What happened, the result, its cost and the limits it ran under" testid="pop-x-report" />
        {markets.map((m, i) => <Tile key={m} i={i + 1} tone={f.market === m ? (popResult(f) || 'live') : 'coin'} ic={f.market === m ? '⭐' : '📊'} label={`${m}-PERP`} sub={reads.find(r => r.market === m) ? popPct(reads.find(r => r.market === m).chgPct) : `${(f.calls || []).filter(c => c.market === m).length} calls`} onOpen={() => setPath([f.id, `m:${m}`])} tip={`${m}: what the minds read and who called it`} testid={`pop-x-m-${m}`} />)}
        <Tile i={markets.length + 1} tone="none" ic="🛰" label="Sources" sub={f.sources ? `${Object.values(f.sources).flat().filter(r => r.ok).length} reads` : 'not recorded'} onOpen={() => setPath([f.id, 'src'])} tip="What each mind read, each number measured against the chart" testid="pop-x-src" />
        <Tile kind="file" i={markets.length + 2} tone="none" ic="💬" label="Discussion" sub={`${(f.talk || f.calls || []).length} lines`} onOpen={() => setPath([f.id, 'talk'])} tip="Every call the minds made and what the engine did" testid="pop-x-talk" /></div>
      {f.why ? <small className="dsk-fold-why">{f.why}</small> : null}</>; }
  return <div className="dsk-pow pop-x" data-testid="dsk-pop">
    {path.length ? <p className="dsk-path dsk-xpath"><button type="button" className="m-btn" onClick={() => setPath(p => (p.length > 1 ? p.slice(0, 1) : []))} aria-label="Up one folder" data-tip="Up one folder">↑</button>{crumbs.map(([l, p], i) => <span key={l}>{i ? <i>›</i> : null}<button type="button" onClick={() => setPath(p)} disabled={i === crumbs.length - 1}>{l}</button></span>)}<BackToDesk /></p> : null}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
    <div key={path.join('/')} className="dsk-pull">{body}</div></div>;
}
// 🎲 THE BIDS FOLDER (owner 2026-11-04): a starting dash like PoW, then the free-chip board and the USA real-money links, each its own folder.
// 🎲 THE PoB FOLDERS: each mind's call and what it read in its own browser, graded by the market's recorded result
const pobTone = x => (x.status !== 'closed' ? 'live' : x.won ? 'good' : x.won === false ? 'bad' : 'none');
function PobTopic({ f, catId, onMark }) {
  const r = f.report; const [big, setBig] = useState(null); const agreed = new Set((f.agreed || []).map(x => x.toLowerCase()));
  return <div className="pob pbt" data-testid="pob-topic">
    <header className="pbt-head m-glass m-live"><Ic3 e="🎲" size="38px" /><span><em className="m-num">{r?.grade || 'RESEARCH'}</em><b>{f.topic}</b><small>{(f.shots || []).length} snapshots · {(f.sites || []).length} sites{f.cost ? ` · $${Number(f.cost).toFixed(4)}` : ''}</small></span>
      {f.noTrade ? null : <span className="m-seg pbt-mark" role="group" aria-label="How it turned out">{[['right', '👍 Right'], ['wrong', '👎 Wrong']].map(([k, l]) => <button key={k} type="button" className={f.graded === k ? 'active' : ''} aria-pressed={f.graded === k} onClick={() => onMark(f.id, f.graded === k ? 'clear' : k)} data-tip="Mark it once the result is known" data-testid={`pbt-${k}`}>{l}</button>)}</span>}</header>
    {r ? <p className="dsk-note">{r.lesson}</p> : null}<BrowseNote f={f} /><SitesRead rows={f.sitesRead} /><ProofSubmit cat={{ id: catId }} work={work} f={f} kind="PoB" />
    {(f.agreed || []).length ? <ul className="pbt-agree" data-testid="pbt-agreed">{f.agreed.map((x, i) => <li key={x} style={{ '--i': i }}><Ic3 e="🤝" size="22px" /><b>{x}</b><small>both minds, blind</small></li>)}</ul> : null}
    {f.kalshi ? <KalshiTicket t={f.kalshi} catId={catId} work={work} /> : null}
    <div className="pop-srcs">{(f.calls || []).map(c => <section key={c.mind} className={`pop-src m-glass is-m${c.mind}`}><b>MIND {c.mind === 0 ? 'A' : 'B'}</b>
      {(c.picks || []).length ? <ul className="pbt-picks">{c.picks.map((p, i) => <li key={p.pick} className={agreed.has(p.pick.toLowerCase()) ? 'is-both' : ''} style={{ '--i': i, '--v': p.confidence / 100 }} data-tip={p.why}><span>{p.pick}</span><em className="m-num">{p.confidence}%</em><u aria-hidden="true"><i /></u><small>{p.why}</small></li>)}</ul> : <small className="pob-why">{c.pass || 'It made no pick.'}</small>}
      <Browsed b={f.browsed?.[c.mind]} /></section>)}</div>
    {(f.shots || []).length ? <div className="pbt-shots" data-testid="pbt-shots">{f.shots.map((x, i) => <button key={x.file} type="button" style={{ '--i': i }} onClick={() => setBig(x)} data-tip={`${x.site}: open it big`} data-testid={`pbt-shot-${i}`}><img src={apiUrl(`/api/cats/${catId}/powshot/${f.id}/${x.file}?${agentAuthQuery()}`)} alt={`${x.site} when it read it`} loading="lazy" /><span><b>{x.site}</b><small>mind {x.mind === 0 ? 'A' : 'B'}</small></span></button>)}</div> : <p className="dsk-note">No snapshots were kept.</p>}
    {big ? <div className="ast-shade" role="dialog" aria-modal="true" aria-label={big.site} onClick={() => setBig(null)}><img src={apiUrl(`/api/cats/${catId}/powshot/${f.id}/${big.file}?${agentAuthQuery()}`)} alt={big.site} /></div> : null}
    <p className="dsk-note">It never bets. Any real bid is yours, on a site where it is legal for you.</p></div>;
}
function PobFolder({ f, catId, onMark }) {
  if (f.topic) return <PobTopic f={f} catId={catId} onMark={onMark} />;
  const r = f.report; const tone = pobTone(f);
  return <div className="pob" data-testid="pob-folder">
    <div className={`dsk-trade is-${tone === 'live' ? 'open' : tone}`}><b>{r?.grade || '● OPEN'}{f.side ? ` · ${String(f.side).toUpperCase()}` : ''}</b><small className="m-num">{f.q || f.why || ''}{f.chips ? ` · ${f.chips} free chips` : ''}</small></div>
    {r ? <p className="dsk-note">{r.lesson}</p> : <p className="dsk-note">The market's own result files this.</p>}
    <BrowseNote f={f} /><SitesRead rows={f.sitesRead} /><ProofSubmit cat={{ id: catId }} work={work} f={f} kind="PoB" />
    <div className="pop-srcs">{(f.calls || []).map(c => <section key={c.mind} className={`pop-src m-glass is-m${c.mind}`}><b>MIND {c.mind === 0 ? 'A' : 'B'} · {c.side ? String(c.side).toUpperCase() : 'NO BID'}</b><small className="pob-why">{c.why || 'No reason given.'}</small><Browsed b={f.browsed?.[c.mind]} /></section>)}</div></div>;
}
function PobShelf({ d, open, setOpen, catId, onMark }) {
  const rows = [...(d?.pobRun ? [d.pobRun] : []), ...(d?.pobFolders || [])]; const f = rows.find(x => x.id === open);
  if (f) return <PobFolder f={f} catId={catId} onMark={onMark} />;
  if (!rows.length) return <p className="dsk-note">No PoB filed yet. Press File a bid.</p>;
  return <div className="dsk-xgrid" data-testid="pob-shelf">{rows.map((x, i) => <Tile key={x.id} print={[x.id, x.graded === 'right' ? 85 : x.graded === 'wrong' ? 25 : null]} i={i} tone={pobTone(x)} ic="🎲" label={`PoB #${x.n || i + 1}`} sub={x.topic ? String(x.topic).slice(0, 20) : x.report?.grade || 'open'} onOpen={() => setOpen(x.id)} tip={x.topic || x.q || x.why || 'Open this proof'} testid={`pob-${x.id}`} />)}</div>;
}
function BidsApp({ cat, d, setD, children, focus = null }) {
  const { wallet } = useWallet() || {}; const address = wallet?.address; const [path, setPath] = useState(focus?.id ? 'pob' : ''); const [m, setM] = useState(null); const [open, setOpen] = useState(focus?.id || '');
  const box = useRef(null);   // 🎯 a picked proof sits under the live tools: scroll it into view
  const want = useRef(null); useEffect(() => { if (focus?.id) { want.current = focus.id; setPath('pob'); setOpen(focus.id); } }, [focus?.at]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!want.current || path !== 'pob' || open !== want.current) return undefined; const t = setTimeout(() => { const el = box.current?.querySelector('.dsk-pull'); if (el && el.getBoundingClientRect().height > 40) { want.current = null; box.current.scrollIntoView?.({ block: 'start', behavior: 'smooth' }); } }, 60); return () => clearTimeout(t); });   // runs after each render until the file has drawn
  const [err, setErr] = useState('');
  useEffect(() => { let on = true; let ver = d?.powVer || null; const load = () => { if (!document.hidden) work(cat.id, { op: 'state', ver }).then(j => { if (j.powVer) ver = j.powVer; if (on) setD?.(x => ({ ...x, pobRead: j.pobRead, pobRun: j.pobRun, pobFolders: j.pobFolders ?? x?.pobFolders })); }).catch(() => {}); };
    load(); const t = setInterval(load, 5000); return () => { on = false; clearInterval(t); }; }, [cat.id, setD]);
  const busy = !!d?.pobRead || !!d?.pobRun;
  const [ask, setAsk] = useState('');
  const mark = (id, job) => work(cat.id, { op: 'pob_folder', text: id, job }).then(j => setD?.(x => ({ ...x, pobFolders: j.pobFolders }))).catch(e => setErr(e.message));
  const file = () => { setErr(''); const text = ask.trim(); work(cat.id, { op: 'pob', ...(text ? { text } : {}) }).then(() => setAsk('')).then(() => setD?.(x => ({ ...x, pobRead: { at: Date.now() / 1000 } }))).catch(e => setErr(e.message)); };
  useEffect(() => { let on = true; const load = () => { if (!document.hidden && !path) Promise.resolve().then(() => fetch(apiUrl(`/api/reputation/rep-markets${address ? `?address=${address}` : ''}`))).then(r => (r?.ok ? r.json() : null)).then(x => on && x && setM(x)).catch(() => {}); };
    load(); const t = setInterval(load, 15000); return () => { on = false; clearInterval(t); }; }, [address, path]);
  const live = (m?.live || []).filter(x => x.kind === 'agent'); const settled = (m?.settled || []).filter(x => x.kind === 'agent');
  const label = { live: 'Live board', settled: 'Settled', sites: 'Real money · USA', pob: 'Its proofs' }[path];
  return <div ref={box} className="dsk-pow bd" data-testid="dsk-bids">
    {path ? <p className="dsk-path dsk-xpath"><button type="button" className="m-btn" onClick={() => (open && path === 'pob' ? setOpen('') : setPath(''))} aria-label="Up one folder" data-tip="Up one folder">↑</button><span><button type="button" onClick={() => setPath('')}>Bids</button></span><span><i>›</i><button type="button" disabled>{label}</button></span><BackToDesk /></p> : null}
    <div key={path} className="dsk-pull">{path === 'sites' ? <BidSites /> : path === 'pob' ? <PobShelf d={d} open={open} setOpen={setOpen} catId={cat.id} onMark={mark} /> : path ? <Suspense fallback={<p className="dsk-note">reading the board…</p>}><BidsLazy only="agent" start={path} /></Suspense> : <>
      <header className="bd-head m-glass m-live"><span><b><Ic3 e="🎲" /> BIDS</b><small>Free chips on your agents, the USA real-money sites, and real Kalshi bids only when you switch that door on below.</small></span><button type="button" className="m-btn m-go bd-file" disabled={busy} onClick={file} data-tip={busy ? 'A PoB is already running' : ask.trim() ? 'Each mind reads major sites, keeps snapshots and calls it blind. Nothing is staked' : 'Each mind reads sites, then calls a market on our board. If they agree, it bids 50 free chips'} data-testid="pob-file"><Ic3 e="🎲" /> File a bid</button></header>
      <input className="m-input pbt-ask" value={ask} onChange={e => setAsk(e.target.value)} placeholder="What to research: best NFL picks this week, or leave empty for our free-chip board" aria-label="What to research" data-tip="Paid model calls" data-testid="pob-topic-input" />
      {d?.pobRead ? <p className="pop-asking m-glass" role="status" data-testid="pob-reading"><i aria-hidden="true" />Each mind is reading sites in its own window. Watch its monitors…</p> : null}
      {err ? <p className="dsk-note" role="alert">{err}</p> : null}
      <KalshiDoor cat={cat} work={work} />
      {children}
      <SiteDoor kind="pob" cat={cat} d={d} setD={setD} work={work} />
      <div className="bd-strip" data-testid="bd-stats">{[['LIVE', m ? live.length : '…', () => setPath('live'), 'Bid free chips on proofs running now', 'bd-live', 'is-live'], ['SETTLED', m ? settled.length : '…', () => setPath('settled'), 'How finished proofs ended', 'bd-settled', ''], ['YOUR CHIPS', m?.bank ? m.bank.chips : '—', () => setPath('live'), 'Free chips. Nothing here bets real money', 'bd-chips', ''], ['ITS PROOFS', (d?.pobFolders || []).length + (d?.pobRun ? 1 : 0), () => setPath('pob'), 'Every PoB it filed', 'bd-proofs', ''], ['REAL MONEY', `${BID_SITES.length} sites`, () => setPath('sites'), 'Links to USA real-money sites, with what each says about automation', 'bd-sites', 'is-money']].map(([k, v, go, tip, id, tone]) => <button key={k} type="button" className={tone} onClick={go} data-tip={tip} data-testid={id}><em>{k}</em><b className="m-num">{v}</b></button>)}</div>
      {live.length ? <ul className="bd-live">{live.slice(0, 5).map((x, i) => <li key={x.id} style={{ '--i': i }}><button type="button" className="m-glass" onClick={() => setPath('live')} data-tip="Open it on the live board"><i aria-hidden="true" /><span>{x.q}</span></button></li>)}</ul> : null}
      <div className="bd-proofs" data-testid="pob-tiles">{[...(d?.pobRun ? [d.pobRun] : []), ...(d?.pobFolders || [])].slice(0, 12).map((x, i) => <Tile key={x.id} print={[x.id, x.graded === 'right' ? 85 : x.graded === 'wrong' ? 25 : null]} i={i} tone={pobTone(x)} ic="🎲" label={`PoB #${x.n || i + 1}`} sub={x.topic ? String(x.topic).slice(0, 20) : x.report?.grade || 'open'} onOpen={() => { setOpen(x.id); setPath('pob'); }} tip={x.topic || x.q || x.why || 'Open this proof'} testid={`pob-${x.id}`} />)}</div></>}</div></div>;
}
function HoneyPot({ cat, pool, d }) {   // 🫙 Its pot (redo 2026-11-14): AgentPot.jsx draws it; the real send controls + ledger ride in
  const p = pool?.pool || {};
  return <Suspense fallback={<p className="dsk-note">reading its pot…</p>}><AgentPotLazy pool={pool} d={d} count={<LiveCount pool={p} readAt={pool?.readAt} testid="clx-f-count" />}
    actions={<><PotSend cat={cat} /><div className="dsk-honey-ways"><b>AUTO-SEND</b><small>Sign once to stake a part of each win of +50% or more. Its score makes its boost and its seat. Only stake what you can lose.</small><HiveSwitch cat={cat} /></div></>}
    ledger={<Suspense fallback={<p className="dsk-note">reading the ledger…</p>}><AgentLedgerLazy api={flowApi} agent={cat.name} /></Suspense>} /></Suspense>;
}
// 👛 the agent's WALLET app (owner 2026-11-01: "desktop agent wallet swapping"): its live SOL + USDC, and YOUR swap inside its own wallet —
// SOL ⇄ USDC only, nothing leaves it, the gas reserve always stays; the server signs only a quote that echoes exactly this swap
function WalletApp({ cat, compact = false, onBrowse = null }) {
  const [pane, setPane] = useState('swap'); const px = useSolPrice();
  const [think, setThink] = useState(null); useEffect(() => { let on = true; work(cat.id, { op: 'wallet_think' }).then(j => on && setThink(j)).catch(() => {}); return () => { on = false; }; }, [cat.id]);
  const [w, setW] = useState(null); const [side, setSide] = useState('USDC>SOL'); const [amt, setAmt] = useState(''); const [busy, setBusy] = useState(false); const [msg, setMsg] = useState('');
  useEffect(() => { let on = true; work(cat.id, { op: 'wallet' }).then(j => on && setW(j)).catch(e => on && setW({ err: e.message })); return () => { on = false; }; }, [cat.id]);
  if (!w) return <p className="dsk-note">reading its wallet…</p>;
  if (w.err) return <p className="dsk-note">{w.err}</p>;
  const days = think?.perDay ? (w.usdc || 0) / think.perDay : null;
  const tok = side.split('>')[0]; const max = tok === 'SOL' ? Math.max(0, (w.sol || 0) - (w.gas || 0)) : (w.usdc || 0);
  const go = async () => { setBusy(true); setMsg('');
    try { const j = await work(cat.id, { op: 'wallet_swap', text: side, cap: Number(amt) || 0 }); setW(j); setAmt('');
      setMsg(j.swap?.landed ? `✓ swapped — it now holds ${Number(j.sol).toFixed(4)} SOL · ${Number(j.usdc).toFixed(2)} USDC` : 'sent — the balance has not moved yet, check again in a minute'); }
    catch (e) { setMsg(e.message || 'Not swapped — nothing moved.'); } finally { setBusy(false); } };
  if (w.fuse) return <div className="dsk-wal" data-testid="dsk-fuse-wallet"><div className="dsk-wal-bal">{[['ON THE CARD', w.cardSol, 'What it can trade with'], ['IN THE WALLET', w.walletSol, 'All SOL at this address'], ['GAS RESERVE', w.reserveSol, 'Kept for network fees'], ['NOT ON THE CARD', w.outsideSol, 'Not assigned to the card yet']].map(([k, v, sub]) => <span key={k} className="is-sol"><em>{k}</em><b className="m-num">{v == null ? '—' : `${Number(v).toFixed(4)} SOL`}</b><small>{sub}</small></span>)}</div>
    <p className="dsk-note">Sicario's trades from the Fuse wallet. To top up, send SOL to this address, then put it on the card in HQ › Fuse. Then ask it to file a PoW.</p>{w.address ? <code className="dsk-wal-addr" data-testid="dsk-fuse-address">{w.address}</code> : <p className="dsk-note" role="alert">The card service did not answer.</p>}</div>;
  const solUsd = Number(w.sol || 0) * (px || 0); const total = solUsd + Number(w.usdc || 0); const gasShare = w.sol ? Math.min(1, (w.gas || 0) / w.sol) : 0; const runway = days == null ? null : Math.min(1, days / 30);
  const PANES = [['swap', 'Swap', 'SOL and USDC, inside its own wallet'], ['topup', 'Top up', 'Its address, to send it SOL or USDC'], ['spend', 'Spending', 'What its thinking costs, call by call'], ['card', 'Get a card', 'A card for its wallet']];
  const tabs = <div className="m-seg wal2-tabs" role="tablist" aria-label="Wallet">{PANES.map(([k, l, t]) => <button key={k} type="button" role="tab" aria-selected={pane === k} className={pane === k ? 'active' : ''} onClick={() => setPane(k)} data-tip={t} data-testid={`wal-tab-${k}`}>{l}</button>)}</div>;
  const copy = () => { try { navigator.clipboard?.writeText(w.address); setMsg('Address copied.'); } catch { setMsg('Copy did not work. Select the address instead.'); } };
  return <div className="dsk-wal wal2" data-testid="dsk-wallet">
    <header className="wal2-hero"><span><small>ITS WALLET</small><b className="m-num" data-testid="wal2-total">{px ? `$${total.toFixed(2)}` : `${Number(w.sol || 0).toFixed(4)} SOL`}</b><em>{px ? 'Live, at today\'s SOL price' : 'Reading the SOL price'}</em></span>
      {w.address ? <button type="button" className="wal2-addr" onClick={copy} data-tip="Its own wallet address. Tap to copy" data-testid="wal2-copy"><code>{`${w.address.slice(0, 4)}…${w.address.slice(-4)}`}</code><i aria-hidden="true">⧉</i></button> : null}</header>
    <div className="wal2-coins">
      <section className="is-sol"><small>SOL</small><b className="m-num">{Number(w.sol || 0).toFixed(4)}</b><em>{px ? `$${solUsd.toFixed(2)}` : ''}</em><u data-tip={`${w.gas} SOL always stays for network fees`}><s style={{ transform: `scaleX(${gasShare})` }} /></u><span>{w.gas} kept for gas</span></section>
      <section className="is-usdc"><small>USDC</small><b className="m-num">{Number(w.usdc || 0).toFixed(2)}</b><em>pays its thinking</em><u data-tip="Days of thinking left, out of 30"><s style={{ transform: `scaleX(${runway ?? 0})` }} className={days != null && days < 3 ? 'is-low' : ''} /></u><span data-testid="dsk-think">{days == null ? 'No spending yet' : days < 3 ? `Top up soon: about ${days.toFixed(1)} days left` : `About ${Math.round(days)} days of thinking left`}</span></section>
    </div>
    {tabs}
    {pane === 'swap' ? (w.canSwap ? <form className="dsk-wal-swap" onSubmit={e => { e.preventDefault(); go(); }}>
      <span className="m-seg" role="group" aria-label="Swap direction">{[['USDC>SOL', 'USDC → SOL'], ['SOL>USDC', 'SOL → USDC']].map(([k, l]) =>
        <button key={k} type="button" className={side === k ? 'active' : ''} aria-pressed={side === k} onClick={() => setSide(k)} data-tip={`Swap its ${k.split('>')[0]} into ${k.split('>')[1]}`}>{l}</button>)}</span>
      <span className="dsk-wal-amt"><input className="m-input" inputMode="decimal" placeholder={`amount ${tok} (empty = all ${max.toFixed(tok === 'SOL' ? 4 : 2)})`} value={amt} onChange={e => setAmt(e.target.value.replace(/[^0-9.]/g, ''))} aria-label={`Amount of ${tok}`} />
        <button type="button" className="m-btn" onClick={() => setAmt(String(Number(max.toFixed(6))))} data-tip="Everything it can swap (the gas reserve stays)">All</button></span>
      <button type="submit" className="m-btn m-go" disabled={busy || !max} data-testid="dsk-wallet-swap" data-tip="Its wallet signs this one swap through FEELESS; the money stays in its wallet">{busy ? 'Swapping…' : `Swap ${tok}`}</button>
    </form> : <p className="dsk-note">Only a wallet Circle signs for this agent can swap.</p>) : null}
    {pane === 'swap' && (w.swaps || []).length ? <ul className="dsk-wal-log">{[...w.swaps].reverse().map((x, i) => <li key={`${x.at}${i}`} style={{ '--i': i }}><b>{x.side.replace('>', ' → ')}</b><em className="m-num">{x.amount}</em><small>{ago(x.at)} ago · {x.landed ? 'landed' : 'sent'}</small></li>)}</ul> : null}
    {pane === 'topup' ? <div className="wal2-topup" data-testid="wal2-topup"><p>Send SOL or USDC on Solana to this address. Only send from a wallet you control.</p><code className="dsk-wal-addr">{w.address}</code><button type="button" className="m-btn m-go" onClick={copy} data-testid="wal2-copy-full">Copy the address</button></div> : null}
    {pane === 'spend' ? <><p className="dsk-note" data-testid="dsk-wallet-model-budget">Model budget: ${Number(cat.brainsCfg?.credit || 0).toFixed(2)} left. Its own USDC pays each call, listed below.</p>
      <div className="dsk-receipts" data-testid="dsk-model-receipts"><b>What each call cost</b>{(w.modelReceipts || []).length ? <ul>{w.modelReceipts.map(r => <li key={r.id}><strong>${Number(r.usd).toFixed(4)}</strong> · {String(r.model || '').split('/').pop()} <small>{r.tokens == null ? 'tokens unreported' : `${r.tokens} tokens`} · {ago(r.at)} ago · {r.status}</small></li>)}</ul> : <small>No model charges recorded yet.</small>}</div></> : null}
    {pane === 'card' ? <CardSites onBrowse={onBrowse} cat={cat} work={work} link={w.cardLink} /> : null}
    {msg ? <small className="dsk-wal-msg" role="status">{msg}</small> : null}
  </div>;
}
// 🧹 Folders that live inside another (owner 2026-11-06). Same folder, same window: reached by a tab along its parent's title bar, so the desktop stays short.
// 🔔 A desktop alert when a proof is done. It compares what is filed, so the first look only sets the count. Nothing is sent anywhere.
const ALERT_KEYS = [['powFolders', 'PoW'], ['popFolders', 'PoP'], ['pobFolders', 'PoB'], ['pocFolders', 'PoC'], ['psFolders', 'PoStatic'], ['poeFolders', 'PoEco']];
export function proofsDone(before, d) { const out = []; ALERT_KEYS.forEach(([k, word]) => { const now = (d?.[k] || []).filter(f => f?.status === 'closed'); const had = before?.[k]; if (had != null && now.length > had) out.push(`${word}: ${now.find(f => f.topic)?.topic || 'a new proof'} is done`); }); return out; }
export function ProofAlerts({ d }) {
  const seen = useRef(null); const [perm, setPerm] = useState(() => (typeof Notification === 'undefined' ? 'none' : Notification.permission)); const [hide, setHide] = useState(() => { try { return !!localStorage.getItem('feeless.alerts.no'); } catch (e) { return false; } });
  useEffect(() => { if (!d) return; const said = proofsDone(seen.current, d); seen.current = Object.fromEntries(ALERT_KEYS.map(([k]) => [k, (d[k] || []).filter(f => f?.status === 'closed').length])); if (perm === 'granted') said.forEach(text => { try { new Notification('FEELESS', { body: text, tag: text }); } catch (e) { /* a browser may refuse: the proof is still filed */ } }); }, [d, perm]);
  if (perm !== 'default' || hide) return null;
  return <span className="dsk-alerts" data-testid="dsk-alerts"><button type="button" className="m-btn m-go" onClick={async () => setPerm(await Notification.requestPermission())} data-tip="Your browser asks once. Only you see them" data-testid="dsk-alerts-on">Alert me when a proof is done</button><button type="button" className="m-btn" aria-label="No alerts" onClick={() => { try { localStorage.setItem('feeless.alerts.no', '1'); } catch (e) { /* the button still hides */ } setHide(true); }} data-testid="dsk-alerts-no">✕</button></span>;
}
export const FOLD_INTO = { print: 'proofs', jobs: 'proofs', tests: 'proofs', terms: 'manual', cmds: 'manual', deskset: 'manual', sources: 'browser', mail: 'browser', vault: 'github', boost: 'wallet', limits: 'brains' };   // 📺 Watch is its own folder again (owner 2026-11-12) · owner 2026-11-07: folders that belong together are one folder with tabs; the Vault lives inside the Git folder (it was folded the other way and Git "was gone")
export const foldGroup = (k, have = null) => { const home = FOLD_INTO[k] || k; const kids = Object.keys(FOLD_INTO).filter(x => FOLD_INTO[x] === home && (!have || have.includes(x))); return kids.length && (!have || have.includes(home)) ? [home, ...kids] : null; };
const ICONS = [['vault', '📁', 'Vault'], ['pow', '⛏', 'PoW'], ['pop', '📉', 'PoP'], ['bids', '🎲', 'Bids'], ['poc', '📣', 'PoC'], ['postatic', '💻', 'PoStatic'], ['poe', '📊', 'PoEco'], ['proofs', '🏆', 'Proofs'], ['tests', '🧪', 'Test bench'], ['debate', '⚔', 'Debate'], ['watch', '📺', 'Watch'], ['print', '🧬', 'Proofprint'], ['boost', '🪙', 'Boosts'], ['features', '✨', 'Features'], ['character', '🎭', 'Character'], ['manual', '📖', 'Manual'], ['terms', '🛡', 'Terms & security'], ['jobs', '🗂', 'Jobs'], ['engines', '📡', 'Engines'], ['command', '🛰', 'Live ops'], ['db', '🗄', 'Database'], ['browser', '🧭', 'Browser'], ['sources', '🌐', 'Sources'], ['honey', '💎', 'The Collective'], ['wallet', '👛', 'Wallet'], ['mail', '📧', 'Mail'], ['github', '🗃', 'GitHub'], ['cmds', '⌘', 'Commands'], ['deskset', '⚙', 'Desktop settings']];
// 🧱 what each thin folder shows on its wall. Real counts from its state only; a tile with no action is just a number.
const won = rows => rows.filter(f => Number(f.roePct ?? f.net) > 0 || f.graded === 'right').length; const lost = rows => rows.filter(f => Number(f.roePct ?? f.net) < 0 || f.graded === 'wrong').length;
function wallFor(k, d, cat) {
  const pop = (d?.popFolders || []).filter(f => !f.noTrade); const pob = d?.pobFolders || []; const jobs = d?.jobs || []; const files = d?.storage?.files || []; const logins = d?.logins || []; const signed = d?.signedIn || []; const manuals = Object.keys(d?.siteManuals || {});
  const best = pop.length ? Math.max(...pop.map(f => Number(f.roePct) || 0)) : null; const shots = [...(d?.powFolders || []), ...pob].reduce((n, f) => n + (f.shots || []).length, 0); const rate = Object.values(d?.jobRates || {});
  switch (k) {
    case 'pop': return [{ ic: '📉', label: 'File a perp', value: pop.length, cmd: 'file a perp', tip: 'Paper proofs filed. Two small paid model calls for the next one' }, { ic: '✅', label: 'Won', value: won(pop), tone: 'up' }, { ic: '🛑', label: 'Lost', value: lost(pop), tone: 'dn' }, { ic: '🏅', label: 'Best, paper', value: best == null ? '—' : `${best > 0 ? '+' : ''}${best.toFixed(1)}%` }, { ic: '🪄', label: 'Next in the loop', value: `#${(d?.popFolders || []).length + 1}`, to: 'proofs', tip: 'It studies these before its next call' }];
    case 'bids': return [{ ic: '🎲', label: 'File a pob', value: pob.length, cmd: 'file a pob best NFL picks', tip: 'Proofs filed. Researches a topic with snapshots. Paid model calls, nothing staked' }, { ic: '✅', label: 'Right', value: won(pob), tone: 'up' }, { ic: '🛑', label: 'Wrong', value: lost(pob), tone: 'dn' }, { ic: '📸', label: 'Snapshots', value: pob.reduce((n, f) => n + (f.shots || []).length, 0), to: 'proofs' }, { ic: '🪄', label: 'Next in the loop', value: `#${pob.length + 1}`, to: 'proofs' }];
    case 'jobs': return [{ ic: '🗂', label: 'Jobs done', value: jobs.length }, { ic: '👍', label: 'Rated good', value: rate.filter(x => x === 'up').length, tone: 'up' }, { ic: '👎', label: 'Rated bad', value: rate.filter(x => x === 'down').length, tone: 'dn' }, { ic: '💬', label: 'Ask it something', value: 'Go', cmd: 'what can you do?' }];
    case 'sources': return [{ ic: '🔓', label: 'Signed-in sites', value: signed.length, to: 'vault' }, { ic: '📖', label: 'Sites scanned', value: manuals.length, to: 'pow', tip: 'Open a proof folder and scan a site' }, { ic: '📸', label: 'Snapshots kept', value: shots, to: 'proofs' }, { ic: '🛒', label: 'Site trades', value: (d?.siteTrades || []).length }];
    case 'mail': return [{ ic: '📧', label: 'Its email', value: d?.mailbox?.address ? 'Ready' : 'Not yet', tip: d?.mailbox?.address || 'Make it below' }, { ic: '🔐', label: 'Logins sealed', value: logins.length, to: 'vault' }, { ic: '🔓', label: 'Sites signed in', value: signed.length, to: 'vault' }];
    case 'cmds': return [{ ic: '⛏', label: 'file a PoW', value: 'PoW', cmd: 'file a PoW' }, { ic: '📉', label: 'file a perp', value: 'PoP', cmd: 'file a perp' }, { ic: '🎲', label: 'file a pob', value: 'PoB', cmd: 'file a pob best NFL picks' }, { ic: '🔎', label: 'watch a wallet', value: 'Watch', cmd: 'watch a wallet' }, { ic: '🧱', label: 'build a project', value: 'Build', cmd: 'build a project a tip calculator' }, { ic: '💸', label: 'top up pump', value: 'Top up', cmd: 'top up pump' }];
    default: return null;
  }
}
// 🧭 an icon nobody has moved takes the first free slot, a new column once the screen is full: a saved layout from before a new icon existed can never stack two on one spot
export const placeIcons = (saved, height, extra = []) => placeFor([...ICONS.map(x => x[0]), ...extra], saved, height);
// 🪟 a window opens beside the icons on a roomy screen, so none sits behind it; a dragged window stays where you put it
export function clearOfIcons(win, icons, width) {
  if (width < 900 || win.open) return {};
  return { x: Math.max(win.x, Math.min(300, Math.max(0, ...Object.values(icons).map(p => p.x)) + 112)) };
}
// 🖱 desktop icons you can drag anywhere (positions kept on this device); a tap without a drag opens it
// 📉 the PoP folder's face: drawn candles breathing under a light sweep; an open PoP adds its live paper return
const ICON_TIP = { watch: 'Watch room: up to 4 official players at once, on one screen', debate: 'Collective Debate: put a proof on the table, let agents grade it, chat with other owners and trade proofs', poe: 'Proof of Economy: your business books as a proof, with a receipt you can send', github: 'Keep its filed proofs in your own GitHub repo, private or public', poc: 'Proof of Content: every content folder and each idea it filed', postatic: 'Proof of Code: every page it built, each folder a new proof', browser: 'Sign up or sign in on any site with one-click email and codes, or send it off to browse', deskset: 'How this desktop looks: background color, animation, brightness', print: 'Its Proofprint: a ridge drawn from every proof it filed, with the best 2 snapshots of each. Only you see inside', boost: 'Its live count: what its sent proofs have earned, what is locked, and what its boost is doing', terms: 'How this agent is locked down, and the terms you run it under', proofs: 'Every proof it filed: results, the Proof Loop, and a timeline with the snapshots and decisions at the time', mail: 'Its own email: make it once, read its mail and codes', manual: 'How it all works: tutorial, trader vs general, PoW, PoP, fingerprints, limits, code map', vault: "Your agent's drawer — logins, sealed recovery files, signed-in sites, API keys", pow: 'Every Proof of Work its minds filed — the call, the vitals per site, how it graded',
  pop: 'Proof of Perps: both minds call a side and a paper trade runs on true prices', bids: 'Free chips on its live trades, and links to USA real-money sites', honey: 'Its colony vitals — honey, right calls, the next airdrop, the pool — and the ways into the Collective', files: 'Its storage — upload files and images for its tasks', wallet: 'Its own wallet — live SOL + USDC, and swap between them (nothing leaves it)', cmds: 'What it understands in the chat — tap one to put it in the chat box', sources: 'Every site its agents trust — what it is for, how it treated them, and Sign in to open it live in its window', db: 'Its private database: every closed proof, sealed with its own key; share a row with another of your agents or the Collective', engines: 'Every engine that runs on its own, live: the OSSY + G4 reviewer, kit freshness, shared reads, method kits and model routes', command: 'One live screen: what each of your agents is doing, which browser waits on you, who answered and what it cost this hour, review quality, fresh reads, the event river', jobs: 'Every request as its exact log tree — your words, each mind\'s plan and steps, the answer, your 👍 / 👎' };

// 🪙 the live count on the desktop itself: hidden until it has sent a proof, and to anyone but its owner (the server refuses them)
export function DeskCount({ d, onOpen, inline = false }) {
  const p = d?.pool;
  if (!p || p.empty || !(p.owedUsd || p.lockedUsd || p.vaultUsd)) return null;
  return <button type="button" className={`bst-chip${inline ? ' is-inline' : ''}`} onClick={onOpen} data-tip="What its sent proofs have earned, counting live, and how much of it came from its boost. Opens its Boosts folder" data-testid="bst-chip"><BoostCoin earning={!!p.ratePerSecUsd} /><LiveCount pool={p} readAt={d.readAt} testid="bst-chip-count" /><span className="bst-chip-boost"><small>⚡ BOOST</small><LiveCount pool={{ owedUsd: p.boostUsd, ratePerSecUsd: p.boostRateUsd }} readAt={d.readAt} testid="bst-chip-boost" /></span></button>;
}
export function DeskCountLive({ cat, onOpen }) {
  const d = useAgentPool(cat, work, 60000);
  return <DeskCount d={d} onOpen={onOpen} inline />;
}
const EARNS = new Set(['boost', 'print', 'pow', 'pop', 'bids', 'honey']);   // 🪙 the folders whose proofs can earn carry the coin
function DesktopClock() {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(t); }, []);
  return <time className="m-num">{new Date(now).toTimeString().slice(0, 5)}</time>;
}
function LiveDeskWin({ live, s, top, set, onTop, onClose, onReopen, actions }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNow(Date.now()); }, 1000); return () => clearInterval(t); }, []);
  const left = live.at ? Math.max(0, STEEL_MS - (now - live.at)) : null;
  return <DeskWin k="live" title={`🌐 ${live.title || `sign in to ${live.site || 'the site'} yourself`}`} s={s} top={top} set={set} onTop={onTop} onClose={onClose}
    tools={<>{left != null ? <em className={`dsk-left${left < 120000 ? ' is-hot' : ''}`} data-tip="A cloud window lives 15 minutes — save before it closes">{left ? `closes in ${mmss(left)}` : 'closed'}</em> : null}{actions}<a className="m-btn" href={live.live} target="_blank" rel="noopener noreferrer" data-tip="Open this live window in its own browser tab">↗ Tab</a></>}>
    {left === 0 ? <div className="dsk-gone" data-testid="dsk-gone"><b>This cloud window closed</b><span>It lives 15 minutes. Whatever you saved is kept; open it again to carry on.</span>{onReopen ? <button type="button" className="m-btn m-go" onClick={onReopen} data-testid="dsk-reopen">Open it again</button> : null}</div> : <iframe title={live.title || 'Live window'} src={live.live} referrerPolicy="no-referrer" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" allow="clipboard-read; clipboard-write" data-testid="cwb-pop-frame" />}
  </DeskWin>;
}
export const AGENT_COMMAND = 'feeless:agent-command';   // a folder's button puts words in this agent's chat box, wherever the desktop was opened from
export function AgentDesktop({ cat, live = null, onClose, onReopen, actions = null, onCommand: commandProp = null, start = null, extra: extraProp = [], mood = 'agent', glassOver = null }) {
  useEffect(() => { prefetchDeskWindows(); }, []);
  const onCommand = commandProp || (t => { window.dispatchEvent(new CustomEvent(AGENT_COMMAND, { detail: { id: cat?.id, text: t } })); onClose?.(); });
  const pageApps = React.useContext(DeskExtras); const walletTop = pageApps.find(a => a.k === 'wallet')?.body;
  const wallPrices = useProofPrices(cat.id, work);
  const pool = useAgentPool(cat, work, 60000); const [prefs, setPrefs] = useDeskPrefs(cat.id); const [proofStart, setProofStart] = useState({}); const browseSite = h => { setBrowseTo({ site: h, at: Date.now() }); openWin('browser'); };
  const [deskApps, setDeskApps] = useState([]); const [appOpen, setAppOpen] = useState(null);
  useEffect(() => { let on = true; Promise.resolve().then(() => work(cat.id, { op: 'desk_apps' })).then(j => on && setDeskApps(j?.apps || [])).catch(() => {}); return () => { on = false; }; }, [cat.id, work]);   // 📲 builds and games kept on the desktop
  const appTiles = deskApps.map(a => ({ k: `app-${a.ws}`, ic: '🎮', label: a.name, tip: `Opens ${a.name}, running`, ws: a.ws }));
  const extra = [...pageApps.filter(a => a.k !== 'wallet'), ...extraProp, ...appTiles]; const apps = [...ICONS, ...extra.map(a => [a.k, a.ic, a.label])];
  const [tour, setTour] = useState(() => !live && process.env.NODE_ENV !== 'test' && !tourSeen());
  useEffect(() => { const go = () => setTour(true); window.addEventListener('feeless:desk-tour', go); return () => window.removeEventListener('feeless:desk-tour', go); }, []);
  const [w, setW] = useState(() => ({ live: { open: !!live, min: false, max: false, x: 24, y: 12 }, vault: { open: false, min: false, max: false, x: 120, y: 60 },
    debate: { open: false, min: false, max: false, x: 150, y: 40 }, tests: { open: false, min: false, max: false, x: 150, y: 40 }, watch: { open: false, min: false, max: false, x: 130, y: 36 }, app: { open: false, min: false, max: false, x: 120, y: 30 },
    browser: { open: false, min: false, max: false, x: 145, y: 45 }, poc: { open: false, min: false, max: false, x: 140, y: 34 }, postatic: { open: false, min: false, max: false, x: 130, y: 26 }, pop: { open: false, min: false, max: false, x: 160, y: 50 }, bids: { open: false, min: false, max: false, x: 175, y: 60 }, proofs: { open: false, min: false, max: false, x: 150, y: 40 }, character: { open: false, min: false, max: false, x: 130, y: 30 }, features: { open: false, min: false, max: false, x: 110, y: 24 }, boost: { open: false, min: false, max: false, x: 120, y: 28 }, print: { open: false, min: false, max: false, x: 100, y: 20 }, github: { open: false, min: false, max: false, x: 170, y: 40 }, poe: { open: false, min: false, max: false, x: 155, y: 36 }, deskset: { open: false, min: false, max: false, x: 260, y: 70 }, terms: { open: false, min: false, max: false, x: 170, y: 48 }, manual: { open: false, min: false, max: false, x: 165, y: 45 }, pow: { open: false, min: false, max: false, x: 150, y: 40 }, honey: { open: false, min: false, max: false, x: 180, y: 70 }, files: { open: false, min: false, max: false, x: 210, y: 100 }, cmds: { open: false, min: false, max: false, x: 240, y: 60 }, wallet: { open: false, min: false, max: false, x: 190, y: 80 }, jobs: { open: false, min: false, max: false, x: 170, y: 50 }, engines: { open: false, min: false, max: false, x: 175, y: 54 }, command: { open: false, min: false, max: true, x: 120, y: 30 }, db: { open: false, min: false, max: false, x: 180, y: 58 }, sources: { open: false, min: false, max: false, x: 200, y: 40 }, perf: { open: false, min: false, max: false, x: 230, y: 50 }, mail: { open: false, min: false, max: false, x: 215, y: 70 }, ...Object.fromEntries(extra.map((a, i) => [a.k, { open: false, min: false, max: false, x: 150 + i * 18, y: 36 + i * 12 }])) }));
  const folded = k => !!FOLD_INTO[k] && apps.some(a => a[0] === FOLD_INTO[k]);   // a folder only hides inside another that is really on this desktop
  useDeskOverPage(); const { pos, moveIcon, fit: fitFolders, shown: shownApps } = useDeskIcons(cat.id, apps.filter(a => !folded(a[0])), prefs, { load: () => work(cat.id, { op: 'desk_layout' }), store: n => work(cat.id, { op: 'desk_layout', tools: { pos: n } }).catch(() => {}), onDrag: () => setPrefs({ autoFit: false }) });
  const [browseTo, setBrowseTo] = useState(null);
  const foldTabs = k => { const g = foldGroup(k, apps.map(a => a[0])); if (!g) return null; return <span className="m-seg dsk-fold-tabs" role="tablist" aria-label="In this folder">{g.map(x => { const row = apps.find(a => a[0] === x); return <button key={x} type="button" role="tab" aria-selected={x === k} className={x === k ? 'active' : ''} onClick={() => { if (x === k) return; if (x === 'vault' && !safeOk()) { setAsk(true); return; } set(x, { open: true, min: false, x: w[k]?.x, y: w[k]?.y, w: w[k]?.w, h: w[k]?.h }); set(k, { open: false }); setTop(x); }} data-testid={`fold-tab-${x}`}>{row?.[2] || x}</button>; })}</span>; };
  const openWin = k => { if (k.startsWith('app-')) { const ws = k.slice(4); setAppOpen({ ws, name: deskApps.find(a => a.ws === ws)?.name || 'App', preview: null }); set('app', { open: true, min: false }); work(cat.id, { op: 'desk_apps', job: 'open', to: ws }).then(j => setAppOpen(x => (x?.ws === ws ? { ...x, preview: j.preview || '' } : x))).catch(() => setAppOpen(x => (x?.ws === ws ? { ...x, preview: '' } : x))); setTop('app'); return; } if (k === 'vault') { openVault(); return; } set(k, { open: true, min: false, ...(prefs.winOpen === 'max' ? { max: true } : prefs.winOpen === 'center' && !w[k]?.open ? { x: Math.max(8, Math.round((window.innerWidth - 1180) / 2)), y: 24 } : clearOfIcons(w[k], pos, window.innerWidth)) }); setTop(k); };
  const [top, setTop] = useState('live'); const [tab, setTab] = useState('creds'); const [d, setD] = useState(null); const [ask, setAsk] = useState(false);
  const set = useCallback((k, p) => setW(x => deskSet(x, k, p)), []);
  const openVault = useCallback(() => { if (!safeOk()) { setAsk(true); return; } set('vault', { open: true, min: false }); setTop('vault'); }, [set]);
  useEffect(() => { let on = true; work(cat.id, { op: 'state' }).then(j => { if (on) setD(j); }).catch(() => {}); return () => { on = false; }; }, [cat.id]);
  useEffect(() => { if (start && typeof start === 'object') openProof(start); else if (start && start !== 'none') openWin(start); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  // 🎯 AGX-1: ⌘K / Ctrl+K opens the proof picker; a picked proof opens IN its desk window (focus = which file, `at` re-fires the same one)
  const [picker, setPicker] = useState(false); const [focus, setFocus] = useState(null);
  const openProof = useCallback(({ win, id }) => { setPicker(false); setFocus({ win, id, at: Date.now() }); openWin(win); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const k = e => { if ((e.metaKey || e.ctrlKey) && !e.altKey && String(e.key).toLowerCase() === 'k') { e.preventDefault(); setPicker(x => !x); } }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, []);
  useEffect(() => { const k = e => { if (e.key === 'Escape' && !ask && !tour && !picker) onClose(); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose, ask, tour, picker]);
  const pane = { creds: <Credentials cat={cat} rows={d?.logins} log={d?.vaultLog || []} onSaved={logins => setD(x => ({ ...x, logins }))} />,
    sealed: <SealedVault cat={cat} rows={d?.secrets} onSaved={secrets => setD(x => ({ ...x, secrets }))} />,
    sites: <SignedSites cat={cat} d={d} rows={d?.signedIn} nested onSaved={(signedIn, secrets) => setD(x => ({ ...x, signedIn, ...(secrets ? { secrets } : {}) }))} />,
    api: <ApiSlot cat={cat} /> }[tab];
  const tasks = [...(live ? [['live', '🌐', live.site || 'Live window']] : []), ...apps, ['perf', '📈', 'Performance']].filter(([k]) => w[k]?.open);
  const setupKit = { useShare: useColonyShare, caps: CAPS, renderSites: (pick, done) => <SignedSites cat={cat} d={d} rows={d?.signedIn} nested start={pick} onSaved={(signedIn, secrets) => { setD(x => ({ ...x, signedIn, ...(secrets ? { secrets } : {}) })); done?.(); }} /> };
  const setupLeft = Number(d?.setup?.left || 0);
  useEffect(() => { if (d?.setup) window.dispatchEvent(new CustomEvent('feeless:setup-left', { detail: { id: cat.id, left: d.setup.left } })); }, [cat.id, d?.setup]);
  const series = useMemo(() => perfSeries(d), [d]);
  const glass = useMemo(() => glassOf(series), [series]);
  const foregroundOpen = Object.values(w).some(x => x?.open && !x.min);
  const printLines = useMemo(() => linesOf(printOf(proofRows(d))), [d]);
  return createPortal(<IconLook.Provider value><PrintSeed.Provider value={pool?.printSeed || cat.id}><PrintLines.Provider value={printLines}><div className="dsk" data-folders={prefs.folderLook || 'classic'} role="dialog" aria-modal="true" aria-label="Your private desktop" data-testid="cwb-pop">
    {prefs.motion === 'off' ? null : <ShaderWall mood={prefs.wall || mood} frozen={prefs.motion === 'still' || foregroundOpen} style={{ filter: `brightness(${prefs.light / 100})` }} />}{prefs.title ? <div className="dsk-wall" aria-hidden="true"><b>{cat.name || 'FEELESS'}</b><small>private desktop · only you see this</small></div> : null}
    {pool && prefs.print ? <DeskPrint d={d} seed={pool.printSeed || cat.id} level={pool.printLevel} onOpen={() => openWin('print')} /> : null}
    <DeskCount d={pool} onOpen={() => openWin('boost')} />
    <nav className="dsk-icons" aria-label="Desktop" data-size={prefs.iconSize} data-labels={prefs.iconLabels ? undefined : 'off'}><DeskGrid />
      {shownApps.filter(([k]) => !folded(k)).map(([k, ic, l]) => <DeskIcon key={k} k={k} ic={ic} label={l} at={pos[k]} onMove={moveIcon} onOpen={openWin} tip={ICON_TIP[k] || extra.find(a => a.k === k)?.tip} earn={EARNS.has(k)} earning={!!pool?.pool?.ratePerSecUsd} badge={k === 'manual' && setupLeft > 0 ? { lit: true, text: `${setupLeft}` } : k === 'pop' && d?.popFolder ? { up: d.popFolder.roePct >= 0, text: `${d.popFolder.roePct >= 0 ? '+' : ''}${Number(d.popFolder.roePct || 0).toFixed(1)}%` } : null} />)}
      {live ? <button type="button" className="dsk-ico" style={{ transform: `translate(96px, 0px)` }} onClick={() => { set('live', { open: true, min: false }); setTop('live'); }} data-tip="The live window" data-testid="dsk-live-ico">
        <svg viewBox="0 0 48 40" aria-hidden="true"><rect x="3" y="4" width="42" height="32" rx="4" fill="#0d1a13" stroke="#b48cff" strokeWidth="2" /><rect x="3" y="4" width="42" height="7" rx="3" fill="#9b6bff" /><circle cx="24" cy="24" r="7" fill="none" stroke="#b48cff" strokeWidth="2" /><path d="M17 24h14M24 17c3 3 3 11 0 14M24 17c-3 3-3 11 0 14" stroke="#b48cff" strokeWidth="1.4" fill="none" /></svg><span>{live.site || 'Live window'}</span></button> : null}
    </nav>
    {prefs.widgets !== false && !live ? <DeskWidgets d={d} pool={pool} openWin={openWin} cat={cat} work={work} has={apps.map(a => a[0])} /> : null}
    {prefs.glass ? <PerfGlass {...(glassOver || glass)} onOpen={() => { set('perf', { open: true, min: false }); setTop('perf'); }} /> : null}
    {live && w.live.open && !w.live.min ? <LiveDeskWin live={live} s={w.live} top={top === 'live'} set={set} onTop={() => setTop('live')} onClose={onClose} onReopen={onReopen} actions={actions} /> : null}
    {appOpen && w.app?.open && !w.app.min ? <DeskWin k="app" title={`🎮 ${appOpen.name}`} s={w.app} top={top === 'app'} set={set} onTop={() => setTop('app')} onClose={() => set('app', { open: false })}>{appOpen.preview ? <iframe className="dsk-app" title={appOpen.name} sandbox="allow-scripts" srcDoc={appOpen.preview} referrerPolicy="no-referrer" data-testid="dsk-app" /> : <p className="dsk-app-none" data-testid="dsk-app-wait">{appOpen.preview === '' ? 'This build has no page yet.' : 'Opening…'}</p>}</DeskWin> : null}
    <ProofAlerts d={d} />
    {w.vault.open && !w.vault.min ? <DeskWin k="vault" title={`📁 Vault — ${cat.name || 'your agent'}`} s={w.vault} top={top === 'vault'} set={set} onTop={() => setTop('vault')} onClose={() => set('vault', { open: false })}>
      <div className="dsk-explorer"><aside className="dsk-side" aria-label="Vault folders">{VAULT_TABS.map(([k, ic, l, n]) => <button key={k} type="button" className={tab === k ? 'active' : ''} aria-pressed={tab === k} onClick={() => setTab(k)} data-testid={`dsk-tab-${k}`}>
        <Ic3 e={ic} size="20px" /><span>{l}</span>{n(d) != null ? <b className="m-num">{n(d)}</b> : null}</button>)}</aside>
        <div className="dsk-pane"><p className="dsk-path">Vault <i>›</i> {VAULT_TABS.find(t => t[0] === tab)[2]}</p><div key={tab} className="dsk-pull">{pane}</div></div></div>
    </DeskWin> : null}
    {w.browser.open && !w.browser.min ? <BrowserWin cat={cat} d={d} setD={setD} onCommand={onCommand} start={browseTo} s={w.browser} top={top === 'browser'} set={set} onTop={() => setTop('browser')} onClose={() => set('browser', { open: false })} tools={foldTabs('browser')} /> : null}
    {[['tests', '🧪 Test bench', <TestBench catId={cat.id} work={work} />], ['pow', `⛏ PoW — ${cat.name || 'your agent'}`, <div className="prf"><ProofHead kind="pow" folders={d?.powFolders} d={d} cat={cat} pool={pool} work={work} onBrowse={browseSite} /><div className="prf-main"><PowExplorer cat={cat} d={d} setD={setD} focus={focus?.win === 'pow' ? focus : null} /></div><ProofRail kind="pow" folders={d?.powFolders} onCommand={onCommand} /></div>], ['pop', '📉 Proof of Perps', <div className="prf"><ProofHead kind="pop" folders={d?.popFolders} d={d} cat={cat} pool={pool} work={work} onBrowse={browseSite} /><div className="prf-main"><PopApp cat={cat} d={d} setD={setD} focus={focus?.win === 'pop' ? focus : null} /></div><ProofRail kind="pop" folders={d?.popFolders} onCommand={onCommand} /></div>], ['bids', '🎲 Bids', <div className="prf prf-bids"><ProofHead kind="pob" folders={d?.pobFolders} d={d} cat={cat} pool={pool} work={work} onBrowse={browseSite} /><div className="prf-main"><ProofTools kind="bids" onBrowse={browseSite} onCommand={onCommand} loadCalls={gid => work(cat.id, { op: 'game_calls', job: gid })} /><BidsApp cat={cat} d={d} setD={setD} focus={focus?.win === 'bids' ? focus : null} /></div><aside className="prf-rail"><ProofKit kind="pob" folders={d?.pobFolders} onCommand={onCommand} /></aside></div>], ['proofs', '🏆 Proofs', <ProofsFolder cat={cat} d={d} work={work} onOpenFolder={k => { set(k, { open: true, min: false }); setTop(k); }} />], ['github', '🗃 GitHub', <GitFolder cat={cat} work={work} scope={cat.id === 'leader' ? 'collective' : ''} />], ['poe', '📊 PoEco', <EcoFolder cat={cat} d={d} setD={setD} work={work} pool={pool} onCommand={onCommand} onBrowse={browseSite} focus={focus?.win === 'poe' ? focus : null} />], ['debate', '⚔ Collective Debate', <DebateFolder cat={cat} d={d} work={work} />], ['watch', '📺 Watch room', <WatchWall onBrowse={browseSite} onCommand={onCommand} price={priceWord(wallPrices?.pob)} />], ['deskset', '⚙ Desktop settings', <DeskSettings apps={apps} onFit={fitFolders} prefs={prefs} set={setPrefs} mood={mood} />], ['boost', '🪙 Boosts', <BoostLazy cat={cat} work={work} />], ['print', '🧬 Proofprint', <PrintLazy cat={cat} d={d} pool={pool} />], ['features', '✨ Features', <FeaturesLazy cat={cat} d={d} work={work} onCommand={onCommand} onOpenIn={(k, folder, draft) => { setProofStart(x => ({ ...x, [k]: { folder, draft, at: Date.now() } })); openWin(k); }} onBrowse={h => { setBrowseTo({ site: h, at: Date.now() }); openWin('browser'); }} />], ['character', '🎭 Character', <CharacterLazy cat={{ ...cat, ...(d?.face ? { face: d.face } : null) }} work={work} setD={setD} d={d} />], ['manual', '📖 Manual', <AgentManual d={d} cat={cat} setD={setD} work={work} onCommand={onCommand} onOpen={openWin} kit={setupKit} />], ['terms', '🛡 Terms & security', <TermsFolder cat={cat} d={d} setD={setD} work={work} />], ['honey', '💎 The Collective', <div className="cll-inwin"><CollectiveLandingLazy more={<HoneyPot cat={cat} pool={pool} d={d} />} moreLabel="Its pot" /></div>], ['postatic', '💻 PoStatic', <ProofDeskLazy kind="build" cat={cat} d={d} work={work} onCommand={onCommand} start={proofStart.postatic} onBrowse={browseSite} pool={pool} d={d} setD={setD} focus={focus?.win === 'postatic' ? focus : null} />], ['poc', '📣 PoC', <ProofDeskLazy kind="content" cat={cat} d={d} work={work} onCommand={onCommand} onOpenIn={(k, folder, draft) => { setProofStart(x => ({ ...x, [k]: { folder, draft, at: Date.now() } })); openWin(k); }} start={proofStart.poc} onBrowse={browseSite} pool={pool} d={d} setD={setD} focus={focus?.win === 'poc' ? focus : null} />], ['wallet', '👛 Wallet', <div className="dsk-walstack"><WalletApp cat={cat} onBrowse={browseSite} />{walletTop}</div>], ['cmds', '⌘ Commands', <CommandList rows={d?.commands} onPick={onCommand} />], ['jobs', '🗂 Jobs', <JobsFolder d={d} />], ['engines', '📡 Engines', <EngineFolder cat={cat} work={work} />], ['command', '🛰 Live ops', <CommandCenter cat={cat} work={work} />], ['db', '🗄 Database', <DatabaseFolder cat={cat} work={work} />], ['sources', '🌐 Sources', <SourcesFolder cat={cat} d={d} setD={setD} />], ['perf', '📈 Performance', <PerfDiagram series={series} />], ['mail', '📧 Mail', <MailApp cat={cat} d={d} setD={setD} work={work} />], ...extra.map(a => [a.k, `${a.ic} ${a.label}`, a.body])].map(([k, t, body]) =>
      w[k].open && (!w[k].min || KEEP_MIN.has(k)) ? <DeskWin key={k} k={k} title={t} s={w[k]} hid={!!w[k].min} top={top === k} set={set} onTop={() => setTop(k)} onClose={() => set(k, { open: false })} tools={foldTabs(k)}>{wallFor(k, d, cat) ? <VitalsWall tiles={wallFor(k, d, cat)} onCommand={onCommand} onOpen={openWin}>{body}</VitalsWall> : body}</DeskWin> : null)}
    <footer className="dsk-bar"><span className="dsk-start"><i aria-hidden="true" />FEELESS</span>
      {tasks.map(([k, ic, l]) => <button key={k} type="button" className={`dsk-task${!w[k].min && top === k ? ' is-on' : ''}`} onClick={() => { if (w[k].min || top !== k) { set(k, { min: false }); setTop(k); } else set(k, { min: true }); }} data-testid={`dsk-task-${k}`}><Ic3 e={ic} /> {l}</button>)}
      <button type="button" className="m-btn dsk-pick" onClick={() => setPicker(true)} data-tip="Pick any proof it filed and open it here (⌘K)" data-testid="dsk-pick"><Ic3 e="🎯" /> Proofs <kbd>⌘K</kbd></button>
      <DeskBell catId={cat.id} onOpen={r => { const k = { PoW: 'pow', PoP: 'pop', PoB: 'bids', PoC: 'poc', PoStatic: 'postatic', PoEco: 'poe' }[r.kind]; if (!k || !w[k]) return; if (r.id) openProof({ win: k, id: r.id }); else { set(k, { open: true, min: false }); setTop(k); } }} />
      <DesktopClock />
      <button type="button" className="m-btn dsk-exit" onClick={onClose} data-tip="Back to the agent desk (Esc)" data-testid="cwb-pop-close">Exit desktop</button></footer>
    {picker ? <ProofPicker d={d} weights={pool?.weights} onPick={openProof} onClose={() => setPicker(false)} /> : null}
    {tour ? <DeskTour onDone={() => setTour(false)} /> : null}
    {ask ? <SafeGate label="The Vault" onYes={() => { setAsk(false); set('vault', { open: true, min: false }); setTop('vault'); }} onNo={() => setAsk(false)} /> : null}
  </div></PrintLines.Provider></PrintSeed.Provider></IconLook.Provider>, document.body);
}

// 🗄 A TRADER'S FILE CABINET (owner 2026-10-31: "trader agents need sign-in etc in their drawer" — they research X / CoinGecko too): the same
// Credentials + signed-in sites + API keys drawers a general agent has, over its log. Owner only (CatDesk passes canEdit).
export function TraderCabinet({ cat, items }) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; work(cat.id, { op: 'state' }).then(j => { if (on) setD(j); }).catch(() => {}); return () => { on = false; }; }, [cat.id]);
  useEffect(() => { if (d?.setup) window.dispatchEvent(new CustomEvent('feeless:setup-left', { detail: { id: cat.id, left: d.setup.left } })); }, [cat.id, d?.setup]);
  return <AgentLog title="ITS FILE CABINET" items={items} cabinet={keyDrawers(cat, d, setD)} />;   // the desk's DESKTOP tab opens the desktop: one door
}
// 🔐 + 🔑 the key drawers every agent's cabinet shares (general + trader): sealed logins, signed-in sites, API keys
function keyDrawers(cat, d, setD, ask = null) {
  return [['creds', '🔐', 'Credentials', (d?.logins || []).length + (d?.signedIn || []).length + (d?.secrets || []).length, <><Credentials cat={cat} rows={d?.logins} log={d?.vaultLog || []} ask={ask} onSaved={logins => setD(x => ({ ...x, logins }))} />
      <SealedVault cat={cat} rows={d?.secrets} onSaved={secrets => setD(x => ({ ...x, secrets }))} />
      <SignedSites cat={cat} d={d} rows={d?.signedIn} onSaved={(signedIn, secrets) => setD(x => ({ ...x, signedIn, ...(secrets ? { secrets } : {}) }))} /></>, { guard: true }],
    ['api', '🔑', 'API keys', (cat?.apiDrawer || []).filter(r => r.saved).length, <ApiSlot cat={cat} />]];
}

// 🔏 SEALED (owner 2026-10-31: "a recovery phrase I download — where does it go? keep it in the agent's drawer, or I paste it and nobody ever sees
// it"): a file you download in a window you used lands here by itself (sealed, then deleted from the cloud browser); paste a phrase to seal it.
// The list shows labels only; Open = a fresh wallet signature — a note shows 15 s, a file downloads straight to YOUR device.
const kb = n => (n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : n >= 1024 ? `${Math.round(n / 1024)} KB` : `${n} chars`);
function SealedVault({ cat, rows = [], onSaved }) {
  const { signMessage } = useWallet() || {}; const [shown, setShown] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState('');
  useEffect(() => { if (!shown) return undefined; const t = setTimeout(() => setShown(null), 15000); return () => clearTimeout(t); }, [shown]);
  const open = async r => { if (shown?.id === r.id) { setShown(null); return; } setErr(''); setBusy(r.id);
    try { const ts = Math.floor(Date.now() / 1000); const sig = await signMessage(revealMessage(cat.id, r.id, ts)); const j = await work(cat.id, { op: 'unseal', text: r.id, ts, sig });
      if (j.kind === 'file') { const bin = Uint8Array.from(atob(j.b64), c => c.charCodeAt(0)); const url = URL.createObjectURL(new Blob([bin]));
        const a = document.createElement('a'); a.href = url; a.download = j.name || 'sealed-file'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 2000); }
      else setShown({ id: r.id, text: j.text }); } catch (e) { setErr(e.message || 'Not opened'); } finally { setBusy(''); } };
  const drop = async r => { try { onSaved?.((await work(cat.id, { op: 'drop_secret', text: r.id })).secrets); } catch (e) { setErr(e.message); } };
  const seal = async e => { e.preventDefault(); const form = e.currentTarget; const f = new FormData(form); setErr(''); setBusy('seal');
    try { onSaved?.((await work(cat.id, { op: 'seal', job: String(f.get('l') || ''), text: String(f.get('s') || ''), secret: String(f.get('n') || '') })).secrets); form.reset(); } catch (er) { setErr(er.message); } finally { setBusy(''); } };
  return <section className="cwb-signed cwb-sealed" data-testid="cwb-sealed"><b className="cwb-signed-h"><Ic3 e="🔏" /> SEALED <em className="m-num">{rows.length}</em></b>
    <small>Recovery phrases + files. A file you download in a window you used lands here by itself — sealed, and deleted from the cloud browser.</small>
    {rows.length ? <ul>{rows.map(r => <li key={r.id} data-testid={`cwb-secret-${r.id}`}><span><b>{r.kind === 'file' ? '📄' : '📝'} {r.label}</b><small>{kb(r.size || 0)} · {ago(r.at)} ago · sealed</small>
      {shown?.id === r.id ? <code className="cwb-sealed-open" data-testid="cwb-secret-text">{shown.text}</code> : null}</span>
      <span className="cwb-cred-acts"><button type="button" className="m-btn" disabled={busy === r.id} onClick={() => open(r)} data-tip={r.kind === 'file' ? 'Sign once with your wallet — it downloads to THIS device' : shown?.id === r.id ? 'Hide it now (it hides itself in 15 s)' : 'Sign once with your wallet to show it for 15 s'} data-testid={`cwb-secret-open-${r.id}`}>{busy === r.id ? '…' : r.kind === 'file' ? '⬇ Download' : shown?.id === r.id ? 'Hide' : '👁 Open'}</button>
        <button type="button" className="m-btn cwb-cred-x" onClick={() => drop(r)} aria-label={`Delete ${r.label}`} data-tip="Delete it for good">✕</button></span></li>)}</ul> : null}
    <form className="cwb-signed-add cwb-sealed-add" onSubmit={seal} autoComplete="off" data-testid="cwb-seal-add">
      <span className="cwb-sealed-row"><input className="m-input" name="l" placeholder="label, e.g. Proton recovery phrase" aria-label="Label" required maxLength={80} />
        <input className="m-input" name="s" placeholder="site (optional)" aria-label="Site" maxLength={80} /></span>
      <textarea className="m-input cwb-sealed-note" name="n" rows={2} placeholder="paste it here — hidden as you type, sealed on Save" aria-label="Secret to seal" required maxLength={8000} spellCheck={false} autoComplete="off" data-testid="cwb-seal-text" />
      <button type="submit" className="m-btn m-go" disabled={busy === 'seal'} data-testid="cwb-seal-save">{busy === 'seal' ? 'Sealing…' : '🔏 Seal it'}</button></form>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
  </section>;
}

// 🔓 SIGNED-IN SITES (owner 2026-10-31): a site that blocks bots, or your agent's own email — open it here, sign in yourself in the live window,
// Save: its windows start signed in from then on (cookies sealed on the server, never sent to a page). A site that re-checks asks you again.
const SIGNIN_PICKS = [['proton.me', '📧 Proton Mail'], ['accounts.google.com', '📧 Google'], ['github.com', '🐙 GitHub'], ['dexscreener.com', '📈 DexScreener'],
  ['coingecko.com', '🦎 CoinGecko'], ['solscan.io', '🔎 Solscan'], ['pump.fun', '💊 Pump'], ['tradingview.com', '📊 TradingView']];
// 👥 SOCIAL PROFILES (owner 2026-11-11 "social media profile icons so users can sign in to multiple"): one tile per network, ✓ when this agent's
// windows are signed in there. One account per network per agent — a second account = sign another agent in. (X's own API sign-in waits on
// the owner's X app key, so it is not offered here.)
const SOCIALS = [['x.com', '𝕏', 'X'], ['instagram.com', '◎', 'Instagram'], ['tiktok.com', '♪', 'TikTok'], ['youtube.com', '▶', 'YouTube'], ['facebook.com', 'f', 'Facebook'],
  ['linkedin.com', 'in', 'LinkedIn'], ['reddit.com', '👽', 'Reddit'], ['discord.com', '💬', 'Discord'], ['web.telegram.org', '✈', 'Telegram'], ['threads.net', '@', 'Threads']];
const onSite = (rows, host) => rows.some(r => { const s_ = String(r.site || ''); return host === s_ || host.endsWith(`.${s_}`) || s_.endsWith(`.${host}`); });
export function SignedSites({ cat, d = null, rows = [], onSaved, nested = false, start = null }) {
  const [site, setSite] = useState(''); const [live, setLive] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [big, setBig] = useState(true);
  useEffect(() => { if (start) run('signin_open', start); }, [start]);   // eslint-disable-line react-hooks/exhaustive-deps
  const run = async (op, text) => { setBusy(op); setErr('');
    try { const j = await work(cat.id, { op, text }); if (op === 'signin_open') { setLive({ ...j, at: Date.now() }); setBig(!nested); } else { setLive(null); onSaved?.(j.signedIn || [], j.secrets); } } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  return <section className="cwb-signed" data-testid="cwb-signed"><b className="cwb-signed-h"><Ic3 e="🔓" /> SIGNED-IN SITES <em className="m-num">{rows.length}</em></b>
    <small>Blocked by a bot check, or your agent's own email? Sign in once here — its windows open signed in.</small>
    {rows.length ? <ul>{rows.map(r => <li key={r.site}><span><b>{r.site}</b><small data-tip="Only this site's own, newest, unexpired cookies are kept — trackers, other sites and stale logins are cut on every save and every load, then sealed with this agent's key">{ago(r.at)} ago · {r.n} cookies{r.dropped ? ` · ${r.dropped} cleaned out` : ''} · sealed</small></span>
      <button type="button" className="m-btn" disabled={!!busy} onClick={() => run('signin_drop', r.site)} data-tip={`Sign its windows out of ${r.site}`} data-testid={`cwb-signed-drop-${r.site}`}>Sign out</button></li>)}</ul> : null}
    {live ? <div className="cwb-signed-live"><span><em>LIVE · sign in to {live.site} yourself</em><button type="button" className="m-btn" onClick={() => setBig(true)} data-tip="Open the sign-in window big" data-testid="cwb-signed-big">⤢ Big</button>
      <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => run('signin_save')} data-testid="cwb-signed-save">{busy === 'signin_save' ? 'Saving…' : '✓ Signed in — save'}</button></span>
      {big ? <AgentDesktop cat={cat} live={live} onClose={() => setBig(false)} onReopen={() => run('signin_open', live.site)}
        actions={<button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => run('signin_save')} data-tip="Keep this sign-in for its windows (and seal anything you downloaded)" data-testid="cwb-pop-save">{busy === 'signin_save' ? 'Saving…' : '✓ Signed in — save'}</button>} />
        : <SignInFrame live={live} cat={cat} work={work} d={d} />}</div>
      : <><div className="cwb-social" role="group" aria-label="Social profiles" data-testid="cwb-social">{SOCIALS.map(([h, ic, n], i) => { const on = onSite(rows, h); return <button key={h} type="button" className={`cwb-soc${on ? ' is-on' : ''}`} style={{ '--i': i }} disabled={!!busy} onClick={() => run('signin_open', h)} data-tip={on ? `Signed in to ${n} — tap to open it again (to switch account, sign out first)` : `Sign this agent in to ${n}: a live window opens, you sign in yourself, then Save`} data-testid={`cwb-soc-${n.toLowerCase()}`}><i aria-hidden="true">{ic}</i><b>{n}</b><small>{on ? '✓ signed in' : 'Sign in'}</small></button>; })}</div>
      <form className="cwb-signed-add" onSubmit={e => { e.preventDefault(); if (site.trim()) run('signin_open', site.trim()); }}>
        <span className="m-seg">{SIGNIN_PICKS.map(([h, l]) => <button key={h} type="button" className={site === h ? 'active' : ''} onClick={() => setSite(h)} data-tip={`Sign its windows in to ${h}`}>{l}</button>)}</span>
        <input className="m-input" value={site} onChange={e => setSite(e.target.value)} placeholder="any site, e.g. x.com" aria-label="Site to sign in to" data-testid="cwb-signed-site" />
        <button type="submit" className="m-btn m-go" disabled={!site.trim() || !!busy} data-testid="cwb-signed-open">{busy === 'signin_open' ? 'Opening…' : 'Open + sign in'}</button></form></>}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
  </section>;
}
// 🧭 THE BROWSER (owner 2026-11-05): a real window, with a tools box attached to its outside that sticks to either side. Everything needed while signing up or browsing stays in view: one-click email and codes, saving the sign-in, the safety list on a money site, and sending it off to browse.
const BROWSE_MINS = [1, 2, 5];
const MONEY_SITE = /(pump\.fun|axiom|photon|bullx|polymarket|kalshi|stake\.|hyperliquid|coinbase|binance|kraken|robinhood|draftkings|fanduel|betmgm|caesars|fanatics|underdog|prizepicks|novig|sporttrade|crypto\.com|bybit|okx|drift\.|jup\.ag)/i;
const MONEY_CHECK = [['mail', 'It has its own email here, not yours', 'A separate email keeps your main accounts out of it'], ['twofa', 'Two-step login is on, if the site offers it', 'Turn it on in the site\'s own security settings'], ['small', 'Only a small amount is on this account', 'Treat it as money the agent could lose. Top up in small steps'], ['out', 'You know how money comes back out', 'Read the site\'s withdrawal page before you deposit']];
export function BrowserWin({ cat, d, setD, onCommand, s, top, set, onTop, onClose, start = null, tools }) {
  const [addr, setAddr] = useState(''); const [live, setLive] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [saved, setSaved] = useState('');
  const [side, setSide] = useState(() => { try { return localStorage.getItem('feeless.browser.dock') === 'left' ? 'left' : 'right'; } catch { return 'right'; } });
  const [job, setJob] = useState(''); const [mins, setMins] = useState(2); const [code, setCode] = useState(null); const [note, setNote] = useState(''); const [ticks, setTicks] = useState({}); const [fold, setFold] = useState(false);
  const box = d?.mailbox?.address; const signed = d?.signedIn || []; const site = live?.site || addr.trim().replace(/^https?:\/\//, '').split('/')[0]; const money = MONEY_SITE.test(site);
  const readMail = useCallback(async () => { try { const j = await work(cat.id, { op: 'mail_read' }); setCode((j.mail || []).find(m => m.code)?.code || ''); } catch { setCode(''); } }, [cat.id]);
  useEffect(() => { if (!box) return undefined; readMail(); const t = setInterval(() => { if (!document.hidden) readMail(); }, 30000); return () => clearInterval(t); }, [box, readMail]);
  const dockTo = n => { setSide(n); try { localStorage.setItem('feeless.browser.dock', n); } catch { /* private window */ } if (n === 'left' && s.x < 316) set('browser', { x: 316 }); };
  useEffect(() => { if (side === 'left' && s.x < 316) set('browser', { x: 316 }); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  const go = async host => { const h = String(host || '').trim(); if (!h) return; setBusy('open'); setErr(''); setSaved(''); setAddr(h); try { const j = await work(cat.id, { op: 'signin_open', text: h }); setLive(j); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  useEffect(() => { if (start?.site) go(start.site); }, [start?.at]);   // eslint-disable-line react-hooks/exhaustive-deps
  const save = async () => { setBusy('save'); setErr(''); try { const j = await work(cat.id, { op: 'signin_save' }); setD?.(x => ({ ...x, signedIn: j.signedIn || [], ...(j.secrets ? { secrets: j.secrets } : {}) })); setSaved(live?.site || ''); setLive(null); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  const drop = async host => { setBusy('drop'); setErr(''); try { const j = await work(cat.id, { op: 'signin_drop', text: host }); setD?.(x => ({ ...x, signedIn: j.signedIn || [] })); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  const make = async () => { setBusy('make'); setNote(''); try { const j = await work(cat.id, { op: 'mail_make' }); setD?.(x => ({ ...x, mailbox: j.mailbox, logins: j.logins ?? x?.logins })); } catch (e) { setNote(e.message); } finally { setBusy(''); } };
  const copy = async (v, word) => { try { await navigator.clipboard.writeText(String(v)); setNote(`${word} copied.`); } catch { setNote('Your browser blocked copying.'); } };
  const tool = (ic, h, body, testid) => <section className="bwr-t" data-testid={testid}><h5><Ic3 e={ic} size="16px" /> {h}</h5>{body}</section>;
  const dock = <aside className={`bwr-dock is-${side}${fold ? ' is-fold' : ''}`} aria-label="Browser tools" data-testid="bwr-dock" onPointerDown={e => e.stopPropagation()}>
    <header className="bwr-dock-h"><b>TOOLS</b><span className="m-seg" role="group" aria-label="Stick the tools box to a side">{[['left', '◧ Left'], ['right', 'Right ◨']].map(([k, l]) => <button key={k} type="button" aria-pressed={side === k} className={side === k ? 'active' : ''} onClick={() => dockTo(k)} data-tip={`Stick this box to the ${k} of the window`} data-testid={`bwr-dock-${k}`}>{l}</button>)}</span><button type="button" className="m-btn bwr-fold" aria-expanded={!fold} onClick={() => setFold(x => !x)} data-tip={fold ? 'Show the tools' : 'Hide the tools'} data-testid="bwr-fold">{fold ? 'Tools' : 'Hide'}</button></header>
    {fold ? null : <div className="bwr-dock-b">
      {tool('📧', 'ITS DETAILS', <><div className="bwr-id"><span><small>EMAIL</small><b data-testid="bwr-email">{box || 'None yet'}</b></span>{box ? <button type="button" className="m-btn" onClick={() => copy(box, 'Email')} data-tip="Copy its address" data-testid="bwr-email-copy">Copy</button> : <button type="button" className="m-btn m-go" disabled={!!busy} onClick={make} data-tip="Makes it a free mailbox of its own" data-testid="bwr-email-make">{busy === 'make' ? 'Making…' : 'Make it'}</button>}</div>
        <div className="bwr-id"><span><small>NEWEST CODE</small><b className="m-num" data-testid="bwr-code">{!box ? 'Needs its email' : code === null ? 'Reading…' : code || 'None yet'}</b></span>{code ? <button type="button" className="m-btn" onClick={() => copy(code, 'Code')} data-tip="Copy this code" data-testid="bwr-code-copy">Copy</button> : box ? <button type="button" className="m-btn" onClick={readMail} data-tip="Check its mail again" data-testid="bwr-code-read">Check</button> : null}</div>{note ? <small className="bwr-note" role="status">{note}</small> : null}</>, 'bwr-t-ids')}
      {live ? tool('⌨', 'FILL IN', <TypeBar cat={cat} work={work} d={d} />, 'bwr-t-fill') : null}
      {tool('🔓', 'KEEP THE SIGN-IN', <>{live ? <button type="button" className="m-btn m-go bwr-save" disabled={!!busy} onClick={save} data-tip="Keeps only this site's own, newest cookies, sealed for this agent. Its windows then open signed in" data-testid="bwr-save">{busy === 'save' ? 'Saving…' : `✓ Signed in, save ${live.site}`}</button> : <small className="bwr-hint">Open a site and sign in. Saving appears here.</small>}{saved ? <small className="bwr-note" role="status" data-testid="bwr-saved">✓ {saved} saved. Its windows open signed in, and you can sign it out here any time.</small> : null}</>, 'bwr-t-save')}
      {money ? tool('🛡', 'REAL MONEY SITE', <><p className="bwr-warn" data-testid="bwr-money">Never type a wallet seed phrase or your main bank login in this window.</p><ul className="bwr-check">{MONEY_CHECK.map(([k, l, t]) => <li key={k}><label data-tip={t}><input type="checkbox" checked={!!ticks[k]} onChange={e => setTicks(x => ({ ...x, [k]: e.target.checked }))} data-testid={`bwr-check-${k}`} /><span>{l}</span></label></li>)}</ul><small className="bwr-hint">{Object.values(ticks).filter(Boolean).length} of {MONEY_CHECK.length} done. This list is for you. Nothing is checked for you.</small></>, 'bwr-t-money') : null}
      {onCommand ? tool('🧭', 'SEND IT TO BROWSE', <form className="bwr-go" onSubmit={e => { e.preventDefault(); if (site) onCommand(`browse ${site} for ${mins} minute${mins === 1 ? '' : 's'}${job.trim() ? `: ${job.trim()}` : ''}`); }} data-testid="bwr-go"><input className="m-input" value={job} onChange={e => setJob(e.target.value)} placeholder="What should it do?" aria-label="What it should do there" data-testid="bwr-job" />
        <span className="m-seg" role="radiogroup" aria-label="How long">{BROWSE_MINS.map(n => <button key={n} type="button" role="radio" aria-checked={mins === n} className={mins === n ? 'active' : ''} onClick={() => setMins(n)} data-tip={`Browses for about ${n} minute${n === 1 ? '' : 's'}`} data-testid={`bwr-min-${n}`}>{n} min</button>)}</span>
        <button type="submit" className="m-btn m-go" disabled={!site} data-tip="Writes this into its chat box. You press send, and model calls cost as usual" data-testid="bwr-send">{site ? `Put ${site} in its chat` : 'Type a site first'}</button></form>, 'bwr-t-go') : null}
      {tool('💡', 'HOW IT WORKS', <ol className="bwr-steps"><li>Type a site above the window and press Go.</li><li>Sign up or sign in yourself, in the window. Use the buttons here for its email and codes.</li><li>Press save. Its windows open signed in from then on.</li></ol>, 'bwr-t-help')}
    </div>}
  </aside>;
  return <DeskWin k="browser" title="🧭 Browser" s={s} top={top} set={set} onTop={onTop} onClose={onClose} dock={dock} tools={tools}>
    <div className="bwr" data-testid="dsk-browser">
      <form className="bwr-bar" onSubmit={e => { e.preventDefault(); go(addr); }}><i aria-hidden="true">{live ? '●' : '○'}</i><input className="m-input" value={addr} onChange={e => setAddr(e.target.value)} placeholder="Type any site, e.g. pump.fun" aria-label="Site address" autoComplete="off" spellCheck="false" data-testid="bwr-addr" /><button type="submit" className="m-btn m-go" disabled={!addr.trim() || !!busy} data-tip="Opens it in a live window, just for you to use" data-testid="bwr-open">{busy === 'open' ? 'Opening…' : 'Go'}</button></form>
      {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
      {live ? <div className="bwr-view"><SignInView live={live} /></div> : <div className="bwr-home">
        <section><h5>SIGN UP OR SIGN IN</h5><div className="bwr-sites">{SIGNIN_PICKS.map(([h, l]) => <button key={h} type="button" disabled={!!busy} onClick={() => go(h)} data-tip={`Opens ${h}`} data-testid={`bwr-site-${h}`}><Ic3Text text={l} /></button>)}</div></section>
        <section><h5>SAVED SIGN-INS <em className="m-num">{signed.length}</em></h5>{signed.length ? <ul className="bwr-saved">{signed.map(r => <li key={r.site}><b>{r.site}</b><small>{ago(r.at)} ago · {r.n} cookies · sealed</small><button type="button" className="m-btn" disabled={!!busy} onClick={() => go(r.site)} data-tip={`Open ${r.site}`} data-testid={`bwr-reopen-${r.site}`}>Open</button><button type="button" className="m-btn" disabled={!!busy} onClick={() => drop(r.site)} data-tip={`Sign its windows out of ${r.site}`} data-testid={`bwr-drop-${r.site}`}>Sign out</button></li>)}</ul> : <p className="dsk-note">Nothing saved yet. Sign in to a site and press save.</p>}</section>
      </div>}
    </div>
  </DeskWin>;
}
const ago = t => { const s = Math.max(0, Date.now() / 1000 - (t || 0)); return s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };

// 🖼 its media drawer: what it saved for a campaign, a slide strip, cleaned after 7 days on its own
function MediaDrawer({ items }) {
  if (!items?.length) return null;
  return <section className="cwb-media" data-testid="cwb-media"><b><Ic3 e="🖼" /> MEDIA <small>{items.length} · cleaned after 7 days</small></b>
    <div className="cwb-media-strip">{items.map(m => <a key={m.url} href={m.url} target="_blank" rel="noopener noreferrer" data-tip={m.title || m.url}>
      {m.kind === 'video' ? <video src={m.url} muted loop playsInline preload="metadata" /> : <img src={m.url} alt={m.title || ''} loading="lazy" />}<small>{m.title || 'untitled'}</small></a>)}</div></section>;
}

// ☁ its own storage (owner 2026-10-31): the + beside the chat puts images / GIFs in the agent's storage (1 GB, cleaned 7 days after last use);
// the attached ones ride with the next ask — the agent reads their names and its live browser can upload one (e.g. a coin image on pump.fun)
const fileMb = n => (n >= 1024 ** 3 ? `${(n / 1024 ** 3).toFixed(1)} GB` : n >= 1024 ** 2 ? `${(n / 1024 ** 2).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
const readAsDataUrl = f => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = () => no(new Error('That file could not be read.')); r.readAsDataURL(f); });
export async function addFile(catId, file) {
  if (!/^image\/(png|jpeg|webp|gif)$/.test(file?.type || '')) throw new Error('Images only: PNG, JPEG, WebP or GIF.');
  if (file.size > (file.type === 'image/gif' ? 40 : 15) * 1024 * 1024) throw new Error(file.type === 'image/gif' ? 'GIFs up to 40 MB.' : 'Images up to 15 MB.');
  const r = await fetch(apiUrl(`/api/cats/${catId}/files`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), dataUrl: await readAsDataUrl(file), name: file.name }) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`);
  return j;
}
export function AttachChips({ files, store, onDrop }) {
  if (!files.length) return null;
  const pct = store ? Math.min(1, store.used / store.quota) : 0;
  return <div className="cwb-files" data-testid="cwb-files">{files.map((f, i) => <span key={f.id} className="cwb-file" style={{ '--i': i }} data-tip={`${f.name} · ${fileMb(f.size)} — goes with your next ask`}>
    <img src={apiUrl(f.url)} alt="" /><b>{f.name}</b><small className="m-num">{fileMb(f.size)}</small>
    <button type="button" onClick={() => onDrop(f.id)} aria-label={`Take ${f.name} off this ask`} data-tip="Take it off this ask (it stays in its storage until cleaned)" data-testid={`cwb-file-x-${f.id}`}>✕</button></span>)}
    {store ? <span className="cwb-store" data-tip={`Attachments: ${fileMb(store.used)} of ${fileMb(store.quota)} — they leave FEELESS 24 h after last use (☁ Keep one in your own cloud)`} data-testid="cwb-store">
      <em><Ic3 e="☁" /> STORAGE</em><u aria-hidden="true"><s style={{ transform: `scaleX(${pct})` }} /></u><small className="m-num">{fileMb(store.used)} / {fileMb(store.quota)}</small></span> : null}</div>;
}

function WorkbenchLive({ cat }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [text, setText] = useState(''); const [busy, setBusy] = useState(false); const [tick, setTick] = useState(0);
  useEffect(() => { const take = e => { if (e.detail?.id === cat?.id && e.detail?.text) setText(e.detail.text); }; window.addEventListener(AGENT_COMMAND, take); return () => window.removeEventListener(AGENT_COMMAND, take); }, [cat?.id]);
  const [files, setFiles] = useState([]); const [store, setStore] = useState(null); const [upping, setUpping] = useState(false); const pick = useRef(null);   // ☁ attached to the next ask
  const attach = async e => { const list = Array.from(e.target.files || []).slice(0, 4); e.target.value = ''; if (!list.length) return; setUpping(true); setErr('');
    try { for (const f of list) { const j = await addFile(cat.id, f); setFiles(x => [...x, j.file].slice(-4)); setStore({ used: j.used, quota: j.quota }); } } catch (er) { setErr(er.message); } finally { setUpping(false); } };
  const [signIn, setSignIn] = useState(null);   // 🔑 a window's sign-in card → the credentials drawer, this site filled in
  const [to, setTo] = useState('both');   // 🧠 talk to both minds, or ONE of them (it works the whole task in its own window)
  const [down, setDown] = useState(false);
  const verRef = useRef(null);   // ⚡ the filed PoW folders (~90 KB) come only when they changed (measured: 126 KB every 1.5 s was the lag)
  const load = useCallback(() => work(cat.id, { op: 'state', ver: verRef.current }).then(x => { if (x.powVer) verRef.current = x.powVer;
    setD(o => ({ ...x, powFolders: x.powFolders ?? o?.powFolders, powVer: x.powVer ?? o?.powVer, poi: x.poi ?? o?.poi, kernel: x.kernel ?? o?.kernel, popFolders: x.popFolders ?? o?.popFolders })); setErr(''); setDown(false); }).catch(e => { setErr(e.message); setDown(!!e.down); }), [cat.id]);
  const status = d?.task?.status;
  const live = !down && (LIVE_STATES.includes(status) || status === 'human' || !!d?.powFolder || (d?.windows || []).some(w => w.status === 'human' || w.status === 'working'));   // a running PoW folder is live too — its chat lines arrive every 1.5 s   // the service down = never a stale "Working"
  useEffect(() => { window.dispatchEvent(new CustomEvent('feeless:agent-live', { detail: { id: cat.id, live } })); }, [cat.id, live]);   // 💡 the lamp over its monitors
  useEffect(() => () => window.dispatchEvent(new CustomEvent('feeless:agent-live', { detail: { id: cat.id, live: false } })), [cat.id]);
  useEffect(() => { if (d?.setup) window.dispatchEvent(new CustomEvent('feeless:setup-left', { detail: { id: cat.id, left: d.setup.left } })); }, [cat.id, d?.setup]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) { load(); setTick(x => x + 1); } }, live ? 1500 : 8000); return () => clearInterval(t); }, [load, live]);
  const act = async (op, extra = {}) => { setBusy(true); setErr(''); try { const r = await work(cat.id, { op, ...extra }); setD(x => ({ ...x, ...r })); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const [aiCur, setAiCur] = useState(readCursor);
  const go = !!d?.go; const queue = d?.queue || [];   // 🏇 let it go (owner Q1): long tasks, asks queue up and run one after another until a human is needed
  const way = d?.workMode || 'plan';
  const send = e => { e?.preventDefault?.(); if (busy) return;
    const t = text.trim(); if (!t) return; setText(''); const ids = files.map(f => f.id); setFiles([]); toBottom(); act('ask', { text: t, to, ...(ids.length ? { files: ids } : {}) }); };
  const setWay = async k => { setBusy(true); try { await work(cat.id, { op: 'mode', job: k }); await load(); } catch (er) { setErr(er.message); } finally { setBusy(false); } };
  const brains_ = cat.brainsCfg?.brains || ['', ''];
  const wins = useMemo(() => {   // 🖥 both monitors always (owner 2026-11-01): each of its models in its own slot — one asked alone, the other shows its desktop
    const ws = d?.windows || []; if (!ws.length) return brains_.slice(0, 8).map((m, i) => ({ i, model: m, status: 'idle' }));
    if (ws.length !== 1 || brains_.length < 2) return ws;
    const at = Math.max(0, brains_.indexOf(ws[0].model)); const other = brains_.find((m, k) => k !== at && k < 2);
    const shown = [{ ...ws[0], slot: at }, { i: -1, slot: at ? 0 : 1, model: other, status: 'idle', bubble: '', steps: [] }];
    return at ? shown.reverse() : shown;
  }, [d?.windows, brains_.join('|')]);   // eslint-disable-line react-hooks/exhaustive-deps
  const credit = Number(d?.credit ?? cat.brainsCfg?.credit ?? 0); const cap = Number(d?.cap ?? 0.05); const spent = Number(d?.task?.cost || 0);
  const [chatLook, setChatLook] = useChatStyle(cat.id);
  const [gear, setGear] = useState(false); const log = useMemo(() => genLog(d), [d]); const [flip, setFlip] = useState(false); const [desk, setDesk] = useState(false); const [old, setOld] = useState(false);
  useEffect(() => { if (!gear && !flip) return undefined; const k = e => { if (e.key === 'Escape') { setGear(false); setFlip(false); } }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [gear, flip]);
  useEffect(() => { if (signIn) setFlip(true); }, [signIn]);   // a window asked for a login → the chat flips to the cabinet, on Credentials
  const msgs = useMemo(() => (d?.chat || []).slice(-24).filter(m => !(m.by !== 'you' && BUDGET_STOP.test(m.text))).reduce(squash, []), [d?.chat]);
  const lastYou = msgs.map(m => m.by).lastIndexOf('you'); const cut = lastYou > 0 ? lastYou : Math.max(0, msgs.length - 4);   // 🗂 this run up front; earlier runs fold away
  const doing = wins.find(w => w.status === 'working')?.bubble || (live ? 'working on it' : '');
  const proofs = useMemo(() => newestProofs(d), [d]);
  const liveKind = live ? proofOf(d, live) : null; const [peek, setPeek] = useState(false);   // 🎆 a running proof turns the chat into its live stage
  useEffect(() => { setPeek(false); }, [liveKind, d?.task?.id]);   // 🖥 an idle monitor shows its agent's newest proofs, never a blank page
  const dash = useRef(null); const chatRef = useRef(null); const inRef = useRef(null);
  const [unseen, toBottom] = useStickToBottom(chatRef, Number(msgs[msgs.length - 1]?.at || 0) + msgs.length + (live ? 1 : 0) + (old ? 100 : 0));   // 💬 follows the newest message; scrolled up → it waits and the ↓ arrow counts what arrived
  useEffect(() => { const el = inRef.current; if (!el) return; el.style.height = 'auto'; el.style.height = `${Math.min(el.scrollHeight, 168)}px`; }, [text]);   // ✍ the box grows as you type
  const chatSize = useChatSize();
  return <section ref={dash} className="cwb kd-card cwb-dash" data-testid="cat-workbench" {...chatSize.attrs}>
    <header className="cwb-head"><span><b><Ic3 e="🧠" />🧠 ITS MINDS</b><small>{(d?.providers || []).filter(x => x !== 'reader').length ? `browsers in the cloud · ${d.providers.join(' → ')}` : 'reading pages as text (no hosted browser key yet)'}</small></span>
      <button type="button" className={`cwb-go${go ? ' is-on' : ''}`} aria-pressed={go} disabled={busy} onClick={() => act('go', { on: !go })} data-testid="cwb-go"
        data-tip={go ? 'ON: up to 30 steps a window, asks queue and run back to back — it stops only when done, at the $ cap, or for a sign-in / CAPTCHA / card payment' : 'Let it go: it works long tasks on its own and takes queued asks one after another until a person is needed'}>
        <i aria-hidden="true" />🏇 LET IT GO <b>{go ? 'ON' : 'OFF'}</b></button>
      <button type="button" className="m-btn cwb-hbtn" onClick={() => setDesk(true)} data-tip="Your private desktop: work in its Vault, sign in to sites, keep recovery files — only you see it" data-testid="cwb-desk-open"><Ic3 e="🖥" /> Desktop<SetupDot id={cat.id} left={d?.setup?.left ?? null} /></button>
      <span className="cwb-meters">
        <span data-tip="Model credit left: every answer and browsing step is paid from it. Add more in its wallet panel"><em>CREDIT</em><b className="m-num">{usd(credit)}</b><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, credit / 10)})` }} /></u></span>
        <span data-tip="This task's spend against its cap — it stops at the cap with what it has"><em>THIS TASK</em><b className="m-num">{usd(spent)} / {usd(cap)}</b><u aria-hidden="true"><s className={spent >= cap * 0.8 ? 'is-hot' : ''} style={{ transform: `scaleX(${Math.min(1, spent / (cap || 1))})` }} /></u></span>
      </span></header>
    <NowLine cat={cat} wins={wins} live={live} folder={d?.powFolder} />
    <div className="cwb-stage agd-wins">{wins.map((w, n) => <Window key={`${w.i}-${w.slot ?? w.i}`} folder={d?.powFolder} d={d} w={w} proof={monitorProof(proofs, n, wins.length, wins.map(monitorIdle))} onProof={() => setDesk(true)} catId={cat.id} tick={tick} busy={busy} cursor={aiCur} onGo={(op, i, text) => act(op, { i, ...(text ? { text } : {}) })} onLogin={site => setSignIn({ site, at: Date.now() })} />)}</div>
    <DeskFlip cat={cat} size={chatSize} flip={flip} setFlip={setFlip} name={cat.name} live={live} count={log.length} cloud={<HeadCloud items={(d?.cloud || []).slice(-5).reverse()} />}
      left={<MindVitals cat={cat} model={wins[0]?.model} i={0} kind="general" live={!!wins[0]?.model} hot={wins[0]?.status === 'working'} extra={<><WinVitals w={wins[0]} f={d?.powFolder} i={0} model={cat.brainsCfg?.brains?.[0]} /><MindNow d={d} w={wins[0]} p={d?.pow?.['0']} /></>} />}
      right={<MindVitals cat={cat} model={wins[1]?.model || cat.brainsCfg?.brains?.[1]} i={1} kind="general" live={!!(wins[1]?.model || cat.brainsCfg?.brains?.[1])} hot={wins[1]?.status === 'working'}
        extra={<><WinVitals w={wins[1] || (cat.brainsCfg?.brains?.[1] ? { i: 1, status: 'not asked' } : undefined)} f={d?.powFolder} i={1} model={cat.brainsCfg?.brains?.[1]} />{cat.brainsCfg?.brains?.[1] || wins[1] ? <MindNow d={d} w={wins[1]} p={d?.pow?.['1']} /> : null}</>} />}   // its second model is still there when only A was asked
      back={<><LastMoney m={d?.lastMoney} />
    <AgentLog title="FILES" items={log} onDesktop={() => setDesk(true)} open={signIn ? { key: 'creds', at: signIn.at } : null} cabinet={[
      ...keyDrawers(cat, d, setD, signIn),
      ['made', '🎨', 'Creations', (d?.storage?.files || []).length, <Creations files={d?.storage?.files || []} chat={msgs} />],
      ['earn', '⚡', 'Earn', (d?.lastMoney ? 1 : 0), <EarnCard cat={cat} />],
      ['cmds', '⌘', 'Commands', (d?.commands || []).length, <CommandList rows={d?.commands} onPick={setText} />],
      ['treasury', '🏦', 'Treasury', 0, <TreasuryDrawer cat={cat} />],
      ['pass', '🎫', 'Agent Pass', cat?.pass?.asset ? 1 : 0, <PassDrawer cat={cat} />],
      ['notes', '🧠', 'Main cloud', (d?.cloud || []).length, <div className="cwb-cloud" data-testid="cwb-cloud">{(d?.cloud || []).slice(-6).reverse().map((c, i) => <span key={i} style={{ '--i': i }}>{c.text || `${c.word} $${c.sym}`}</span>)}</div>],
      ...((d?.media || []).length ? [['media', '🖼', 'Media', d.media.length, <MediaDrawer items={d.media} />]] : []),
      ...((d?.artifacts || []).length ? [['builds', '🛠', 'Builds', d.artifacts.length, <div className="cwb-builds">
      {(d?.artifacts || []).map((a, i) => <details className="cwb-artifact" key={i}><summary>{a.title} · {a.kind}</summary>{a.kind === 'build' ? <iframe title={a.title} sandbox="allow-scripts" referrerPolicy="no-referrer" srcDoc={'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src data:; connect-src \'none\'; form-action \'none\'; base-uri \'none\'">' + a.content} /> : <pre>{a.content}</pre>}</details>)}
      </div>]] : [])]} /></>}>
    {status === 'stopped' || status === 'error' || status === 'parked' ? <p className={`cwb-answer s-${status}`} data-testid="cwb-answer">{d.task.fast ? '⚡ from memory · ' : ''}{d.task.answer || d.task.why}</p> : null}
    {liveKind && !peek ? <ProofLive d={d} wins={wins} spent={spent} name={cat.name} kind={liveKind} onShowChat={() => setPeek(true)} />
    : <>{liveKind ? <button type="button" className="m-chip pl-back" onClick={() => setPeek(false)} data-tip="Back to the live stage of this proof" data-testid="proof-live-back">● Back to live</button> : null}
    {chatLook.style === 'agent' ? <AgentStage cat={cat} msgs={msgs} working={live} onChip={c => act('ask', { text: c, to })} /> : <ol ref={chatRef} className={`cwb-chat ${chatClass(chatLook)}`} aria-label="Chat with its models" aria-live="polite" data-testid="cwb-chat">
      {cut > 0 ? <li className="cwb-earlier"><button type="button" onClick={() => setOld(o => !o)} aria-expanded={old} data-testid="cwb-earlier">{old ? 'Hide earlier' : `Earlier · ${cut} message${cut === 1 ? '' : 's'}`}</button></li> : null}
      {(old ? msgs : msgs.slice(cut)).map((m, i, a) => <ChatMsg key={`${m.at || i}-${String(m.text).slice(0, 24)}`} m={m} job={m.tid ? (d?.jobs || []).find(j => j.id === m.tid) : null} name={cat.name} fresh={i === a.length - 1 && m.by !== 'you'} onOpen={k => setDesk(chatProof(d, k, m.at))} rate={d?.jobRates?.[m.tid]} onRate={(tid, k) => act('rate', { text: tid, job: k })} onChip={c => act('ask', { text: c, to })} />)}
      {live ? <li className="cwb-msg is-cats is-typing" data-testid="cwb-typing"><i className="cwb-av" aria-hidden="true"><Ic3 e="🧠" /></i><div><header><b>{cat.name || 'Its minds'}</b><em className="cwb-tag">working</em></header>
        <p><span className="cwb-dots" aria-hidden="true"><i /><i /><i /></span>{doing}</p></div></li> : null}
      {!msgs.length && !live ? <li className="cwb-empty" data-testid="cwb-empty"><b>What should it do?</b><span>Ask in plain words. It works in its own cloud browsers and reports back here.</span>
        <span className="cwb-sugg">{SUGGEST.map(t => <button key={t} type="button" onClick={() => setText(t)}>{t}</button>)}</span></li> : null}
    </ol>}
    </>}
    {unseen ? <button type="button" className="cwb-newmsg" onClick={toBottom} data-tip="Jump to the newest message" data-testid="cwb-newmsg">↓ {unseen} new</button> : null}
    {BUDGET_STOP.test((d?.chat || []).filter(m => m.by !== 'you').at(-1)?.text || '') ? <p className="m-note warn cwb-topup" role="status" data-testid="cwb-topup"><b><Ic3 e="💸" /> Out of budget for that ask</b>
      <span>Its next step could pass the $ cap you set. Raise the cap, or add model credit in Wallet.</span><button type="button" className="m-btn m-go" onClick={() => setGear(true)} data-testid="cwb-topup-cap">Raise the cap</button></p> : null}
    <TopupCard cat={cat} d={d} setD={setD} work={work} />
    <SiteTradeCard cat={cat} d={d} setD={setD} work={work} />
    {queue.length ? <ol className="cwb-queue" aria-label="Queued asks" data-testid="cwb-queue">{queue.map((q, i) => <li key={i} style={{ '--i': i }}><b className="m-num">{i + 1}</b><span>{q.text}</span>
      <button type="button" onClick={() => act('unqueue', { i })} aria-label="Drop this ask" data-tip="Drop it from the queue" data-testid={`cwb-unq-${i}`}>✕</button></li>)}</ol> : null}
    {(d?.parked || []).length ? <ol className="cwb-queue is-parked" aria-label="Filed to come back to" data-testid="cwb-parked">{d.parked.map((q, i) => <li key={`${q.at}-${i}`} style={{ '--i': i }}><b className="m-num">⏸</b><span data-tip={`Nobody answered for 5 min, so it moved on: ${q.why}`}>{q.text}</span>
      <button type="button" disabled={busy || live} onClick={async () => { await act('unpark', { i }); act('ask', { text: q.text, to: 'both' }); }} aria-label="Resume it now" data-tip={live ? 'Resume once the current task is done' : 'Ask it again now — you are here to help this time'} data-testid={`cwb-resume-${i}`}>▶</button>
      <button type="button" onClick={() => act('unpark', { i })} aria-label="Drop it" data-tip="Drop it" data-testid={`cwb-unpark-${i}`}>✕</button></li>)}</ol> : null}
    <AttachChips files={files} store={store} onDrop={id => setFiles(x => x.filter(f => f.id !== id))} />
    {d?.deskProof ? <div className="cwb-focus" data-testid="cwb-focus"><Ic3 e="🎯" size="18px" /><span><small className="m-num">{d.deskProof.label}</small><b>{d.deskProof.name}</b></span><em>Your words go to it</em><button type="button" className="m-btn" disabled={busy} onClick={() => act('ask', { text: 'back to the desk', to: 'both' })} data-tip="Stops talking to this proof. It keeps its folder" data-testid="cwb-focus-x">Back to the desk</button></div> : null}
    <ChatComposer onSubmit={send}
      field={<>
        <CmdPop text={text} rows={d?.commands} anchor={inRef} onPick={c => { setText(c); requestAnimationFrame(() => { const el = inRef.current; if (el) { el.focus(); el.setSelectionRange(c.length, c.length); } }); }} />
        <ChatInput ref={inRef} value={text} onChange={e => setText(e.target.value)} onKeyDown={e => { if (e.key === 'Tab' && text.startsWith('/')) { const q_ = text.slice(1).toLowerCase(); const hit_ = (d?.commands?.length ? d.commands : CMDS_FALLBACK).find(([c]) => c.toLowerCase().includes(q_)); if (hit_) { e.preventDefault(); setText(hit_[0]); } return; } if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }} placeholder={live ? (go ? 'Working… type the next ask — it queues' : 'Working… press Stop to ask again') : `Message ${cat.name || 'your agent'}…`} disabled={live && !go} aria-label="Ask the agent" data-testid="cwb-input" />
      </>}
      tools={<>
        <ChatAttach busy={upping} onPress={() => pick.current?.click()} isDisabled={upping || files.length >= 4} aria-label="Attach images for it"
          data-tip="Attach images or GIFs (up to 4) — they go in its own storage and ride with your next ask; it can upload them to a site, e.g. a coin image" data-testid="cwb-plus" />
        <ChatSettings open={gear} onOpen={setGear} testid="cwb-gear" panelTestid="cwb-settings" tip="Settings: how its minds work, its cursor, the $ cap, its job + tools">
      <ChatStylePicker value={chatLook} set={setChatLook} />
      {live ? <small className="m-note" data-testid="cwb-locked"><Ic3 e="🔒" /> Locked while it works — press ■ Stop to change these</small> : null}
      <em>HOW ITS MINDS WORK</em>
    <div className="m-seg cwb-way" role="radiogroup" aria-label="How its minds work">{WAYS.map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={way === k}
      className={way === k ? 'active' : ''} disabled={live || busy} onClick={() => setWay(k)} data-tip={tip} data-testid={`cwb-way-${k}`}>{l}</button>)}</div>
      <em>ITS CURSOR</em>
    <div className="m-seg cwb-cur" role="radiogroup" aria-label="How its cursor looks in its window">{CURSORS.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={aiCur === k}
      className={aiCur === k ? 'active' : ''} onClick={() => { setAiCur(k); try { localStorage.setItem(CURSOR_KEY, k); } catch { /* private window: this visit only */ } }} data-tip="How the AI's cursor looks as it clicks in its window (this device)" data-testid={`cwb-cur-${k}`}>{l}</button>)}</div>
      <em>MOST A TASK MAY SPEND</em>
    <div className="m-seg cwb-cap" role="radiogroup" aria-label="The most one task may spend">{CAPS.map(c => <button key={c} type="button" role="radio" aria-checked={Math.abs(cap - c) < 1e-9} className={Math.abs(cap - c) < 1e-9 ? 'active' : ''} onClick={() => act('cap', { cap: c })} data-tip={`A task stops at $${c}`} data-testid={`cwb-cap-${c}`}>${c}</button>)}</div>
      <em>JOB + TOOLS</em>
    <div className="cwb-tools"><label>Job<select className="m-input" aria-label="Cat job" value={d?.job || 'agent'} disabled={live || busy} onChange={e => act('tools', { job: e.target.value })}>{Object.keys(d?.toolkits || { agent: [] }).map(j => <option key={j}>{j}</option>)}</select></label><div className="m-seg">{Object.entries(d?.tools || {}).map(([k, on]) => <button key={k} type="button" aria-pressed={on} disabled={live || busy} className={on ? 'active' : ''} data-tip={`Allow this agent to use ${k}`} onClick={() => act('tools', { tools: { ...d.tools, [k]: !on } })}>{k} · {on ? 'ON' : 'OFF'}</button>)}</div></div>
        </ChatSettings>
        <input ref={pick} type="file" accept="image/png,image/jpeg,image/webp,image/gif,video/mp4,video/webm" multiple hidden onChange={attach} data-testid="cwb-file-input" />
      {wins.length > 1 ? <span className="m-seg cwb-to" role="radiogroup" aria-label="Who this message goes to">{[...wins.slice(0, 2).map(w => [String(w.i), <><b>{'AB'[w.i]}</b><span> · {String(w.model || '').split('/').pop().split(':')[0]}</span></>]), ['both', <b>Both</b>]].map(([k, l]) =>
        <button key={k} type="button" role="radio" aria-checked={to === k} className={to === k ? 'active' : ''} disabled={live} onClick={() => setTo(k)} data-testid={`cwb-to-${k}`}
          data-tip={k === 'both' ? 'Both minds work it, each in its own window' : 'Only this mind: it works the whole ask in its own window'}>{l}</button>)}</span> : null}
      </>}
      action={live && go && text.trim() ? <button type="submit" className="m-btn m-go" disabled={busy} data-testid="cwb-queue-add">＋ Queue ↵</button>
        : live ? <ChatStop onPress={() => act('stop')} isDisabled={busy} data-tip="Stop it" data-testid="cwb-stop" />
        : <ChatSend isDisabled={busy || !text.trim()} data-tip="Send (Enter ↵)" data-testid="cwb-send" />} />
    </DeskFlip>
    {desk ? <AgentDesktop cat={cat} start={typeof desk === 'string' || (desk && typeof desk === 'object') ? desk : null} onClose={() => setDesk(false)} onCommand={t => { setText(t); setDesk(false); }} /> : null}
    <FirstTips id="agent-desk" tips={DESK_TIPS} />
    {d && !d.live ? <p className="cwb-note" data-testid="cwb-off">Model calls are switched off on this server — asking sends and charges nothing until the owner turns them on.</p> : null}
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
  </section>;
}
