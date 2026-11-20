import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { PobDash, SlipVerdict } from './PobDash';

// 🎲 Slice 13: the PoB folder dashboard. Wired: a tap → the PoB door (op pob, the same as File a bid) → the engine; his slip → op pob with
// his legs → the minds check it (backend tests: test_slice13_pob_dash.py). Nothing here sends an order.
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);
async function mount(node) { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await act(async () => { await Promise.resolve(); }); return el; }
const soon = h => new Date(Date.now() + h * 3600e3).toISOString().slice(0, 16) + 'Z';
const DASH = {
  totals: { filings: 3, real: 2, won: 1, lost: 1, live: 0, cost: 3.06, pnl: -1.06, atRisk: 0, judged: 2, avg: 45, passed: 0, tests: 1, waiting: 0, spent: 0.2 },
  curve: [{ at: 1, pnl: -1.36, n: 1, step: -1.36 }, { at: 2, pnl: -1.06, n: 2, step: 0.3 }],
  rows: [{ id: 'pob2', n: 2, topic: 'Bucks vs Heat team to win', mode: 'team', result: 'won', bids: [{ filled: 2, side: 'yes', price: 0.85 }], pnl: 0.3, judge: { state: 'scored', score: 60, verdict: 'fail', by: ['ossy'] }, game: null, ticket: null },
    { id: 'pob3', n: 3, topic: 'Bucks vs Heat parlay slip 3 legs', mode: 'parlay', result: 'refused', bids: [], pnl: null, judge: { state: 'none', why: 'Every judge built this proof' }, ticket: { say: 'No market maker quoted.' } }],
  odds: [{ id: '1', sport: 'nhl', label: 'Kings at Maple Leafs', start: soon(3), line: 'TOR -115', total: 6.5, teams: [{ short: 'Kings', kalshi: 0.48, poly: 0.4 }, { short: 'Maple Leafs', kalshi: 0.53, poly: 0.6 }], agree: true, sources: 2, age: 600, stale: false }],
  oddsAt: Date.now() / 1000 - 600,
  next: [{ key: '1', game: '1', sport: 'nhl', start: soon(3), mins: 180, teams: ['Kings', 'Maple Leafs'], kalshi: [0.48, 0.53], poly: [0.4, 0.6], why: 'Kalshi and Polymarket differ by 8 pts on Kings', filed: 0,
    files: [{ mode: 'team', topic: 'Kings vs Maple Leafs team to win' }, { mode: 'parlay', topic: 'Kings vs Maple Leafs parlay slip 3 legs' }]}],
  live: [{ id: '7', sport: 'nba', status: 'Q3', teams: [{ short: 'Bucks', score: '70' }, { short: 'Heat', score: '66' }], label: 'Bucks vs Heat', mine: true }],
  upcoming: 9,
};
const MENU = { topic: 'Kings vs Maple Leafs parlay slip 3 legs', min: 2, max: 4, legs: [
  { ticker: 'KXNHLGAME-26NOV19LATOR-TOR', kind: 'team', over: 'Toronto', under: 'NOT Toronto', yes: 0.53, no: 0.48 },
  { ticker: 'KXNHLGAME-26NOV19LATOR-LA', kind: 'team', over: 'Los Angeles', under: 'NOT Los Angeles', yes: 0.48, no: 0.53 },
  { ticker: 'KXNHLPTS-26NOV19LATOR-TORMMARNER16-1', kind: 'player', stat: 'points', line: 0.5, over: 'Mitch Marner OVER 0.5 points', under: 'Mitch Marner UNDER 0.5 points', yes: 0.62, no: 0.4 }] };

beforeEach(() => { try { localStorage.clear(); } catch { /* none */ } document.body.classList.add('fx-lite'); });

test('it opens on the numbers: P&L without fees, the record, the judges, tonight, and live games', async () => {
  const el = await mount(<PobDash catId="c" work={async () => DASH} onOpen={() => {}} />);
  expect(q(el, 'pdb-pnl').textContent).toBe('−$1.06'); expect(q(el, 'pdb-record').textContent).toBe('1–1');
  expect(q(el, 'pdb-judges').textContent).toContain('45'); expect(q(el, 'pdb-tonight').textContent).toContain('1');
  expect(q(el, 'pdb-hero').textContent).toContain('no fees'); expect(q(el, 'pdb-live').textContent).toContain('YOURS');
});

test('one tap on a suggestion files it through the PoB door, and it is held while a PoB runs', async () => {
  const sent = []; const work = async (_c, b) => { sent.push(b); return b.op === 'pob_dash' ? DASH : { ok: true }; };
  const el = await mount(<PobDash catId="c" work={work} onOpen={() => {}} />);
  await act(async () => { q(el, 'pdb-file-1-team').click(); });
  expect(sent.filter(b => b.op === 'pob')).toEqual([{ op: 'pob', text: 'Kings vs Maple Leafs team to win' }]);
  expect(q(el, 'pdb-filed').textContent).toContain('Kings vs Maple Leafs team to win');
  const held = await mount(<PobDash catId="c" work={work} busy onOpen={() => {}} />);
  expect(q(held, 'pdb-file-1-parlay').disabled).toBe(true);
});

