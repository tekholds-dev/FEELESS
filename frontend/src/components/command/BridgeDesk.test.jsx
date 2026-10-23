import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { error: () => {}, success: () => {}, info: () => {} } }));
const EVM = '0xAbC0000000000000000000000000000000000001';
const mockPeek = jest.fn();
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'SOLME' }, peekAddress: mockPeek, switchTo: async () => ({}) }) }));
const QUOTE = { feeless: { safety: { verified: true } }, transactionRequest: { data: 'AQID' }, tool: 'relaydepository', toolDetails: { name: 'Relay' },
  action: { fromChainId: 1151111081099710, toChainId: 8453, fromAddress: 'SOLME', toAddress: EVM, fromAmount: '10000000', fromToken: { symbol: 'USDC', decimals: 6 }, toToken: { symbol: 'USDC', decimals: 6 } },
  estimate: { toAmount: '9950000', fromAmountUSD: '10', toAmountUSD: '9.95', executionDuration: 3, feeCosts: [{ amountUSD: '0.03' }], gasCosts: [{ amountUSD: '0.02' }] } };
const { BridgeDesk, StepRail, stepOf } = require('./BridgeDesk');
const { GetGas } = require('./TradeDesk');
const urls = [];
const flush = async () => { for (let i = 0; i < 6; i++) await act(async () => { await Promise.resolve(); }); };
async function mount(node) {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(node); }); await flush();
  const q = id => el.querySelector(`[data-testid="${id}"]`); const all = re => [...el.querySelectorAll('[data-testid]')].filter(x => re.test(x.dataset.testid));
  return { el, root, q, all, click: async n => { await act(async () => { n.click(); }); await flush(); } };
}
beforeEach(() => {
  urls.length = 0;
  mockPeek.mockImplementation(async t => (t === 'solana' ? 'SOLME' : EVM));
  global.fetch = jest.fn(async url => { urls.push(String(url));
    const body = /lifi\/quote/.test(url) ? QUOTE : /lifi\/token/.test(url) ? { priceUSD: '150' }
      : /reputation\/gas/.test(url) ? { chains: [{ chain: 'arbitrum', symbol: 'ETH', balance: 0, usd: 0, enough: false, minUsd: 0.25 }, { chain: 'base', symbol: 'ETH', balance: 0.01, usd: 30, enough: true, minUsd: 0.25 }],
        solana: { chain: 'solana', symbol: 'SOL', address: 'SOLME', balance: 2, usd: 300 } } : {};
    return { ok: true, json: async () => body }; });
});

test('every chain the bridge lists is drawn as a chip on both rails — Solana first, Zora gone; picking the other side flips', async () => {
  const { q, all, el, click } = await mount(<BridgeDesk />);
  expect(all(/^br-from-/)).toHaveLength(12); expect(all(/^br-to-/)).toHaveLength(12); expect(q('br-from-zora')).toBeNull();
  expect(q('br-from-solana').getAttribute('aria-checked')).toBe('true');
  await click(q('br-to-solana'));     // Solana → Solana flips the route
  expect(q('br-from-base').getAttribute('aria-checked')).toBe('true'); expect(q('br-to-solana').getAttribute('aria-checked')).toBe('true');
  expect(el.textContent).toContain('0xAb…0001');
});

test('Get quote asks FEELESS for Solana → Base paying YOUR EVM wallet, and the vitals light up', async () => {
  const { q, click } = await mount(<BridgeDesk />);
  await click(q('br-quote'));
  expect(q('br-sign')).not.toBeNull();
  const u = urls.find(x => /lifi\/quote/.test(x));
  expect(u).toMatch(/fromChain=1151111081099710/); expect(u).toMatch(/toChain=8453/); expect(u).toMatch(/fromToken=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v/);
  expect(u).toMatch(/fromAmount=10000000\b/); expect(u).toMatch(new RegExp(`toAddress=${EVM}`)); expect(u).toMatch(/fromAddress=SOLME/);
  expect(q('br-vitals').textContent).toContain('You get9.950 USDC'); expect(q('br-scene').textContent).toContain('via Relay');
});

test('the step rail: done steps before, the live one pulsing, a failure marked', async () => {
  const a = await mount(<StepRail step={stepOf('bridge')} />);
  expect([...a.el.querySelectorAll('li')].map(li => li.className)).toEqual(['done', 'done', 'done', 'done', 'now', '']);
  const b = await mount(<StepRail step={stepOf('sign')} failed />);
  expect(b.el.querySelectorAll('li')[2].className).toBe('fail');
  const c = await mount(<StepRail step={stepOf('landed')} />);
  expect(c.el.querySelectorAll('li.done')).toHaveLength(6);
});

test('⛽ the station fills a dry tank FROM SOL, paying out to your own EVM wallet', async () => {
  const { q, el, click } = await mount(<GetGas />);
  expect(q('gas-arbitrum')).not.toBeNull();
  expect(urls.find(x => /reputation\/gas/.test(x))).toMatch(new RegExp(`gas/${EVM}\\?sol=SOLME`));
  await click(q('gas-arbitrum'));
  const pay = [...el.querySelectorAll('.gs-pay [role="radio"]')];
  expect(pay[0].textContent).toContain('SOL $300'); expect(pay[0].getAttribute('aria-checked')).toBe('true');
  await click(q('gas-quote'));
  const u = urls.find(x => /lifi\/quote/.test(x));
  expect(u).toMatch(/fromChain=1151111081099710/); expect(u).toMatch(/toChain=42161/); expect(u).toMatch(/fromToken=11111111111111111111111111111111/);
  expect(u).toMatch(/fromAmount=13333333\b/); expect(u).toMatch(new RegExp(`toAddress=${EVM}`));   // $2 at $150 / SOL
});
