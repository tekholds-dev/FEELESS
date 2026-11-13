import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ProofValue } from './StashWeb';
import { ReviewReel } from './ProofDoors';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
async function mount(el) {
  const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box);
  await act(async () => root.render(el));
  return { box, root, q: s => box.querySelector(`[data-testid="${s}"]`) };
}

test('💵 verified missions per dollar: the total, one meter per kind (proved of settled), free when nothing was spent', async () => {
  const v = { total: { proved: 6, settled: 10, usd: 2, perDollar: 3 }, byKind: { pos: { proved: 4, settled: 5, usd: 2, perDollar: 2 }, pop: { proved: 2, settled: 5, usd: 0, perDollar: null } },
    anchor: { ok: true, day: '2026-11-13', n: 812, tip: 'ab12cd34ef56ab78', days: 1 } };
  const { q, box, root } = await mount(<ProofValue v={v} />);
  expect(q('stw-per-dollar').textContent).toBe('3 / $1');
  expect(q('stw-value').textContent).toContain('6 proved of 10 settled · $2.00 spent');
  const kinds = [...box.querySelectorAll('.stw-val-kinds li')].map(li => li.textContent);
  expect(kinds).toEqual(['PoStatic2 / $1', 'PoPfree']);
  expect(box.querySelector('.stw-val-kinds s').style.transform).toBe('scaleX(0.8)');
  expect(q('stw-anchor').textContent).toContain('HOLDS'); expect(q('stw-anchor').textContent).toContain('row 812');
  await act(async () => root.unmount());
});

test('📌 a record cut back below the kept tip shows BROKEN with the reason; no tip yet says when the first comes', async () => {
  const a = await mount(<ProofValue v={{ total: { proved: 0, settled: 0, usd: 0, perDollar: null }, byKind: {}, anchor: { ok: false, why: 'the chain was cut back: row 812 is gone', day: '2026-11-13', n: 812, tip: 'x', days: 2 } }} />);
  expect(a.q('stw-anchor').className).toContain('is-bad'); expect(a.q('stw-anchor').getAttribute('data-tip')).toContain('row 812 is gone');
  expect(a.q('stw-per-dollar').textContent).toBe('—');
  await act(async () => a.root.unmount());
  const b = await mount(<ProofValue v={{ total: { proved: 0, settled: 0, usd: 0 }, byKind: {}, anchor: { ok: null } }} />);
  expect(b.q('stw-anchor').textContent).toContain('FIRST TIP TONIGHT');
  await act(async () => b.root.unmount());
  const c = await mount(<ProofValue v={null} />);
  expect(c.q('stw-value')).toBeNull();
  await act(async () => c.root.unmount());
});

test('🧰 a PoStatic review lists the existing tools it checked; a stale one names the pin', async () => {
  const rows = [{ id: 'a', title: 'GLINT', score: 80, verdict: 'pass', agree: true, by: { ossy: { score: 80, verdict: 'pass', checks: [] } },
    hidden: { passed: 9, total: 10, failed: ['kits-current'], kits: [{ pkg: 'echarts', used: '5.4.3', pin: '6', ok: false }, { pkg: 'three', used: '0.187.0', pin: '0.187.0', ok: true }] } }];
  const { q, root } = await mount(<ReviewReel rows={rows} />);
  expect(q('prv-hidden').textContent).toContain("missed: today's tested kit versions");
  expect(q('prv-kits').textContent).toBe('EXISTING TOOLS CHECKED · echarts@5.4.3 (stale, now 6) · three@0.187.0');
  await act(async () => root.unmount());
});
