import { LEGAL_NEEDED, LEGAL_VERSION, assertLegal, forgetLegal, legalOk, markAccepted } from './legal';

jest.mock('./chatSession', () => ({ readChatSession: a => (a === 'SIGNED' ? 'sess-1' : null) }));

const gates = (over = {}) => Object.fromEntries(['site', 'swap', 'perps', 'agents', 'launch', 'games', 'brokers'].map(f => [f, over[f] || { ok: true, why: '' }]));
const answer = body => { global.fetch = jest.fn(async () => ({ ok: true, json: async () => body })); };
beforeEach(() => { forgetLegal(); localStorage.clear(); });

test('⚖ an accepted wallet passes; every caller shares ONE status read for 60 s; its own session rides along so its stated country counts', async () => {
  answer({ version: LEGAL_VERSION, accepted: true, gates: gates() });
  expect(await legalOk('swap', 'SIGNED')).toEqual({ ok: true, why: '' });
  expect(await legalOk('perps', 'SIGNED')).toEqual({ ok: true, why: '' });
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][0]).toContain('/api/reputation/legal/status?wallet=SIGNED');
  expect(fetch.mock.calls[0][1].headers['x-feeless-session']).toBe('sess-1');
  await expect(assertLegal('swap', 'SIGNED')).resolves.toBe(true);
});

test('⚖ a wallet that never accepted is held before the wallet opens, and the accept window is asked to open', async () => {
  answer({ accepted: false, gates: gates({ swap: { ok: false, why: "Confirm you're 18+ and accept the terms first." } }) });
  const seen = []; const on = e => seen.push(e.detail.feature); window.addEventListener(LEGAL_NEEDED, on);
  await expect(assertLegal('swap', 'W')).rejects.toThrow("Confirm you're 18+");
  window.removeEventListener(LEGAL_NEEDED, on);
  expect(seen).toEqual(['swap']);
});

test('⚖ a closed country refuses with the server\'s words and does NOT reopen the accept window (accepting again would not help)', async () => {
  answer({ accepted: true, gates: gates({ perps: { ok: false, why: 'Perps + leverage (Jupiter Perps / Lend) are closed in GB.' } }) });
  const seen = []; const on = () => seen.push(1); window.addEventListener(LEGAL_NEEDED, on);
  await expect(assertLegal('perps', 'W')).rejects.toThrow('closed in GB');
  window.removeEventListener(LEGAL_NEEDED, on);
  expect(seen).toEqual([]);
  await expect(assertLegal('swap', 'W')).resolves.toBe(true);   // other features stay open
});

test('⚖ server down: fail-open ONLY for a wallet this browser saw accept this version; never for a new wallet; an unknown feature is refused', async () => {
  global.fetch = jest.fn(async () => { throw new Error('offline'); });
  const r = await legalOk('swap', 'NEW');
  expect(r.ok).toBe(false); expect(r.offline).toBe(true);
  markAccepted('OLD');
  expect((await legalOk('swap', 'OLD')).ok).toBe(true);
  global.fetch = jest.fn(async () => ({ ok: false, status: 502, json: async () => ({}) }));
  forgetLegal();
  expect((await legalOk('swap', 'NEW2')).ok).toBe(false);
  expect((await legalOk('custody', 'OLD')).ok).toBe(false);
});

test('⚖ accepting drops the cached answer so the very next trade sees it', async () => {
  answer({ accepted: false, gates: gates({ swap: { ok: false, why: 'accept first' } }) });
  expect((await legalOk('swap', 'W')).ok).toBe(false);
  answer({ accepted: true, gates: gates() });
  expect((await legalOk('swap', 'W')).ok).toBe(false);   // still the cached 60 s answer
  markAccepted('W');
  expect((await legalOk('swap', 'W')).ok).toBe(true);
});

test('⚖ a HUNG status call is cut after 8 s and counts as offline — a trade never sits on "signing" forever (accepted-here wallet goes on, a new one is held)', async () => {
  jest.useFakeTimers();
  global.fetch = jest.fn((url, opts) => new Promise((_, rej) => opts.signal.addEventListener('abort', () => rej(new Error('aborted')))));
  markAccepted('OLD');
  const a = legalOk('swap', 'OLD'); const b = legalOk('swap', 'NEW');
  jest.advanceTimersByTime(8001);
  expect(await a).toEqual({ ok: true, why: '', offline: true });
  expect((await b).ok).toBe(false);
  jest.useRealTimers();
});

test('⚖ Kalshi / lend / bridge / proof-send sign through the gate too (perps.signTx takes the feature; lendSign is perps)', () => {
  const fs = require('fs'); const path = require('path'); const read = f => fs.readFileSync(path.join(__dirname, f), 'utf8');
  expect(read('perps.js')).toMatch(/signTx\(provider, address, b64, feature = 'perps'\) \{\n\s+await assertLegal\(feature, address\)/);
  expect(read('lendEarn.js')).toMatch(/lendSign\([^)]*\) \{\n\s+await assertLegal\('perps', address\)/);
  expect(read('bridgeExec.js')).toMatch(/await assertLegal\('swap', address\);[^\n]*\n[^\n]*\n\s+const signed = await provider\.signTransaction\(tx\)/);
  expect(read('../components/perps/KalshiDesk.jsx')).toContain("signTx(provider, addr, b.transaction, 'games')");
  expect(read('../components/command/ProofKit.jsx')).toMatch(/await assertLegal\('agents'/);
});
