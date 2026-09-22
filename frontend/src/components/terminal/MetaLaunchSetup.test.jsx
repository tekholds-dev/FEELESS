import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import MetaLaunchSetup, { DEFAULT_META_LAUNCH_FORM, validateMetaLaunch } from './MetaLaunchSetup';
import { LAUNCHPADS } from '../../lib/launchpads';

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
  liquidityAmount: '1',
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
  const errors = validateMetaLaunch({ ...DEFAULT_META_LAUNCH_FORM, symbol: 'M', holderAllocation: '70', airdropAmount: '40' });
  expect(errors.name).toBeTruthy();
  expect(errors.symbol).toBeTruthy();
  expect(errors.liquidityAmount).toBeTruthy();
  expect(errors.allocations).toBeTruthy();
});

test('moves a valid setup to review and keeps deployment unavailable safely', () => {
  const { container } = mount(<MetaLaunchSetup initialValues={validForm} />);

  act(() => container.querySelector('[data-testid="meta-launch-review"]').click());

  expect(container.querySelector('[data-testid="meta-launch-review-page"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="meta-launch-provider-warning"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="meta-launch-deploy"]').disabled).toBe(true);
});