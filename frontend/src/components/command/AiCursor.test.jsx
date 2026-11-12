import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { AiCursor } from './CatWorkbench';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('🖱 AGT-19: over a page screenshot the cursor uses the page shares; over the live window it keeps the window shares', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const c = { x: 0.5, y: 0.125, px: 0.5, py: 0.025, act: 'click', at: 1 };
  const t = () => el.querySelector('[data-testid="cwb-cursor"]').style.transform;
  await act(async () => root.render(<AiCursor c={c} kind="arrow" />)); expect(t()).toBe('translate(calc(var(--box-w, 0px) * 0.5), calc(var(--box-h, 0px) * 0.125))');
  await act(async () => root.render(<AiCursor c={c} kind="arrow" page />)); expect(t()).toBe('translate(calc(var(--box-w, 0px) * 0.5), calc(var(--box-h, 0px) * 0.025))');
  await act(async () => root.render(<AiCursor c={{ x: 0.3, y: 0.4 }} kind="arrow" page />)); expect(t()).toBe('translate(calc(var(--box-w, 0px) * 0.3), calc(var(--box-h, 0px) * 0.4))');   // an old cursor still draws
  await act(async () => root.unmount());
});
