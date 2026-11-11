import { langOf, tint } from './codeTint';

test('code lines are coloured by kind and never lose a character', () => {
  const js = 'const a = fetch("x"); // go';
  const t = tint(js, 'js'); expect(t.map(x => x[0]).join('')).toBe(js);
  expect(t).toEqual(expect.arrayContaining([['const', 'k'], ['fetch', 'f'], ['"x"', 's'], ['// go', 'c']]));
  const html = '<div class="hero">Hi</div>'; expect(tint(html, 'html').map(x => x[0]).join('')).toBe(html); expect(tint(html, 'html')[0]).toEqual(['<div', 'k']);
  expect(tint('.hero { color: #9b6bff; }', 'css')).toEqual(expect.arrayContaining([['color', 'k'], ['#9b6bff', 'n']]));
  expect([langOf('a/b.css'), langOf('x.js'), langOf('index.html')]).toEqual(['css', 'js', 'html']);
  expect(tint('', 'js')).toEqual([]);
});
