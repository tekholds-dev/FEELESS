import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import Landing from './Landing';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockSetEcosystem = jest.fn();

jest.mock('react-router-dom', () => {
  const mockReact = require('react');
  return {
    Link: ({ children, ...props }) => mockReact.createElement('a', props, children),
    useSearchParams: () => [new URLSearchParams('node=solana')],
  };
}, { virtual: true });

jest.mock('../hooks/useWorkspace', () => ({
  useWorkspace: () => ({ setEcosystem: mockSetEcosystem }),
}));

jest.mock('../components/Globe3D', () => () => <div data-testid="mock-globe" />);
jest.mock('../components/EcosystemChat', () => () => <div data-testid="mock-chat">Chat panel</div>);
jest.mock('../components/EcosystemPlatforms', () => () => <div data-testid="mock-platforms" />);
jest.mock('../components/WalletModal', () => () => null);
jest.mock('../components/terminal/TerminalShell', () => ({
  TerminalHeader: () => <header data-testid="mock-header" />,
  MarketTicker: () => <div data-testid="mock-ticker" />,
}));
jest.mock('../components/command/WorkspaceChrome', () => ({
  ContextBar: () => <div data-testid="mock-context-bar" />,
  MouseGlow: () => null,
}));
jest.mock('../components/TopCoins', () => ({ ecosystem }) => (
  <div data-testid="globe-coin-radar">
    <span data-testid="mock-radar-ecosystem">{ecosystem.name}</span>
    <button data-testid="mock-top-coins">Top coins</button>
    <button data-testid="mock-new-coins">New coins</button>
  </div>
));

function setViewport(isMobile) {
  window.matchMedia = jest.fn(query => ({
    matches: isMobile && query === '(max-width: 760px)',
    media: query,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  }));
}

function mount() {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<Landing />));
  return { container, root };
}

afterEach(() => {
  document.body.innerHTML = '';
  mockSetEcosystem.mockClear();
});

test('opens the coin radar on keyboard focus and keeps feeds reachable', () => {
  setViewport(false);
  const { container, root } = mount();
  const rail = container.querySelector('[data-testid="degen-coins-rail"]');
  const toggle = container.querySelector('[data-testid="degen-coins-toggle"]');

  expect(toggle.getAttribute('aria-expanded')).toBe('false');
  act(() => toggle.focus());
  expect(toggle.getAttribute('aria-expanded')).toBe('true');
  expect(container.querySelector('[data-testid="mock-top-coins"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="mock-new-coins"]')).toBeTruthy();

  act(() => container.querySelector('[data-testid="mock-new-coins"]').focus());
  expect(rail.classList.contains('is-open')).toBe(true);
  act(() => root.unmount());
});


test('keeps both coin feeds exposed on mobile without hover', () => {
  setViewport(true);
  const { container, root } = mount();
  const rail = container.querySelector('[data-testid="degen-coins-rail"]');
  const toggle = container.querySelector('[data-testid="degen-coins-toggle"]');

  expect(rail.classList.contains('is-open')).toBe(true);
  expect(toggle.getAttribute('aria-expanded')).toBe('true');
  expect(container.querySelector('[data-testid="mock-top-coins"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="mock-new-coins"]')).toBeTruthy();
  act(() => root.unmount());
});

test('keeps the open coin radar attached when switching ecosystems', () => {
  setViewport(false);
  const { container, root } = mount();
  const toggle = container.querySelector('[data-testid="degen-coins-toggle"]');

  act(() => toggle.focus());
  expect(toggle.getAttribute('aria-expanded')).toBe('true');
  expect(container.querySelector('[data-testid="mock-radar-ecosystem"]').textContent).toBe('Solana');

  act(() => container.querySelector('[data-testid="globe-filter-ecosystems"]').click());
  act(() => container.querySelector('[data-testid="globe-node-ethereum"]').click());

  const nextToggle = container.querySelector('[data-testid="degen-coins-toggle"]');
  const rail = container.querySelector('[data-testid="degen-coins-rail"]');
  expect(container.querySelector('[data-testid="degen-panel-name"]').textContent).toBe('Ethereum');
  expect(nextToggle.getAttribute('aria-expanded')).toBe('true');
  expect(nextToggle.getAttribute('aria-controls')).toBe('degen-coins-popover-ethereum');
  expect(rail.classList.contains('is-open')).toBe(true);
  expect(container.querySelector('[data-testid="mock-radar-ecosystem"]').textContent).toBe('Ethereum');
  expect(container.querySelector('[data-testid="mock-top-coins"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="mock-new-coins"]')).toBeTruthy();

  act(() => nextToggle.focus());
  expect(document.activeElement).toBe(nextToggle);
  act(() => container.querySelector('[data-testid="mock-new-coins"]').focus());
  expect(document.activeElement).toBe(container.querySelector('[data-testid="mock-new-coins"]'));
  expect(rail.classList.contains('is-open')).toBe(true);
  act(() => root.unmount());
});