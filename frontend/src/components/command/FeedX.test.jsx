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
  expect(el.querySelector('[data-testid="rooms-chat"]')).toBeNull();                         // ⚡ FEELESS = its posts on the timeline (E13)
  expect(el.querySelector('[data-testid="feed-timeline"]')).not.toBeNull();
  expect(JSON.parse(localStorage.getItem('feeless.feedSrc'))).toEqual(['feeless']);
  await act(async () => { el.querySelector('[data-testid="feed-rooms"]').click(); });
  expect(el.querySelector('[data-testid="rooms-chat"]')).not.toBeNull();                     // the live rooms: one tap on 💬 ROOMS
  act(() => root.unmount()); global.fetch = real;
});

test('FEEd v3: the new-posts pill counts only posts newer than what is on screen; counts read like X', () => {
  const { newSince, kWord } = require('./FeedX');
  expect(newSince([{ at: 10 }, { at: 20 }, { at: 30 }], 20)).toBe(1);
  expect(newSince([], 0)).toBe(0);
  expect(kWord(999)).toBe('999'); expect(kWord(1234)).toBe('1.2K'); expect(kWord(2500000)).toBe('2.5M');
});

test('only real X post links can be brought in', () => {
  const { isXPost } = require('./FeedX');
  expect(isXPost('https://x.com/aeyakovenko/status/1849011223344')).toBe(true);
  expect(isXPost('https://twitter.com/a/statuses/123456')).toBe(true);
  expect(isXPost('https://x.com/aeyakovenko')).toBe(false);
  expect(isXPost('https://evil.com/x.com/a/status/123456')).toBe(false);
});

test('dev-null tabs: trending ranks stars + replies, following / saved filter, hash is stable', () => {
  const { tabPosts, hashOf, authorKey } = require('./FeedX');
  const now = 1000000;
  const posts = [{ id: 'a', src: 'x', handle: 'bob', at: now - 10 }, { id: 'b', src: 'pump', handle: 'amy', at: now - 20 }, { id: 'c', src: 'x', handle: 'old', at: now - 90000 }];
  const counts = { a: { likes: 1 }, b: { likes: 1, comments: 2 }, c: { likes: 50 } };
  expect(tabPosts(posts, 'trending', counts, new Set(), new Set(), now).map(p => p.id)).toEqual(['b', 'a']);
  expect(tabPosts(posts, 'following', counts, new Set([authorKey(posts[0])]), new Set(), now).map(p => p.id)).toEqual(['a']);
  expect(tabPosts(posts, 'saved', counts, new Set(), new Set(['c']), now).map(p => p.id)).toEqual(['c']);
  expect(hashOf('a')).toBe(hashOf('a')); expect(hashOf('a')).toHaveLength(7);
});

describe('FEELESS call receipts', () => {
  const { xWord, ladderAt, stampOf, wireRows, tabPosts } = require('./FeedX');
  test('the multiple, its rail and its stamp', () => {
    expect(xWord(3.24)).toBe('3.2×'); expect(xWord(0.42)).toBe('0.42×'); expect(xWord(12.6)).toBe('13×'); expect(xWord(null)).toBe('—');
    expect(ladderAt(10)).toBe(1); expect(ladderAt(0.01)).toBe(0); expect(ladderAt(2)).toBeGreaterThan(ladderAt(1));
    expect(stampOf({ state: 'rug' })).toEqual(['☠', 'RUGGED']); expect(stampOf({})).toBeNull();
  });
  test('the wire leads with the biggest moves either way; heat and graveyard lenses', () => {
    const p = [{ id: 1, coin: { x: 1.1 } }, { id: 2, coin: { x: 0.1 } }, { id: 3, coin: { x: 4 } }, { id: 4 }];
    expect(wireRows(p).map(x => x.id)).toEqual([2, 3, 1]);
    expect(tabPosts(p, 'heat', {}, new Set(), new Set()).map(x => x.id)).toEqual([3, 1]);
    expect(tabPosts(p, 'grave', {}, new Set(), new Set()).map(x => x.id)).toEqual([2]);
  });
});

test('the pulse counts the last hour in 12 five-minute buckets, by site, and the coins called most', () => {
  const { feedPulse } = require('./FeedX');
  const now = 10_000;
  const p = feedPulse([{ at: now - 30, src: 'x', coin: { symbol: 'wif', mint: 'M1' } }, { at: now - 400, src: 'pump', coin: { symbol: 'WIF', mint: 'M1' } }, { at: now - 1000, src: 'x' }, { at: now - 7200, src: 'x', coin: { symbol: 'OLD' } }], now);
  expect(p.n).toBe(3); expect(p.buckets).toHaveLength(12); expect(p.buckets[11]).toBe(1); expect(p.buckets[10]).toBe(1);
  expect(p.bySrc).toEqual([['x', 2], ['pump', 1]]); expect(p.top).toEqual([{ sym: 'wif', mint: 'M1', n: 2 }]); expect(p.calls).toBe(2);
});

test('FEEd v5: a pasted CA is found, For you lifts calls / stars / follows, Calls lists coin posts, search and who-to-follow', () => {
  const { caOf, tabPosts, matchQ, whoToFollow, authorKey } = require('./FeedX');
  expect(caOf('aping 7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr now')).toBe('7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr');
  expect(caOf('gm trenches 0OIl')).toBeNull(); expect(caOf('')).toBeNull();
  const now = 100000;
  const p = [{ id: 'a', src: 'x', handle: 'bob', at: now - 100, text: 'gm' }, { id: 'b', src: 'pump', handle: 'amy', at: now - 1000, text: 'send $WIF', coin: { symbol: 'WIF', mint: 'M' } },
    { id: 'c', src: 'telegram', handle: 'cat', at: now - 5000, text: 'old' }];
  expect(tabPosts(p, 'foryou', {}, new Set(), new Set(), now).map(x => x.id)).toEqual(['b', 'a', 'c']);                  // a call gets +30 min
  expect(tabPosts(p, 'foryou', { c: { comments: 2 } }, new Set(), new Set(), now)[0].id).toBe('c');                       // 2 replies = +2h
  expect(tabPosts(p, 'calls', {}, new Set(), new Set(), now).map(x => x.id)).toEqual(['b']);
  expect(p.filter(x => matchQ(x, '$wif')).map(x => x.id)).toEqual(['b']); expect(p.filter(x => matchQ(x, '')).length).toBe(3);
  expect(whoToFollow(p, new Set([authorKey(p[0])])).map(r => r.p.id)).toEqual(['b', 'c']);                                // callers first, followed people never
});
