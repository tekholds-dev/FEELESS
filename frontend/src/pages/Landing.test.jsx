import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import Landing from './Landing';
import { ECOSYSTEMS } from '../lib/ecosystems';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockSetEcosystem = jest.fn();
const selectableEcosystems = ECOSYSTEMS.filter(ecosystem => !ecosystem.isFeeless);

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
jest.mock('../components/EcosystemWorld', () => ({ ecosystem }) => <div data-testid="mock-ecosystem-world">{ecosystem.name}</div>);
jest.mock('../components/WalletModal', () => () => null);
jest.mock('../components/terminal/TerminalShell', () => ({
  TerminalHeader: () => <header data-testid="mock-header" />,
  MarketTicker: () => <div data-testid="mock-ticker" />,
}));
jest.mock('../components/command/WorkspaceChrome', () => ({
  ContextBar: () => <div data-testid="mock-context-bar" />,
  MouseGlow: () => null,
}));

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

test('does not render the removed ecosystem side panel or coin radar rail', () => {
  const { container, root } = mount();

  expect(container.querySelector('[data-testid="degen-panel"]')).toBeNull();
  expect(container.querySelector('[data-testid="degen-coins-rail"]')).toBeNull();
  expect(container.querySelector('.globe-layout').classList.contains('with-panel')).toBe(false);

  act(() => root.unmount());
});

test('keeps ecosystem selection and announcements working without the side panel', () => {
  const { container, root } = mount();

  act(() => container.querySelector('[data-testid="globe-filter-ecosystems"]').click());
  act(() => container.querySelector('[data-testid="globe-node-ethereum"]').click());

  expect(container.querySelector('[data-testid="globe-node-ethereum"]').classList.contains('active')).toBe(true);
  expect(container.querySelector('[data-testid="mock-ecosystem-world"]').textContent).toBe('Ethereum');
  expect(container.querySelector('[data-testid="degen-panel"]')).toBeNull();
  expect(container.querySelector('[data-testid="globe-ecosystem-announcement"]').textContent)
    .toBe('Ethereum selected. Top coins and New coins feeds are active.');

  act(() => root.unmount());
});

test('keeps every ecosystem directory node usable without the side panel', () => {
  const { container, root } = mount();

  act(() => container.querySelector('[data-testid="globe-filter-ecosystems"]').click());
  selectableEcosystems.forEach(ecosystem => {
    const node = container.querySelector(`[data-testid="globe-node-${ecosystem.id}"]`);
    expect(node).toBeTruthy();

    act(() => node.click());
    expect(node.classList.contains('active')).toBe(true);
    expect(container.querySelector('[data-testid="degen-panel"]')).toBeNull();
  });

  act(() => root.unmount());
});