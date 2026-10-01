import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FUSE_TAG, pickFuse } from '../lib/fuseFeed';
import { FuseChatCard } from './FuseChatCard';
import { FusePnl } from './FuseHQ';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'W' } }) }));
jest.mock('./FuseGo', () => ({ FuseGo: ({ legs, fuse }) => <div data-testid="go">{fuse.id}:{legs.map(l => l.sol).join('+')}</div> }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
const F = { id: 'abc123def0', name: 'FEE Core', emoji: '⚛️', index: 104.2, tvlUsd: 2e6, aprEst: 88, stats: { buys: 3 }, score: { grade: 'A', parts: [] },
  legs: [{ pairAddress: 'P1', symbol: 'SOL', weight: 60, baseAddress: 'X' }, { pairAddress: 'P2', symbol: 'FEE', weight: 40, baseAddress: 'Y' }] };

test('/fuse tag + pick: name match, else best', () => {
  expect(FUSE_TAG.exec('⚛️ FEE Core ⚛️ fuse:abc123def0')[1]).toBe('abc123def0');
  expect(pickFuse([F, { ...F, name: 'Meme Mix' }], 'meme').name).toBe('Meme Mix');
  expect(pickFuse([F], '').id).toBe(F.id);
});

test('chat card: live numbers, amount → one-click with the fuse id and an exact split', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ fuses: [F] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FuseChatCard id="abc123def0" />); }); await tick(10);
  expect(el.textContent).toContain('FEE Core'); expect(el.textContent).toContain('104.2');
  await act(async () => { el.querySelector('[data-testid="fcc-amt-0.5"]').click(); });
  expect(el.querySelector('[data-testid="go"]').textContent).toBe('abc123def0:0.3+0.2');
});

test('trader P&L strip shows total and each fuse', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ positions: 1, pnlUsd: 1.5, pnlPct: 30, valueUsd: 6.5, rows: [{ id: 'x', name: 'Lab fuse', at: Date.now() / 1000, pnlUsd: 1.5, pnlPct: 30, legs: [{ symbol: 'A' }] }] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FusePnl />); }); await tick(10);
  expect(el.textContent).toContain('$1.50'); expect(el.textContent).toContain('+30.0%');
});
