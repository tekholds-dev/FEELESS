import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LegalConsent, LegalPage, MyDataCard, renderLegalMd } from './LegalConsent';
import { LEGAL_NEEDED, LEGAL_VERSION, acceptedHere, forgetLegal } from '../lib/legal';

let mockWallet = null;
jest.mock('react-router-dom', () => ({ Link: ({ to, children, ...p }) => <a href={to} {...p}>{children}</a> }), { virtual: true });
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: mockWallet, signMessage: async () => 'sig' }) }));
const mockSessCalls = [];
jest.mock('../lib/chatSession', () => ({ readChatSession: () => 'sess', getChatSession: async (...a) => { mockSessCalls.push(a); return 'sess'; }, clearAllChatSessions: () => Object.keys(localStorage).filter(k => k.startsWith('feeless:chat-session:')).forEach(k => localStorage.removeItem(k)) }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const W = 'So1anaWa11etAddre55xxxxxxxxxxxxxxxxxxxx';
const gates = ok => Object.fromEntries(['site', 'swap', 'perps', 'agents', 'launch', 'games', 'brokers'].map(f => [f, { ok, why: ok ? '' : 'accept first' }]));
let posts = [];
function server({ accepted = false, country = null, acceptStatus = 200 } = {}) {
  posts = [];
  global.fetch = jest.fn(async (url, opts = {}) => {
    if (String(url).includes('/legal/status')) return { ok: true, json: async () => ({ version: LEGAL_VERSION, accepted, country, stated: null, minAge: 18, sanctioned: ['CU', 'IR', 'KP', 'SY'], gates: gates(accepted) }) };
    if (String(url).includes('/legal/accept')) { posts.push(JSON.parse(opts.body)); return { ok: acceptStatus === 200, status: acceptStatus, json: async () => (acceptStatus === 200 ? { ok: true } : { detail: 'FEELESS is not available in IR.' }) }; }
    if (String(url).endsWith('.md')) return { ok: true, text: async () => '# FEELESS Terms of Use — DRAFT v0.1 (x)\n\n1. **Who we are.** Run by [ENTITY], [STATE].\n2. **Risk.** You can lose it all.\n' };
    if (String(url).includes('/legal/export')) { posts.push(JSON.parse(opts.body)); return { ok: true, json: async () => ({ data: { profile: {}, chat: [] } }) }; }
    if (String(url).includes('/legal/delete')) { posts.push(JSON.parse(opts.body)); return { ok: true, json: async () => ({ ok: true, removed: { profile: 1, chat: 3 } }) }; }
    return { ok: false, json: async () => ({}) };
  });
}
async function mount(el) {
  const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box);
  await act(async () => root.render(el));
  for (let i = 0; i < 4; i++) await act(async () => { await Promise.resolve(); });
  return { box, root, q: s => box.querySelector(`[data-testid="${s}"]`) };
}
const pick = async (node, value) => act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set; set.call(node, value); node.dispatchEvent(new Event('change', { bubbles: true })); });
const tick = async node => act(async () => node.click());
beforeEach(() => { forgetLegal(); localStorage.clear(); mockWallet = null; });

test('⚖ a visitor with no wallet only gets the short notice (no modal), and Got it closes it', async () => {
  mockWallet = null; server();
  const b = await mount(<LegalConsent />);
  expect(b.q('legal-consent')).not.toBeNull(); expect(b.q('legal-modal')).toBeNull();
  await tick(b.q('legal-accept')); expect(b.q('legal-consent')).toBeNull();
  await act(async () => b.root.unmount());
});

