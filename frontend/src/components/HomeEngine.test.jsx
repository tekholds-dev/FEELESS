import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { HomeEngine, forgeCards, pctWord } from './HomeEngine';

jest.mock('./CoinDrawer', () => ({ openCoin: jest.fn() }));
jest.mock('./terminal/MarketPrimitives', () => ({ TokenAvatar: () => null }));
jest.mock('./HomeForgeCard', () => ({ __esModule: true, default: ({ card }) => <div data-testid="live-card">{card?.real ? 'REAL MONEY' : 'PAPER'} {(card?.legs || []).map(l => l.symbol).join(' ')} {(card?.legs || []).map(l => l.pnlPct).join(' ')}</div> }));
const prime = { cards: [{ id: 'g', tpl: 'balanced', label: '🥇 Prime Gold', legs: [{ symbol: 'SOL', mint: 'S', pnlPct: 1.2 }, { symbol: 'WIF', mint: 'W', pnlPct: -3 }, { placeholder: true, symbol: 'X' }] },
  { id: 'd', tpl: 'degen', label: '🔥 Prime Blaze', real: true, legs: [{ symbol: 'FOMO', mint: 'F', pnlPct: null }] }, { id: 'e', tpl: 'ever', label: 'Empty', legs: [] }] };

test('the forge cycles real cards first, only coins that hold money, each with its own live %', () => {
  const c = forgeCards(prime);
  expect(c.map(x => x.tpl)).toEqual(['degen', 'balanced']);             // real first; an empty card is not forged
  expect(c[1].coins.map(x => x.sym)).toEqual(['SOL', 'WIF']);           // a reserved seat is not a coin
  expect([pctWord(1.2), pctWord(-3), pctWord(null), pctWord(2400)]).toEqual(['+1.2%', '-3.0%', '—', '+25.0x']);
});

test('the forge draws the coins, forges the card and opens a coin on tap', async () => {
  const { openCoin } = require('./CoinDrawer');
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(prime) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HomeEngine />); });
  await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('frg-card').textContent).toContain('REAL MONEY'); expect(q('frg-stage').querySelectorAll('.frg-coin')).toHaveLength(1);
  await act(async () => { q('frg-t-balanced').click(); });
  expect(q('frg-stage').querySelectorAll('.frg-coin')).toHaveLength(2); expect(q('frg-card').textContent).toContain('WIF');
  await act(async () => { el.querySelector('.frg-legs button').click(); });
  expect(openCoin).toHaveBeenCalledWith(expect.objectContaining({ mint: 'S' }));
});
