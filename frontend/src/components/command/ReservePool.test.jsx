import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('react-router-dom', () => ({ Link: ({ children, ...p }) => <a {...p}>{children}</a>, useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: mockWallet.address }, provider: {}, connect: jest.fn() }) }));
jest.mock('../../lib/batchSend', () => ({ batchSend: (...a) => mockSend(...a) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockWallet = { address: 'Other1111111111111111111111111111111111111' };
const mockSend = jest.fn(async () => ['sig1']);
const { ReservePool } = require('./CommandCenter');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const RES = 'Res11111111111111111111111111111111111111111';

const plan = {
  poolSol: 4, pct: 50, potSol: 2, paidSol: 1.95, droppedDust: 0, assigned: true, balanceKnown: true, ended: true, payout: null,
  weights: { Legend: 12, Diamond: 6, Gold: 3, Silver: 2, Bronze: 1, Recruit: 0 },
  season: { id: 's1', name: 'Genesis', reserveWallet: RES, badgeRewardPct: 50 },
  rows: [{ address: 'Aaaa1111111111111111111111111111111111111111', tier: 'Legend', weight: 12, sharePct: 92.3, sol: 1.8, score: 13000 },
    { address: 'Bbbb1111111111111111111111111111111111111111', tier: 'Bronze', weight: 1, sharePct: 7.7, sol: 0.15, score: 300 }],
};

async function mount() {
  const call = jest.fn(async (path, opts) => (path === '/admin/seasons' ? { seasons: [{ id: 's1', name: 'Genesis', start: 1, end: 2 }] } : path.endsWith('/paid') ? { ok: true } : plan));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ReservePool call={call} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  return { el, call };
}

test('shows the pot, tier shares and only pays from the reserve wallet', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({}) }));
  mockSend.mockImplementation(async () => ['sig1']);
  let { el, call } = await mount();
  expect(el.textContent).toContain('2 SOL');
  expect(el.textContent).toContain('Legend');
  expect(el.textContent).toContain('Connect the reserve wallet to pay');
  mockWallet.address = RES;
  ({ el, call } = await mount());
  const btn = [...el.querySelectorAll('button')].find(b => b.textContent.startsWith('Pay out'));
  await act(async () => { btn.click(); });
  expect(mockSend.mock.calls[0][0].recipients).toEqual([{ address: plan.rows[0].address, amount: 1.8 }, { address: plan.rows[1].address, amount: 0.15 }]);
  expect(call).toHaveBeenCalledWith('/admin/reserve/s1/paid', expect.objectContaining({ body: JSON.stringify({ sigs: ['sig1'] }) }));
  require('fs').writeFileSync('/tmp/claude-0/pool.html', el.innerHTML);
});
