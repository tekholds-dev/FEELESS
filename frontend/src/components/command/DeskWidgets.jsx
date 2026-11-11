import React, { useEffect, useState } from 'react';
import { Activity, Brain, Users, Wallet } from 'lucide-react';
import { LiveCount } from './BoostFolder';
import '../../styles/deskWidgets.css';

// 🧩 Dashboard, CRM and finances as small widgets on the agent's desktop (owner 2026-11-05). Real numbers from its own state: a number it does not have stays out, and each opens the folder behind it.
const money = v => `$${(Number(v) || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const won = rows => (rows || []).filter(f => Number(f.pnlPct ?? f.roePct ?? f.net) > 0 || f.graded === 'right').length;
const lost = rows => (rows || []).filter(f => Number(f.pnlPct ?? f.roePct ?? f.net) < 0 || f.graded === 'wrong').length;
const Card = ({ icon: I, title, onOpen, testid, tip, children }) => <button type="button" className="dwg-card" onClick={onOpen} data-tip={tip} data-testid={testid}><header><I size={13} aria-hidden="true" /><b>{title}</b></header>{children}</button>;
const Row = ({ k, v }) => <span className="dwg-row"><small>{k}</small><em className="m-num">{v}</em></span>;
// 🖥 Every agent of this owner and what it is doing, whichever proof it is in. Tap one to go to its desk.
export const OPEN_AGENT = 'feeless:open-agent';
function WorkingNow({ cat, work }) {
  const [rows, setRows] = useState(null);
  useEffect(() => { if (!cat?.id || !work) return undefined; let on = true; const read = () => { if (document.hidden) return; Promise.resolve().then(() => work(cat.id, { op: 'agents_now' })).then(j => on && setRows(j.agents || [])).catch(() => {}); }; read(); const t = setInterval(read, 8000); return () => { on = false; clearInterval(t); }; }, [cat?.id, work]);
  if (!rows?.length) return null;
  return <section className="dwg-card dwg-now" data-testid="dwg-now"><header><Activity size={13} aria-hidden="true" /><b>WORKING NOW</b></header>{rows.map(r => <button key={r.id} type="button" className={`dwg-agent${r.doing.length ? ' is-on' : ''}`} disabled={r.me} onClick={() => window.dispatchEvent(new CustomEvent(OPEN_AGENT, { detail: { id: r.id } }))} data-tip={r.me ? 'This desk' : `Go to ${r.name}'s desk`} data-testid={`dwg-agent-${r.id}`}><i aria-hidden="true" /><span><b>{r.name}{r.me ? ' · here' : ''}</b>{r.doing.length ? r.doing.map((x, n) => <small key={n} className={x.wait ? 'is-wait' : ''}><em>{x.kind}</em> {x.wait ? 'needs you: ' : ''}{x.say}</small>) : <small>Idle</small>}</span></button>)}</section>;
}
// 🧾 Every proof kind it files, not only the trading three (owner 2026-11-08: "finish the vitals of agents tab"). A kind it never filed stays out.
const KINDS = [['PoW', 'powFolders'], ['PoP', 'popFolders'], ['PoB', 'pobFolders'], ['PoC', 'pocFolders'], ['PoStatic', 'psFolders'], ['PoEco', 'poeFolders']];
export const kindRows = d => KINDS.map(([k, key]) => { const rows = (d?.[key] || []).filter(f => !f.noTrade && !f.hidden); return { k, n: rows.length, w: won(rows), l: lost(rows) }; }).filter(x => x.n);
// 🧠 Its two minds by their own names (OSSY and G4, never a stand-in), where each runs, and what its thinking has cost.
export const mindRows = cat => { const b = cat?.brainsCfg || {}; return (b.brains || []).slice(0, 2).map((m, i) => ({ name: (b.mindNames || [])[i] || String(m).split('/').pop().split(':')[0], where: String(m).startsWith('local/') ? 'Its own machine' : String(m).split('/')[0], model: String(m).split('/').pop() })); };
export function DeskWidgets({ d, pool, openWin, cat, work, has = null }) {
  const kinds = kindRows(d); const total = kinds.reduce((n, x) => n + x.n, 0); const w = kinds.reduce((n, x) => n + x.w, 0); const l = kinds.reduce((n, x) => n + x.l, 0); const top = Math.max(1, ...kinds.map(x => x.n)); const minds = mindRows(cat); const b = cat?.brainsCfg || {}; const s = pool?.stake || {}; const open = (d?.jobs || []).filter(j => !j.done && j.status !== 'done').length;
  return <aside className="dwg" aria-label="Desktop widgets" data-testid="dsk-widgets">
    <WorkingNow cat={cat} work={work} />
    <Card icon={Activity} title="DASHBOARD" onOpen={() => openWin('proofs')} tip="Every proof it filed, by kind, and its jobs. Opens Proofs" testid="dwg-dash"><Row k="Proofs" v={total} /><Row k="Won / lost" v={`${w} / ${l}`} /><span className="dwg-bar" aria-hidden="true" data-tip="Won out of won and lost"><u style={{ transform: `scaleX(${w + l ? w / (w + l) : 0})` }} /></span>
      {kinds.length ? <span className="dwg-kinds" data-testid="dwg-kinds">{kinds.map(x => <span key={x.k} data-tip={`${x.k}: ${x.n} filed, ${x.w} won or marked working, ${x.l} lost or marked wrong`}><small>{x.k}</small><i aria-hidden="true"><u style={{ transform: `scaleX(${x.n / top})` }} /></i><em className="m-num">{x.n}</em></span>)}</span> : null}<Row k="Jobs open" v={open} /></Card>
    {minds.length ? <Card icon={Brain} title="MINDS" onOpen={!has || has.includes('brains') ? () => openWin('brains') : () => openWin('manual')} tip={!has || has.includes('brains') ? 'Its two minds, where each runs, and what thinking cost. Opens Brains' : 'Its two minds and what thinking cost. Opens its Manual'} testid="dwg-minds">{minds.map((m, i) => <span key={i} className="dwg-mind" data-testid={`dwg-mind-${i}`}><b>{m.name}</b><small>{m.where} · {m.model}</small></span>)}{b.credit != null ? <Row k={cat?.orCredit ? "OpenRouter left" : "Credit left"} v={money(cat?.orCredit ? cat.orCredit.left : b.credit)} /> : null}{b.spent != null ? <Row k="Thinking spent" v={money(b.spent)} /> : null}</Card> : null}
    <Card icon={Users} title="CRM" onOpen={() => openWin('mail')} tip="Who it deals with: sites and mail. Opens Mail" testid="dwg-crm"><Row k="Signed in to" v={(d?.signedIn || []).length} /><Row k="Saved sign-ins" v={(d?.logins || []).length} /><Row k="Mail" v={d?.mail?.address ? 'Yes' : 'None'} /></Card>
    <Card icon={Wallet} title="FINANCES" onOpen={() => openWin('boost')} tip="Its boost cash and its stake. Opens Boosts" testid="dwg-money"><span className="dwg-cash"><small>BOOST CASH</small><LiveCount pool={pool?.pool} readAt={pool?.readAt} testid="dwg-cash" /></span><Row k="Boost points" v={Number(s.pointsLeft || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })} /><Row k="Staked" v={money(s.sentUsd)} /><Row k="Seat" v={`${(s.nowPct || 0).toFixed(2)}%`} /></Card>
  </aside>;
}
