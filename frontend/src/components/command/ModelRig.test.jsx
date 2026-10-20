import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ModelRig } from './ModelRig';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const view = { rows: [{ key: 'lan', name: 'G4', ctx: 0, parallel: 2, timeout: 90, perMin: 4, cmd: 'lms load x --parallel 2' }, { key: 'win', name: 'NEXA', ctx: 4096, parallel: 1, timeout: 240, perMin: 2, every: 300, cmd: 'llamafile.exe' }],
  options: { ctx: [0, 4096, 8192], parallel: [1, 2, 3], timeout: [60, 90, 240], perMin: [2, 4], every: [300, 600] }, live: { lan: { state: 'ONLINE' } } };

test('the rig shows each model and saves one tap', async () => {
  const call = jest.fn((u, o) => Promise.resolve(o ? { ...view, rows: view.rows.map(r => r.key === 'lan' ? { ...r, parallel: 3 } : r) } : view));
  const el = document.createElement('div');
  await act(async () => { createRoot(el).render(<ModelRig call={call} />); });
  expect(el.textContent).toContain('G4'); expect(el.textContent).toContain('NEXA'); expect(el.textContent).toContain('ONLINE');
  await act(async () => { el.querySelector('[data-testid="rig-lan-parallel-3"]').click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/ai/rig', expect.objectContaining({ method: 'POST', body: JSON.stringify({ lan: { parallel: 3 } }) }));
  expect(el.querySelector('[data-testid="rig-lan-parallel-3"]').className).toBe('active');
});
