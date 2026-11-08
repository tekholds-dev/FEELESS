import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';

jest.mock('./AtomPrint', () => ({ __esModule: true, default: ({ proofs }) => <div data-testid="cll-print">{(proofs || []).length} atoms</div> }));
jest.mock('./KeepDeal', () => ({ KeepDeal: ({ start, testid }) => <div data-testid={testid}>{start.usd}</div>, StakeStory: ({ testid }) => <div data-testid={testid} />, ScoreLadder: ({ testid }) => <div data-testid={testid} /> }));
jest.mock('./SplitFlow', () => ({ usePoolRules: () => ({ score: { top: 300 } }) }));
jest.mock('../../lib/adminCall', () => ({ useAdmin: () => ({ isAdmin: false, call: jest.fn() }) }));

test('the front page: real atoms from the safe feed, three pages, $1 first, and no stash or internal names', async () => {
  const urls = []; global.fetch = jest.fn(async u => { urls.push(String(u)); return { ok: true, json: async () => (String(u).includes('atoms') ? { proofs: [{ id: 'a', kind: 'PoW', result: 'won', active: true }] } : { theme: 'NEBULA', glow: 70 }) }; });
  const { CollectiveLanding } = require('./CollectiveLanding');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CollectiveLanding />); }); await act(async () => { await new Promise(r => { setTimeout(r, 30); }); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(urls.some(u => u.includes('/collective/atoms'))).toBe(true); expect(urls.some(u => u.includes('colony/flow'))).toBe(false); expect(q('cll-print').textContent).toBe('1 atoms');
  expect([...el.querySelectorAll('[role=tab]')].map(b => b.textContent)).toEqual(['The print', 'How a proof works', 'How it pays']); expect(q('cll-view-stash')).toBeNull();
  await act(async () => { q('cll-cta').click(); }); expect(q('cll-walk')).toBeTruthy(); expect(el.textContent).toContain('Tally');
  await act(async () => { q('cll-view-pays').click(); }); expect(q('cll-deal').textContent).toBe('1'); expect(q('cll-pays').textContent).toContain('no money moves'); expect(q('cll-view-try')).toBeNull(); expect(q('cll-ladder')).toBeNull();
  expect(el.textContent).not.toMatch(/OSSY|G4/);
  el.remove();
});
