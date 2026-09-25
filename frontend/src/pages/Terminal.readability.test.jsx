import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import fs from 'fs';
import path from 'path';
import Terminal from './Terminal';

let mockPage = 'settings';
let mockSearch = new URLSearchParams();
let mockPairResult = { data: { pairs: [] }, loading: false, refreshing: false, error: undefined, reload: jest.fn() };
let mockMarketResult = { data: { pairs: [] }, loading: false, refreshing: false, error: undefined, reload: jest.fn() };
let mockMarketPaths = [];

jest.mock('@solana/web3.js', () => ({
  VersionedTransaction: { deserialize: jest.fn() },
}));

jest.mock('react-router-dom', () => {
  const mockReact = require('react');
  return {
    Link: ({ children, ...props }) => mockReact.createElement('a', props, children),
    useNavigate: () => jest.fn(),
    useParams: () => ({ '*': mockPage }),
    useSearchParams: () => [mockSearch, jest.fn()],
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
    if (path) mockMarketPaths.push(path);
    if (path === '/assets') {
      return { data: { assets: [{ id: 'fee', label: 'FEE', mint: 'fee-mint', chain: 'solana' }] }, loading: false };
    }
    if (path === '/api/trading/status') {
      return { data: { configured: false }, loading: false };
    }
    if (path === '/pair/ethereum/pool1') return mockPairResult;
    if (path?.startsWith('/feed?kind=trending') || path?.startsWith('/feed?kind=new')) return mockMarketResult;
    return { data: { pairs: [] }, loading: false, refreshing: false, error: undefined, reload: jest.fn() };
  },
  useWatchlist: () => ({ watchlist: [], toggle: jest.fn(), has: jest.fn(() => false) }),
}));

jest.mock('../components/terminal/TerminalShell', () => {
  const mockReact = require('react');
  const Placeholder = ({ children, onWallet, onProfile, onMenu, onClose, savedCount, ...props }) => mockReact.createElement('div', props, children);
  return {
    TerminalHeader: Placeholder,
    TerminalSidebar: Placeholder,
    MarketTicker: Placeholder,
    TerminalFooter: Placeholder,
  };
});

jest.mock('../components/terminal/MarketPrimitives', () => {
  const actual = jest.requireActual('../components/terminal/MarketPrimitives');
  return {
    ...actual,
    DataStatus: () => <span />,
    MarketError: ({ id, error }) => <div data-testid={id}>{error}</div>,
  };
});

jest.mock('../components/terminal/CommunityRail', () => ({
  ChatRoom: ({ selectedPair, selectedPerspective }) => selectedPair
    ? <div data-testid="restored-chat-room">{selectedPair.chainId}:{selectedPair.pairAddress}:{selectedPerspective}</div>
    : null,
  TrenchesView: ({ selectedPair, selectedPerspective }) => selectedPair
    ? <div data-testid="restored-chat-room">{selectedPair.chainId}:{selectedPair.pairAddress}:{selectedPerspective}</div>
    : null,
}));

jest.mock('../components/terminal/TokenFocus', () => ({
  TokenFocus: () => null,
}));

jest.mock('../components/terminal/MarketTable', () => ({
  MarketTable: ({ pairs, screenerLabel, loading }) => (
    <div data-testid="terminal-market-table" data-loading={loading ? 'true' : 'false'}>
      {pairs.map(pair => {
        const signals = pair.signals || {};
        return <div data-testid="terminal-market-row" key={pair.pairAddress}>
          <span data-testid="terminal-market-label">{signals.score_label || screenerLabel}</span>
          <span data-testid="terminal-market-score">{signals.screener_score}</span>
          <span data-testid="terminal-market-reasons">{(signals.score_reasons || []).join(' · ')}</span>
        </div>;
      })}
    </div>
  ),
}));

jest.mock('../components/terminal/LaunchpadDirectory', () => ({
  LaunchpadDirectory: () => null,
}));

jest.mock('../components/terminal/MetaLaunchSetup', () => () => null);

jest.mock('../components/command/WorkspaceChrome', () => ({
  ContextBar: () => null,
  MouseGlow: () => null,
  AmbientFlakes: () => null,
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
  PumpRadarView: () => null,
  MetaDetector: () => null,
}));

