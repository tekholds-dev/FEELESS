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

test('verdict: what is working and what is not, filterable, losers first', async () => {
  const { Verdict } = require('./FuseDeck');
  const { act } = require('react');
  const { createRoot } = require('react-dom/client');
  const V = { headline: "Nothing is proven to make money yet: 2 losing, 1 still unproven.", keep: 0, scrap: 2, watch: 1, rows: [
    { area: '💵 Real run', name: '🔥 Prime Blaze', n: 120, avgPct: -12.5, medPct: -12.5, verdict: 'scrap', why: '-12.5% so far · fees 4.2% of money in' },
    { area: '🧠 Sim config', name: 'round length (min) = 5', n: 60, avgPct: -2, medPct: -4, verdict: 'scrap', why: 'average -2.0%' },
    { area: '🏃 Runner lane', name: 'scalp', n: 3, avgPct: 5, medPct: 5, verdict: 'watch', why: 'needs 5 more to call' }] };
  const call = jest.fn(async () => V);
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<Verdict call={call} />); });
  await act(() => new Promise(r => setTimeout(r, 10)));
  expect(call).toHaveBeenCalledWith('/admin/fuses/verdict');
  expect(el.querySelector('[data-testid="fdv-head"]').textContent).toContain('Nothing is proven');
  expect(el.querySelectorAll('.fdv-row').length).toBe(3);
  await act(async () => { el.querySelector('[data-testid="fdv-watch"]').click(); });
  expect(el.querySelectorAll('.fdv-row').length).toBe(1); expect(el.textContent).toContain('needs 5 more to call');
});

test('verdict: one click adds a proven setting to all cards and scraps a losing strategy', async () => {
  const { Verdict } = require('./FuseDeck');
  const { act } = require('react');
  const { createRoot } = require('react-dom/client');
  const V = { headline: '1 working', keep: 1, scrap: 1, watch: 0, rows: [
    { area: '🏟 Strategy', name: 'degen', n: 9, avgPct: -6, medPct: -3, verdict: 'scrap', why: 'x', acts: [['scrap', '🗑 Scrap']] },
    { area: '🧠 Sim config', name: 'sell off its peak = 8', n: 40, avgPct: 2, medPct: 1, verdict: 'keep', why: 'y', acts: [['apply', '➕ Add to all cards'], ['apply-one', '🃏 One card'], ['apply-real', '💵 Real card']] }] };
  const posts = []; const call = jest.fn(async (url, o) => { if (o) { posts.push([url, JSON.parse(o.body)]); return { done: 'ok' }; } return V; });
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<Verdict call={call} />); });
  await act(() => new Promise(r => setTimeout(r, 10)));
  await act(async () => { el.querySelector('[data-testid="fdv-act-apply-1"]').click(); });
  expect(posts[0]).toEqual(['/admin/fuses/verdict/act', { area: '🧠 Sim config', name: 'sell off its peak = 8', act: 'apply', tier: 'degen' }]);
  await act(async () => { el.querySelector('[data-testid="fdv-act-scrap-0"]').click(); });
  expect(posts[1][1]).toMatchObject({ area: '🏟 Strategy', name: 'degen', act: 'scrap' });
});
