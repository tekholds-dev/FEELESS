import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { SitesRead } from './ProofKit';

// 🧠 COL-9: a folder that reused another agent's fresh read says whose and how old.
test('a reused read names the agent that read it', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<SitesRead rows={[{ host: 'espn.com', name: 'ESPN', ok: true, sharedBy: 'Happy', sharedAgo: 240 }]} />); });
  expect(el.querySelector('[data-testid="sites-shared"]').textContent).toBe("↺ Happy's read · 4 min old");
  await act(async () => { root.render(<SitesRead rows={[{ host: 'espn.com', name: 'ESPN', ok: true }]} />); });
  expect(el.querySelector('[data-testid="sites-shared"]')).toBeNull();
  await act(async () => root.unmount()); el.remove();
});
