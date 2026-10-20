import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeelessUniverse, PLANETS } from './FeelessUniverse';

jest.mock('react-router-dom', () => ({ Link: ({ to, children, ...p }) => <a href={to} {...p}>{children}</a> }), { virtual: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('every planet opens its own walk-through and the flagships explain the plan', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FeelessUniverse />); });
  expect(el.querySelectorAll('[data-testid^="fu-planet-"]').length).toBe(PLANETS.length);
  await act(async () => { el.querySelector('[data-testid="fu-planet-fuse"]').click(); });
  expect(el.querySelector('[data-testid="fu-guide"]').textContent).toContain('ONE wallet approval');
  expect(el.textContent).toContain('not a promise');
});
