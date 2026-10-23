import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FamEmpty } from './FamEmpty';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
test('🌹 an empty Familia room is drawn: its own scene, a headline, how to fill it, an action', () => {
  const el = document.createElement('div'); const root = createRoot(el);
  act(() => root.render(<FamEmpty art="raid" title="NO RAIDS ON" note="Tap a rival building." ><button type="button" data-testid="go">go</button></FamEmpty>));
  const box = el.querySelector('[data-testid="fam-empty-raid"]');
  expect(box.className).toContain('a-raid'); expect(box.querySelector('svg .tgt')).not.toBeNull();
  expect(box.textContent).toContain('NO RAIDS ON'); expect(box.textContent).toContain('Tap a rival building.'); expect(el.querySelector('[data-testid="go"]')).not.toBeNull();
  act(() => root.render(<FamEmpty art="nope" title="X" note="y" />)); expect(el.querySelector('svg circle')).not.toBeNull();   // an unknown art falls back to the crew
  act(() => root.unmount());
});
