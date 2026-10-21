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

describe('/dev/null shell', () => {
  const { parseCmd, nullPosts } = require('./FeedX');
  test('commands parse like a shell', () => {
    expect(parseCmd('> /dev/null @Spammer')).toEqual({ op: 'null', arg: 'spammer' });
    expect(parseCmd('cat feed | > /dev/null bob')).toEqual({ op: 'null', arg: 'bob' });
    expect(parseCmd('unnull @bob')).toEqual({ op: 'unnull', arg: 'bob' });
    expect(parseCmd('grep -i "$SOL"')).toEqual({ op: 'grep', arg: '$sol' });
    expect(parseCmd('top')).toEqual({ op: 'tab', arg: 'trending' });
    expect(parseCmd('ls ~/saved')).toEqual({ op: 'tab', arg: 'saved' });
    expect(parseCmd('rm -rf /')).toEqual({ op: 'bad', arg: 'rm' });
    expect(parseCmd('  ')).toBeNull();
  });
  test('voided authors and grep filter the timeline', () => {
    const p = [{ id: 1, handle: 'Bob', text: 'buy $SOL' }, { id: 2, author: 'amy', text: 'gm' }, { id: 3, handle: 'cy', text: 'SOL to 500' }];
    expect(nullPosts(p, new Set(['bob']), '').map(x => x.id)).toEqual([2, 3]);
    expect(nullPosts(p, new Set(), 'sol').map(x => x.id)).toEqual([1, 3]);
  });
});
