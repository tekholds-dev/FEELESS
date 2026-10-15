import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { CoinChips, FuseClean } from './CircleWallets';

jest.mock('react-router-dom', () => ({ Link: ({ children, ...p }) => <a {...p}>{children}</a>, useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('../terminal/MarketPrimitives', () => ({ TokenAvatar: ({ pair }) => <img alt={pair.baseToken.symbol} data-testid="logo" /> }));

test('every coin shows its logo and its $; dust is dimmed; the wallet total adds up', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CoinChips w={{ balances: [{ symbol: 'SOL', amount: '0.029', usd: 3.4 }, { symbol: 'MINU', amount: '1659', mint: 'M1', usd: 0.02 }, { symbol: 'PAUL', amount: '10109', mint: 'M2', usd: 0.61 }] }} />); });
  expect(el.querySelectorAll('[data-testid="logo"]').length).toBe(2);
  expect(el.querySelector('.cwc-c.is-dust').textContent).toContain('MINU');
  expect(el.querySelector('.cwc-total').textContent).toContain('$4.03');
});

test('🧹 one click: check shows what sells and what burns, clean burns first then queues the sales', async () => {
  const call = jest.fn(async (path, opts) => {
    if (path === '/admin/fuse-wallet/close-dust') return JSON.parse(opts.body).confirm ? { accounts: [{ mint: 'M1' }], rentUsd: 0.18 } : { accounts: [{ mint: 'M1', symbol: 'MINU', usd: 0.02 }], dustUsd: 0.02, rentUsd: 0.18 };
    if (path === '/admin/fuse-wallet') return { recoverable: [{ card: 'degen', mint: 'M2', symbol: 'PAUL' }, { card: 'degen', mint: 'M1', symbol: 'MINU' }] };
    if (path === '/admin/fuse-wallet/recover-sell-all') return { queued: 1 };
    return {};
  });
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FuseClean call={call} />); });
  await act(async () => { el.querySelector('[data-testid="fuse-clean-check"]').click(); });
  const plan = el.querySelector('[data-testid="fuse-clean-plan"]').textContent;
  expect(plan).toContain('sell 1: $PAUL'); expect(plan).toContain('burn + close 1');
  await act(async () => { el.querySelector('[data-testid="fuse-clean-go"]').click(); });
  const paths = call.mock.calls.map(c => c[0]);
  expect(paths.indexOf('/admin/fuse-wallet/recover-sell-all')).toBeGreaterThan(paths.lastIndexOf('/admin/fuse-wallet/close-dust') - 1);
  expect(call).toHaveBeenCalledWith('/admin/fuse-wallet/recover-sell-all', { method: 'POST', body: JSON.stringify({ tpl: 'degen' }) });
});
