import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import PocWire, { placePic, planDay, planned, blankPost, FORMATS, DAYS } from './PocWire';

beforeEach(() => { try { localStorage.clear(); } catch { /* no store */ } });

test('cover fills the post and crops around the focus; contain fits the whole picture', () => {
  const c = placePic(1080, 1080, 2000, 1000, 'cover', '0% 50%');
  expect(c.h).toBe(1080); expect(c.w).toBe(2160); expect(c.x).toBe(0);
  const r = placePic(1080, 1080, 2000, 1000, 'cover', '100% 50%'); expect(r.x).toBe(1080 - 2160);
  const f = placePic(1080, 1920, 2000, 1000, 'contain'); expect(f.w).toBe(1080); expect(f.h).toBe(540); expect(f.y).toBe((1920 - 540) / 2);
});

test('a day keeps its own copy of the post', () => {
  const p = blankPost('Sneaker'); const w = planDay({}, 'Mon', p); p.headline = 'changed';
  expect(w.Mon.headline).toBe('Sneaker'); expect(planned(w)).toBe(1); expect(FORMATS).toHaveLength(3); expect(DAYS).toHaveLength(7);
});

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const $ = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const type = (input, v) => { const set = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), 'value').set; set.call(input, v); input.dispatchEvent(new Event('input', { bubbles: true })); };

test('the board edits words, switches format and plans days', () => {
  const onClose = jest.fn(); const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => root.render(<PocWire src={null} from="m1" title="Sneaker" onClose={onClose} />));
  expect($(el, 'pwr-headline').value).toBe('Sneaker');
  act(() => type($(el, 'pwr-headline'), 'Drop day'));
  expect(el.textContent).toContain('Drop day');
  act(() => $(el, 'pwr-fmt-billboard').click());
  expect($(el, 'pwr-fmt-billboard').getAttribute('aria-checked')).toBe('true');
  act(() => $(el, 'pwr-day-Wed').click());
  expect(el.textContent).toContain('1/7 planned'); expect(el.textContent).toContain('Editing Wed · 1920×1080');
  act(() => $(el, 'pwr-rm-Wed').click());
  expect(el.textContent).toContain('0/7 planned');
  act(() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))); expect(onClose).toHaveBeenCalled();
  act(() => root.unmount()); el.remove();
});
