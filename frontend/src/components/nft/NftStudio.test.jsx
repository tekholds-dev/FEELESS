import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'Own1111111111111111111111111111111111111111' }, provider: {}, connect: jest.fn() }) }));
jest.mock('../../lib/cardImage', () => ({ uploadCardImage: async () => '/api/reputation/uploads/' + 'a'.repeat(32) + '.webp' }));
jest.mock('../../lib/metaplexCore', () => ({ coreDrop: (...a) => mockDrop(...a), coreCreateCollection: async () => ({ address: 'Coxx1111111111111111111111111111111111111111', signature: '5sig' }) }));
const mockDrop = jest.fn(async ({ recipients }) => [{ signature: 's1', assets: recipients.map((o, i) => ({ owner: o, address: `A${i}` })) }]);
const { NftStudio } = require('./NftStudio');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const setVal = (el, v) => { const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
const W1 = 'Aaaa1111111111111111111111111111111111111111', W2 = 'Bbbb1111111111111111111111111111111111111111';
const CARD = { key: 'badge:og', kind: 'badge', title: 'OG', subtitle: 'FEELESS badge', glyph: '⭐', lore: 'Here first.', design: 'holo', rarity: 'epic', holders: 2, earns: [] };
const PLATFORMS = { metaplex: { ready: true }, crossmint: { ready: true, env: 'staging' }, underdog: { ready: false, how: 'Add UNDERDOG_API_KEY' } };

test('create a Crossmint collection from a card, then drop it with the typed confirmation', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [CARD] }) }));
  const cols = [];
  const call = jest.fn(async (path, o) => {
    if (path === '/admin/nft') return { platforms: PLATFORMS, collections: cols };
    if (path === '/admin/nft/collections') { const c = { ...JSON.parse(o.body), id: 'c1', status: 'live', address: 'cm-1', royaltyBps: 500, uri: 'https://f.xyz/api/reputation/nft-meta/c1.json', drops: [], platform: 'crossmint' }; cols.push(c); return c; }
    if (path === '/admin/nft/holders/badge:og') return { wallets: [W1, W2] };
    if (path.endsWith('/drop')) return { minted: 2, failed: [] };
    return {};
  });
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<NftStudio call={call} />); });
  await act(async () => { el.querySelector('[data-testid="nft-new"]').click(); });
  await act(async () => { el.querySelector('.mc-pick').click(); });
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent === 'Platform →').click(); });
  expect(el.querySelector('[data-testid="nft-platform-underdog"]').disabled).toBe(true);
  await act(async () => { el.querySelector('[data-testid="nft-platform-crossmint"]').click(); });
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent === 'Review →').click(); });
  if (process.env.DUMP_PANEL) require('fs').writeFileSync('/tmp/claude-0/panels.html', el.innerHTML);
  await act(async () => { el.querySelector('[data-testid="nft-create"]').click(); });
  expect(JSON.parse(call.mock.calls.find(c => c[0] === '/admin/nft/collections')[1].body)).toMatchObject({ platform: 'crossmint', cardKey: 'badge:og', name: 'OG' });
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent.startsWith('Load everyone')).click(); });
  const drop = el.querySelector('[data-testid="nft-drop"]');
  expect(drop.disabled).toBe(true);
  await act(async () => { setVal(el.querySelector('input[placeholder="DROP 2"]'), 'DROP 2'); });
  await act(async () => { el.querySelector('[data-testid="nft-drop"]').click(); });
  expect(JSON.parse(call.mock.calls.find(c => c[0].endsWith('/drop'))[1].body)).toEqual({ to: [W1, W2], confirm: 'DROP 2' });
  act(() => root.unmount());
});

test('Metaplex drop: minted in the browser, then each transaction is recorded', async () => {
  require('sonner').toast.error.mockClear();
  mockDrop.mockImplementation(async ({ recipients }) => [{ signature: 's1', assets: recipients.map((o, i) => ({ owner: o, address: `A${i}` })) }]);
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [CARD] }) }));
  const col = { id: 'm1', name: 'Core OG', symbol: 'OG', platform: 'metaplex', status: 'live', address: 'Coxx1111111111111111111111111111111111111111', cardKey: 'badge:og', royaltyBps: 0, uri: 'https://f.xyz/api/reputation/nft-meta/m1.json', drops: [], image: '/x.webp' };
  const call = jest.fn(async path => (path === '/admin/nft' ? { platforms: PLATFORMS, collections: [col] } : { ...col }));
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<NftStudio call={call} />); });
  await act(async () => { el.querySelector('.nft-tile').click(); });
  await act(async () => { setVal(el.querySelector('textarea[aria-label="Wallets to drop to"]'), `${W1}\n${W2}\n${W1}`); });
  await act(async () => { el.querySelector('[data-testid="nft-drop"]').click(); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(mockDrop.mock.calls[0][0]).toMatchObject({ collection: col.address, recipients: [W1, W2], start: 1 });
  expect(mockDrop.mock.calls[0][0].uriFor(2)).toBe('https://f.xyz/api/reputation/nft-meta/m1-2.json');
  expect(require('sonner').toast.error.mock.calls).toEqual([]);
  expect(JSON.parse(call.mock.calls.find(c => c[0] === '/admin/nft/collections/m1/onchain')[1].body).assets).toHaveLength(2);
  act(() => root.unmount());
});
