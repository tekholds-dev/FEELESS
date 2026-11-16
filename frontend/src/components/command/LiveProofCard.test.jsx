import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LiveProofCard, powLive } from './LiveProofCard';

beforeAll(() => { global.ResizeObserver = global.ResizeObserver || class { observe() {} unobserve() {} disconnect() {} }; });

test('📺 a live PoW reads its move from entry; a closed one shows the settled P&L (fees never in it)', () => {
  const live = powLive({ status: 'open', entry: 0.1, now: 0.11, line: [0.1, 0.105, 0.11], sol: 0.01, tp: 10, sl: 6, buySig: 'x', sym: 'ABC' });
  expect(live.pct).toBeCloseTo(10); expect(live.sol).toBeCloseTo(0.001); expect(live.tp).toBeCloseTo(0.11); expect(live.sl).toBeCloseTo(0.094); expect(live.bought).toBe(true);
  const done = powLive({ status: 'closed', entry: 0.1559, now: 0.1383, pnlPct: -1.31, netPnlSol: -0.0000665, sol: 0.005 });   // PoW #16: the cash P&L, not the price move
  expect(done.pct).toBe(-1.31); expect(done.sol).toBeCloseTo(-0.0000665); expect(done.closed).toBe(true);
  expect(powLive({ status: 'open', phase: 'read' }).pct).toBeNull();   // nothing bought: no number invented
});

test('📺 the PoW and PoP cards render and close; nothing on them trades', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); let closed = 0;
  await act(async () => { root.render(<LiveProofCard kind="pow" f={{ id: 'p1', n: 17, status: 'open', sym: 'ABC', entry: 0.1, now: 0.09, line: [0.1, 0.09], sol: 0.01, tp: 10, sl: 6 }} onClose={() => { closed += 1; }} />); });
  const q = t => el.querySelector(`[data-testid="${t}"]`);
  expect(q('lpc-pow-card').textContent).toContain('PoW #17'); expect(q('lpc-pct').textContent).toBe('−10.00%');
  expect([...el.querySelectorAll('button')].map(b => b.dataset.testid)).toEqual(['lpc-close']);
  await act(async () => { q('lpc-close').click(); }); expect(closed).toBe(1);
  await act(async () => { root.render(<LiveProofCard kind="pop" f={{ id: 'q1', n: 5, status: 'closed', noTrade: true, why: 'a mind called no trade' }} onClose={() => {}} />); });
  expect(q('lpc-pop').textContent).toContain('No trade');
  await act(async () => { root.unmount(); }); el.remove();
});