jest.mock('../components/command/LiveTrust', () => ({
  TrustSignals: () => null,
  CaseStudies: () => null,
  LiveProof: () => null,
  RoadmapVoting: () => null,
  DataSovereignty: () => null,
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
  mockSearch = new URLSearchParams();
  mockPairResult = { data: { pairs: [] }, loading: false, refreshing: false, error: undefined, reload: jest.fn() };
  mockMarketResult = { data: { pairs: [] }, loading: false, refreshing: false, error: undefined, reload: jest.fn() };
  mockMarketPaths = [];
  localStorage.clear();
  document.body.innerHTML = '';
  document.head.querySelector('[data-testid="trade-styles"]')?.remove();
  jest.restoreAllMocks();
});

test('shows provider retry timing in Terminal discovery without hiding the fallback snapshot', () => {
  mockPage = 'discover';
  mockMarketResult = {
    data: {
      provider: 'DexScreener',
      primary_provider: 'GeckoTerminal',
      pairs: [{
        chainId: 'solana',
        pairAddress: 'fallback-pair',
        baseToken: { address: 'fallback-mint', symbol: 'FALLBACK' },
        liquidity: { usd: 5000 },
      }],
      provider_warning: {
        provider: 'GeckoTerminal',
        status: 429,
        rate_limited: true,
        retry_after_seconds: 6,
      },
    },
    loading: false,
    refreshing: false,
    error: undefined,
    reload: jest.fn(),
  };
  const { container, root } = mount();

  const notice = container.querySelector('[data-testid="market-feed-availability"]');
  expect(notice.textContent).toMatch(/GeckoTerminal is cooling down/i);
  expect(notice.textContent).toMatch(/available in about 6 seconds/i);
  expect(container.querySelectorAll('[data-testid="terminal-market-row"]')).toHaveLength(1);
  act(() => root.unmount());
});

test('restores an exact pair and discussion perspective after a direct-link remount', () => {
  mockPage = 'chat';
  mockSearch = new URLSearchParams('chain=ethereum&pair=pool1&room=bears');
  const pair = {
    chainId: 'ethereum',
    pairAddress: 'pool1',
    baseToken: { symbol: 'ALPHA', name: 'Alpha Coin' },
  };
  mockPairResult = { data: { provider: 'DexScreener', pairs: [pair] }, loading: false, refreshing: false, error: undefined, reload: jest.fn() };

  const first = mount();
  expect(first.container.querySelector('[data-testid="restored-chat-room"]').textContent).toBe('ethereum:pool1:bears');
  act(() => first.root.unmount());

  const reloaded = mount();
  expect(reloaded.container.querySelector('[data-testid="restored-chat-room"]').textContent).toBe('ethereum:pool1:bears');
  act(() => reloaded.root.unmount());
});

test('shows a visible error and does not substitute a coin for an unavailable pair link', () => {
  mockPage = 'chat';
  mockSearch = new URLSearchParams('chain=ethereum&pair=missingpool&room=trenches');
  const { container, root } = mount();

  expect(container.querySelector('[data-testid="selected-pair-route-error"]').textContent).toContain('was not returned by the market provider');
  expect(container.querySelector('[data-testid="restored-chat-room"]')).toBeNull();
  act(() => root.unmount());
});

test('switches terminal market rows to the selected screener without showing cached reasons', () => {
  mockPage = 'discover';
  mockSearch = new URLSearchParams('screen=quality');
  const qualityPair = {
    chainId: 'solana',
    pairAddress: 'quality-pair',
    baseToken: { symbol: 'QUALITY' },
    liquidity: { usd: 10000 },
    signals: {
      screener: 'quality',
      screener_score: 41.1,
      score_label: 'Best observed setups',
      score_reasons: ['quality liquidity', 'quality activity'],
    },
  };
  mockMarketResult = {
    data: {
      screener: 'quality',
      screener_label: 'Best observed setups',
      pairs: [qualityPair],
    },
    loading: false,
    refreshing: false,
    error: undefined,
    reload: jest.fn(),
  };

  const { container, root } = mount();
  expect(container.querySelector('[data-testid="terminal-market-label"]').textContent).toBe('Best observed setups');
  expect(container.querySelector('[data-testid="terminal-market-score"]').textContent).toBe('41.1');
  expect(container.querySelector('[data-testid="terminal-market-reasons"]').textContent).toBe('quality liquidity · quality activity');

  mockSearch = new URLSearchParams('screen=momentum');
  mockMarketResult = {
    ...mockMarketResult,
    data: { ...mockMarketResult.data, stale: true, error: 'provider temporarily unavailable' },
    refreshing: true,
  };
  renderCurrentPage(root);
  expect(container.querySelector('[data-testid="terminal-market-row"]')).toBeNull();
  expect(container.querySelector('[data-testid="terminal-market-table"]').getAttribute('data-loading')).toBe('true');
  expect(container.querySelector('[data-testid="market-stale-warning"]')).toBeNull();

  const momentumPair = {
    ...qualityPair,
    pairAddress: 'momentum-pair',
    signals: {
      screener: 'momentum',
      screener_score: 72.2,
      score_label: 'Momentum',
      score_reasons: ['momentum movement', 'momentum activity'],
    },
  };
  mockMarketResult = {
    ...mockMarketResult,
    data: {
      screener: 'momentum',
      screener_label: 'Momentum',
      stale: true,
      error: 'provider temporarily unavailable',
      pairs: [momentumPair],
    },
    refreshing: false,
  };
  renderCurrentPage(root);
  expect(container.querySelector('[data-testid="terminal-market-label"]').textContent).toBe('Momentum');
  expect(container.querySelector('[data-testid="terminal-market-score"]').textContent).toBe('72.2');
  expect(container.querySelector('[data-testid="terminal-market-reasons"]').textContent).toBe('momentum movement · momentum activity');
  expect(container.querySelector('[data-testid="market-stale-warning"]').textContent).toContain('provider temporarily unavailable');
  act(() => root.unmount());
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

test.each([
  ['unknown', 'normal'],
  ['legacy-large', 'normal'],
  [null, 'normal'],
  [42, 'normal'],
])('normalizes an invalid saved font scale (%p) before settings and trade render', (savedValue, expected) => {
  installTradeStyles();
  localStorage.setItem('feeless-settings', JSON.stringify({ compact: false, fontScale: savedValue }));
  const { container, root } = mount();
  expect(container.querySelector('[data-testid="config-text-size"]').value).toBe(expected);
  expect(JSON.parse(localStorage.getItem('feeless-settings')).fontScale).toBe(expected);

  mockPage = 'trade';
  renderCurrentPage(root);
  const app = container.querySelector('.terminal-app');
  expect(app.classList.contains(`text-scale-${expected}`)).toBe(true);
  expect(container.querySelector('[data-testid="swap-amount"]').closest(`.text-scale-${expected}`)).not.toBeNull();
  act(() => root.unmount());
});

test('normalizes every malformed terminal preference and rewrites safe storage values', () => {
  localStorage.setItem('feeless-settings', JSON.stringify({
    compact: 'compact',
    autoRefresh: 'yes',
    reducedMotion: 1,
    fontScale: 'huge',
    chartInterval: '10m',
    defaultEcosystem: 'not-a-context',
  }));
  localStorage.setItem('feeless-default-ecosystem', 'also-not-a-context');

  const { container, root } = mount();

  expect(container.querySelector('[data-testid="config-density"]').value).toBe('comfortable');
  expect(container.querySelector('[data-testid="config-text-size"]').value).toBe('normal');
  expect(container.querySelector('[data-testid="config-chart-interval"]').value).toBe('1h');
  expect(container.querySelector('[data-testid="settings-reduced-motion"]').checked).toBe(false);
  expect(container.querySelector('[data-testid="settings-autorefresh"]').checked).toBe(true);
  expect(container.querySelector('[data-testid="config-default-ecosystem"]').value).toBe('solana');
  expect(container.querySelector('.terminal-app').classList.contains('compact-rows')).toBe(false);
  expect(container.querySelector('.terminal-app').classList.contains('reduced-motion')).toBe(false);

  expect(JSON.parse(localStorage.getItem('feeless-settings'))).toEqual({
    compact: false,
    autoRefresh: true,
    reducedMotion: false,
    fontScale: 'normal',
    chartInterval: '1h',
    defaultEcosystem: 'solana',
  });
  expect(localStorage.getItem('feeless-default-ecosystem')).toBe('solana');
  act(() => root.unmount());
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
  expect(tradeRule('[data-testid="swap-review-dialog"]').style.getPropertyValue('max-height')).toBe('calc(100vh - 24px)');
  expect(tradeRule('[data-testid="swap-review-dialog"] > .btn-primary').style.getPropertyValue('width')).toBe('100%');
  expect(narrowTradeRule('[data-testid="swap-review-dialog"]').style.getPropertyValue('width')).toBe('calc(100% - 20px)');

  act(() => root.unmount());
});

test('all-chain fresh discovery advances through the next bounded provider page window', () => {
  mockPage = 'new';
  mockSearch = new URLSearchParams('chain=all&screen=new');
  mockMarketResult = {
    data: {
      provider: 'GeckoTerminal',
      pairs: Array.from({ length: 21 }, (_, index) => ({
        chainId: 'solana',
        pairAddress: `pool-${index}`,
        pairCreatedAt: Date.now() - 3600000,
        priceChange: { h24: -6 },
        baseToken: { address: `mint-${index}`, symbol: `TOKEN${index}` },
      })),
      provider_pagination: { can_request_next_page: true, pages_requested: [1, 2, 3] },
    },
    loading: false,
    refreshing: false,
    error: undefined,
    reload: jest.fn(),
  };
  const { container, root } = mount();

  expect(mockMarketPaths.filter(path => path === '/feed?kind=new&chain=all&page=1&screen=new')).toHaveLength(2);
  expect(container.querySelector('[data-testid="market-coverage"]').textContent).toContain('Provider pages 1–3 sampled');
  const nextPage = container.querySelector('[data-testid="market-next-page"]');
  expect(nextPage.disabled).toBe(false);
  act(() => nextPage.dispatchEvent(new MouseEvent('click', { bubbles: true })));

  expect(mockMarketPaths.filter(path => path === '/feed?kind=new&chain=all&page=2&screen=new').length).toBeGreaterThanOrEqual(2);
  mockMarketResult = {
    ...mockMarketResult,
    data: {
      ...mockMarketResult.data,
      provider_pagination: { can_request_next_page: false, pages_requested: [4, 5] },
    },
  };
  renderCurrentPage(root);
  expect(container.querySelector('[data-testid="market-next-page"]').disabled).toBe(true);
  act(() => root.unmount());
});
