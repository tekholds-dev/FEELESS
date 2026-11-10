import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Door } from './LaunchLab';

test('the HQ door opens the creator\'s HQ pop-up instead of the old /terminal/hq 404 (SITE-10)', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const heard = jest.fn();
  window.addEventListener('feeless:hq-open', heard);
  await act(async () => root.render(<Door to="hq:" testId="d">House config (HQ)</Door>));
  const a = el.querySelector('[data-testid="d"]'); expect(a.getAttribute('href')).toBe('#hq');
  await act(async () => a.click()); expect(heard).toHaveBeenCalledTimes(1);
  window.removeEventListener('feeless:hq-open', heard); act(() => root.unmount());
});
