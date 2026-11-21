import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { AnimatePresence, motion, useDragControls, useMotionValue } from 'motion/react';
import { boxRef } from '../../lib/boxRef';
import '../../styles/proofWorkspace.css';
import { TaskStrip, useTaskChats } from '../desk/TaskChat';
import { scopeKey } from '../../lib/taskChats';

// 🗂 THE FILING WORKSPACE (Slice 33, owner 2026-11-20 night: "in any proof type folder the ui/layout isnt robust and lit!! just bulky and annoying
// … don't be afraid to use popouts"). ONE shell for every opened filing of every proof type: a slim top bar (back, kind, name, status, cost),
// the big work area, a chat pane that docks beside it or pops out (a floating window on the desk, or a real browser window of its own), and a
// tools rail that collapses. Panes resize by dragging their seams (react-resizable-panels) and every size, fold and pop is remembered per
// workspace id. Width comes from lib/boxRef (data-w640 / data-w980), never a container query; at phone width the panes become three tabs.

export const KIND = { pow: 'PoW', pop: 'PoP', pob: 'PoB', poc: 'PoC', pos: 'PoStatic', poe: 'PoEco' };
const KEY = id => `feeless.pws.${id}`;
export const readWs = id => { try { return JSON.parse(localStorage.getItem(KEY(id)) || '{}') || {}; } catch { return {}; } };
const writeWs = (id, patch) => { try { localStorage.setItem(KEY(id), JSON.stringify({ ...readWs(id), ...patch })); } catch { /* private mode: it just forgets */ } };
const wsBox = boxRef([640, 980]);
const money = v => (v == null || Number.isNaN(Number(v)) ? null : Number(v) < 0.01 ? `$${Number(v).toFixed(4)}` : `$${Number(v).toFixed(2)}`);

// 🪟 a pane in a browser window of its own: the page's own sheets are copied in, React renders into it through a portal (events still work)
export function OwnWindow({ title, onClose, children }) {
  const [box, setBox] = useState(null); const done = useRef(onClose); done.current = onClose;
  useEffect(() => {
    const w = window.open('', '', 'width=560,height=760');
    if (!w) { done.current('blocked'); return undefined; }
    w.document.title = `${title} · FEELESS`;
    document.querySelectorAll('link[rel="stylesheet"], style').forEach(n => w.document.head.appendChild(n.cloneNode(true)));
    w.document.body.className = `${document.body.className} pws-ownbody`;
    const el = w.document.createElement('div'); el.className = 'pws-own'; w.document.body.appendChild(el); setBox(el);
    const bye = () => done.current();
    w.addEventListener('pagehide', bye);
    return () => { w.removeEventListener('pagehide', bye); w.close(); };
  }, [title]);
  return box ? createPortal(children, box) : null;
}

// 🫧 a pane floating over the desk: drag it by its head, resize it from its corner; where it sits is remembered
function FloatPane({ id, which, kind, title, onDock, onOwn, children }) {
  const at = readWs(id)[`${which}At`] || { x: 0, y: 0 }; const x = useMotionValue(at.x); const y = useMotionValue(at.y); const drag = useDragControls();
  return createPortal(<motion.aside className={`pws-float is-${kind}`} role="dialog" aria-label={title} data-testid={`pws-float-${which}`} style={{ x, y }}
    drag dragListener={false} dragControls={drag} dragMomentum={false} onDragEnd={() => writeWs(id, { [`${which}At`]: { x: Math.round(x.get()), y: Math.round(y.get()) } })}
    initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }} transition={{ duration: 0.16 }}>
    <header className="pws-float-h" onPointerDown={e => { if (!e.target.closest('button')) drag.start(e); }} data-tip="Drag it anywhere">
      <i aria-hidden="true" /><b>{title}</b>
      <button type="button" className="pws-ic" onClick={onOwn} data-tip="Open it in a browser window of its own (a second screen, say)" aria-label={`${title} in its own window`} data-testid={`pws-own-${which}`}>⧉</button>
      <button type="button" className="pws-ic" onClick={onDock} data-tip="Put it back beside the work" aria-label={`Dock ${title}`} data-testid={`pws-dock-${which}`}>⇲</button>
    </header>
    <div className="pws-float-in">{children}</div>
  </motion.aside>, document.body);
}

function Seam({ id }) {
  return <PanelResizeHandle className="pws-seam" id={`pws-seam-${id}`} data-tip="Drag to resize. It remembers"><i aria-hidden="true" /></PanelResizeHandle>;
}

