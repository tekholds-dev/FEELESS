import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LagAdvice, LagVitals } from './LagCatcher';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('advice and vitals render the server read', async () => {
  const el = document.createElement('div');
  await act(async () => { createRoot(el).render(<><LagVitals v={[{ k: 'SWAP', v: 94, unit: '%', tone: 'bad' }]} /><LagAdvice a={[{ level: 'bad', area: 'machine', what: 'Swap 94% full', why: 'w', fix: 'close it' }]} /></>); });
  expect(el.textContent).toContain('94%'); expect(el.textContent).toContain('Swap 94% full'); expect(el.textContent).toContain('close it');
  expect(el.querySelector('.lgv-t.t-bad')).toBeTruthy();
});

test('🧱 Layout watch names every page that spills, overlaps or scrolls sideways for real visitors', async () => {
  const React = require('react'); const { act } = require('react'); const { createRoot } = require('react-dom/client');
  const { LagCatcher } = require('./LagCatcher');
  const call = async () => ({ reports: 3, fixes: [], routes: [], pages: [{ page: '/terminal/fuse', fps: 60, jankMsPerReport: 0, sideways: 24, spills: ['fdeck-tile'], covered: [] },
    { page: '/', fps: 60, jankMsPerReport: 0, sideways: 0, spills: [], covered: [] }] });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(React.createElement(LagCatcher, { call })); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const rows = el.querySelectorAll('[data-testid="lag-layout-row"]');
  expect(rows).toHaveLength(1); expect(rows[0].textContent).toContain('/terminal/fuse'); expect(rows[0].textContent).toContain('scrolls sideways 24px');
  expect(rows[0].textContent).toContain('spills: fdeck-tile');
  act(() => root.unmount()); el.remove();
});
