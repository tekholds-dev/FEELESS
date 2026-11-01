import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { SendCard } from './SendCard';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mockSend = jest.fn(async () => {});
jest.mock('../../lib/batchSend', () => ({ batchSend: (...a) => mockSend(...a) }));

test('📤 Send: your coin → one of your agents\' wallets (or any address), refused when wrong, dry-run + one approval when right', async () => {
  const AG = '2CkRvWbJ8YtGgz6rXXqk7sKbkHcmV4nRoo8xAJ1pczQ7';
  global.fetch = async () => ({ ok: true, json: async () => ({ cats: [{ name: 'Happy', agentWallet: { address: AG } }, { name: 'NoWallet' }] }) });
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<SendCard wallet={{ address: 'Me1111111111111111111111111111111111111111' }} provider={{}} holdings={[{ mint: 'So11111111111111111111111111111111111111112', amount: 0.5 }]} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('send-mine').textContent).toContain('Happy'); expect(q('send-mine').textContent).not.toContain('NoWallet');
  const set = async (node, v) => { const proto = Object.getPrototypeOf(node); Object.getOwnPropertyDescriptor(proto, 'value').set.call(node, v); await act(async () => { node.dispatchEvent(new Event(node.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })); }); };
  await set(q('send-to'), 'not-an-address'); await set(q('send-amount'), '0.1');
  expect(q('send-review').disabled).toBe(true); expect(el.textContent).toContain('Solana address');
  await set(q('send-mine'), AG); await set(q('send-amount'), '0.6');
  expect(el.textContent).toContain('You hold 0.5 SOL');                                                       // never more than you hold (+ fees kept)
  await set(q('send-amount'), '0.1');
  await act(async () => { q('send-review').click(); }); await act(async () => { q('send-go').click(); });
  expect(mockSend).toHaveBeenCalledTimes(1); expect(mockSend.mock.calls[0][0]).toMatchObject({ mint: null, recipients: [{ address: AG, amount: 0.1 }], kind: 'send' });
  expect(el.textContent).toContain('✓ Sent 0.1 SOL');
});
