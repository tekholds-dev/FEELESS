import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Panther, PantherPicker, PantherStage, GESTURES, COATS, readCoat } from './Panther';
import { FeeCatMark } from './FeeCatMark';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); act(() => root.render(node)); return { el, root }; };

test('eight gestures and a pink panther exist', () => {
  expect(GESTURES).toHaveLength(8); expect(COATS.pink.name).toBe('Pink panther');
});
test('a gesture button plays it on the stage, then the panther goes back to idle', () => {
  jest.useFakeTimers();
  const { el, root } = mount(<PantherStage />);
  act(() => el.querySelector('[data-testid="pt-do-roar"]').click());
  expect(el.querySelector('svg.pt').getAttribute('data-gesture')).toBe('roar');
  act(() => { jest.advanceTimersByTime(4000); });
  expect(el.querySelector('svg.pt').getAttribute('data-gesture')).toBe('idle');
  act(() => root.unmount()); jest.useRealTimers();
});
test('picking a coat is remembered and repaints every panther', () => {
  const { el, root } = mount(<><PantherPicker /><Panther label="main" /></>);
  act(() => el.querySelector('[data-testid="panther-pink"]').click());
  expect(readCoat()).toBe('pink');
  expect(el.querySelector('[data-testid="panther-pink"]').getAttribute('aria-checked')).toBe('true');
  expect(el.querySelector('[aria-label="main"]')).toBeTruthy();
  act(() => root.unmount());
});
test('FeeCatMark is the panther head and keeps its old props', () => {
  const { el, root } = mount(<FeeCatMark size={22} animate={false} colors={['#111', '#f0f']} />);
  const svg = el.querySelector('svg');
  expect(svg.classList.contains('is-head')).toBe(true); expect(svg.classList.contains('is-still')).toBe(true);
  act(() => root.unmount());
});