// 💬 a filing's own thread when it has no chat of its own: what each mind said on it, in order (read only, never a dead input box)
export function MindsThread({ rows = [], empty = 'Its minds have not said anything on this filing yet.' }) {
  return rows.length ? <ol className="pws-thread" data-testid="pws-thread">{rows.map((r, i) => <li key={`${r.by}-${i}`} className={/B$/.test(r.by || '') ? 'is-b' : ''} style={{ '--i': i }}>
    <small>{r.by}{r.at ? ` · ${r.at}` : ''}</small>{r.title ? <b>{r.title}</b> : null}{r.text ? <p>{r.text}</p> : null}{r.sub ? <em>{r.sub}</em> : null}</li>)}</ol>
    : <p className="pws-thread-none">{empty}</p>;
}

/**
 * <ProofWorkspace id kind name status tone cost onBack backLabel bar chat chatLabel tools toolsLabel testid>{the work}</ProofWorkspace>
 * id: what it remembers its sizes under (one per kind of view, e.g. "pos-build"); chat / tools: nodes, or null when that view has none.
 */
export function ProofWorkspace({ id, kind, name, status = null, tone = 'none', cost = null, onBack = null, backLabel = '', backId = 'pws-back', crumbs = null, bar = null, chat: chatIn = null, chatLabel = 'Chat', tools = null, toolsLabel = 'Tools', children, testid = 'pws', taskRef = '', sizes = null }) {   // sizes: {chat, tools} first-open % (a saved layout wins)
  const tcx = useTaskChats();   // 🧵 Slice 35: every proof chat can split a task off this filing; its cards + recaps sit on top of the chat
  const chat = chatIn && tcx && KIND[kind] ? <><TaskStrip scope={scopeKey(kind, taskRef)} title="Task chats from this filing" />{chatIn}</> : chatIn;
  const [pop, setPop] = useState(() => ({ chat: 'dock', tools: 'dock', ...readWs(id).pop }));   // dock | float | window
  const [fold, setFold] = useState(() => ({ chat: false, tools: false, ...readWs(id).fold }));
  const [tab, setTab] = useState(() => readWs(id).tab || 'work');   // the phone's one pane
  const [narrow, setNarrow] = useState(false); const [note, setNote] = useState('');
  const chatRef = useRef(null); const toolsRef = useRef(null);
  const root = useCallback(node => {   // boxRef for the CSS, and the same width for which panes exist at all
    if (!node) return undefined;
    const off = wsBox(node); const ro = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(([e]) => setNarrow(e.contentRect.width > 0 && e.contentRect.width <= 640));
    ro?.observe(node);
    return () => { off?.(); ro?.disconnect(); };
  }, []);
  const setP = (which, v) => setPop(p => { const n = { ...p, [which]: v }; writeWs(id, { pop: n }); return n; });
  const toggle = which => { const r = (which === 'chat' ? chatRef : toolsRef).current; if (pop[which] !== 'dock') { setP(which, 'dock'); return; }
    if (!r) return; if (r.isCollapsed()) r.expand(); else r.collapse(); };
  const onFold = which => v => setFold(f => { if (f[which] === v) return f; const n = { ...f, [which]: v }; writeWs(id, { fold: n }); return n; });
  const pick = t => { setTab(t); writeWs(id, { tab: t }); };
  useEffect(() => { if (!note) return undefined; const t = setTimeout(() => setNote(''), 4000); return () => clearTimeout(t); }, [note]);
  const docked = which => (which === 'chat' ? chat : tools) && (narrow || pop[which] === 'dock');
  const own = which => r => { if (r === 'blocked') { setNote('The browser blocked the new window. Allow pop-ups for this site, then try again.'); setP(which, 'float'); } else setP(which, 'dock'); };
  const paneHead = (which, label) => <header className="pws-pane-h"><b>{label}</b>
    <button type="button" className="pws-ic" onClick={() => setP(which, 'float')} data-tip={`Pop ${label.toLowerCase()} out over the desk`} aria-label={`Pop ${label} out`} data-testid={`pws-pop-${which}`}>⇱</button>
    <button type="button" className="pws-ic" onClick={() => setP(which, 'window')} data-tip="Open it in a browser window of its own" aria-label={`${label} in its own window`} data-testid={`pws-win-${which}`}>⧉</button>
    <button type="button" className="pws-ic" onClick={() => toggle(which)} data-tip={`Fold ${label.toLowerCase()} away (the bar brings it back)`} aria-label={`Fold ${label}`} data-testid={`pws-fold-${which}`}>›</button></header>;
  const btn = (which, label, ic) => <button type="button" className={`pws-tg${!fold[which] || pop[which] !== 'dock' ? ' is-on' : ''}${pop[which] !== 'dock' ? ' is-out' : ''}`} aria-pressed={!fold[which] || pop[which] !== 'dock'} onClick={() => toggle(which)}
    data-tip={pop[which] !== 'dock' ? `${label} is popped out. Tap to dock it here` : fold[which] ? `Show ${label.toLowerCase()}` : `Fold ${label.toLowerCase()} away`} data-testid={`pws-tg-${which}`}><i aria-hidden="true">{ic}</i>{label}</button>;
  return <section ref={root} className={`pws is-${kind}${narrow ? ' is-narrow' : ''}`} data-tab={tab} data-testid={testid} aria-label={`${KIND[kind] || ''} ${name || ''}`.trim()}>
    <header className="pws-bar" data-testid="pws-bar">
      {onBack ? <button type="button" className="pws-back" onClick={onBack} data-tip={`Back to ${backLabel || KIND[kind]}`} aria-label={`Back to ${backLabel || KIND[kind]}`} data-testid={backId}><i aria-hidden="true">‹</i>{backLabel || KIND[kind]}</button> : null}
      <span className="pws-kind" aria-hidden="true">{KIND[kind]}</span>
      {crumbs ? <span className="pws-crumbs" title={name || ''}>{crumbs}</span> : <b className="pws-name" title={name || ''} data-testid="pws-name">{name}</b>}
      {status ? <em className={`pws-status is-${tone}`} data-testid="pws-status"><i aria-hidden="true" />{status}</em> : null}
      {money(cost) ? <span className="pws-cost" data-tip="What its minds cost on this filing (fees never counted)" data-testid="pws-cost"><small>COST</small><b>{money(cost)}</b></span> : null}
      {bar ? <span className="pws-extra">{bar}</span> : null}
      <span className="pws-ctl">{chat && !narrow ? btn('chat', chatLabel, '💬') : null}{tools && !narrow ? btn('tools', toolsLabel, '⚙') : null}</span>
    </header>
    {narrow && (chat || tools) ? <nav className="m-seg pws-tabs" role="tablist" aria-label="Pane">{[['work', 'Work'], ...(chat ? [['chat', chatLabel]] : []), ...(tools ? [['tools', toolsLabel]] : [])].map(([k, l]) =>
      <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => pick(k)} data-testid={`pws-tab-${k}`}>{l}</button>)}</nav> : null}
    {note ? <p className="pws-note" role="status">{note}</p> : null}
    <PanelGroup direction="horizontal" autoSaveId={`pws-${id}`} className="pws-body">
      <Panel id="work" order={1} minSize={34} className="pws-pane pws-work" data-pane="work"><div className="pws-work-in">{children}</div></Panel>
      {docked('chat') ? <><Seam id="chat" /><Panel id="chat" order={2} ref={chatRef} defaultSize={sizes?.chat || 30} minSize={18} collapsible collapsedSize={0} onCollapse={() => onFold('chat')(true)} onExpand={() => onFold('chat')(false)}
        className="pws-pane pws-chat" data-pane="chat" data-testid="pws-chat">{paneHead('chat', chatLabel)}<div className="pws-pane-in">{chat}</div></Panel></> : null}
      {docked('tools') ? <><Seam id="tools" /><Panel id="tools" order={3} ref={toolsRef} defaultSize={sizes?.tools || 24} minSize={14} collapsible collapsedSize={0} onCollapse={() => onFold('tools')(true)} onExpand={() => onFold('tools')(false)}
        className="pws-pane pws-tools" data-pane="tools" data-testid="pws-tools">{paneHead('tools', toolsLabel)}<div className="pws-pane-in">{tools}</div></Panel></> : null}
    </PanelGroup>
    <AnimatePresence>{['chat', 'tools'].filter(w => (w === 'chat' ? chat : tools) && !narrow && pop[w] === 'float').map(w =>
      <FloatPane key={w} id={id} which={w} kind={kind} title={`${w === 'chat' ? chatLabel : toolsLabel} · ${name || KIND[kind]}`} onDock={() => setP(w, 'dock')} onOwn={() => setP(w, 'window')}>{w === 'chat' ? chat : tools}</FloatPane>)}</AnimatePresence>
    {['chat', 'tools'].filter(w => (w === 'chat' ? chat : tools) && !narrow && pop[w] === 'window').map(w =>
      <OwnWindow key={w} title={`${w === 'chat' ? chatLabel : toolsLabel} · ${name || KIND[kind]}`} onClose={own(w)}><div className={`pws-ownin is-${kind}`} data-testid={`pws-window-${w}`}>{w === 'chat' ? chat : tools}</div></OwnWindow>)}
  </section>;
}
