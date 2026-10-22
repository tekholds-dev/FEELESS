import React, { useState } from 'react';
import { Crews } from '../components/Crews';
import { FamilyFuseBoard } from '../components/FamilyFuseBoard';
import '../styles/feeCity.css';
import '../styles/familyNoir.css';

// 🧪 DEV ONLY (`/dev/familia?tab=wars|board|feed`): the Familia tabs on fixtures, no wallet — every read below is answered locally.
const now = Date.now() / 1000;
const B = (shape, field, emblem, frame, c1, c2, c3, tag) => ({ shape, field, emblem, frame, fx: 'embers', banner: 'ribbon', c1, c2, c3, es: 1, er: 0, ef: false, tag, set: true });
const FAM = [
  { id: 'c1', tag: 'SIC', name: 'Sicario Family', badge: B('heater', 'quarterly', 'skull', 'gold', '#7a0f1f', '#d4af37', '#ffffff', 'SIC') },
  { id: 'c2', tag: 'WLF', name: 'Lupi Neri', badge: B('kite', 'bend', 'wolf', 'silver', '#1b3a6b', '#ffffff', '#d4af37', 'WLF') },
  { id: 'c3', tag: 'LEO', name: 'Leoni', badge: B('chevron', 'stripes', 'lion', 'warlord', '#111111', '#ff4d6d', '#ffd36b', 'LEO') },
  { id: 'c4', tag: 'ROS', name: 'Rosa Nera', badge: B('card', 'split', 'rose', 'black', '#111111', '#7a0f1f', '#ff4d6d', 'ROS') },
  { id: 'c5', tag: 'DRG', name: 'Draghi', badge: B('round', 'chevron', 'dragon', 'blood', '#15d16a', '#111111', '#ffd36b', 'DRG') },
];
const BOARD = { total: 5, rule: 'Verified FEELESS trades over 7 days (price result, fees apart). A family ranks with ≥ 2 members and ≥ 5 closed trades.',
  board: FAM.map((f, i) => ({ ...f, members: 6 - i, seats: 10, active: 3 - (i % 3), pct: [18.2, 9.4, 3.1, -2.6, null][i], ranked: i < 4, trades: 12 - i, wonPct: 64 - i * 6, bounties: i, card: { style: ['noir', 'gold', 'neon', 'blood', 'ice'][i], fx: 'embers' } })) };
const W = (id, a, b, state, extra) => ({ id, a: FAM[a], b: FAM[b], state, pot: 650, potSides: { a: 350, b: 300 }, hours: 4, startAt: now + 3600, endAt: now + 3 * 3600, log: [[now - 600, `[${FAM[a].tag}] called [${FAM[b].tag}] out for 350`], [now - 300, `[${FAM[b].tag}] matched 300 — bell set`]], ...extra });
const WARS = { wars: [
  W('w1', 0, 1, 'live', { startAt: now - 1800, endAt: now + 5400, score: { a: { pct: 6.4, trades: 9, team: 5 }, b: { pct: 2.1, trades: 7, team: 4 } }, allies: { a: [FAM[3]], b: [] } }),
  W('w2', 2, 4, 'set', { pot: 1200, potSides: { a: 600, b: 600 } }),
  W('w3', 3, 2, 'open', { pot: 250, potSides: { a: 250 } }),
  W('w4', 1, 2, 'done', { winner: 'a', startAt: now - 90000, endAt: now - 76000, score: { a: { pct: 11.2, trades: 14, team: 5 }, b: { pct: -3.4, trades: 8, team: 5 } } }),
], alliances: [], asks: [] };
const LIVE = { vitals: { families: 5, members: 21, joinedWeek: 6, openBounties: 3, ptsWeek: 1840, launches: 2 }, events: [
  { kind: 'crown', id: 1, fam: 'SIC', text: 'took the week — #1 on the board', at: now - 120 }, { kind: 'joined', id: 2, fam: 'WLF', text: 'a new member sat at the table', at: now - 900 },
  { kind: 'bounty', id: 3, fam: 'LEO', text: 'posted 250 pts: find the next 10x before it runs', at: now - 2400 }, { kind: 'paid', id: 4, fam: 'ROS', text: 'paid 100 pts to its sharpest caller', at: now - 5000 },
  { kind: 'launch', id: 5, fam: 'DRG', text: 'pinned $DRAGO — every member sees it live', at: now - 9000 }, { kind: 'badge', id: 6, fam: 'SIC', text: 'restyled its crest', at: now - 15000 }] };
