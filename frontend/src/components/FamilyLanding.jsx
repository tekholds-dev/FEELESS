import React from 'react';
import { Crown, Swords, Users, Map as MapIcon, Trophy, Shield, ArrowUpRight } from 'lucide-react';
import '../styles/familyLanding.css';

// 🌹 THE FAMILIA LANDING (owner, 2026-10-21: "a landing page for Familia — it must be META"): the pitch in one screen — headline, the live
// numbers (every one read from the board + the families' live feed + the war room), four steps, the three families on top, and the way in.
export const STEPS = [
  [Users, 'Form the family', 'Start one or take an invite. Five seats to start; the Don adds more.'],
  [Trophy, 'Trade verified', 'Only FEELESS-verified trades count. The week ranks every family on its real result.'],
  [Swords, 'Call out a rival', 'Bet family points, set the bell, bring allies. The trades decide the war.'],
  [Crown, 'Hold the city', 'Win districts on the map, unlock badge parts, crown the season.'],
];

export function landingNumbers(board, live, wars) {
  const rows = board?.board || [];
  const v = live?.vitals || {};
  const ws = wars?.wars || [];
  return [
    ['FAMILIES', rows.length || v.families || 0], ['MEMBERS', v.members ?? rows.reduce((a, r) => a + (r.members || 0), 0)],
    ['WARS LIVE', ws.filter(w => w.state === 'live').length], ['POINTS AT STAKE', ws.filter(w => ['live', 'set', 'open'].includes(w.state)).reduce((a, w) => a + (Number(w.pot) || 0), 0)],
  ];
}

export function FamilyLanding({ board, live, wars, mine, onGo, podium }) {
  const nums = landingNumbers(board, live, wars);
  return (
    <section className="fld2" data-testid="familia-landing">
      <div className="fld2-hero">
        <span className="fld2-eyebrow"><Shield size={13} /> LA FAMILIA · FEELESS</span>
        <h1>Run the trenches <em>as a family.</em></h1>
        <p>Every family is ranked on its members' verified trades. Win the week, win the wars, hold the city — and wear what you earned.</p>
        <div className="fld2-cta">
          {mine ? <button type="button" className="m-btn m-go" onClick={() => onGo('family')} data-testid="fld2-mine">Enter {mine.name} <ArrowUpRight size={14} /></button>
            : <button type="button" className="m-btn m-go" onClick={() => onGo('family')} data-testid="fld2-start">Start or join a family <ArrowUpRight size={14} /></button>}
          <button type="button" className="m-btn" onClick={() => onGo('wars')}><Swords size={14} /> War room</button>
          <button type="button" className="m-btn" onClick={() => onGo('map')}><MapIcon size={14} /> The city</button>
        </div>
      </div>
      <div className="fld2-nums">{nums.map(([k, n], i) => <span key={k} style={{ '--i': i }}><b key={n}>{Number(n || 0).toLocaleString('en-US')}</b><em>{k}</em></span>)}</div>
      <ol className="fld2-steps">{STEPS.map(([Icon, t, d], i) => <li key={t} style={{ '--i': i }}><i><Icon size={18} /></i><b>{t}</b><small>{d}</small></li>)}</ol>
      {podium}
    </section>
  );
}
