import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { LensDock, LensVitals, lensVitals } from './LensDock';

const D = { judge: { wins: 8, losses: 4 }, desk: { x: 0.83, stake: 15, trades: 1, heat: 'cold' }, road: { pct: 0 }, proof: { paper: { n: 3, w: 1, l: 2 }, card: { n: 0 } },
  office: { seat: { held: 1, want: 4, freeUsd: 3.99, movesLeft: 24, emptyFor: 46, target: 10 }, mission: { value: 4 }, generations: [{ status: 'ACTIVE', generation: 2, lineage: [1] }, { status: 'PROBATION', generation: 1 }] } };

test('every lens gets four live tubes from the payload; a missing number reads — with an empty tube', () => {
  for (const k of ['live', 'review', 'missed', 'board', 'limits', 'learn', 'life', 'ctl']) expect(lensVitals(k, D, { ready: 1, contending: 3, probation: ['devil'] })).toHaveLength(4);
  const lim = lensVitals('limits', D, {});
  expect(lim.find(x => x.k === 'seats')).toMatchObject({ val: '1/4', fill: 0.25, tone: 'ok' }); expect(lim.find(x => x.k === 'empty').tone).toBe('bad');
  expect(lensVitals('learn', D, {}).find(x => x.k === 'judge')).toMatchObject({ val: '8–4' });
  expect(lensVitals('learn', D, {}).find(x => x.k === 'card')).toMatchObject({ val: '—', fill: 0 });
  expect(lensVitals('nope', D, {})).toEqual([]);
});

test('the dock: tap and ← / → walk the lenses; badges show; vitals render for the open lens', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); let lens = 'live';
  const tabs = [['live', '🟢 Live'], ['review', '📝 Review'], ['ctl', '⚙ Control']]; const set = jest.fn(k => { lens = k; });
  await act(async () => { root.render(<><LensDock tabs={tabs} lens={lens} setLens={set} badge={k => (k === 'live' ? '2 READY' : null)} /><LensVitals lens={lens} d={D} cnt={{ ready: 2 }} /></>); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('lens-live').textContent).toContain('2 READY'); expect(q('lens-live').getAttribute('aria-selected')).toBe('true'); expect(q('lv-ready').textContent).toContain('2');
  await act(async () => { q('lens-ctl').click(); }); expect(set).toHaveBeenLastCalledWith('ctl');
  await act(async () => { q('lens-live').dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true })); }); expect(set).toHaveBeenLastCalledWith('ctl');
  await act(async () => { q('lens-live').dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })); }); expect(set).toHaveBeenLastCalledWith('review');
  root.unmount(); el.remove();
});
