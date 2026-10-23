import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { LpPositionCard, LpPositions } from './LpPositions';

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'W1' }, provider: {} }) }));
jest.mock('../lib/lpPositions', () => ({ useLpPositions: jest.fn(), lpAction: jest.fn() }));
const { lpAction, useLpPositions } = require('../lib/lpPositions');
const P = { id: 'P1', position: 'Pos1111111111111111111111111111111111111111', sym: 'PANGEA-SOL', coinSym: 'PANGEA', valueUsd: 12.5, valueSol: 0.12, solAmt: 0.06, coinAmt: 5210,
  feeUsd: 0.31, feeValueSol: 0.003, feeDay: 0.06, inRange: true, empty: false };

test('🏗 the position card: worth now, fees earned, pace, IN RANGE — claim runs in place; close asks first', async () => {
  lpAction.mockImplementation(() => Promise.resolve({ signature: 'SIG12345678' }));   // CRA resets mock bodies before each test
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<LpPositionCard p={P} />); });
  const t = q('lp-card-P1').textContent; expect(t).toContain('IN RANGE'); expect(t).toContain('$12.50'); expect(t).toContain('+$0.310'); expect(t).toContain('6.0%/d'); expect(t).toContain('≈ +$0.750 a day');
  expect(el.querySelectorAll('a[href^="http"]')).toHaveLength(0);
  await act(async () => { q('lp-claim-P1').click(); }); expect(lpAction).toHaveBeenLastCalledWith(expect.objectContaining({ owner: 'W1', position: P.position, act: 'claim' })); expect(q('lp-done').textContent).toContain('Fees claimed');
  window.confirm = jest.fn(() => false); await act(async () => { q('lp-close-P1').click(); }); expect(lpAction).toHaveBeenCalledTimes(1);   // declined the confirm → nothing built
  window.confirm = jest.fn(() => true); await act(async () => { q('lp-close-P1').click(); }); expect(lpAction).toHaveBeenLastCalledWith(expect.objectContaining({ act: 'close' }));
  await act(async () => { root.render(<LpPositionCard p={{ ...P, inRange: false, feeValueSol: 0, feeUsd: 0 }} />); });
  expect(q('lp-card-P1').textContent).toContain('OUT OF RANGE'); expect(q('lp-claim-P1').disabled).toBe(true);   // nothing to claim
  act(() => root.unmount()); el.remove();
});

test('🏗 your positions in the desk: the total, how many earn, the fees to claim — tap a row for its card', async () => {
  useLpPositions.mockReturnValue([P, { ...P, id: 'P2', position: 'Pos2222222222222222222222222222222222222222', sym: 'BORDR-SOL', valueUsd: 4, feeUsd: 0.02, inRange: false }]);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<LpPositions compact />); });
  expect(useLpPositions).toHaveBeenCalledWith('W1');                                         // the connected wallet's own positions
  const t = q('lp-list').textContent; expect(t).toContain('2 · 1 earning'); expect(t).toContain('$16.50 in pools'); expect(t).toContain('+$0.330 fees to claim');
  await act(async () => { q('lp-row-P2').click(); }); expect(q('lp-card-P2').textContent).toContain('OUT OF RANGE');
  useLpPositions.mockReturnValue([]); await act(async () => { root.render(<LpPositions compact />); }); expect(q('lp-list')).toBeNull();   // nothing to show → no box
  act(() => root.unmount()); el.remove();
});
