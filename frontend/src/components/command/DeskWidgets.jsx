import React, { useEffect, useState } from 'react';
import { Activity, Users, Wallet } from 'lucide-react';
import { LiveCount } from './BoostFolder';
import '../../styles/deskWidgets.css';

// 🧩 Dashboard, CRM and finances as small widgets on the agent's desktop (owner 2026-11-05). Real numbers from its own state: a number it does not have stays out, and each opens the folder behind it.
const money = v => `$${(Number(v) || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
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
export function DeskWidgets({ d, pool, openWin, cat, work }) {
  const proofs = [...(d?.powFolders || []), ...(d?.popFolders || []).filter(f => !f.noTrade), ...(d?.pobFolders || [])]; const w = won(proofs); const l = lost(proofs); const s = pool?.stake || {}; const open = (d?.jobs || []).filter(j => !j.done && j.status !== 'done').length;
  return <aside className="dwg" aria-label="Desktop widgets" data-testid="dsk-widgets">
    <WorkingNow cat={cat} work={work} />
    <Card icon={Activity} title="DASHBOARD" onOpen={() => openWin('jobs')} tip="Its proofs and jobs. Opens Jobs" testid="dwg-dash"><Row k="Proofs" v={proofs.length} /><Row k="Won / lost" v={`${w} / ${l}`} /><Row k="Jobs open" v={open} /><span className="dwg-bar" aria-hidden="true"><u style={{ transform: `scaleX(${w + l ? w / (w + l) : 0})` }} /></span></Card>
    <Card icon={Users} title="CRM" onOpen={() => openWin('mail')} tip="Who it deals with: sites and mail. Opens Mail" testid="dwg-crm"><Row k="Signed in to" v={(d?.signedIn || []).length} /><Row k="Saved sign-ins" v={(d?.logins || []).length} /><Row k="Mail" v={d?.mail?.address ? 'Yes' : 'None'} /></Card>
    <Card icon={Wallet} title="FINANCES" onOpen={() => openWin('boost')} tip="Its boost cash and its stake. Opens Boosts" testid="dwg-money"><span className="dwg-cash"><small>BOOST CASH</small><LiveCount pool={pool?.pool} readAt={pool?.readAt} testid="dwg-cash" /></span><Row k="Boost points" v={Number(s.pointsLeft || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })} /><Row k="Staked" v={money(s.sentUsd)} /><Row k="Seat" v={`${(s.nowPct || 0).toFixed(2)}%`} /></Card>
  </aside>;
}
