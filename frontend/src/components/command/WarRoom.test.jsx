import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { WarRoom } from './WarRoom';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const FIX = {
  counts: { events: 3, captures: 1, canaries: 2, opens: 1, keyUses: 0, nets: 1, revoked: 0, reports: 1 },
  feed: [
    { seq: 3, at: Date.now() / 1000, kind: 'harden', ip: '8.8.8.9', net: '8.8.8.0/24', method: '', path: '', action: 'banned a subnet' },
    { seq: 2, at: Date.now() / 1000 - 5, kind: 'decoy', ip: '9.9.9.9', net: '9.9.9.0/24', method: 'GET', path: '/.env', action: 'served a decoy + captured' },
  ],
  timeline: [{ h: Math.floor(Date.now() / 3600000) * 3600, decoy: 1, harden: 1 }],
  captures: [{ at: Date.now() / 1000, ip: '9.9.9.9', ua: 'python-requests', method: 'GET', path: '/.env', bodyLen: 0 }],
  canaries: [], hits: [{ at: Date.now() / 1000, tok: 'a', ip: '5.6.7.8', ua: 'Mozilla', lang: 'ru' }],
  nets: [{ net: '8.8.8.0/24', left: 600 }], moves: [{ kind: 'ban-net', net: '8.8.8.0/24', at: Date.now() / 1000, why: 'scanners' }],
  reports: [{ at: Date.now() / 1000, wallet: 'W1', detail: 'found a thing' }],
  hardening: { items: [{ id: 'drift', attack: 'Drift $285M', how: 'social eng', item: 'verify signed==quoted', state: 'done', source: 'x' }], counts: { done: 1 }, total: 1 },
  encyclopedia: { intro: 'how attacks work', entries: [{ id: 'recon', name: 'Reconnaissance', how: 'bots probe', defence: 'decoys' }], total: 1 },
  bounty: { intro: 'report it', inScope: ['the API'], outOfScope: ['DoS'], rules: ['report privately'], severity: [] },
};

async function mount(call) {
  document.body.classList.add('fx-lite');
  const host = document.createElement('div'); document.body.appendChild(host);
  const root = createRoot(host);
  await act(async () => { root.render(<WarRoom call={call} />); });
  await act(async () => { await Promise.resolve(); });
  return { host, root };
}

test('War Room renders the live feed, hardening list, encyclopedia and bounty from one call', async () => {
  const call = jest.fn(() => Promise.resolve(FIX));
  const { host } = await mount(call);
  expect(host.querySelector('[data-testid="war-room"]')).toBeTruthy();
  expect(host.querySelector('[data-testid="war-feed"]')).toBeTruthy();
  expect(host.querySelector('[data-testid="war-trace-wallet"]')).toBeTruthy();
  expect(host.textContent).toContain('banned a subnet');
  expect(host.textContent).toContain('Drift $285M');
  expect(host.textContent).toContain('Reconnaissance');
  expect(call).toHaveBeenCalledWith('/admin/security/war-room');
});

test('War Room shows the error state when the load fails', async () => {
  const call = jest.fn(() => Promise.reject(new Error('nope')));
  const { host } = await mount(call);
  expect(host.textContent).toContain('nope');
});
