import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import fs from 'fs';
import path from 'path';
import Terminal from './Terminal';

let mockPage = 'settings';

jest.mock('@solana/web3.js', () => ({
  VersionedTransaction: { deserialize: jest.fn() },
}));

jest.mock('react-router-dom', () => {
  const mockReact = require('react');
  return {
    Link: ({ children, ...props }) => mockReact.createElement('a', props, children),
    useNavigate: () => jest.fn(),
    useParams: () => ({ '*': mockPage }),
    useSearchParams: () => [new URLSearchParams(), jest.fn()],
  };
}, { virtual: true });

jest.mock('../hooks/useWorkspace', () => {
  const actual = jest.requireActual('../hooks/useWorkspace');
  return {
    ...actual,
    useWorkspace: () => ({
      ecosystem: { id: 'solana', name: 'Solana', chainId: 'solana', color: '#00e9a0' },
      setEcosystem: jest.fn(),
      selectedPair: null,
      selectPair: jest.fn(),
      watchlist: [],
      toggle: jest.fn(),
      has: jest.fn(() => false),
      alertPair: null,
    }),
  };
});

jest.mock('../hooks/useWallet', () => ({
  useWallet: () => ({ wallet: null, provider: null }),
}));

jest.mock('../hooks/useMarket', () => ({
  useMarket: path => {
    if (path === '/assets') {
      return { data: { assets: [{ id: 'fee', label: 'FEE', mint: 'fee-mint', chain: 'solana' }] }, loading: false };
    }
    if (path === '/api/trading/status') {
      return { data: { configured: false }, loading: false };
    }
    return { data: { pairs: [] }, loading: false, refreshing: false, error: undefined, reload: jest.fn() };
  },
  useWatchlist: () => ({ watchlist: [], toggle: jest.fn(), has: jest.fn(() => false) }),
}));

jest.mock('../components/terminal/TerminalShell', () => {
  const mockReact = require('react');
  const Placeholder = ({ children, onWallet, onMenu, onClose, savedCount, ...props }) => mockReact.createElement('div', props, children);
  return {
    TerminalHeader: Placeholder,
    TerminalSidebar: Placeholder,
    MarketTicker: Placeholder,
    TerminalFooter: Placeholder,
  };
});

jest.mock('../components/terminal/MarketPrimitives', () => ({
  DataStatus: () => <span />,
  MarketError: () => null,
}));

jest.mock('../components/terminal/CommunityRail', () => ({
  ChatRoom: () => null,
  TrenchesView: () => null,
}));

jest.mock('../components/terminal/TokenFocus', () => ({
  TokenFocus: () => null,
}));

jest.mock('../components/terminal/MarketTable', () => ({
  MarketTable: () => null,
}));

jest.mock('../components/terminal/LaunchpadDirectory', () => ({
  LaunchpadDirectory: () => null,
}));

jest.mock('../components/terminal/MetaLaunchSetup', () => () => null);

jest.mock('../components/command/WorkspaceChrome', () => ({
  ContextBar: () => null,
  MouseGlow: () => null,
  AlphaTape: () => null,
  PulseGrid: () => null,
  ContractScanner: () => null,
  useClock: () => 1_700_000_000_000,
}));

jest.mock('../components/command/FeeCommand', () => ({
  FeeHeartbeat: () => null,
  Tokenomics: () => null,
  FeeAssetPage: () => null,
}));

jest.mock('../components/command/FeeBack', () => ({
  FeeBackCenter: () => null,
  FeeCatCenter: () => null,
  FeeBackFlow: () => null,
  FeeBackPreview: () => null,
}));

jest.mock('../components/command/DiscoveryViews', () => ({
  RadarView: () => null,
  SignalMovers: () => null,
  LivingWatchlist: () => null,
  ParticipationBoard: () => null,
}));

jest.mock('../components/WalletModal', () => () => null);

jest.mock('../components/command/PdfReader', () => ({
  PdfReader: () => null,
}));

jest.mock('../components/ui/dialog', () => {
  const mockReact = require('react');
  const Passthrough = ({ children }) => mockReact.createElement('div', null, children);
  return {
    Dialog: Passthrough,
    DialogContent: Passthrough,
    DialogTitle: Passthrough,
    DialogDescription: Passthrough,
  };
});

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function installTradeStyles() {
  const style = document.createElement('style');
  style.dataset.testid = 'trade-styles';
  style.textContent = fs.readFileSync(path.join(__dirname, '../styles/trade.css'), 'utf8');
  document.head.appendChild(style);
  return style;
}

function tradeRule(selector) {
  for (const sheet of document.styleSheets) {
    for (const rule of sheet.cssRules || []) {
      if (rule.selectorText?.split(',').some(candidate => candidate.trim() === selector)) return rule;
    }
  }
  return null;
}