test('⚖ a connected wallet that never accepted gets the window; Accept stays off until country + 18+ + not-restricted; sanctioned places can\'t be picked; it saves the three answers with this version', async () => {
  server({ country: 'DE' }); mockWallet = { chain: 'solana', address: W };
  const { q, box, root } = await mount(<LegalConsent />);
  expect(q('legal-modal')).not.toBeNull(); expect(q('legal-consent')).toBeNull();
  expect(q('legal-country').value).toBe('DE');   // the CDN's country is pre-picked
  expect(box.querySelector('option[value="IR"]').disabled).toBe(true);
  expect(q('legal-submit').disabled).toBe(true);
  await tick(q('legal-adult')); expect(q('legal-submit').disabled).toBe(true);
  await tick(q('legal-clear')); expect(q('legal-submit').disabled).toBe(false);
  await pick(q('legal-country'), 'US');
  await act(async () => q('legal-submit').closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  for (let i = 0; i < 4; i++) await act(async () => { await Promise.resolve(); });
  expect(posts).toEqual([{ wallet: W, session: 'sess', version: LEGAL_VERSION, country: 'US', adult: true, notRestricted: true }]);
  expect(q('legal-modal')).toBeNull(); expect(acceptedHere(W)).toBe(true);
  await act(async () => root.unmount());
});

test('⚖ the server\'s refusal shows in the window and nothing is marked accepted', async () => {
  server({ acceptStatus: 400 }); mockWallet = { chain: 'solana', address: W };
  const { q, root } = await mount(<LegalConsent />);
  await pick(q('legal-country'), 'FR'); await tick(q('legal-adult')); await tick(q('legal-clear'));
  await act(async () => q('legal-submit').closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  for (let i = 0; i < 4; i++) await act(async () => { await Promise.resolve(); });
  expect(q('legal-err').textContent).toContain('not available in IR'); expect(acceptedHere(W)).toBe(false);
  await act(async () => root.unmount());
});

test('⚖ an accepted wallet sees nothing; a held signing point reopens the window', async () => {
  server({ accepted: true }); mockWallet = { chain: 'solana', address: W };
  const a = await mount(<LegalConsent />);
  expect(a.q('legal-modal')).toBeNull(); expect(a.q('legal-consent')).toBeNull();
  await act(async () => window.dispatchEvent(new CustomEvent(LEGAL_NEEDED, { detail: { feature: 'perps' } })));
  expect(a.q('legal-modal').textContent).toContain('trade perps');
  await tick(a.q('legal-later')); expect(a.q('legal-modal')).toBeNull();
  await act(async () => a.root.unmount());
});

test('📜 the three pages render the ONE markdown copy; [BLANKS] are marked, the DRAFT tag leaves the heading', async () => {
  const out = renderLegalMd('# Terms — DRAFT v0.1\n\n1. **A.** [ENTITY] runs it.\n- **B:** two');
  expect(out).toHaveLength(3);
  server();
  const { q, box, root } = await mount(<LegalPage doc="terms" />);
  expect(fetch).toHaveBeenCalledWith('/legal/terms.md');
  expect(q('legal-doc-terms').querySelector('h1').textContent).toBe('FEELESS Terms of Use');
  expect([...box.querySelectorAll('.lgl-blank')].map(m => m.textContent)).toEqual(['ENTITY', 'STATE']);
  expect(q('legal-tab-terms').getAttribute('aria-current')).toBe('page'); expect(q('legal-tab-risk').getAttribute('href')).toBe('/terminal/risk');
  await act(async () => root.unmount());
});

test('👤 Your data: Download sends the signed session; Delete only after typing DELETE, asks for a fresh sign-in, shows what went and signs you out', async () => {
  server(); mockWallet = { chain: 'solana', address: W };
  global.URL.createObjectURL = () => 'blob:x'; global.URL.revokeObjectURL = () => {}; HTMLAnchorElement.prototype.click = () => {};
  const { q, root } = await mount(<MyDataCard />);
  await tick(q('data-export')); for (let i = 0; i < 4; i++) await act(async () => { await Promise.resolve(); });
  expect(posts[0]).toEqual({ wallet: W, session: 'sess' }); expect(q('data-msg').textContent).toContain('2 kinds');
  expect(q('data-delete').disabled).toBe(true);
  const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(q('data-confirm'), 'DELETE'); q('data-confirm').dispatchEvent(new Event('input', { bubbles: true })); });
  expect(q('data-delete').disabled).toBe(false);
  localStorage.setItem(`feeless:chat-session:${W}`, '{}');
  await tick(q('data-delete')); for (let i = 0; i < 4; i++) await act(async () => { await Promise.resolve(); });
  expect(mockSessCalls[mockSessCalls.length - 1][2]).toEqual({ own: true, fresh: true });
  expect(posts[1]).toEqual({ wallet: W, session: 'sess', confirm: 'DELETE' });
  expect(q('data-gone').textContent).toContain('signed out'); expect(localStorage.getItem(`feeless:chat-session:${W}`)).toBeNull();
  await act(async () => root.unmount());
});
