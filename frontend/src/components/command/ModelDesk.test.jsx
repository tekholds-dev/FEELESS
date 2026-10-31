import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ModelDesk, knobWord, KNOBS } from './ModelDesk';
import { desk } from './__fixtures__/modelDesk';

jest.mock('./ModelRig', () => ({ ModelRig: ({ only, bare, cards }) => <div data-testid={`rig-${only || 'all'}-${bare ? 'bare' : 'full'}-${cards === false ? 'nocards' : 'cards'}`} /> }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('🌡 a knob reads your override, else the desk default, else the runtime\'s own', () => {
  const inf = desk().models[2].inference; const k = f => KNOBS.find(x => x[0] === f);
  expect(knobWord(k('temp'), inf)).toEqual({ v: 0.1, src: 'desk' });
  expect(knobWord(k('topK'), inf)).toEqual({ v: 40, src: 'runtime' });
  expect(knobWord(k('topK'), { ...inf, infer: { topK: 20 } })).toEqual({ v: 20, src: 'yours' });
  expect(knobWord(k('minP'), desk().models[0].inference)).toEqual({ v: null, src: 'model default' });
});

test('🧠 vitals for every model, then the picked one: info · load · inference · server · MCP', async () => {
  const posts = []; let infer = {};
  const call = jest.fn(async (path, o) => { if (o?.method === 'POST') { const b = JSON.parse(o.body); posts.push(b); Object.entries(b).forEach(([k, r]) => { infer[k] = { ...(infer[k] || {}), ...r.infer }; }); return {}; } return desk(infer); });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ModelDesk call={call} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(el.querySelectorAll('.mdk-vc').length).toBe(3);
  expect(q('mdk-vc-lan').textContent).toContain('38.2'); expect(q('mdk-vc-lan').textContent).toContain('1 thinking'); expect(q('mdk-vc-lan').textContent).toContain('🎭 progressive');
  expect(q('mdk-vc-local').textContent).toContain('✕ 1'); expect(q('mdk-panel-lan').textContent).toContain('qwen3');
  expect(q('mdk-panel-lan').textContent).toContain('8.5Kof 256K max'); expect(q('mdk-panel-lan').textContent).toContain('🛠 tool use');
  await act(async () => { q('mdk-tab-load').click(); }); expect(q('rig-lan-bare-cards')).not.toBeNull();
  await act(async () => { q('mdk-tab-infer').click(); });
  expect(q('mdk-sys').textContent).toContain('PROGRESSIVE'); expect(q('mdk-sys').textContent).toContain('✓ in use'); expect(q('rig-all-full-nocards')).not.toBeNull();
  await act(async () => { q('mdk-temp-0.4').click(); }); expect(posts[0]).toEqual({ lan: { infer: { temp: 0.4 } } });
  await act(async () => { await call('/admin/ai/models'); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('mdk-knob-temp').textContent).toContain('0.4 · yours');
  await act(async () => { q('mdk-temp-def').click(); }); expect(posts[1]).toEqual({ lan: { infer: { temp: null } } });
  await act(async () => { q('mdk-tab-server').click(); }); expect(q('mdk-panel-lan').textContent).toContain('ANSWERING'); expect(q('mdk-panel-lan').textContent).toContain('http://10.0.0.249:1236');
  await act(async () => { q('mdk-tab-mcp').click(); }); expect(q('mdk-panel-lan').textContent).toContain('FEELESS MCP ONLINE'); expect(el.querySelectorAll('.mdk-tools span').length).toBe(6);
  await act(async () => { q('mdk-tab-infer').click(); }); expect(q('mdk-knob-topK').textContent).toContain('model default');   // no runtime defaults without llamafile (NEXA retired)
  act(() => root.unmount());
});

test('🩺 a stalled model wears the watchdog flag with its evidence (the reload stays your tap)', async () => {
  const d = desk(); d.models[0] = { ...d.models[0], stall: { streak: 4, timeouts: 4, sinceOk: 1500, why: '4 timeouts in a row, last good answer 25m ago' } };
  const call = jest.fn(async () => d);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ModelDesk call={call} />); }); await act(async () => { await Promise.resolve(); });
  const k = d.models[0].key;
  expect(el.querySelector(`[data-testid="mdk-stall-${k}"]`).textContent).toContain('STALLED · 4 timeouts in a row');
  expect(el.querySelector(`[data-testid="mdk-vc-${k}"]`).className).toContain('is-stalled');
  expect(el.querySelectorAll('.mdk-stall')).toHaveLength(1);
  await act(async () => { root.unmount(); });
});
