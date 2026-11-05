import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { PATTERNS, collectivePrint, growthExample, identityOf, inkOf, part, pickTwo, printOf, scoreOf, spans } from '../../lib/proofprint';
import { ProofprintFolder } from './Proofprint';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
test('a score is the real result, and no result means no segment', () => {
  expect(scoreOf({ kind: 'pow', value: 50 })).toBe(100); expect(scoreOf({ kind: 'pow', value: 0 })).toBe(50); expect(scoreOf({ kind: 'pop', value: -80 })).toBe(0); expect(scoreOf({ kind: 'pob', value: 1 })).toBe(85); expect(scoreOf({ kind: 'poc', value: -1 })).toBe(25); expect(scoreOf({ kind: 'pow', value: null })).toBeNull();
});
test('the print grows a ridge every 12 proofs and never draws an open proof', () => {
  const rows = Array.from({ length: 26 }, (_, i) => ({ kind: 'pow', id: `w${i}`, at: i, value: 10 })); const p = printOf([...rows, { kind: 'pow', id: 'open', at: 99, value: null }]);
  expect(p.total).toBe(26); expect(p.rings.map(r => r.checkpoints.length)).toEqual([12, 12, 2]); expect(printOf([]).total).toBe(0);
  expect(part(identityOf('a'), 2, 0, 1)).not.toEqual(part(identityOf('b'), 2, 0, 1));
});
test('at most the best 2 snapshots show, from different sites', () => {
  expect(pickTwo([{ file: 'a', site: 'dex' }, { file: 'b', site: 'dex' }, { file: 'c', site: 'rug' }]).map(s => s.file)).toEqual(['c', 'b']); expect(pickTwo(undefined)).toEqual([]);
});
test('the Collective print counts only proofs really sent', () => {
  const p = collectivePrint([{ id: 'a', agent: 'H', pct: 60, sent: { sig: 's' } }, { id: 'b', agent: 'H', pct: 70 }, { id: 'c', agent: 'N', pct: 90, sent: { sig: 't' } }]);
  expect(p.total).toBe(2); expect(p.rings.map(r => r.name)).toEqual(['H', 'N']);
});
test('each proof is a green, yellow or red section, and a bigger result takes more of the line', () => {
  expect(inkOf(90)).toBe('#4dea8f'); expect(inkOf(60)).toBe('#f5cf52'); expect(inkOf(20)).toBe('#f2697a');
  const sp = spans([{ score: 100 }, { score: 50 }, { score: 0 }]); expect(sp[0][1] - sp[0][0]).toBeGreaterThan(sp[1][1] - sp[1][0]); expect(sp[1][1]).toBeCloseTo(sp[2][0]);
  expect(spans(Array.from({ length: 12 }, () => ({ score: 100 })))[11][1]).toBeLessThanOrEqual(Math.PI * 2 + 1e-9);
});
test('every agent has its own print: 30 patterns, 30 inks, and no two curves alike', () => {
  expect(PATTERNS).toHaveLength(30); expect(new Set(PATTERNS).size).toBe(30);
  const ids = Array.from({ length: 400 }, (_, i) => identityOf(`seed-${i}`));
  expect(new Set(ids.map(x => x.pattern)).size).toBe(30); expect(new Set(ids.map(x => x.inkN)).size).toBe(30);
  expect(new Set(ids.map(x => part(x, 6, 0, 3))).size).toBe(400);
  expect(identityOf('seed-1').code).toBe(identityOf('seed-1').code); expect(identityOf('seed-1').code).toMatch(/^FP-[0-9A-F]{4}-[0-9A-F]{4}$/);
});
const RULES = { skimPct: 20, splitPct: 75, splitMaxPct: 78, halfLifeDays: 30, halfLifeMinDays: 15, potPct: 50, potHalfLifeDays: 30, weightMaxX: 2, earnRoomX: 1, txnSmallPct: 5, txnMidPct: 3, txnBigPct: 1, txnSmallUsd: 10, txnBigUsd: 100, boostMode: 'payout' };
test('the year example: no trading means only its own money back, and trading adds the fee share', () => {
  const none = growthExample(RULES, { tradeDay: 0, sendWeek: 10 }).pop(); expect(none.fee).toBe(0); expect(none.own / none.sent).toBeLessThan(0.6);
  const some = growthExample(RULES, { tradeDay: 50, sendWeek: 10 }).pop(); expect(some.fee).toBeGreaterThan(0); expect(some.keep).toBeGreaterThan(none.keep);
  const full = growthExample(RULES, { tradeDay: 50, sendWeek: 10, boost: 1 }).pop(); expect(full.own).toBeGreaterThan(some.own);
});
test('the wired card opens on the line and any click lets go, and nothing picks a look', async () => {
  const d = { powFolders: [{ id: 'w1', at: 100, soldAt: 100, name: 'PoW #1', status: 'closed', pnlPct: 60, pnlSol: 0.5 }] };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ProofprintFolder cat={{ id: 'c' }} d={d} pool={{ pool: { owedUsd: 1, ratePerSecUsd: 0 }, readAt: 1, printLevel: 12, printSeed: 'abc' }} />); });
  expect(el.querySelector('[data-testid="pp-id"]').textContent).toContain(identityOf('abc').code); expect(el.querySelector('[data-testid^="pp-shape"]')).toBeNull();
  await act(async () => { el.querySelector('.pp-hit').dispatchEvent(new MouseEvent('click', { bubbles: true })); });
  expect(el.querySelector('[data-testid="pp-card"]').textContent).toContain('+60.0%'); expect(el.querySelector('.pp-wire path')).toBeTruthy();
  await act(async () => { el.querySelector('[data-testid="pp-stage"]').dispatchEvent(new MouseEvent('click', { bubbles: true })); });
  expect(el.querySelector('[data-testid="pp-card"]')).toBeNull();
  await act(async () => { el.querySelector('.pp-hit').dispatchEvent(new MouseEvent('click', { bubbles: true })); });
  await act(async () => { el.querySelector('.pp-hit').dispatchEvent(new MouseEvent('click', { bubbles: true })); });
  expect(el.querySelector('[data-testid="pp-card"]')).toBeNull();
  await act(async () => { el.querySelector('[data-testid="pp-tab-earn"]').click(); });
  expect(el.textContent).toContain('Nothing sent yet');
  await act(async () => root.unmount());
});
