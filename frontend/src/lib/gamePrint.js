// 🧬 A GAME'S FINGERPRINT (owner 2026-11-05). The same ridges as an agent's Proofprint, so every print on FEELESS reads the same way.
// Live: the core is tip-off and the outer ridge is the final horn. Each real play inks the stretch of ridge between it and the play before, at the spot the game's clock says.
// The print grows outward as the game runs. It is only FINAL once ESPN says final and every agent call on this game is graded.
// A team's or a player's print: one ridge per stat. The first half of the ridge is last season, the second half this season, inked by which way it went.
import { geom, identityOf, inkOf, part, ridge } from './proofprint';

export const GAME_RINGS = 14;
const TWO = Math.PI * 2;
const MIN_SPAN = 0.05;
export const SIDE_INK = { a: '#5bb8ff', b: '#b58cff' };
const ringOf = i => i * 2 + 2;   // the same spacing as the Proofprint's own lines

export const placeAt = at => { const v = Math.max(0, Math.min(0.99999, Number(at) || 0)) * GAME_RINGS; const ring = Math.floor(v); return { ring, t: (v - ring) * TWO }; };

// One inked stretch per play, oldest first. A big swing in win chance or a score draws heavier. A stretch never crosses into the next ridge.
export function gameSegments(seed, plays) {
  const id = identityOf(seed); const out = []; let prev = 0; let prevWp = null;
  (plays || []).forEach(p => {
    const at = Number(p.at) || 0; const from = placeAt(Math.min(prev, at)); const to = placeAt(at);
    const a = from.ring === to.ring ? from.t : 0; const b = Math.min(TWO, Math.max(to.t, a + MIN_SPAN));
    const swing = p.wp != null && prevWp != null ? Math.abs(p.wp - prevWp) : 0;
    out.push({ id: p.id, ring: to.ring, d: part(id, ringOf(to.ring), a, b, Math.max(2, Math.round((b - a) * 10))), ink: SIDE_INK[p.side] || '#8a93a6', w: 2.2 + (p.pts ? 1.4 + p.pts * 0.7 : 0) + Math.min(5, swing * 40), bright: !!p.pts || swing >= 0.03 });
    prev = Math.max(prev, at); if (p.wp != null) prevWp = p.wp;
  });
  return out;
}

// The pen: where the next play will land.
export function penAt(seed, at) { const id = identityOf(seed); const { ring, t } = placeAt(at); return geom(id, ringOf(ring), t); }

// The faint ridges the game has not reached yet.
export function blankRidges(seed, fromRing = 0) { const id = identityOf(seed); const out = []; for (let i = fromRing; i < GAME_RINGS; i += 1) out.push(ridge(id, ringOf(i), 44)); return out; }

// The final seal: one mark on the outermost ridge per agent call, green for right, red for wrong.
export function gradeMarks(seed, calls) {
  const id = identityOf(seed); const n = (calls || []).length; if (!n) return [];
  return calls.map((c, i) => { const a = (i / n) * TWO; const b = a + (TWO / n) * 0.82; return { ...c, d: part(id, ringOf(GAME_RINGS), a, b, 16), ink: c.won === true ? '#4dea8f' : c.won === false ? '#f2697a' : '#8a93a6' }; });
}

// FINAL only when the game is over and no call on it is still waiting for its grade.
export const printStage = (state, calls) => (state === 'post' ? ((calls || []).some(c => c.won == null) ? 'grading' : 'final') : state === 'in' ? 'live' : 'pre');

// A stat row's ridge: last season's half and this season's half. No last season means only this season's half is inked.
export function statRidges(seed, rows) {
  const id = identityOf(seed);
  return (rows || []).map((r, i) => ({ ...r, j: ringOf(i), last: r.last == null ? null : part(id, ringOf(i), 0.1, Math.PI - 0.08, 18), now: part(id, ringOf(i), Math.PI + 0.08, TWO - 0.1, 18), ink: inkOf(r.score) }));
}

const fmt = v => (v == null ? '—' : Math.abs(v) >= 100 ? String(Math.round(v)) : String(Math.round(v * 10) / 10));
export const statLine = r => (r ? `${r.label || r.abbr} ${fmt(r.now)} this season${r.last == null ? ', no last season to compare' : `, ${fmt(r.last)} last season`}` : '');

// Two markets and ESPN's own model against each other. The server cannot see the board's prices, so these two reads are made here.
export function marketReads(edge, a, b) {
  const out = []; const name = b?.short || b?.name || 'Home';
  if (b?.chance != null && b?.kalshi != null && Math.abs(b.chance - b.kalshi) >= 0.02) out.push({ k: 'MARKETS DISAGREE', text: `Polymarket has ${name} at ${Math.round(b.chance * 100)}%, Kalshi at ${Math.round(b.kalshi * 100)}%.`, tone: '' });
  const m = edge?.model; const px = b?.chance ?? b?.kalshi;
  if (m && px != null && Math.abs(m.b - px) >= 0.05) out.push({ k: 'MODEL AND MARKET', text: `ESPN's model gives ${name} ${Math.round(m.b * 100)}%, the market ${Math.round(px * 100)}%.`, tone: m.b > px ? 'b' : 'a' });
  return out;
}

// ESPN's shot spots → a point on our drawn floor. Away shots on the left basket, home on the right. x 0-50 across, y 0-47 from the baseline.
export function shotPoint(p, W = 188, H = 100) {
  const across = (Number(p.x) / 50) * H; const deep = Math.min(47, Number(p.y)) / 94 * W;
  return p.side === 'a' ? [deep, across] : [W - deep, H - across];
}
