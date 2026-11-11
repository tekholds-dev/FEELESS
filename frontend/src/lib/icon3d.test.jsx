import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Ic3 } from './icon3d';

test('🎩 the elite edition swaps the 3D cartoon icon for a line icon, and back', async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  await act(async () => { root.render(<Ic3 e="🔥" />); });
  expect(host.querySelector('img.ic3')).toBeTruthy(); expect(host.querySelector('svg')).toBeNull();
  await act(async () => { document.documentElement.dataset.edition = 'elite'; window.dispatchEvent(new Event('feeless:edition')); });
  expect(host.querySelector('svg.ic3-line')).toBeTruthy(); expect(host.querySelector('img.ic3')).toBeNull(); expect(host.textContent).toContain('🔥');
  await act(async () => { delete document.documentElement.dataset.edition; window.dispatchEvent(new Event('feeless:edition')); });
  expect(host.querySelector('img.ic3')).toBeTruthy();
  await act(async () => { root.unmount(); });
});
