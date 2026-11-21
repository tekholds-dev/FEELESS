import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeftRight, Bot, Home, MessagesSquare, Radar, Settings, Trophy, Atom } from 'lucide-react';
import { useWallet } from '../hooks/useWallet';
import { useQuests } from './QuestBoard';
import { sharedJson } from '../lib/sharedJson';
import { DESK_BGS, DeskBackdrop, useDeskLook, useRipple } from './desk/DeskLook';
import '../styles/deskLayout.css';

// 🖥 DESK (owner's pick 2026-11-12: "Desk" layout in Feeless Green): the terminal as a desktop — a menu bar with a live clock, a window bar over
// the page, your rank / today's quests / the weekly board as widgets (REAL data only: /api/reputation/quests/{you} + /api/reputation/league;
// nothing shown that the server did not say), and a dock to every part of the site.
const DOCK = [['', 'Home', Home], ['trade', 'Trade', ArrowLeftRight], ['chat', 'Trenches', MessagesSquare], ['pump', 'Pump radar', Radar], ['fuse', 'Fuse', Atom],
  ['leaderboard', 'Leaderboard', Trophy], ['feecat/agents', 'Agents', Bot], ['settings', 'Settings · looks', Settings]];
const NAMES = Object.fromEntries(DOCK.map(([k, n]) => [k, n]));

function Clock() {
  const [t, setT] = useState(() => new Date());
  useEffect(() => { const i = setInterval(() => setT(new Date()), 1000); return () => clearInterval(i); }, []);
  return <time className="dk-clock" dateTime={t.toISOString()} data-testid="desk-clock">{t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time>;
}

/** Night or day, as the site wears it (body.theme-day), live. */
function useDay() {
  const [day, setDay] = useState(() => typeof document !== 'undefined' && document.body.classList.contains('theme-day'));
  useEffect(() => { const b = document.body; const o = new MutationObserver(() => setDay(b.classList.contains('theme-day'))); o.observe(b, { attributes: true, attributeFilter: ['class'] }); return () => o.disconnect(); }, []);
  return day;
}
/** 🖥 Slice 34: the Desk look site-wide — the agent desk's background (Smoke / Aurora / Grid / Film / Plain, the same saved pick as every desk) behind the page,
 *  its glass and small type on every panel (deskLayout.css), and the press + ripple click effects. White follows the site's own day mode. */
export function SiteDeskLook() {
  const [look] = useDeskLook(); const day = useDay(); const ref = useRef(typeof document !== 'undefined' ? document.body : null); useRipple(ref);
  return createPortal(<div className="dk-site-bg" aria-hidden="true" data-testid="desk-site-bg"><DeskBackdrop bg={look.bg} light={day} /></div>, document.body);   // on <body>: a transformed page wrapper never pins it
}

/** Menu bar: sits at the top of the terminal page (slim glass, like the agent desk's bar), with the background picker. */
export function DeskBar({ page }) {
  const [look, setLook] = useDeskLook();
  return <div className="dk-top" data-testid="desk-bar">
    <div className="dk-menu"><b>FEELESS</b><span>{NAMES[page] || page || 'Home'}</span><Link to="/terminal/settings" data-tip="Change the look or layout">Look</Link>
      <span className="dk-bgs" role="group" aria-label="Background">{DESK_BGS.map(([k, l]) => <button key={k} type="button" aria-pressed={look.bg === k} onClick={() => setLook({ bg: k })} data-testid={`desk-bg-${k}`}>{l}</button>)}</span>
      <Clock /></div>
  </div>;
}

/** Rank · quests · board widgets: every number from the server; no wallet / no data = say so, never a placeholder number. */
export function DeskWidgets({ onConnect }) {
  const { wallet } = useWallet() || {};
  const [q] = useQuests(wallet?.address);
  const [lg, setLg] = useState(null);
  useEffect(() => { let on = true; sharedJson('/api/reputation/league', { maxAge: 60000 }).then(d => on && setLg(d)).catch(() => {}); return () => { on = false; }; }, []);
  const lv = q?.level; const tasks = q?.quests?.daily?.tasks || []; const done = tasks.filter(t => t.done).length;
  const pct = lv?.next ? Math.min(1, lv.xp / lv.next) : 1;
  return <div className="dk-widgets" data-testid="desk-widgets">
    <section className="dk-w" style={{ '--i': 0 }} data-testid="desk-rank"><span className="m-label">YOUR RANK</span>
      {!wallet?.address ? <button type="button" className="m-btn" onClick={onConnect} data-tip="Connect a wallet to see your rank">Connect wallet</button>
        : !lv ? <small className="m-dim">Reading your record…</small>
          : <><b className="dk-big">L{lv.level} <small>{lv.name}</small></b><div className="dk-bar"><i style={{ transform: `scaleX(${pct})` }} /></div><small className="m-dim">{lv.xp.toLocaleString()} XP{lv.next ? ` · ${(lv.next - lv.xp).toLocaleString()} to next` : ' · top level'}</small></>}
    </section>
    <section className="dk-w" style={{ '--i': 1 }} data-testid="desk-quests"><span className="m-label">TODAY'S QUESTS</span>
      {!wallet?.address ? <small className="m-dim">Connect to track today's quests.</small> : !q ? <small className="m-dim">Reading…</small> : !tasks.length ? <small className="m-dim">No quests today.</small>
        : <><b className="dk-big">{done}/{tasks.length}</b><ul className="dk-q">{tasks.slice(0, 3).map(t => <li key={t.id} className={t.done ? 'is-done' : ''}><span>{t.label}</span><small>{Math.min(t.have, t.target)}/{t.target}</small></li>)}</ul><Link to="/terminal/badges" className="dk-more">All quests →</Link></>}
    </section>
    <section className="dk-w" style={{ '--i': 2 }} data-testid="desk-board"><span className="m-label">WEEKLY BOARD</span>
      {!lg ? <small className="m-dim">Reading…</small> : !(lg.rows || []).length ? <small className="m-dim">No calls this week yet. Drop a CA in chat to get on it.</small>
        : <ol className="dk-board">{lg.rows.slice(0, 4).map((r, i) => <li key={r.address}><b>{i + 1}</b><span>{r.caller}</span><em>{r.points}</em></li>)}</ol>}
      <Link to="/terminal/leaderboard" className="dk-more">Leaderboard →</Link>
    </section>
  </div>;
}

/** The dock: one lucide icon per part of the site, the open page lit. */
export function DeskDock({ page }) {
  const nav = useNavigate();
  return <nav className="dk-dock" aria-label="Dock" data-testid="desk-dock">{DOCK.map(([k, n, I]) => <button key={k || 'home'} type="button" className={(page || '') === k ? 'is-on' : ''} onClick={() => nav(`/terminal${k ? `/${k}` : ''}`)} data-tip={n} aria-label={n}><I size={18} strokeWidth={1.75} /></button>)}</nav>;
}
