import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { SitesRead } from './ProofKit';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('📖 a proof shows what it really read and what walled it, and nothing for an old proof', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<SitesRead rows={[{ host: 'motion.dev', name: 'Motion', ok: true }, { host: 'codepen.io', name: 'CodePen', ok: false }]} />); });
  const row = el.querySelector('[data-testid="sites-read"]'); expect(row.textContent).toContain('✓ Motion'); expect(row.textContent).toContain('✕ CodePen');
  expect(row.querySelector('em.is-on').dataset.tip).toContain('motion.dev');
  await act(async () => { root.render(<SitesRead rows={undefined} />); }); expect(el.querySelector('[data-testid="sites-read"]')).toBeNull();
  act(() => root.unmount());
});
