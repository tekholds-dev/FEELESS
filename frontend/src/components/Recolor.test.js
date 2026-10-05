jest.mock('react-router-dom', () => ({}), { virtual: true });
// eslint-disable-next-line import/first
import { recolorText } from './HolderTheme';

test('site recolor swaps the FEELESS green everywhere, keeping alpha', () => {
  const css = '.a{color:#15d16a;border:1px solid #15d16a55;background:rgba(21, 209, 106,.2);box-shadow:0 0 4px rgb(21, 209, 106)}.b{color:#15d16aab0}';
  expect(recolorText(css, '#f5c451')).toBe('.a{color:#f5c451;border:1px solid #f5c45155;background:rgba(245, 196, 81,.2);box-shadow:0 0 4px rgb(245, 196, 81)}.b{color:#15d16aab0}');
});
