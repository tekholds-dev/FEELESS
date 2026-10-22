import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import HqLink, { pairLink } from './HqLink';
import { pairedAddress, SESSION_KEY, PAIRED_KEY } from '../lib/hqPaired';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
if (!global.TextEncoder) global.TextEncoder = require('util').TextEncoder;   // jsdom has none
jest.mock('qrcode', () => ({ toString: async () => '<svg data-qr="1"></svg>' }));   // a plain fn: CRA resets jest.fn mocks before each test
const settle = async (n = 6) => { for (let i = 0; i < n; i += 1) await act(async () => { await Promise.resolve(); }); };
const mount = async () => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<HqLink />); }); return el; };

test('the QR opens the page inside Phantom, on this computer\'s Wi-Fi address', () => {
  expect(pairLink('10.0.0.5', '51367', 'abc')).toBe(`https://phantom.app/ul/browse/${encodeURIComponent('http://10.0.0.5:51367/hq-link?c=abc')}?ref=${encodeURIComponent('http://10.0.0.5:51367')}`);
});

test('computer: shows the QR, then keeps the signed session and unlocks HQ for that wallet', async () => {
  jest.useFakeTimers({ doNotFake: ['nextTick', 'setImmediate'] });
  window.history.replaceState(null, '', '/hq-link');
  let polls = 0;
  global.fetch = jest.fn(async (url, o) => ({ ok: true, json: async () => (o?.method === 'POST' ? { code: 'C1', ttl: 180, lan: '10.0.0.5' }
    : (polls += 1) < 2 ? { status: 'waiting' } : { status: 'signed', session: { address: 'OWNERxyz', ts: Math.floor(Date.now() / 1000), sig: 'S' } }) }));
  const el = await mount(); await settle();
  expect(el.querySelector('[data-qr]')).not.toBeNull();
  await act(async () => { jest.advanceTimersByTime(2050); }); await settle(); await act(async () => { jest.advanceTimersByTime(2050); }); await settle();
  expect(el.querySelector('[data-testid="hq-link-done"]').textContent).toContain('OWNE');
  expect(JSON.parse(localStorage.getItem(SESSION_KEY)).address).toBe('OWNERxyz'); expect(pairedAddress()).toBe('OWNERxyz');
  localStorage.removeItem(PAIRED_KEY); expect(pairedAddress()).toBeNull();               // only a phone-paired session counts as paired
  jest.useRealTimers();
});

test('phone: signs the HQ message (never a transaction) and posts it under the code', async () => {
  window.history.replaceState(null, '', '/hq-link?c=C9');
  const signMessage = jest.fn(async () => ({ signature: new Uint8Array([1, 2, 3]) }));
  window.phantom = { solana: { connect: async () => ({ publicKey: { toString: () => 'OWNERxyz' } }), signMessage } };
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ ok: true }) }));
  const el = await mount();
  await act(async () => { el.querySelector('[data-testid="hq-link-sign"]').click(); }); await settle();
  expect(Buffer.from(signMessage.mock.calls[0][0]).toString('utf8')).toMatch(/^FEELESS HQ\naddress:OWNERxyz\nts:\d+$/);
  const [url, opt] = global.fetch.mock.calls[0]; expect(url).toContain('/api/reputation/hq/pair/C9');
  expect(JSON.parse(opt.body)).toMatchObject({ address: 'OWNERxyz', sig: btoa(String.fromCharCode(1, 2, 3)) });
  expect(el.textContent).toContain('look at your computer');
});
