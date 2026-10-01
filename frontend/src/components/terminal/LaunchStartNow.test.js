jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn(), Link: () => null }), { virtual: true });
// eslint-disable-next-line import/first
import { startNow } from './LaunchForensics';

test('forensics show start → now for a group', () => {
  expect(startNow(['a', 'b', 'c'], { topHolders: [{ owner: 'b' }, { owner: 'z' }] }, 4.2)).toBe('3 at launch → 1 still in top holders · group holds 4.2% now');
  expect(startNow([], {}, 0)).toBe('0 at launch → 0 still in top holders · group holds 0% now');
});
