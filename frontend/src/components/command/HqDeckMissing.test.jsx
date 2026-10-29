import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

// 🗂 H01 "missing-data handling": every HQ tab mounts on an EMPTY server (every read answers {}) — the state a tab shows before its first
// read lands, after a 500, or on a fresh install. No tab may crash, and none may print NaN / undefined / [object Object] / Infinity.
// The same stub drives the browser harness (`/dev/hq?deck=<tab>`, src/dev/HqHarness.jsx).
jest.mock('react-router-dom', () => ({ Link: ({ children, ...p }) => <a {...p}>{children}</a>, useNavigate: () => jest.fn(), useLocation: () => ({ pathname: '/', search: '' }) }), { virtual: true });
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'HQdev1111111111111111111111111111111111111' }, provider: {}, connect: jest.fn(), signMessage: jest.fn() }) }));
jest.mock('sonner', () => ({ toast: Object.assign(jest.fn(), { success: jest.fn(), error: jest.fn(), info: jest.fn(), message: jest.fn(), warning: jest.fn(), loading: jest.fn(), dismiss: jest.fn() }) }));

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const FAKE = 'HQdev1111111111111111111111111111111111111';
const TABS = ['agents', 'money', 'fees', 'latency', 'launch', 'fuse', 'familia', 'feecat', 'pools', 'verify', 'numbers', 'traffic', 'pulse', 'marketing', 'kols', 'ads', 'ideas',
  'holders', 'studio', 'airdrops', 'snapshots', 'invites', 'broadcast', 'badges', 'nfts', 'seasons', 'investigate', 'shield', 'overview', 'mod', 'access', 'bugs'];

beforeAll(() => {
  global.fetch = async (u, o = {}) => {   // a plain function: CRA resetMocks would wipe a jest.fn between tests
    const url = String(u);
    const body = /is-admin/.test(url) ? { owner: true } : /\/admin\/roles/.test(url) ? { yourRole: 'owner' } : (o.method && o.method !== 'GET') ? { ok: true } : {};
    return { ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body) };
  };
  global.EventSource = class { close() {} addEventListener() {} };
  global.IntersectionObserver = class { observe() {} disconnect() {} unobserve() {} };
  global.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} };
  window.matchMedia = window.matchMedia || (() => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }));
});

test.each(TABS)('HQ › %s survives an empty server', async tab => {
  localStorage.setItem('feeless:cc-session', JSON.stringify({ address: FAKE, ts: Math.floor(Date.now() / 1000), sig: 'dev' }));
  localStorage.setItem('feeless.hq.tab', JSON.stringify(tab));
  const { HqDeck } = require('./HqDeck');
  const errs = []; const spy = jest.spyOn(console, 'error').mockImplementation((...a) => errs.push(a.map(String).join(' ')));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const crash = [];
  const run = async f => { try { await act(f); } catch (e) { (e.errors || [e]).forEach(x => crash.push(String(x?.stack || x).split('\n').slice(0, 3).join(' | '))); } };
  await run(async () => { root.render(<HqDeck address={FAKE} signMessage={async () => 'dev'} onClose={() => {}} startTab={tab} />); });
  await run(async () => { await new Promise(r => setTimeout(r, 30)); });
  const text = el.textContent;
  act(() => root.unmount()); el.remove(); spy.mockRestore();
  expect(crash).toEqual([]);
  expect(errs.filter(e => /TypeError|ReferenceError|Cannot read|is not a function|is not iterable/.test(e))).toEqual([]);
  expect(text).toContain('HQ');
  expect([...text.matchAll(/NaN|undefined|\[object Object\]|Infinity/g)].map(m => text.slice(Math.max(0, m.index - 40), m.index + 20))).toEqual([]);   // shows WHERE
});

test('TabGuard: a tab that throws shows its name, the error and a Retry — the rest of HQ keeps rendering', async () => {
  const { TabGuard } = require('./HqDeck');
  let boom = true; const Bad = () => { if (boom) throw new Error('rows is undefined'); return <p>fine now</p>; };
  const spy = jest.spyOn(console, 'error').mockImplementation(() => {}); const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<div><nav>HQ nav</nav><TabGuard tab="Numbers"><Bad /></TabGuard></div>); });
  expect(el.textContent).toContain('HQ nav'); expect(el.querySelector('[data-testid="hq-tab-crash"]').textContent).toContain('Numbers');
  expect(el.textContent).toContain('rows is undefined');
  boom = false; await act(async () => { el.querySelector('[data-testid="hq-tab-crash"] button').click(); });
  expect(el.textContent).toContain('fine now');
  act(() => root.unmount()); spy.mockRestore(); warn.mockRestore();
});
