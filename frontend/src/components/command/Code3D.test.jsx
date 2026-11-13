import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { Code3D, pageOf } from './Code3D';

test('🛡 the preview page reports a black page, never just "running" (AGT-17)', () => {
  const p = pageOf('const x = 1;');
  expect(p).toContain("p3c-dark"); expect(p).toContain('preserveDrawingBuffer'); expect(p).not.toContain("setTimeout(function(){try{parent.postMessage({t:'p3c-ok'}");
});

test('🛡 a black page says why and one tap sends that exact error to its minds', async () => {
  const work = jest.fn(async () => ({ code: 'fixed', by: 'Mind A', model: 'g4', usd: 0, chat: [] }));
  const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box);
  await act(async () => root.render(<Code3D cat={{ id: 'c' }} work={work} initial="const a = 1;" minds={['ossy', 'g4']} />));
  const frame = box.querySelector('[data-testid="p3c-frame"]');
  await act(async () => { window.dispatchEvent(new MessageEvent('message', { data: { t: 'p3c-dark', m: 'It drew almost nothing in 6 seconds: the page looks black.' }, source: frame.contentWindow })); });
  expect(box.querySelector('[data-testid="p3c-err"]').textContent).toContain('It opened black');
  expect(box.textContent).toContain('STOPPED');
  await act(async () => { box.querySelector('[data-testid="p3c-fixit"]').click(); });
  const sent = work.mock.calls[0][1]; expect(sent.op).toBe('play3d_code'); expect(sent.text).toContain('the page looks black'); expect(sent.job).toBe('const a = 1;');
  act(() => root.unmount());
});

test('⏱ the run bar shows the real frame rate the page measured, coloured by how smooth it is (AGT-17 real FPS)', async () => {
  expect(pageOf('x')).toContain("say('p3c-fps'");
  const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box);
  await act(async () => root.render(<Code3D cat={{ id: 'c' }} work={jest.fn()} initial="const a = 1;" minds={[]} />));
  expect(box.querySelector('[data-testid="p3c-fps"]')).toBeNull();   // nothing until the page measures
  const src = box.querySelector('[data-testid="p3c-frame"]').contentWindow;
  await act(async () => { window.dispatchEvent(new MessageEvent('message', { data: { t: 'p3c-fps', m: '58|21' }, source: src })); });
  const chip = box.querySelector('[data-testid="p3c-fps"]'); expect(chip.textContent).toBe('58 FPS'); expect(chip.className).toContain('is-ok'); expect(chip.getAttribute('data-tip')).toContain('21 ms');
  await act(async () => { window.dispatchEvent(new MessageEvent('message', { data: { t: 'p3c-fps', m: '24|90' }, source: src })); });
  expect(box.querySelector('[data-testid="p3c-fps"]').className).toContain('is-bad');
  act(() => root.unmount());
});
