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
// The war room charts with the same TrenchChart as the trenches; stub it and record the pair it gets.
const mockTrench = jest.fn();
jest.mock('./terminal/TrenchChart', () => ({ TrenchChart: props => { mockTrench(props); return <div data-testid="mock-trench-chart">{props.pair?.priceUsd}</div>; } }));
jest.mock('./terminal/DegenWeather', () => ({ DegenWeather: () => null }));

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
    if (!path) return { data: null };
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
test('war room charts with the trench chart and feeds it the live pool price', async () => {
  const top = { chainId: 'solana', pairAddress: 'Pool1', priceUsd: '0.001', baseToken: { symbol: 'WIF', name: 'dogwifhat' } };
  mockUseMarket.mockImplementation(path => {
    if (!path) return { data: null };
    if (path.startsWith('/feed')) return { data: { pairs: [top] } };
    if (path === '/pair/solana/Pool1') return { data: { pairs: [{ ...top, priceUsd: '0.002' }] } };
    return { data: { online: 0, messages: 0, pairs: [] } };
  });
  const { container, root } = mount();
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(container.querySelector('[data-testid="eco-room-chart"]').className).toContain('m-live');
  expect(container.querySelector('[data-testid="mock-trench-chart"]').textContent).toBe('0.002');
  expect(mockTrench).toHaveBeenLastCalledWith(expect.objectContaining({ className: 'eco-trench' }));
  act(() => root.unmount());
});
