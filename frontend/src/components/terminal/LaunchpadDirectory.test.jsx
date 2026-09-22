import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LaunchpadDirectory } from './LaunchpadDirectory';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockSetEcosystem = jest.fn();

jest.mock('react-router-dom', () => {
  const mockReact = require('react');
  return {
    Link: ({ children, ...props }) => mockReact.createElement('a', props, children),
    useNavigate: () => () => {},
  };
}, { virtual: true });

jest.mock('../../hooks/useWorkspace', () => ({
  useWorkspace: () => ({ setEcosystem: mockSetEcosystem }),
}));

function mount() {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(<LaunchpadDirectory />));
  return { host, root };
}

afterEach(() => {
  document.body.innerHTML = '';
  mockSetEcosystem.mockClear();
});

test('renders a visible FEELESS launch path and logo-first native guide', () => {
  const { host, root } = mount();

  expect(host.querySelector('[data-testid="feeless-launch-hero"]')).toBeTruthy();
  expect(host.querySelector('[data-testid="launchpad-logo-feeless-launch"]')).toBeTruthy();
  expect(host.querySelectorAll('[data-testid="launchpad-guide"] article')).toHaveLength(6);
  expect(host.querySelector('[data-testid="launchpad-card-pump"] img')).toBeTruthy();

  act(() => root.unmount());
});

test('filters launch rails by chain and search without losing the native launch action', () => {
  const { host, root } = mount();

  act(() => host.querySelector('[data-testid="launchpad-filter-bsc"]').click());
  expect(host.querySelector('[data-testid="launchpad-card-four"]')).toBeTruthy();
  expect(host.querySelector('[data-testid="launchpad-card-pump"]')).toBeNull();
  expect(host.querySelector('[data-testid="launchpad-warroom-feeless-launch"]')).toBeTruthy();

  act(() => root.unmount());
});

test('opens the FEELESS setup from the native launch action', () => {
  const { host, root } = mount();

  act(() => host.querySelector('[data-testid="launchpad-warroom-feeless-launch"]').click());
  expect(mockSetEcosystem).toHaveBeenCalledWith('feeless-launch');

  act(() => root.unmount());
});