import { saverWhy, applySaver, pollMs } from './saverMode';
const win = ({ coarse = false, w = 1440, reduce = false } = {}) => ({ innerWidth: w, document, localStorage,
  matchMedia: q => ({ matches: (q.includes('coarse') && coarse) || (q.includes('reduce') && reduce) }) });
afterEach(() => { document.body.className = ''; localStorage.clear(); });
test('🔋 phones, Save-Data, reduced motion and low battery turn the saver on by themselves; a desktop stays full', () => {
  expect(saverWhy(win({ coarse: true, w: 390 }), {})).toBe('phone');
  expect(saverWhy(win({ coarse: true, w: 820 }), {})).toBe('phone');   // a foldable / Duo open
  expect(saverWhy(win(), { connection: { saveData: true } })).toBe('save-data');
  expect(saverWhy(win({ reduce: true }), {})).toBe('reduced-motion');
  expect(saverWhy(win(), {}, { charging: false, level: 0.12 })).toBe('low-battery');
  expect(saverWhy(win(), {}, { charging: true, level: 0.12 })).toBe('');
  expect(saverWhy(win(), {})).toBe('');
});
test('🔋 the saver wears fx-lite (still smoke, no animation), names why, slows polling; a user who picked full effects keeps them', () => {
  expect(applySaver(win({ coarse: true, w: 390 }), {})).toBe('phone');
  expect(document.body.classList.contains('fx-lite')).toBe(true); expect(document.body.dataset.saver).toBe('phone');
  expect(pollMs(30000)).toBe(90000);
  document.body.className = ''; localStorage.setItem('feeless:fx-full', '1');
  expect(applySaver(win({ coarse: true, w: 390 }), {})).toBe(''); expect(document.body.classList.contains('fx-lite')).toBe(false);
});
