import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeeHeartbeat } from './FeeCommand';

const marketResponses = {};

jest.mock('../../hooks/useMarket', () => ({
  useMarket: path => marketResponses[path] || { data: undefined, error: undefined },
}));

jest.mock('react-router-dom', () => {
  const mockReact = require('react');
  return {
    Link: ({ children, ...props }) => mockReact.createElement('a', props, children),
  };
}, { virtual: true });

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function mount(assets) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<FeeHeartbeat assets={assets} loading={false} />));
  return { container, root };
}

afterEach(() => {
  document.body.innerHTML = '';
  Object.keys(marketResponses).forEach(key => delete marketResponses[key]);
});

test('flips through every returned fee asset and updates price and mint state', () => {
  const assets = [
    { id: 'fee', label: 'FEE', mint: 'fee-mint', pair: { priceUsd: '1.00' } },
    { id: 'rfee', label: 'RFEE', mint: 'rfee-mint', pair: { priceUsd: '2.00' } },
    { id: 'feecat', label: 'FEECAT', mint: 'feecat-mint', pair: { priceUsd: '3.00' } },
  ];
  const { container, root } = mount(assets);
  const flip = () => act(() => container.querySelector('[data-testid="fee-heartbeat-flip"]').click());
  const readState = () => ({
    heading: container.querySelector('.fee-name b').textContent,
    price: container.querySelector('[data-testid="heartbeat-market-price"] b').textContent,
    mintTitle: container.querySelector('[data-testid="fee-copy-mint"]').title,
  });

  expect(readState()).toEqual({ heading: '$FEE', price: '$1.00', mintTitle: 'Copy FEE mint' });
  flip();
  expect(readState()).toEqual({ heading: '$RFEE', price: '$2.00', mintTitle: 'Copy RFEE mint' });
  flip();
  expect(readState()).toEqual({ heading: '$FEECAT', price: '$3.00', mintTitle: 'Copy FEECAT mint' });
  flip();
  expect(readState()).toEqual({ heading: '$FEE', price: '$1.00', mintTitle: 'Copy FEE mint' });
  act(() => root.unmount());
});