jest.mock('react-router-dom', () => ({}), { virtual: true });
// eslint-disable-next-line import/first
import { livesRow } from './FeeCatHQ';

test('nine paws, lit for each life left', () => {
  expect(livesRow(7)).toEqual([true, true, true, true, true, true, true, false, false]);
  expect(livesRow(0).every(x => !x)).toBe(true);
});

test('the HQ strip shows her auto-strength with the reason', async () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  const { FeeCatHQ } = require('./FeeCatHQ');
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ cat: { balanceSol: 1, positions: [] }, discipline: { lives: 9, sizeMult: 1 },
    strength: { level: 'cold', mult: 0.6, label: '🧊 cold', why: 'losing 24h' } }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(React.createElement(FeeCatHQ)); });
  await act(() => new Promise(r => setTimeout(r, 10)));
  const s = el.querySelector('[data-testid="feecat-strength"]');
  expect(s.textContent).toContain('🧊 cold ×0.6');
  expect(s.dataset.tip).toContain('losing 24h');
});
