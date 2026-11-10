import { webcrypto } from 'crypto';
import { TextEncoder } from 'util';
import { pkcePair, authUrl, finishOpenRouterConnect, takeConnectResult } from './openrouterConnect';

beforeAll(() => { if (!globalThis.crypto?.subtle) Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true }); if (!globalThis.TextEncoder) globalThis.TextEncoder = TextEncoder; });
beforeEach(() => sessionStorage.clear());

const loc = search => ({ search, href: `http://localhost:51367/terminal/feecat/agents${search}` });

test('a fresh one-time pair: the challenge is the SHA-256 of the verifier, url-safe', async () => {
  const a = await pkcePair(); const b = await pkcePair();
  expect(a.verifier).toMatch(/^[A-Za-z0-9_-]{43}$/); expect(a.verifier).not.toBe(b.verifier);
  const want = Buffer.from(await webcrypto.subtle.digest('SHA-256', new TextEncoder().encode(a.verifier))).toString('base64url');
  expect(a.challenge).toBe(want);
  expect(authUrl(a.challenge, 'http://localhost:51367/x')).toBe(`https://openrouter.ai/auth?callback_url=${encodeURIComponent('http://localhost:51367/x')}&code_challenge=${a.challenge}&code_challenge_method=S256`);
});

test('back from OpenRouter: the code and this tab\'s verifier go to the server once, and the code leaves the address bar', async () => {
  sessionStorage.setItem('feeless.orConnect', JSON.stringify({ verifier: 'v'.repeat(43), cat: 'c1', at: 1000 }));
  const sent = []; globalThis.fetch = jest.fn(async (url, o) => { sent.push([url, JSON.parse(o.body)]); return { ok: true, json: async () => ({ cat: { apiDrawer: [{ provider: 'openrouter', saved: true, last4: 'ab12' }] } }) }; });
  const hist = { replaceState: jest.fn() };
  const out = await finishOpenRouterConnect(loc('?code=THE_CODE&tab=1'), hist, 2000);
  expect(out).toEqual({ ok: true, cat: 'c1', last4: 'ab12' });
  expect(sent[0][0]).toContain('/api/cats/c1/action'); expect(sent[0][1]).toMatchObject({ action: 'openrouter_connect', secret: 'THE_CODE', text: 'v'.repeat(43) });
  expect(hist.replaceState).toHaveBeenCalledWith(null, '', '/terminal/feecat/agents?tab=1');
  expect(takeConnectResult('c1')).toEqual(out); expect(takeConnectResult('c1')).toBeNull();   // shown once
  expect(await finishOpenRouterConnect(loc('?code=THE_CODE'), hist, 3000)).toBeNull(); expect(sent).toHaveLength(1);   // the verifier is gone: a replayed code does nothing
});

test('a code with no verifier, or a stale approval, never calls the server', async () => {
  globalThis.fetch = jest.fn(); const hist = { replaceState: jest.fn() };
  expect(await finishOpenRouterConnect(loc('?code=X'), hist, 1)).toBeNull();
  sessionStorage.setItem('feeless.orConnect', JSON.stringify({ verifier: 'v'.repeat(43), cat: 'c1', at: 0 }));
  const out = await finishOpenRouterConnect(loc('?code=X'), hist, 16 * 60 * 1000);
  expect(out.ok).toBe(false); expect(out.why).toContain('too long'); expect(globalThis.fetch).not.toHaveBeenCalled();
});

test('a refused approval says why', async () => {
  sessionStorage.setItem('feeless.orConnect', JSON.stringify({ verifier: 'v'.repeat(43), cat: 'c1', at: 1 }));
  globalThis.fetch = jest.fn(async () => ({ ok: false, status: 400, json: async () => ({ detail: 'OpenRouter did not accept that approval' }) }));
  const out = await finishOpenRouterConnect(loc('?code=X'), { replaceState: () => {} }, 2);
  expect(out).toEqual({ ok: false, cat: 'c1', why: 'OpenRouter did not accept that approval' });
});
