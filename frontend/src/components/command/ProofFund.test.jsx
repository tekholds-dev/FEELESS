import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ProofFundForm } from './ProofKit';
jest.mock('../../lib/legal', () => ({ ...jest.requireActual('../../lib/legal'), assertLegal: jest.fn(async () => true) }));   // ⚖ the LEGAL-1 gate has its own tests (lib/legal.test.js); these test the signing flow after it

jest.mock('@solana/web3.js', () => ({ Transaction: { from: bytes => ({ bytes }) } }));

// 💸 COL-16: amounts + % on screen before anything is signed; the wallet signs the quoted tx; the receipt shows on the proof.
test('send with funds: quote shows both amounts and the %, the wallet signs the quote, the receipt is filed', async () => {
  const work = jest.fn(async (_, b) => (b.op === 'fund_quote' ? { quote: { id: 'Q1', userSol: 0.1, pct: 20, agentSol: 0.02, totalSol: 0.12 }, tx: btoa('TX') }
    : b.op === 'fund_send' ? { receipt: { quote: 'Q1', userSol: 0.1, pct: 20, agentSol: 0.02, totalSol: 0.12, userSig: 'US', agentSig: 'AS' } } : {}));
  const signer = { signTransaction: jest.fn(async tx => ({ serialize: () => Uint8Array.from([7, 8, 9]), tx })) };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ProofFundForm cat={{ id: 'c', fundGrade: { auto: true, pct: 20 } }} work={work} f={{ id: 'p1' }} signer={signer} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(q('fund-sol'), '0.1'); q('fund-sol').dispatchEvent(new Event('input', { bubbles: true })); });
  expect(q('fund-math').textContent).toContain('Its wallet adds 20%'); expect(q('fund-math').textContent).toContain('0.1200 SOL');
  expect(signer.signTransaction).not.toHaveBeenCalled();
  await act(async () => { q('fund-quote').click(); });
  expect(work).toHaveBeenCalledWith('c', expect.objectContaining({ op: 'fund_quote', job: 'p1', cap: 0.1 }));
  expect(q('fund-send').textContent).toBe('Sign and send 0.1200 SOL');
  await act(async () => { q('fund-send').click(); });
  expect(Array.from(signer.signTransaction.mock.calls[0][0].bytes)).toEqual([84, 88]);   // exactly the quoted tx ('TX')
  expect(work).toHaveBeenCalledWith('c', expect.objectContaining({ op: 'fund_send', job: 'p1', text: 'Q1', sig: btoa(String.fromCharCode(7, 8, 9)) }));
  expect(q('fund-receipt').textContent).toContain('0.1200 SOL'); expect(q('fund-receipt').textContent).toContain('its 20%');
  await act(async () => root.unmount()); el.remove();
});
