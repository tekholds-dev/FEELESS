import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LagAdvice, LagVitals } from './LagCatcher';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('advice and vitals render the server read', async () => {
  const el = document.createElement('div');
  await act(async () => { createRoot(el).render(<><LagVitals v={[{ k: 'SWAP', v: 94, unit: '%', tone: 'bad' }]} /><LagAdvice a={[{ level: 'bad', area: 'machine', what: 'Swap 94% full', why: 'w', fix: 'close it' }]} /></>); });
  expect(el.textContent).toContain('94%'); expect(el.textContent).toContain('Swap 94% full'); expect(el.textContent).toContain('close it');
  expect(el.querySelector('.lgv-t.t-bad')).toBeTruthy();
});
