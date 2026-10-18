import { shareLinks, SHARE_TO } from './socialShare';

test('cross-post opens each platform’s own compose page, pre-filled, links http(s) only', () => {
  const s = shareLinks('LFG $FEE', 'https://feeless.app/x');
  expect(s.x).toBe('https://x.com/intent/post?text=LFG%20%24FEE%20https%3A%2F%2Ffeeless.app%2Fx');
  expect(s.reddit.startsWith('https://www.reddit.com/submit?title=LFG')).toBe(true);
  expect(shareLinks('hi', 'javascript:alert(1)').x).toBe('https://x.com/intent/post?text=hi');
  expect(SHARE_TO.map(r => r[0]).every(k => s[k])).toBe(true);
});
