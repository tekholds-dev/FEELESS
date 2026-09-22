import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import MetaLaunchSetup, { DEFAULT_META_LAUNCH_FORM, ReceiptCopyButton, StepStatus, validateMetaLaunch } from './MetaLaunchSetup';
import { LAUNCHPADS, META_LAUNCH_STEPS } from '../../lib/launchpads';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('../../hooks/useWallet', () => ({
  useWallet: () => ({ wallet: null }),
}));

function mount(element) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(element));
  return { container, root };
}

afterEach(() => {
  document.body.innerHTML = '';
});

const validForm = {
  ...DEFAULT_META_LAUNCH_FORM,
  name: 'Meta Coin',
  symbol: 'META',
  graduationTarget: '1',
  holderAllocation: '10',
  airdropAmount: '5',
  airdropRecipients: 'wallet-one',
};

test('keeps FEELESS as a distinct native launchpad entry', () => {
  const feeless = LAUNCHPADS.find(pad => pad.isFeelessLaunch);
  expect(feeless).toBeTruthy();
  expect(feeless.name).toBe('Launch on FEELESS');
  expect(feeless.url).toBe('/terminal/launch');
});

test('rejects invalid launch allocations and missing liquidity', () => {
  const errors = validateMetaLaunch({ ...DEFAULT_META_LAUNCH_FORM, symbol: 'M', liquidityPair: '', holderAllocation: '70', airdropAmount: '40', creatorFeeShare: '20', holderRewardShare: '20', buybackBurnShare: '20' });
  expect(errors.name).toBeTruthy();
  expect(errors.symbol).toBeTruthy();
  expect(errors.liquidityPair).toBeTruthy();
  expect(errors.feeShares).toBeTruthy();
  expect(errors.allocations).toBeTruthy();
});

test('moves a valid setup to review and keeps deployment unavailable safely', () => {
  const { container } = mount(<MetaLaunchSetup initialValues={validForm} />);

  act(() => container.querySelector('[data-testid="meta-launch-review"]').click());

  expect(container.querySelector('[data-testid="meta-launch-review-page"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="meta-launch-provider-warning"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="meta-launch-deploy"]').disabled).toBe(true);
});

test('shows explorer links only for confirmed launch steps', () => {
  const { container, root } = mount(
    <div>
      <StepStatus step={META_LAUNCH_STEPS[0]} status={{ state: 'confirmed', signature: 'confirmed-signature' }} />
      <StepStatus step={META_LAUNCH_STEPS[1]} status={{ state: 'pending', signature: 'pending-signature' }} />
      <StepStatus step={META_LAUNCH_STEPS[2]} status={{ state: 'failed', signature: 'failed-signature', detail: 'Fee policy failed.' }} />
    </div>,
  );

  expect(container.querySelector('[data-testid="meta-launch-step-explorer-token"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="meta-launch-step-explorer-liquidity"]')).toBeNull();
  expect(container.querySelector('[data-testid="meta-launch-step-explorer-fee"]')).toBeNull();
  act(() => root.unmount());
});

test('copies the full confirmed signature and announces success', async () => {
  const writeText = jest.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  const { container, root } = mount(
    <StepStatus step={META_LAUNCH_STEPS[0]} status={{ state: 'confirmed', signature: 'full-confirmed-signature' }} />,
  );

  await act(async () => container.querySelector('[data-testid="meta-launch-step-copy-token"]').click());

  expect(writeText).toHaveBeenCalledWith('full-confirmed-signature');
  expect(container.querySelector('[role="status"]').textContent).toBe('Copied to clipboard.');
  act(() => root.unmount());
});

test('shows an accessible clipboard failure for the mint receipt', async () => {
  const writeText = jest.fn().mockRejectedValue(new Error('Permission denied'));
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  const { container, root } = mount(
    <ReceiptCopyButton value="full-mint-address" label="Copy mint" testId="meta-launch-mint-copy" />,
  );

  await act(async () => container.querySelector('[data-testid="meta-launch-mint-copy"]').click());

  expect(writeText).toHaveBeenCalledWith('full-mint-address');
  expect(container.querySelector('[role="alert"]').textContent).toBe('Copy failed. Clipboard access is unavailable.');
  expect(container.querySelector('[role="status"]')).toBeNull();
  act(() => root.unmount());
});