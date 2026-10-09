import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { BsBar } from './BsBar';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('buys vs sells bar: 5m / 1h toggle for the whole site, the bar opens the flow-exit menu', async () => {
  const row = { '5m': { buyUsd: 30, sellUsd: 170, n: 20, pxChg: -3 }, '1h': { buyUsd: 900, sellUsd: 300, n: 300, pxChg: 12 } };
  const onFlow = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<><BsBar row={row} onFlow={onFlow} flowMode="normal" /><BsBar row={row} /></>); });
  const bars = el.querySelectorAll('.bsb');
  expect(bars[0].className).toContain('is-sell'); expect(bars[0].textContent).toContain('$30 ⇄ $170');
  await act(async () => { bars[0].querySelector('[data-testid="bs-tf"]').click(); });
  expect(bars[0].className).toContain('is-buy'); expect(bars[1].textContent).toContain('1h');   // one choice for every bar
  await act(async () => { bars[0].querySelector('[data-testid="bs-bar"]').click(); });
  await act(async () => { document.querySelector('[data-testid="bs-flow-tight"]').click(); });
  expect(onFlow).toHaveBeenCalledWith('tight'); expect(document.querySelector('[data-testid="bs-flow-pop"]')).toBeNull();
  await act(async () => { bars[1].querySelector('[data-testid="bs-bar"]').click(); }); expect(document.querySelector('[data-testid="bs-flow-pop"]')).toBeNull();   // no menu without onFlow
  await act(async () => { root.unmount(); });
});