const real = window.fetch.bind(window);
const json = d => Promise.resolve(new Response(JSON.stringify(d), { status: 200, headers: { 'Content-Type': 'application/json' } }));
window.fetch = (u, o) => { const s = String(u);
  if (s.includes('/crew-wars')) return json(WARS); if (s.includes('/crews/live')) return json(LIVE); if (s.includes('/crews/mine')) return json({ crew: null });
  if (s.includes('/crews/price')) return json({}); if (/\/api\/reputation\/crews(\?|$)/.test(s)) return json(BOARD); return real(u, o); };
try { sessionStorage.setItem('feeless.fam.tab', JSON.stringify(new URLSearchParams(window.location.search).get('tab') || 'wars')); } catch { /* */ }

const SIDE = (i, extra) => ({ id: FAM[i].id, tag: FAM[i].tag, name: FAM[i].name, color: [FAM[i].badge.c2, FAM[i].badge.c3].find(c => c !== '#111111'), rating: [1180, 1040, 1420, 990, 1260][i], bracket: ['Made', 'Street', 'Don', 'Street', 'Capo'][i], ...extra });
const FIGHTS = [
  { id: 'f1', status: 'live', stake: 'mp', mp: 2500, mins: 30, left: 1240, ranked: true, by: 'Vito', a: SIDE(0, { card: { name: 'Meme Mafia', coins: 5 }, pct: 4.21 }), b: SIDE(1, { card: { name: 'Dog Pound', coins: 5 }, pct: -1.08 }),
    duel: { a: 4, b: 2, seats: [{ seat: 1, a: { symbol: 'BONK', pct: 6.2 }, b: { symbol: 'WIF', pct: -2.1 }, win: 'a' }, { seat: 2, a: { symbol: 'POPCAT', pct: 1.4 }, b: { symbol: 'MEW', pct: 3.3 }, win: 'b' }] },
    crowd: { pool: { a: 1800, b: 900 }, total: 2700, pays: { a: 1.43, b: 2.85 }, bidders: 14 }, bidsOpen: true, lockIn: 400 },
  { id: 'f2', status: 'done', stake: 'paper', mp: 0, mins: 15, left: 0, ranked: true, winner: 'a', a: SIDE(2, { card: { name: 'Lion Den', coins: 4 }, pct: 7.7 }), b: SIDE(4, { card: { name: 'Fire Breath', coins: 3 }, pct: 1.2 }),
    crowd: { pool: { a: 300, b: 200 }, total: 500, pays: { a: 1.58, b: 2.37 }, bidders: 5 }, paid: { fam: {}, bids: { x: 1 }, house: 25 }, elo: { a: [1404, 1420], b: [1276, 1260] } },
  { id: 'f3', status: 'open', stake: 'paper', mp: 0, mins: 15, left: 1500, ranked: false, by: 'a member', a: SIDE(3, { card: { name: 'Black Rose', coins: 3 } }), b: SIDE(2, {}), crowd: { pool: { a: 0, b: 0 }, total: 0, pays: {}, bidders: 0 }, bidsOpen: true, lockIn: 900 },
];
const FV = { me: { id: 'c1', boss: false, pts: 1200, bank: 900 }, rules: { fuseMinMp: 2000 }, ranked: FAM, blocks: [],
  ffuse: { fights: FIGHTS, mins: [15, 30, 60], cards: [{ key: 'k1', name: 'Meme Mafia', coins: 5 }], brackets: [{ key: 'street', word: 'Street', from: 0 }, { key: 'made', word: 'Made', from: 1100 }, { key: 'capo', word: 'Capo', from: 1250 }, { key: 'don', word: 'Don', from: 1400 }],
    ladder: FAM.map((f, i) => ({ ...f, rating: [1180, 1040, 1420, 990, 1260][i], bracket: ['Made', 'Street', 'Don', 'Street', 'Capo'][i] })).sort((a, b) => b.rating - a.rating) } };

export default function FamiliaHarness() {
  const [fv, setFv] = useState(FV);
  if (new URLSearchParams(window.location.search).get('tab') === 'fuse') return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 16, background: '#070504', color: '#e9d3a0' }}><FamilyFuseBoard v={fv} setV={setFv} addr="dev" sess="" /></div>;
  return <FamiliaTabs />;
}
function FamiliaTabs() {
  const [scene, setScene] = useState('');
  return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 16, background: '#070504', color: '#e9d3a0' }} data-scene={scene}>
    <h2 className="m-label">🧪 DEV PREVIEW · Familia tabs (fixtures) · {scene}</h2>
    <Crews onScene={setScene} />
  </div>;
}
