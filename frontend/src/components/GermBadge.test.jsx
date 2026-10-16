import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { GermChip } from './GermBadge';

const mount = el => { const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box); act(() => root.render(el)); return { box, root }; };

test('germ chip draws the word, the distance and a meter from a germ record', () => {
  const { box, root } = mount(<GermChip germ={{ d: 4, w: 'floor', e: 'floor', line: 15, ok: true }} />);
  const chip = box.querySelector('[data-testid="germ-chip"]');
  expect(chip.textContent).toContain('AT THE FLOOR');
  expect(chip.textContent).toContain('+4%');
  expect(chip.className).toMatch(/gm-floor/);
  act(() => root.unmount());
});

test('no germ read = nothing drawn', () => {
  const { box, root } = mount(<GermChip germ={{ w: 'floor' }} />);
  expect(box.innerHTML).toBe('');
  act(() => root.unmount());
});
