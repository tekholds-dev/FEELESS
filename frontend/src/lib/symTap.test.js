import { symOf } from './symTap';
const el = (html) => { const d = document.createElement('div'); d.innerHTML = html; document.body.appendChild(d); return d; };
test('a bare ticker is a coin, a dollar amount or a ticker inside a button is not', () => {
  const r = el('<b id="a">$EXFIL</b><b id="b">$2.76</b><button><b id="c">$DCT</b></button><span id="d">$JEANPHIL <i>x</i></span>');
  expect(symOf(r.querySelector('#a'), r)).toBe('EXFIL');
  expect(symOf(r.querySelector('#b'), r)).toBeNull();
  expect(symOf(r.querySelector('#c'), r)).toBeNull();
  expect(symOf(r.querySelector('#d'), r)).toBeNull();
});
