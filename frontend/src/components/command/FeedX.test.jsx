import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('react-router-dom', () => ({ Link: ({ children, ...p }) => <a {...p}>{children}</a>, useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('../EcosystemChat', () => () => <div data-testid="rooms-chat" />);
jest.mock('../../hooks/useMarket', () => ({ useMarket: () => ({ data: { pairs: [] } }) }));

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('📰 bubbles: All clears the rest, sites toggle into a mix, never empty', () => {
  const { toggleSrc } = require('./FeedX');
  expect(toggleSrc(['all'], 'pump')).toEqual(['pump']);
  expect(toggleSrc(['pump'], 'telegram')).toEqual(['pump', 'telegram']);
  expect(toggleSrc(['pump'], 'pump')).toEqual(['all']);
  expect(toggleSrc(['pump', 'telegram'], 'all')).toEqual(['all']);
});

test('📰 FEEd shows the mixed timeline with cross-post links; FEELESS alone = the live rooms', async () => {
  localStorage.clear();
  const posts = [{ id: 'telegram:p/1', src: 'telegram', author: 'Pump.fun', handle: 'pumpfun', text: 'gm trenches', at: Date.now() / 1000 - 60, url: 'https://t.me/p/1' },
    { id: 'pump:1', src: 'pump', author: 'caller', text: 'send it', at: Date.now() / 1000 - 120, coin: { symbol: 'ABC', mint: 'M' } }];
  const real = global.fetch;
  global.fetch = jest.fn(u => Promise.resolve({ ok: true, json: () => Promise.resolve(String(u).includes('social-feed') ? { posts } : { rows: [] }) }));
  const { FeedPanel } = require('./FeedX');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FeedPanel />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(el.querySelectorAll('[data-testid="feed-post"]').length).toBe(2);
  expect(el.querySelector('[data-testid="feed-share-x"]').getAttribute('aria-disabled')).toBe('true');   // empty box → nothing to post
  await act(async () => { el.querySelector('[data-testid="feed-src-feeless"]').click(); });
  expect(el.querySelector('[data-testid="rooms-chat"]')).not.toBeNull();
  expect(JSON.parse(localStorage.getItem('feeless.feedSrc'))).toEqual(['feeless']);
  act(() => root.unmount()); global.fetch = real;
});

test('FEEd v3: the new-posts pill counts only posts newer than what is on screen; counts read like X', () => {
  const { newSince, kWord } = require('./FeedX');
  expect(newSince([{ at: 10 }, { at: 20 }, { at: 30 }], 20)).toBe(1);
  expect(newSince([], 0)).toBe(0);
  expect(kWord(999)).toBe('999'); expect(kWord(1234)).toBe('1.2K'); expect(kWord(2500000)).toBe('2.5M');
});
