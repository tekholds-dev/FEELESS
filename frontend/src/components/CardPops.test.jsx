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

test('a REAL card pops only confirmed fills: real compound buys ($ in) and sales above cost ($ gained) — one at a time, never dust', () => {
  const { popsFromFills } = require('./CardPops');
  const o = [{ at: 9, side: 'sell', status: 'filled', symbol: 'CAT', usd: 2.36, realizedPnlUsd: 0.07, why: 'not on the card any more' },      // newest first, like the book
    { at: 8, side: 'buy', status: 'filled', symbol: 'SND', usd: 0.99, why: 'card buys its coin' },                                             // a normal buy is not a compound
    { at: 7, side: 'buy', status: 'filled', symbol: 'DON', usd: 0.25, why: 'idle card cash back into its coin' },
    { at: 6, side: 'buy', status: 'skipped', symbol: 'X', usd: 5, why: 'idle card cash back into its coin' },                                  // never landed
    { at: 5, side: 'sell', status: 'filled', symbol: 'L', usd: 1, realizedPnlUsd: -0.3 }, { at: 4, side: 'buy', status: 'filled', symbol: 'D', usd: 0.01, why: 'idle card cash back into its coin' }];
  expect(popsFromFills(o, new Set())).toEqual([expect.objectContaining({ text: '+$0.07', label: 'PROFIT', symbol: 'CAT' })]);                  // the newest one only
  expect(popsFromFills(o.slice(2), new Set())).toEqual([expect.objectContaining({ text: '+$0.25', label: 'COMPOUND', symbol: 'DON' })]);
  expect(popsFromFills(o.slice(3), new Set())).toEqual([]);                                                                                   // skipped · a loss · dust
});

test('the card pops ONE small number when a real compound lands after it was mounted, then waits before the next; the charge chip shows', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const legs = [{ symbol: 'SK', pnlPct: 13.4, usd: 1 }];
  const f = (at, usd) => ({ at, side: 'buy', status: 'filled', symbol: 'SK', usd, why: 'idle card cash back into its coin' });
  await act(async () => { root.render(<CardPops fills={[f(1, 9)]} legs={legs} cfg={{ rideAt: 15 }} />); });
  expect(el.querySelector('[data-testid="card-pop"]')).toBeNull();                       // what was already there never bursts
  expect(el.querySelector('[data-testid="card-near"]').textContent).toContain('⚡ $SK +13%'); expect(el.querySelector('[data-testid="card-near"]').textContent).toContain('lock +15%');
  await act(async () => { root.render(<CardPops fills={[f(50, 1.4), f(1, 9)]} legs={legs} cfg={{ rideAt: 15 }} />); });
  expect(el.querySelectorAll('[data-testid="card-pop"]')).toHaveLength(1);
  expect(el.querySelector('[data-testid="card-pop"]').textContent).toContain('+$1.40'); expect(el.querySelector('[data-testid="card-pop"]').textContent).toContain('COMPOUND');
  await act(async () => { root.render(<CardPops fills={[f(60, 0.5), f(50, 1.4), f(1, 9)]} legs={legs} cfg={{ rideAt: 15 }} />); });
  expect(el.querySelector('[data-testid="card-pop"]').textContent).toContain('+$1.40');   // a second fill seconds later does not stack another pop
});
