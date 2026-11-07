import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';

test('what it boxed runs down a wire to its tray, says the site, and goes after a few seconds', async () => {
  jest.useFakeTimers();
  const { FindWires } = require('./CatWorkbench');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FindWires m={{ at: 1, site: 'espn.com', pts: [[0.2, 0.3], [0.6, 0.5]], got: ['odds: -110', 'Nets +4.5'] }} />); });
  const q = () => el.querySelector('[data-testid=cwb-find]');
  expect(q().querySelectorAll('path')).toHaveLength(2); expect(q().textContent).toContain('FOUND ON ESPN.COM'); expect(q().textContent).toContain('Nets +4.5');
  await act(async () => { jest.advanceTimersByTime(7100); }); expect(q()).toBeNull();
  await act(async () => { root.render(<FindWires m={{ at: 2, site: 'nba.com', pts: [[0.5, 0.5]], got: ['nets'], hunt: true }} />); }); expect(q().className).toContain('is-hunt'); expect(q().textContent).toContain('LOOKING FOR');
  await act(async () => { root.render(<FindWires m={null} />); });
  jest.useRealTimers(); root.unmount(); el.remove();
});
