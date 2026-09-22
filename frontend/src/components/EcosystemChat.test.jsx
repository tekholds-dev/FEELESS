import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import EcosystemChat from './EcosystemChat';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('./TokenCard', () => () => null);
jest.mock('./command/IntelligenceCard', () => ({ IntelligenceCard: () => null }));

function mount(props) {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(<EcosystemChat compact {...props} />));
  return { host, root };
}

afterEach(() => {
  document.body.innerHTML = '';
  jest.restoreAllMocks();
});

test('loads an empty coin room and keeps the exact room in the request', async () => {
  global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ messages: [] }) });
  const mounted = mount({ room: 'coin-ethereum-pool-1-bulls', ecosystem: { name: 'ALPHA / bulls' } });

  await act(async () => {});

  expect(global.fetch).toHaveBeenCalledWith('/api/chat/coin-ethereum-pool-1-bulls', expect.objectContaining({ signal: expect.any(AbortSignal) }));
  expect(mounted.host.querySelector('[data-testid="chat-empty-coin-ethereum-pool-1-bulls"]')).not.toBeNull();
  act(() => mounted.root.unmount());
});

test('shows a retry action when the room provider fails', async () => {
  global.fetch = jest.fn().mockRejectedValue(new Error('offline'));
  const mounted = mount({ room: 'coin-solana-pool-2-bears' });

  await act(async () => {});

  expect(mounted.host.querySelector('[data-testid="chat-error-coin-solana-pool-2-bears"]')).not.toBeNull();
  expect(mounted.host.querySelector('[data-testid="chat-retry-coin-solana-pool-2-bears"]')).not.toBeNull();
  act(() => mounted.host.querySelector('[data-testid="chat-retry-coin-solana-pool-2-bears"]').click());
  expect(global.fetch).toHaveBeenCalledTimes(2);
  act(() => mounted.root.unmount());
});