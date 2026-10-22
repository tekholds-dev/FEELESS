import React from 'react';
import { CrestForge } from '../components/CrestForge';
import { CrewCard3D } from '../components/Crews';
import { CardStudio } from '../components/FamilyRoom';
import { FamilyBadge } from '../components/FamilyBadge';
import '../styles/familyNoir.css';

// 🧪 DEV ONLY (`/dev/crest`, never in a production build — index.js imports it behind NODE_ENV): the Crest Forge, the six family-card scenes and
// a row of crests on fixtures, no wallet / no sign-in. The forge's catalog read is answered locally; nothing reaches the server.
const MET = { members: 4, podiums: 1, crowns: 0, best: 2, points: 640, wars: 1 };
const OPT = (keys, locks = {}) => keys.map(k => (locks[k] ? { key: k, label: k[0].toUpperCase() + k.slice(1), ok: false, metric: locks[k][0], min: locks[k][1], need: `${locks[k][1]} ${locks[k][0]} (now ${MET[locks[k][0]] ?? 0})` } : { key: k, label: k[0].toUpperCase() + k.slice(1), ok: true, metric: null, min: 0, need: null }));
const CAT = {
  metrics: MET, metricWords: { members: 'members', podiums: 'weeks in the top 3', crowns: 'weeks at #1', best: 'best weekly place (1 = #1)', points: 'bounty points paid', wars: 'family wars won' },
  parts: { shape: OPT(['heater', 'round', 'kite', 'coin', 'chevron', 'card']), field: OPT(['plain', 'split', 'bend', 'chevron', 'quarterly', 'stripes']),
    emblem: OPT(['rose', 'skull', 'snake', 'dice', 'gun', 'hat', 'scorp', 'dragon', 'crown', 'diamond', 'sword', 'wolf', 'lion'], { hat: ['members', 5], dragon: ['podiums', 3], crown: ['crowns', 1], diamond: ['points', 1000], wolf: ['wars', 3], lion: ['wars', 10] }),
    frame: OPT(['iron', 'silver', 'gold', 'blood', 'holo', 'black', 'warlord'], { silver: ['members', 5], blood: ['crowns', 1], black: ['best', 1], warlord: ['wars', 5] }),
    fx: OPT(['none', 'smoke', 'embers', 'lightning', 'rain', 'gunsmoke'], { lightning: ['crowns', 1], rain: ['points', 2000] }), banner: OPT(['ribbon', 'scroll', 'plate']) },
  colors: ['#15d16a', '#ffd36b', '#ff4d6d', '#9b5cff', '#6fd3ff', '#ffffff', '#ff9f45', '#111111', '#d4af37', '#7a0f1f', '#1b3a6b'], mottoMax: 24, owner: true, built: true, restyleUsd: 2, free: false,
  adjust: { es: { min: 0.7, max: 1.3, default: 1 }, er: { min: -30, max: 30, default: 0 } },
  badge: { shape: 'heater', field: 'quarterly', emblem: 'skull', frame: 'gold', fx: 'embers', banner: 'ribbon', c1: '#7a0f1f', c2: '#d4af37', c3: '#ffffff', es: 1, er: 0, ef: false, motto: 'Famiglia prima di tutto', tag: 'SIC', name: 'Sicario', ranks: MET },
};
const real = window.fetch.bind(window);
window.fetch = (u, o) => (String(u).includes('/crews/badge/catalog') ? Promise.resolve(new Response(JSON.stringify(CAT), { status: 200, headers: { 'Content-Type': 'application/json' } })) : real(u, o));
const B = CAT.badge;
const LOOKS = [{ ...B }, { ...B, shape: 'kite', field: 'bend', emblem: 'wolf', frame: 'silver', c1: '#1b3a6b', c2: '#ffffff', c3: '#d4af37', banner: 'scroll', tag: 'WLF' },
  { ...B, shape: 'coin', field: 'plain', emblem: 'diamond', frame: 'holo', c1: '#111111', c2: '#9b5cff', c3: '#6fd3ff', banner: 'plate', tag: 'ICE' },
  { ...B, shape: 'chevron', field: 'stripes', emblem: 'lion', frame: 'warlord', c1: '#111111', c2: '#ff4d6d', c3: '#ffd36b', tag: 'LEO', er: -10 },
  { ...B, shape: 'card', field: 'split', emblem: 'rose', frame: 'black', c1: '#111111', c2: '#7a0f1f', c3: '#ff4d6d', tag: 'ROS' },
  { ...B, shape: 'round', field: 'chevron', emblem: 'dragon', frame: 'blood', c1: '#15d16a', c2: '#111111', c3: '#ffd36b', tag: 'DRG', ef: true }];
const STYLES = ['noir', 'gold', 'blood', 'neon', 'ice', 'royal'];
const ROWS = STYLES.map((st, i) => ({ id: `c${i}`, tag: LOOKS[i].tag, name: ['Sicario', 'Lupi Neri', 'Ice Cartel', 'Leoni', 'Rosa Nera', 'Draghi'][i], members: 3 + i, seats: 10, active: i + 1, pct: [12.4, -3.1, 41.8, 6.2, -12.5, 2.9][i], bounties: i, badge: LOOKS[i], card: { style: st, fx: ['embers', 'smoke', 'stars', 'rain', 'none', 'lightning'][i], line: i % 2 ? '' : 'Famiglia prima di tutto' } }));
const MINE = { id: 'c0', tag: 'SIC', name: 'Sicario', members: [1, 2, 3, 4], seats: 10, badge: LOOKS[0], card: ROWS[0].card, cardOpts: { style: STYLES, fx: ['none', 'smoke', 'embers', 'rain', 'lightning', 'stars'] } };

export default function CrestHarness() {
  return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 16, background: '#070504', color: '#e9d3a0', display: 'grid', gap: 18 }}>
    <h2 className="m-label">🧪 DEV PREVIEW · crest forge + family cards (fixtures)</h2>
    <CrestForge mine={MINE} owner addr="dev" sess="dev" costWord="$2 ≈ 0.012 SOL" act={() => {}} busy="" />
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'end' }}>{LOOKS.map(b => <FamilyBadge key={b.tag} b={b} size="lg" />)}{LOOKS.map(b => <FamilyBadge key={`s${b.tag}`} b={b} size="sm" />)}</div>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>{ROWS.map((r, i) => <CrewCard3D key={r.id} r={r} place={i < 3 ? i + 1 : 4} />)}</div>
    <div className="crw-top-row" style={{ maxWidth: 560 }}>{ROWS.slice(0, 3).map((r, i) => <CrewCard3D key={r.id} r={r} place={i + 1} small />)}</div>
    <CardStudio mine={MINE} owner addr="dev" sess="dev" onChanged={() => {}} preview={d => <CrewCard3D r={{ ...ROWS[0], card: d }} place={1} />} />
  </div>;
}
