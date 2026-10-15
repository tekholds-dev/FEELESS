import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { HomeEngine, relayOf, relays, board, DESKS } from './HomeEngine';

jest.mock('./CoinDrawer', () => ({ openCoin: jest.fn() }));
const feed = [{ sig: 's1', at: 100, side: 'sell', symbol: 'FOMO', mint: 'M1', pct: 4.1, why: '🤖 agents banked $FOMO: ☠ Reaper R4f sellers took over: +5.7%' },
  { sig: 's2', at: 90, side: 'buy', symbol: 'SLOP', mint: 'M2', usd: 0.25, why: 'card buys its coin' }, { sig: 's3', at: 80, side: 'sell', symbol: 'DODO', mint: 'M3', pct: -19 }];

test('each real decision becomes a relay step from the public proof feed; the board counts real exits only', () => {
  expect(DESKS).toHaveLength(10);
  expect(relayOf(feed[0])).toMatchObject({ desk: 'reaper', stamp: 'SOLD +4.1%', why: 'Reaper: sellers took over' });
  expect(relayOf(feed[1])).toMatchObject({ desk: 'courier', stamp: 'BOUGHT $0.25' });
  expect(relayOf(feed[2]).why).toBe('Reaper closed it');
  expect(board(relays({ feed }))).toEqual({ decisions: 3, sells: 2, won: 1, rate: 50 });
  expect(relays(null)).toEqual([]);
});

test('the relay draws the ten desks, lights the one that decided and stamps the call', async () => {
  const { openCoin } = require('./CoinDrawer');
  global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('proof') ? { feed } : { cards: [{ real: true, valueUsd: 2.22 }] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HomeEngine />); });
  await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('arl-chain').querySelectorAll('.arl-desk')).toHaveLength(10);
  expect(q('arl-reaper').className).toContain('is-on'); expect(q('arl-call').textContent).toContain('SOLD +4.1%');
  expect(q('arl-score').textContent).toContain('$2.22');
  await act(async () => { q('arl-call').querySelector('.arl-coin').click(); });
  expect(openCoin).toHaveBeenCalledWith(expect.objectContaining({ mint: 'M1' }));
});
