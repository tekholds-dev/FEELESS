jest.mock('react-router-dom', () => ({}), { virtual: true });
// eslint-disable-next-line import/first
import { recolorText } from './HolderTheme';

test('site recolor swaps the FEELESS green everywhere, keeping alpha', () => {
  const css = '.a{color:#9b6bff;border:1px solid #9b6bff55;background:rgba(155, 107, 255,.2);box-shadow:0 0 4px rgb(155, 107, 255)}.b{color:#9b6bffab0}';
  expect(recolorText(css, '#f5c451')).toBe('.a{color:#f5c451;border:1px solid #f5c45155;background:rgba(245, 196, 81,.2);box-shadow:0 0 4px rgb(245, 196, 81)}.b{color:#9b6bffab0}');
});

test('the whole brand family follows the theme (one gradient, one colour) and price-up greens never change', () => {
  const out = recolorText('.go{background:linear-gradient(135deg, rgb(124, 77, 255), rgb(155, 107, 255) 55%, rgb(255, 111, 191))}.hi{color:#b48cff;border-color:rgba(180, 140, 255, 0.4)}.up{color:#3ee58a}', '#a41934');
  expect(out).not.toMatch(/rgb\(124, 77, 255\)|rgb\(255, 111, 191\)|#b48cff|180, 140, 255/);   // no green left in the brand stops
  expect(out).toContain('rgb(164, 25, 52) 55%'); expect(out).toContain('.up{color:#3ee58a}');
  const [r, g, b] = out.match(/^\.go\{background:linear-gradient\(135deg, rgb\((\d+), (\d+), (\d+)\)/).slice(1).map(Number);
  expect(r).toBeGreaterThan(g); expect(r).toBeGreaterThan(b);   // the first stop is now a red of its own lightness, not green
  expect(out).toMatch(/border-color:rgba\(\d+, \d+, \d+, 0\.4\)/);
});
