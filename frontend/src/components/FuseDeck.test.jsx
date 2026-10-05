import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FuseDeck, FuseExplainer } from './FuseDeck';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('deck shows one panel at a time and remembers the tab; explainer opens', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  const root = createRoot(el);
  await act(async () => { root.render(<FuseDeck panels={[['lab', 'Lab', <p key="a">LAB</p>], ['hq', 'HQ', <p key="b">HQ PANEL</p>]]} />); });
  expect(el.querySelector('[data-testid="fdeck-overview"]')).not.toBeNull(); expect(el.textContent).not.toContain('HQ PANEL');   // 🗺 Overview first
  await act(async () => { el.querySelector('[data-testid="fdeck-tile-lab"]').click(); });
  expect(el.textContent).toContain('LAB'); expect(el.textContent).not.toContain('HQ PANEL');
  await act(async () => { el.querySelector('[data-testid="fdeck-hq"]').click(); });
  expect(el.textContent).toContain('HQ PANEL'); expect(localStorage.getItem('feeless-fuse-deck')).toBe('hq');
  await act(async () => { root.render(<FuseExplainer />); });
  await act(async () => { el.querySelector('.fx-more').click(); });
  expect(el.textContent).toContain('A Fuse buys several coins at once');
});

test('HQ overview opens on what needs a decision: real-run flaws and engine cards waiting for approval', async () => {
  const { DeckAlerts } = require('./FuseDeck');
  const { act } = require('react');
  const { createRoot } = require('react-dom/client');
  const call = jest.fn(async path => (path.includes('report') ? { reports: [{ card: 'blaze', label: '🔥 Blaze', open: true, verdict: 'fix', swaps: 40, feesPct: 6, pnlPct: -4, flaws: [{ level: 'high', what: 'Network fees ate 6% of the money in.' }] }] }
    : { record: { x: { w: 3, l: 1 } }, picks: [], field: [{ id: 'x', name: 'Moon v.02', legs: [1, 2, 3, 4], clock: 15 }] }));
  const gone = [];
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<DeckAlerts call={call} go={k => gone.push(k)} />); });
  await act(() => new Promise(r => setTimeout(r, 10)));
  expect(el.textContent).toContain('1 flaw — Network fees ate 6%');
  expect(el.textContent).toContain('Moon v.02 is 3–1 in the field');
  await act(async () => { el.querySelector('[data-testid="fdeck-alert-pg-x"]').click(); });
  expect(gone).toEqual(['pub']);
});
