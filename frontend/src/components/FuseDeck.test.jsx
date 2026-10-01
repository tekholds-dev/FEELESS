import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FuseDeck, FuseExplainer } from './FuseDeck';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('deck shows one panel at a time and remembers the tab; explainer opens', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  const root = createRoot(el);
  await act(async () => { root.render(<FuseDeck panels={[['lab', 'Lab', <p key="a">LAB</p>], ['hq', 'HQ', <p key="b">HQ PANEL</p>]]} />); });
  expect(el.textContent).toContain('LAB'); expect(el.textContent).not.toContain('HQ PANEL');
  await act(async () => { el.querySelector('[data-testid="fdeck-hq"]').click(); });
  expect(el.textContent).toContain('HQ PANEL'); expect(localStorage.getItem('feeless-fuse-deck')).toBe('hq');
  await act(async () => { root.render(<FuseExplainer />); });
  await act(async () => { el.querySelector('.fx-more').click(); });
  expect(el.textContent).toContain('A Fuse buys several coins at once');
});
