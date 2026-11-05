import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { collectivePrint, part, pickTwo, printOf, scoreOf } from '../../lib/proofprint';
import { ProofprintFolder } from './Proofprint';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
test('a score is the real result, and no result means no segment', () => {
  expect(scoreOf({ kind: 'pow', value: 50 })).toBe(100); expect(scoreOf({ kind: 'pow', value: 0 })).toBe(50); expect(scoreOf({ kind: 'pop', value: -80 })).toBe(0); expect(scoreOf({ kind: 'pob', value: 1 })).toBe(85); expect(scoreOf({ kind: 'poc', value: -1 })).toBe(25); expect(scoreOf({ kind: 'pow', value: null })).toBeNull();
});
test('the print grows a ridge every 12 proofs and never draws an open proof', () => {
  const rows = Array.from({ length: 26 }, (_, i) => ({ kind: 'pow', id: `w${i}`, at: i, value: 10 })); const p = printOf([...rows, { kind: 'pow', id: 'open', at: 99, value: null }]);
  expect(p.total).toBe(26); expect(p.rings.map(r => r.checkpoints.length)).toEqual([12, 12, 2]); expect(printOf([]).total).toBe(0);
  expect(part('whorl', 2, 0, 1)).not.toEqual(part('arch', 2, 0, 1));
});
test('at most the best 2 snapshots show, from different sites', () => {
  expect(pickTwo([{ file: 'a', site: 'dex' }, { file: 'b', site: 'dex' }, { file: 'c', site: 'rug' }]).map(s => s.file)).toEqual(['c', 'b']); expect(pickTwo(undefined)).toEqual([]);
});
test('the Collective print counts only proofs really sent', () => {
  const p = collectivePrint([{ id: 'a', agent: 'H', pct: 60, sent: { sig: 's' } }, { id: 'b', agent: 'H', pct: 70 }, { id: 'c', agent: 'N', pct: 90, sent: { sig: 't' } }]);
  expect(p.total).toBe(2); expect(p.rings.map(r => r.name)).toEqual(['H', 'N']);
});
test('the folder opens a proof card and saves the look', async () => {
  const d = { powFolders: [{ id: 'w1', at: 100, soldAt: 100, name: 'PoW #1', status: 'closed', pnlPct: 60, pnlSol: 0.5 }] }; const work = jest.fn(async () => ({}));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ProofprintFolder cat={{ id: 'c' }} d={d} work={work} pool={{ pool: { owedUsd: 1, ratePerSecUsd: 0 }, readAt: 1, printLevel: 12, printStyle: { shape: 'arch', ink: 'blue' } }} />); });
  expect(el.querySelector('[data-testid="pp-shape-arch"]').getAttribute('aria-pressed')).toBe('true');
  await act(async () => { el.querySelector('.pp-hit').dispatchEvent(new MouseEvent('click', { bubbles: true })); });
  expect(el.querySelector('[data-testid="pp-card"]').textContent).toContain('+60.0%');
  await act(async () => { el.querySelector('[data-testid="pp-shape-left"]').click(); });
  expect(work).toHaveBeenCalledWith('c', { op: 'print_style', text: 'left', job: 'blue' });
  await act(async () => root.unmount());
});
