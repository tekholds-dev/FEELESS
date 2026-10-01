jest.mock('react-router-dom', () => ({}), { virtual: true });
// eslint-disable-next-line import/first
import { recolorText } from './HolderTheme';

test('site recolor swaps the FEELESS green everywhere, keeping alpha', () => {
  const css = '.a{color:#19F58F;border:1px solid #19f58f55;background:rgba(25,245,143,.2);box-shadow:0 0 4px rgb(25, 245, 143)}.b{color:#19f58fab0}';
  expect(recolorText(css, '#f5c451')).toBe('.a{color:#f5c451;border:1px solid #f5c45155;background:rgba(245, 196, 81,.2);box-shadow:0 0 4px rgb(245, 196, 81)}.b{color:#19f58fab0}');
});
