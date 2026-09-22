import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import Landing from './Landing';
import { ECOSYSTEMS } from '../lib/ecosystems';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockSetEcosystem = jest.fn();
const selectableEcosystems = ECOSYSTEMS.filter(ecosystem => !ecosystem.isFeeless);
const mockRadarStates = { top: 'loading', new: 'loading' };

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
    {['top', 'new'].map(feed => {
      const title = feed === 'top' ? 'Top coins' : 'New coins';
      const state = mockRadarStates[feed];
      if (state === 'error') {
        return <div key={feed} role="alert" tabIndex="0" data-testid={`mock-${feed}-error`}>Unable to load {title.toLowerCase()} for {ecosystem.name}. Provider unavailable<button type="button">Retry {title}</button></div>;
      }
      if (state === 'empty') {
        return <p key={feed} role="status" aria-live="polite" tabIndex="0" data-testid={`mock-${feed}-empty`}>No {title.toLowerCase()} available for {ecosystem.name} in this provider feed.</p>;
      }
      return <p key={feed} role="status" aria-live="polite" tabIndex="0" data-testid={`mock-${feed}-loading`}>Loading {title.toLowerCase()} for {ecosystem.name}…</p>;
    })}
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
  mockRadarStates.top = 'loading';
  mockRadarStates.new = 'loading';
});

test('opens the coin radar on keyboard focus and keeps feeds reachable', () => {
  setViewport(false);
  const { container, root } = mount();
  const rail = container.querySelector('[data-testid="degen-coins-rail"]');
  const toggle = container.querySelector('[data-testid="degen-coins-toggle"]');

  expect(toggle.getAttribute('aria-expanded')).toBe('false');
  act(() => toggle.focus());
  expect(toggle.getAttribute('aria-expanded')).toBe('true');
  expect(container.querySelector('[data-testid="mock-top-loading"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="mock-new-loading"]')).toBeTruthy();

  act(() => container.querySelector('[data-testid="mock-new-loading"]').focus());
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
  expect(container.querySelector('[data-testid="mock-top-loading"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="mock-new-loading"]')).toBeTruthy();
  act(() => root.unmount());
});

test('mobile keyboard flow reaches loading, empty, and error states after switching ecosystems', () => {
  setViewport(true);
  const { container, root } = mount();
  const rail = container.querySelector('[data-testid="degen-coins-rail"]');
  const toggle = container.querySelector('[data-testid="degen-coins-toggle"]');

  expect(rail.classList.contains('is-open')).toBe(true);
  expect(toggle.getAttribute('aria-expanded')).toBe('true');
  act(() => toggle.focus());
  act(() => container.querySelector('[data-testid="mock-top-loading"]').focus());
  expect(document.activeElement).toBe(container.querySelector('[data-testid="mock-top-loading"]'));
  act(() => container.querySelector('[data-testid="mock-new-loading"]').focus());
  expect(document.activeElement).toBe(container.querySelector('[data-testid="mock-new-loading"]'));

  act(() => container.querySelector('[data-testid="globe-filter-ecosystems"]').click());
  act(() => container.querySelector('[data-testid="globe-node-ethereum"]').click());
  mockRadarStates.top = 'empty';
  mockRadarStates.new = 'empty';
  act(() => root.render(<Landing />));

  expect(container.querySelector('[data-testid="degen-panel-name"]').textContent).toBe('Ethereum');
  expect(rail.classList.contains('is-open')).toBe(true);
  const topEmpty = container.querySelector('[data-testid="mock-top-empty"]');
  const newEmpty = container.querySelector('[data-testid="mock-new-empty"]');
  expect(topEmpty.textContent).toContain('No top coins available for Ethereum');
  expect(newEmpty.textContent).toContain('No new coins available for Ethereum');
  act(() => topEmpty.focus());
  expect(document.activeElement).toBe(topEmpty);
  act(() => newEmpty.focus());
  expect(document.activeElement).toBe(newEmpty);

  mockRadarStates.top = 'error';
  mockRadarStates.new = 'error';
  act(() => root.render(<Landing />));
  const topError = container.querySelector('[data-testid="mock-top-error"]');
  const newError = container.querySelector('[data-testid="mock-new-error"]');
  expect(topError.getAttribute('role')).toBe('alert');
  expect(newError.getAttribute('role')).toBe('alert');
  act(() => topError.focus());
  expect(document.activeElement).toBe(topError);
  act(() => newError.focus());
  expect(document.activeElement).toBe(newError);
  expect(rail.classList.contains('is-open')).toBe(true);
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
   expect(container.querySelector('[data-testid="mock-top-loading"]')).toBeTruthy();
   expect(container.querySelector('[data-testid="mock-new-loading"]')).toBeTruthy();

  act(() => nextToggle.focus());
  expect(document.activeElement).toBe(nextToggle);
   act(() => container.querySelector('[data-testid="mock-new-loading"]').focus());
   expect(document.activeElement).toBe(container.querySelector('[data-testid="mock-new-loading"]'));
  expect(rail.classList.contains('is-open')).toBe(true);
  act(() => root.unmount());
});

test('opens every ecosystem from the directory without breaking either coin feed', () => {
  setViewport(false);
  const { container, root } = mount();

  act(() => container.querySelector('[data-testid="globe-filter-ecosystems"]').click());
  selectableEcosystems.forEach(ecosystem => {
    const node = container.querySelector(`[data-testid="globe-node-${ecosystem.id}"]`);
    expect(node).toBeTruthy();

    act(() => node.click());
    expect(container.querySelector('[data-testid="degen-panel-name"]').textContent).toBe(ecosystem.name);
    expect(container.querySelector('[data-testid="mock-radar-ecosystem"]').textContent).toBe(ecosystem.name);
     expect(container.querySelector('[data-testid="mock-top-loading"]')).toBeTruthy();
     expect(container.querySelector('[data-testid="mock-new-loading"]')).toBeTruthy();
  });

  act(() => root.unmount());
});