test('every tab: filings open their file, stash odds show their age, and no stash says so', async () => {
  const opened = []; const el = await mount(<PobDash catId="c" work={async () => DASH} onOpen={id => opened.push(id)} />);
  await act(async () => { q(el, 'pdb-tab-filings').click(); });
  expect(q(el, 'pdb-rows').textContent).toContain('+$0.30'); expect(q(el, 'pdb-rows').textContent).toContain('No money moved');
  await act(async () => { q(el, 'pdb-row-pob3').click(); }); expect(opened).toEqual(['pob3']);
  await act(async () => { q(el, 'pdb-tab-odds').click(); });
  expect(q(el, 'pdb-odds').textContent).toContain('10 min ago'); expect(q(el, 'pdb-odds').textContent).toContain('2 sources agree');
  localStorage.clear();   // the tab it remembers: a fresh visitor opens on Next to file
  const none = await mount(<PobDash catId="c" work={async () => ({ ...DASH, odds: [], oddsAt: null, next: [] })} onOpen={() => {}} />);
  expect(q(none, 'pdb-next-none')).not.toBeNull();
  await act(async () => { q(none, 'pdb-tab-odds').click(); }); expect(q(none, 'pdb-odds-none').textContent).toContain('COMP reads');
});

test('his own slip: legs from Kalshi\'s list, 2 to 4, then op pob with exactly his legs', async () => {
  const sent = []; const work = async (_c, b) => { sent.push(b); return b.op === 'pob_dash' ? DASH : b.op === 'pob_menu' ? MENU : { ok: true, topic: 'Kings vs Maple Leafs parlay slip 2 legs' }; };
  const el = await mount(<PobDash catId="c" work={work} onOpen={() => {}} />);
  await act(async () => { q(el, 'pdb-tab-slip').click(); });
  const sel = q(el, 'pdb-slip-game');
  await act(async () => { sel.value = '1'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  await act(async () => { await Promise.resolve(); });
  expect(sent.find(b => b.op === 'pob_menu')).toEqual({ op: 'pob_menu', text: 'Kings vs Maple Leafs parlay slip 3 legs' });
  await act(async () => { q(el, 'pdb-leg-0-yes').click(); });
  expect(q(el, 'pdb-slip-send').disabled).toBe(true);   // one leg is not a slip
  await act(async () => { q(el, 'pdb-leg-1-yes').click(); });
  expect(q(el, 'pdb-ticket').textContent).not.toContain('Toronto');   // one winner per game: Los Angeles replaced Toronto
  await act(async () => { q(el, 'pdb-leg-0-yes').click(); });
  await act(async () => { q(el, 'pdb-leg-2-no').click(); });
  expect(q(el, 'pdb-ticket').textContent).not.toContain('Los Angeles');
  expect(q(el, 'pdb-ticket').textContent).toContain('Mitch Marner UNDER 0.5 points');
  await act(async () => { q(el, 'pdb-slip-send').click(); });
  expect(sent.filter(b => b.op === 'pob')).toEqual([{ op: 'pob', text: 'Kings vs Maple Leafs parlay slip 3 legs', tools: { slip: [
    { ticker: 'KXNHLGAME-26NOV19LATOR-TOR', side: 'yes', title: 'Toronto' }, { ticker: 'KXNHLPTS-26NOV19LATOR-TORMMARNER16-1', side: 'no', title: 'Mitch Marner UNDER 0.5 points' }] } }]);
  expect(q(el, 'pdb-filed').textContent).toContain('parlay slip 2 legs');
});

test('his slip on its reading: each leg says which mind backed it, and a slip not backed whole says it was not sent', async () => {
  const v = { whole: false, say: 'Your slip is not sent: Toronto: gpt backs it, glm did not back it.', legs: [
    { ticker: 'T1', side: 'yes', title: 'Toronto', ok: false, minds: [{ name: 'gpt', backs: true, conf: 60, side: 'yes' }, { name: 'glm', backs: false, conf: null, side: null }] }] };
  const el = await mount(<SlipVerdict v={v} />);
  expect(q(el, 'pdb-verdict').textContent).toContain('not sent'); expect(q(el, 'pdb-verdict').textContent).toContain('✓ gpt');
  expect(q(el, 'pdb-verdict').textContent).toContain('✕ glm'); expect(q(el, 'pdb-verdict').textContent).toContain('glm did not back it');
  const none = await mount(<SlipVerdict v={null} />); expect(q(none, 'pdb-verdict')).toBeNull();
});
