import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { useRemembered, recall } from './remember';

test('🔁 a remembered value survives a remount (a refresh) in the same tab', () => {
  sessionStorage.clear();
  let api;
  const C = () => { api = useRemembered('t.k', 'a'); return null; };
  const box = document.createElement('div'); const root = createRoot(box);
  act(() => root.render(<C />)); expect(api[0]).toBe('a');
  act(() => api[1]('b')); expect(recall('t.k', 'x')).toBe('b');
  act(() => root.unmount());
  const root2 = createRoot(document.createElement('div')); act(() => root2.render(<C />)); expect(api[0]).toBe('b');
  act(() => api[1](null)); expect(recall('t.k', 'z')).toBe('z'); act(() => root2.unmount());
});
