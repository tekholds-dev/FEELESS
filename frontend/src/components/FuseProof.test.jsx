import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./CoinDrawer', () => ({ openCoin: jest.fn() }));
const D = { setups: [{ key: 'rhunt', name: '🚀 Runner hunt', why: 'room to run', source: 'replay', proven: true, n: 11, medPct: 6.7, upPct: 82, worstPct: -9.9, hours: 6 },
  { key: 'real:degen', name: '💵 🔥 Prime Blaze', why: 'a real-money card', source: 'real', proven: false, medPct: -28.7, upPct: 44, record: { tpl: 'degen', putIn: 11, nowUsd: 6.88, closed: 320, wonPct: 44, takes: { n: 90, wonPct: 96 }, exits: { n: 230, wonPct: 24 }, swaps: 707, days: 1.7 } }],
  realLegs: { degen: [{ mint: 'M1', pairAddress: 'P1', symbol: 'SK' }] },
  feed: [{ at: Date.now() / 1000 - 90, side: 'sell', symbol: 'SK', mint: 'M1', pair: 'P1', pct: 31.4, why: '💰 profit of $SK taken, its stake keeps riding', sig: 'SIG1', label: '🔥 Prime Blaze' },
    { at: Date.now() / 1000 - 300, side: 'buy', symbol: 'DOG', mint: 'M2', pair: 'P2', pct: null, why: 'card buys its coin', sig: 'SIG2', label: '🔥 Prime Blaze' }],
  duels: { hours: 24, real: ['prime:degen'], rec: { 'prime:degen': { w: 1, l: 2, d: 0 } }, log: [{ id: 'old', a: 'prime:degen', b: 'prime:gold', aLabel: 'Blaze', bLabel: 'Gold', aPct: -3, bPct: 2, winner: 'prime:gold' }],
    live: [{ id: 'd1', a: 'prime:degen', b: 'prime:gold', aLabel: 'Blaze', bLabel: 'Gold', aPct: 4.2, bPct: -1.1, leader: 'prime:degen', endsAt: Date.now() / 1000 + 7200 }] } };

test('proof: setups side by side with their own record (a losing real card reads as losing), the live feed with reason + tx, and real duels', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => D }));
  const { FuseProof, PROOF_LENSES } = require('./FuseProof');
  const go = jest.fn(); const run = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FuseProof onGo={go} onRun={run} />); });
  await act(async () => { await Promise.resolve(); });
  expect(PROOF_LENSES.map(x => x[0])).toEqual(['setups', 'feed', 'duels']);
  const hunt = el.querySelector('[data-testid="setup-rhunt"]'); const real = el.querySelector('[data-testid="setup-real:degen"]');
  expect(hunt.textContent).toContain('✅ PROVEN'); expect(hunt.textContent).toContain('+6.7%'); expect(hunt.textContent).toContain('82% of windows up');
  expect(real.textContent).toContain('👀 NOT PROVEN'); expect(real.textContent).toContain('-28.7%'); expect(real.textContent).toContain('put in $11 → now $6.88'); expect(real.textContent).toContain('full exits 230 (24% won)');
  await act(async () => { el.querySelector('[data-testid="setup-run-real:degen"]').click(); }); expect(run).toHaveBeenCalledWith(D.realLegs.degen);
  await act(async () => { el.querySelector('[data-testid="setup-run-rhunt"]').click(); }); expect(go).toHaveBeenCalledWith('cards');
  await act(async () => { el.querySelector('[data-testid="proof-lens-feed"]').click(); });
  const feed = el.querySelector('[data-testid="proof-feed"]');
  expect(feed.textContent).toContain('SELL'); expect(feed.textContent).toContain('+31.4%'); expect(feed.textContent).toContain('stake keeps riding');
  expect(feed.querySelector('a.fpf-tx').getAttribute('href')).toBe('https://solscan.io/tx/SIG1');
  await act(async () => { el.querySelector('[data-testid="proof-lens-duels"]').click(); });
  const du = el.querySelector('[data-testid="proof-duels"]').textContent;
  for (const s of ['💵 REAL · 1W 2L 0D', '📄 PAPER', '+4.2%', '-1.1%', 'VS', '🏆 Gold', 'points and a record only']) expect(du).toContain(s);
});
