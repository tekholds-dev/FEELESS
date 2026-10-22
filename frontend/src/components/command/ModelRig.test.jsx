import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { renderToStaticMarkup } from 'react-dom/server';
import { ModelRig, NexaRuntime } from './ModelRig';

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

const base = { desired: { ctx: 2048, slots: 1 }, controller: { reachable: true }, auto: false };

test('NEXA shows wanted vs running and only says ACTIVE when the runtime reports it', () => {
  const on = renderToStaticMarkup(<NexaRuntime n={{ ...base, state: 'active', actual: { ctx: 2048, slots: 1, model: 'q.gguf' } }} onAct={() => {}} />);
  expect(on).toContain('ACTIVE'); expect(on).toContain('2K × 1');
  const off = renderToStaticMarkup(<NexaRuntime n={{ ...base, state: 'differs', actual: { ctx: 2048, slots: 4 } }} onAct={() => {}} />);
  expect(off).toContain('NOT APPLIED'); expect(off).not.toContain('✅ ACTIVE'); expect(off).toContain('2K × 4');
  const down = renderToStaticMarkup(<NexaRuntime n={{ ...base, state: 'unreachable', actual: null, controller: { reachable: false }, job: { msg: 'the Windows controller did not answer — your settings are saved, NEXA was NOT changed' } }} onAct={() => {}} />);
  expect(down).toContain('NEXA OFFLINE'); expect(down).toContain('NOT changed'); expect(down).toContain('controller offline');
});

const lms = { model: 'openai/gpt-oss-20b', name: 'gpt-oss-20b', fmt: 'mlx', maxCtx: 131072, sizeGb: 12, loaded: [{ id: 'openai/gpt-oss-20b', ctx: 7659, par: 2 }] };
const full = { ...view, rows: [{ key: 'local', name: 'OSSY', ctx: 0, parallel: 1, timeout: 60, perMin: 4, cmd: 'lms load', load: { ctx: 16384 }, lms, diff: { ctx: [7659, 16384] } }],
  loadOptions: { ctx: [8192, 16384], par: [1, 2], flash: [0, 1], kv: [0, 1], batch: [512] }, chat: { temp: 0.3, len: 'normal', lens: { short: 250, normal: 600, long: 1200 } }, reloading: [] };

test('one LM Studio view: loaded now vs the wanted load, reload is a tap, GGUF-only fields are off for MLX', async () => {
  const call = jest.fn((u, o) => Promise.resolve(o && JSON.parse(o.body).reload ? { ...full, reload: { ok: true, ms: 9100 } } : full));
  const el = document.createElement('div');
  await act(async () => { createRoot(el).render(<ModelRig call={call} />); });
  expect(el.querySelector('[data-testid="lms-now"]').textContent).toContain('LOADED NOW');
  expect(el.querySelector('[data-testid="rig-local-load-ctx-16384"]').className).toContain('active');
  expect(el.querySelector('[data-testid="rig-local-load-ctx-8192"]').className).not.toContain('active');
  expect(el.querySelector('[data-testid="rig-local-load-flash-1"]').disabled).toBe(true);   // MLX: flash attention is not a thing
  const btn = el.querySelector('[data-testid="rig-local-reload"]'); expect(btn.textContent).toContain('Reload OSSY'); expect(btn.textContent).toContain('16K');
  await act(async () => { btn.click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/ai/rig', expect.objectContaining({ body: JSON.stringify({ reload: 'local' }) }));
  expect(el.querySelector('[data-testid="rig-reload-note"]').textContent).toContain('reloaded in 9.1s');
  await act(async () => { el.querySelector('[data-testid="rig-local-load-ctx-8192"]').click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/ai/rig', expect.objectContaining({ body: JSON.stringify({ local: { load: { ctx: 8192 } } }) }));
  await act(async () => { el.querySelector('[data-testid="rig-chat-temp-0.6"]').click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/ai/chat/settings', expect.objectContaining({ body: JSON.stringify({ temp: 0.6 }) }));
});
