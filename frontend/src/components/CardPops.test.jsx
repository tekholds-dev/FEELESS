import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CardPops, popsFrom, nearTargets } from './CardPops';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('pops: only money events that are NEW, and coins in the last quarter before their lock charge up', () => {
  const ev = [{ at: 1, kind: 'compound', usd: 0.25 }, { at: 2, kind: 'skim', usd: 1.4, symbol: 'SK' }, { at: 3, kind: 'sl', usd: 1, symbol: 'X' }, { at: 4, kind: 'compound', usd: 0 }, { at: 5, kind: 'ride', symbol: 'CAT' }];
  expect(popsFrom(ev, new Set()).map(p => [p.text, p.label])).toEqual([['+$0.25', 'COMPOUND'], ['+$1.40', 'PROFIT'], ['$CAT', 'LOCKED']]);   // a stop and an empty compound never pop
  expect(popsFrom(ev, new Set(['10-compound--0']))).toHaveLength(2);
  expect(popsFrom([{ at: 9, kind: 'compound', usd: 5.2, lastUsd: 0.25, n: 12 }], new Set())[0].text).toBe('+$0.25');   // a folded line pops its latest amount
  const legs = [{ symbol: 'A', pnlPct: 13, usd: 1 }, { symbol: 'B', pnlPct: 5, usd: 1 }, { symbol: 'C', pnlPct: 14, usd: 1, ride: true }, { symbol: 'D', pnlPct: 12, usd: 0, buying: true }, { symbol: 'E', pnlPct: 16, usd: 1 }];
  expect(nearTargets(legs, { rideAt: 15 })).toEqual([{ symbol: 'A', gain: 13, target: 15, fill: 13 / 15, kind: 'lock' }]);   // riding / buying / already past / far away = no charge
  expect(nearTargets([{ symbol: 'T', pnlPct: 80, usd: 1 }], { rideAt: 0 }, 100)[0]).toMatchObject({ kind: 'take profit', target: 100 });
});

test('the card pops a floating number when a compound lands after it was mounted, and shows the charge chip', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const legs = [{ symbol: 'SK', pnlPct: 13.4, usd: 1 }];
  await act(async () => { root.render(<CardPops events={[{ at: 1, kind: 'compound', usd: 9 }]} legs={legs} cfg={{ rideAt: 15 }} />); });
  expect(el.querySelector('[data-testid="card-pop"]')).toBeNull();                       // what was already there never bursts
  expect(el.querySelector('[data-testid="card-near"]').textContent).toContain('⚡ $SK +13%'); expect(el.querySelector('[data-testid="card-near"]').textContent).toContain('lock +15%');
  await act(async () => { root.render(<CardPops events={[{ at: 1, kind: 'compound', usd: 9 }, { at: 50, kind: 'compound', usd: 1.4 }]} legs={legs} cfg={{ rideAt: 15 }} />); });
  expect(el.querySelector('[data-testid="card-pop"]').textContent).toContain('+$1.40'); expect(el.querySelector('[data-testid="card-pop"]').textContent).toContain('COMPOUND');
});
