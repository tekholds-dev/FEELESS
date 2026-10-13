globalThis.IS_REACT_ACT_ENVIRONMENT = true;
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChartLevels } from './ChartLevels';

test('levels render as live rows (title + price), one per id, and nothing renders with no level', () => {
  const host = document.createElement('div'); document.body.appendChild(host);
  const root = createRoot(host);
  const refs = { seriesRef: { current: null }, chartRef: { current: null }, lastBarRef: { current: null }, shownRef: { current: null }, container: { current: null } };
  act(() => { root.render(<ChartLevels {...refs} fmt={v => `$${v}`} levels={[{ id: 'stop', px: 8, title: '🛑 stop −20%', tone: 'dn', key: true }, { id: 'stop', px: 9, title: 'dup', tone: 'dn' }, { id: 'g0', px: 5, title: '🪜 gap', tone: 'up' }]} />); });
  const rows = host.querySelectorAll('.clx-row');
  expect(rows.length).toBe(2);
  expect(host.querySelector('[data-testid="chart-level-stop"]').textContent).toContain('🛑 stop −20%$8');
  expect(host.querySelector('[data-testid="chart-level-stop"]').className).toContain('is-key');
  act(() => { root.render(<ChartLevels {...refs} levels={[]} />); });
  expect(host.querySelector('.clx')).toBeNull();
  act(() => root.unmount());
});
