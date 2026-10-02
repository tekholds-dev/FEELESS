import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { address: 'MeWa11et' } }) }));
jest.mock('../lib/chatSession', () => ({ readChatSession: () => 'sess' }));
import { CardRounds } from './CardRounds';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const tick = () => act(async () => { await new Promise(r => setTimeout(r, 0)); });

test('card rounds: 5 by default, out → +5 pay or compound pays; compound posts without a payment', async () => {
  const calls = [];
  global.fetch = jest.fn(async (url, o) => { calls.push([String(url), o?.body]); return { ok: true, json: async () => (String(url).includes('/fees/pricing') ? { rounds: { per5Usd: 0.25, compoundPay: true, step: 5, payTo: 'FEE' } } : { roundsLeft: 5, roundsOwedUsd: 0.25 }) }; });
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<CardRounds card={{ id: 'c1', roundsLeft: 0, roundsUsed: 5 }} />); }); await tick();
  const box = host.querySelector('[data-testid="rounds-c1"]');
  expect(box.className).toContain('is-out'); expect(box.textContent).toContain('0 left'); expect(box.textContent).toContain('$0.25');
  act(() => host.querySelector('[data-testid="rounds-compound"]').click()); await tick();
  const sent = calls.find(c => c[0].includes('/fuses/rounds'));
  expect(JSON.parse(sent[1])).toMatchObject({ id: 'c1', mode: 'compound', signature: '' });
});
