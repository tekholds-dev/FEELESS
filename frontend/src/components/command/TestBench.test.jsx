import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { TestBench } from './TestBench';

test('🧪 the bench lists every filed test with its result, cost and outputs, and can run a 3D module', async () => {
  const runs = [{ id: 'aaaaaaaaaaaa', at: Date.now() / 1000 - 60, kind: '3d', title: 'NOVA on G4', ok: false, why: 'Looped and was cut off', models: ['local/g4'], costUsd: 0, secs: 412, steps: ['asked', 'cut'], files: [{ name: 'nova.js', bytes: 30 }], by: 'Claude' },
    { id: 'bbbbbbbbbbbb', at: Date.now() / 1000 - 30, kind: 'ui', title: 'Money page', ok: true, why: 'Seen live', models: [], costUsd: 0, secs: 5, steps: [], files: [], by: 'Claude' }];
  const work = jest.fn(async (id, b) => (b.op === 'test_runs' ? { runs, stats: { runs: 2, passed: 1, failed: 1, costUsd: 0, secs: 417 } } : { text: "import * as THREE from 'three';\nnew THREE.Scene();" }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<TestBench catId="c" work={work} />); });
  expect(el.textContent).toContain('NOVA on G4'); expect(el.textContent).toContain('FAIL'); expect(el.textContent).toContain('7 min');
  await act(async () => { [...el.querySelectorAll('.m-seg button')].find(b => b.textContent === 'Failed').click(); });
  expect(el.textContent).not.toContain('Money page');
  await act(async () => { el.querySelector('[data-testid="tbn-run-aaaaaaaaaaaa"] .tbn-head').click(); });
  await act(async () => { [...el.querySelectorAll('.tbn-files button')][0].click(); });
  expect(work).toHaveBeenCalledWith('c', { op: 'test_run_file', job: 'aaaaaaaaaaaa', text: 'nova.js' });
  expect(el.querySelector('.tbn-file pre').textContent).toContain('new THREE.Scene()');
  await act(async () => { el.querySelector('.tbn-go').click(); });
  expect(el.querySelector('.tbn-file iframe').getAttribute('sandbox')).toBe('allow-scripts');
  act(() => root.unmount());
});
