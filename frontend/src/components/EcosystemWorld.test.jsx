import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import EcosystemWorld from './EcosystemWorld';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockUseMarket = jest.fn();

jest.mock('react-router-dom', () => ({
  Link: ({ children, ...props }) => <a {...props}>{children}</a>,
}), { virtual: true });

jest.mock('../hooks/useMarket', () => ({
  useMarket: (...args) => mockUseMarket(...args),
}));

jest.mock('./EcosystemChat', () => () => <div data-testid="mock-ecosystem-chat" />);
jest.mock('./NewStuffFeed', () => () => <div data-testid="mock-new-stuff-feed" />);

const ecosystem = {
  id: 'pump',
  name: 'Pump.fun',
  chainId: 'solana',
  color: '#14f195',
  symbol: 'P',
  isLaunchpad: true,
  dex: 'https://dex.example',
  explorer: 'https://explorer.example',
};

function mount() {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<EcosystemWorld ecosystem={ecosystem} onClose={() => {}} />));
  return { container, root };
}

beforeEach(() => {
  mockUseMarket.mockImplementation(path => {
    if (path.includes('/online')) return { data: { online: 0 } };
    if (path.includes('/community')) return { data: { messages: 0 } };
    return { data: { pairs: [] } };
  });
});

afterEach(() => {
  document.body.innerHTML = '';
  document.body.style.overflow = '';
  mockUseMarket.mockReset();
});

test('switches between balanced, chat-first, and feed-first layouts', () => {
  const { container, root } = mount();
  const world = container.querySelector('[data-testid="ecosystem-world"]');
  const inner = world.querySelector('.eco-world-inner');

  expect(inner.className).toContain('eco-layout-balanced');
  expect(container.querySelector('[data-testid="eco-layout-balanced"]').getAttribute('aria-pressed')).toBe('true');

  act(() => container.querySelector('[data-testid="eco-layout-chat-first"]').click());
  expect(inner.className).toContain('eco-layout-chat-first');
  expect(container.querySelector('[data-testid="eco-layout-chat-first"]').getAttribute('aria-pressed')).toBe('true');

  act(() => container.querySelector('[data-testid="eco-layout-feed-first"]').click());
  expect(inner.className).toContain('eco-layout-feed-first');
  expect(container.querySelector('[data-testid="eco-layout-feed-first"]').getAttribute('aria-pressed')).toBe('true');

  act(() => root.unmount());
});

test('expands and restores the network room window', () => {
  const { container, root } = mount();
  const world = container.querySelector('[data-testid="ecosystem-world"]');
  const toggle = container.querySelector('[data-testid="eco-layout-expand"]');

  expect(world.querySelector('.eco-world-inner').classList.contains('is-expanded')).toBe(false);
  expect(toggle.textContent).toBe('Expand window');

  act(() => toggle.click());
  expect(world.querySelector('.eco-world-inner').classList.contains('is-expanded')).toBe(true);
  expect(toggle.textContent).toBe('Exit expanded');
  expect(toggle.getAttribute('aria-pressed')).toBe('true');

  act(() => toggle.click());
  expect(world.querySelector('.eco-world-inner').classList.contains('is-expanded')).toBe(false);
  expect(toggle.textContent).toBe('Expand window');

  act(() => root.unmount());
});