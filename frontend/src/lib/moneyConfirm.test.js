import { toast } from 'sonner';
import { explorerTx, moneyConfirmed } from './moneyConfirm';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), info: jest.fn(), error: jest.fn(), warning: jest.fn() } }));

test('explorer links follow the chain (name or EVM chain id)', () => {
  expect(explorerTx('solana', 'abc')).toBe('https://solscan.io/tx/abc');
  expect(explorerTx(8453, '0x1')).toBe('https://basescan.org/tx/0x1');
  expect(explorerTx('solana', '')).toBe('');
});

test('a confirmed launch toasts with the tx and refreshes positions for that coin only', () => {
  const seen = [];
  const on = e => seen.push([e.type, e.detail.mint]);
  window.addEventListener('feeless:trade-confirmed', on); window.addEventListener('feeless:money-confirmed', on);
  moneyConfirmed({ title: '$CAT is live', hash: 'sig123456789', mint: 'MintX', wallet: 'W' });
  moneyConfirmed({ title: 'Swap confirmed', chain: 1, hash: '0xabc' });   // EVM: no coin, so no tape/position event
  expect(toast.success).toHaveBeenCalledTimes(2);
  expect(toast.success.mock.calls[0][0]).toContain('$CAT is live');
  expect(seen).toEqual([['feeless:money-confirmed', 'MintX'], ['feeless:trade-confirmed', 'MintX'], ['feeless:money-confirmed', undefined]]);
});
