import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

const mockNav = jest.fn();
jest.mock('react-router-dom', () => ({ useNavigate: () => mockNav }), { virtual: true });
// eslint-disable-next-line import/first
import { RadarPage } from './RadarPage';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('Radar = Signals + Watching in one tab, switching by view', () => {
  const host = document.createElement('div'); document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(<RadarPage view="signals" watchCount={4} signals={<p>SIGNALS</p>} watching={<p>WATCHING</p>} />));
  expect(host.textContent).toContain('SIGNALS'); expect(host.textContent).not.toContain('WATCHING');
  expect(host.querySelector('[data-testid="radar-watching"]').textContent).toContain('4');
  act(() => host.querySelector('[data-testid="radar-watching"]').click());
  expect(mockNav).toHaveBeenCalledWith('/terminal/watchlist');
  act(() => root.render(<RadarPage view="watching" signals={<p>SIGNALS</p>} watching={<p>WATCHING</p>} />));
  expect(host.textContent).toContain('WATCHING');
});