function narrowTradeRule(selector) {
  for (const sheet of document.styleSheets) {
    for (const rule of sheet.cssRules || []) {
      if (!rule.cssText?.startsWith('@media (max-width: 500px)')) continue;
      for (const nestedRule of rule.cssRules || []) {
        if (nestedRule.selectorText?.split(',').some(candidate => candidate.trim() === selector)) return nestedRule;
      }
    }
  }
  return null;
}

function mount() {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<Terminal />));
  return { container, root };
}

function selectTextSize(container, value) {
  const select = container.querySelector('[data-testid="config-text-size"]');
  act(() => {
    select.value = value;
    select.dispatchEvent(new Event('change', { bubbles: true }));
  });
  return select;
}

function renderCurrentPage(root) {
  act(() => root.render(<Terminal />));
}

afterEach(() => {
  mockPage = 'settings';
  localStorage.clear();
  document.body.innerHTML = '';
  document.head.querySelector('[data-testid="trade-styles"]')?.remove();
  jest.restoreAllMocks();
});

test('updates the trade readout for every text size and restores the choice after reload', () => {
  installTradeStyles();
  const { container, root } = mount();
  const app = () => container.querySelector('.terminal-app');
  const amount = () => container.querySelector('[data-testid="swap-amount"]');

  [
    ['normal', 'text-scale-normal', null],
    ['large', 'text-scale-large', '1.12'],
    ['xlarge', 'text-scale-xlarge', '1.24'],
  ].forEach(([value, terminalClass, expectedScale]) => {
    const select = selectTextSize(container, value);
    expect(select.value).toBe(value);
    expect(app().classList.contains(terminalClass)).toBe(true);

    mockPage = 'trade';
    renderCurrentPage(root);
    expect(container.querySelector('[data-testid="swap-workspace"]')).not.toBeNull();
    expect(app().classList.contains(terminalClass)).toBe(true);
    expect(amount().closest(`.${terminalClass}`)).not.toBeNull();
    if (expectedScale) {
      expect(tradeRule(`.${terminalClass} .swap-desk`).style.getPropertyValue('--swap-readable-scale')).toBe(expectedScale);
      expect(tradeRule(`.${terminalClass} .swap-desk .swap-amount-label input`).style.getPropertyValue('font-size'))
        .toBe('calc(30px * var(--swap-readable-scale))');
      expect(tradeRule(`.${terminalClass} .swap-desk .swap-output > strong`).style.getPropertyValue('font-size'))
        .toBe('calc(24px * var(--swap-readable-scale))');
    } else {
      expect(window.getComputedStyle(amount()).fontSize).toBe('30px');
    }
    expect(JSON.parse(localStorage.getItem('feeless-settings')).fontScale).toBe(value);

    mockPage = 'settings';
    renderCurrentPage(root);
  });

  selectTextSize(container, 'xlarge');
  mockPage = 'trade';
  renderCurrentPage(root);
  act(() => root.unmount());

  const reloaded = mount();
  expect(reloaded.container.querySelector('.terminal-app').classList.contains('text-scale-xlarge')).toBe(true);
  expect(reloaded.container.querySelector('[data-testid="swap-amount"]').closest('.text-scale-xlarge')).not.toBeNull();
  act(() => reloaded.root.unmount());
});

test('keeps trade readouts and controls bounded at a narrow preview width for every text size', () => {
  installTradeStyles();
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: 375 });
  const { container, root } = mount();

  ['normal', 'large', 'xlarge'].forEach(value => {
    selectTextSize(container, value);
    mockPage = 'trade';
    renderCurrentPage(root);

    const app = container.querySelector('.terminal-app');
    expect(app.classList.contains(`text-scale-${value}`)).toBe(true);
    expect(container.querySelector('[data-testid="swap-workspace"]')).not.toBeNull();
    expect(container.querySelector('.swap-order').classList.contains('swap-order')).toBe(true);
    expect(container.querySelector('.route-intelligence').classList.contains('route-intelligence')).toBe(true);

    mockPage = 'settings';
    renderCurrentPage(root);
  });

  expect(narrowTradeRule('.swap-amount-label input').style.getPropertyValue('font-size'))
    .toBe('calc(30px * var(--swap-readable-scale))');
  expect(narrowTradeRule('.swap-output > strong').style.getPropertyValue('font-size'))
    .toBe('calc(24px * var(--swap-readable-scale))');
  expect(narrowTradeRule('.swap-pair-heading').style.getPropertyValue('flex-direction')).toBe('column');
  expect(tradeRule('.swap-buttons button').style.getPropertyValue('width')).toBe('100%');

  act(() => root.unmount());
});
