import fs from 'fs';
import path from 'path';
const css = f => fs.readFileSync(path.join(__dirname, f), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
const rule = (src, sel) => { const i = src.indexOf(`${sel} {`); return i < 0 ? '' : src.slice(i, src.indexOf('}', i)); };

// 🖥 owner 2026-11-21 (screenshot, /terminal/fuse arena in the Desk look): the site-wide smoke drew OVER pages. It is a negative layer now —
// under every piece of content, positioned or not — and it carries the page colour itself, so nothing else paints a wall over it.
test('the Desk look background sits behind ALL content', () => {
  const d = css('deskLayout.css'); const bg = rule(d, '.dk-site-bg');
  expect(bg).toMatch(/position:\s*fixed/); expect(bg).toMatch(/z-index:\s*-1/); expect(bg).toMatch(/pointer-events:\s*none/); expect(bg).toMatch(/background:\s*var\(--m-bg\)/);
  expect(d).toMatch(/html\[data-layout="desk"\] body \{ background: transparent !important; \}/);
  expect(rule(d, '.dk-site-bg .dkl-bg')).toMatch(/--dk-acc:\s*var\(--m-accent\)/);   // neutral / FEELESS green, never a page's own hue
});
test('the Fuse arena: league bars never cover their labels, a % never wraps, the FUSE ROOM tab and the tips pill stay off the content', () => {
  const p = css('primeLeague.css');
  expect(rule(p, '.pls-lane u')).toMatch(/overflow:\s*hidden/); expect(rule(p, '.pls-lane u')).toMatch(/text-overflow:\s*ellipsis/);
  expect(rule(p, '.pls-lane em')).toMatch(/white-space:\s*nowrap/);
  expect(css('fuseRoom.css')).toMatch(/body:has\(> \.frm-tab\) \.terminal-main \{ padding-right: 34px; \}/);
  const t = rule(css('firstTips.css'), '.ft-skip'); expect(t).toMatch(/right:\s*16px/); expect(t).not.toMatch(/left:/);   // not over the sidebar
});

// Slice 34 ⛔: the trench dash's coin header was ~380 px before the chart. It is one compact band now — nothing dropped, the 5 numbers fit.
test('the trench dash coin header is compact and keeps every piece', () => {
  const t = css('trenchFlip.css');
  expect(rule(t, '.token-focus.is-v2 > .focus-header')).toMatch(/padding:\s*8px 12px 4px/);
  expect(rule(t, '.token-focus.is-v2 .token-heading')).toMatch(/flex-wrap:\s*wrap/);
  expect(rule(t, '.token-focus.is-v2 > .coin-passport')).toMatch(/flex-wrap:\s*nowrap/);
  expect(rule(t, '.token-focus.is-v2 > .coin-passport')).toMatch(/overflow-x:\s*auto/);   // every chip still there, one scroll row
  expect(rule(t, '.token-focus.is-v2 > .token-metrics :is(strong, .anim-num, .anim-num .digit)')).toMatch(/font-size:\s*13px/);
  const hides = (t.match(/[^{}]*\{[^}]*\}/g) || []).filter(r => r.includes('.token-focus.is-v2') && /display:\s*none/.test(r) && !r.includes('scrollbar'));
  expect(hides).toEqual([]);   // no header piece is hidden (only scrollbars are)
});
