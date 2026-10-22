import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import HqLink from './HqLink';
import { pairedAddress, SESSION_KEY, PAIRED_KEY } from '../lib/hqPaired';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
if (!global.TextEncoder) global.TextEncoder = require('util').TextEncoder;   // jsdom has none
jest.mock('qrcode', () => ({ toString: async () => '<svg data-qr="1"></svg>' }));   // a plain fn: CRA resets jest.fn mocks before each test
const settle = async (n = 6) => { for (let i = 0; i < n; i += 1) await act(async () => { await Promise.resolve(); }); };
const mount = async () => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<HqLink />); }); return el; };

test('computer: shows the QR, then keeps the signed session and unlocks HQ for that wallet', async () => {
  jest.useFakeTimers({ doNotFake: ['nextTick', 'setImmediate'] });
  window.history.replaceState(null, '', '/hq-link');
  let polls = 0;
  global.fetch = jest.fn(async (url, o) => ({ ok: true, json: async () => (o?.method === 'POST' ? { code: 'C1', ttl: 180, lan: '10.0.0.5', link: 'https://phantom.app/ul/v1/connect?x=1' }
    : (polls += 1) < 2 ? { status: 'waiting' } : { status: 'signed', session: { address: 'OWNERxyz', ts: Math.floor(Date.now() / 1000), sig: 'S' } }) }));
  const el = await mount(); await settle();
  expect(el.querySelector('[data-qr]')).not.toBeNull();
  await act(async () => { jest.advanceTimersByTime(2050); }); await settle(); await act(async () => { jest.advanceTimersByTime(2050); }); await settle();
  expect(el.querySelector('[data-testid="hq-link-done"]').textContent).toContain('OWNE');
  expect(JSON.parse(localStorage.getItem(SESSION_KEY)).address).toBe('OWNERxyz'); expect(pairedAddress()).toBe('OWNERxyz');
  localStorage.removeItem(PAIRED_KEY); expect(pairedAddress()).toBeNull();               // only a phone-paired session counts as paired
  jest.useRealTimers();
});

test('phone: relays Phantom\'s connect answer → opens the sign deeplink; the sign answer → done; a "no" shows why', async () => {
  window.history.replaceState(null, '', '/hq-link?c=C9&s=connect&phantom_encryption_public_key=PK&nonce=N1&data=D1');
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ link: 'https://phantom.app/ul/v1/signMessage?x=1' }) }));
  delete window.location; window.location = { search: '?c=C9&s=connect&phantom_encryption_public_key=PK&nonce=N1&data=D1', href: '', port: '51367' };
  await mount(); await settle();
  const [url, opt] = global.fetch.mock.calls[0]; expect(url).toContain('/api/reputation/hq/pair/C9/connect');
  expect(JSON.parse(opt.body)).toEqual({ nonce: 'N1', data: 'D1', pub: 'PK', port: 51367 });
  expect(window.location.href).toBe('https://phantom.app/ul/v1/signMessage?x=1');
  window.location = { search: '?c=C9&s=sign&nonce=N2&data=D2', href: '', port: '51367' }; global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ ok: true }) }));
  const el = await mount(); await settle();
  expect(global.fetch.mock.calls[0][0]).toContain('/hq/pair/C9/signed'); expect(el.querySelector('[data-testid="hq-link-ok"]')).not.toBeNull();
  window.location = { search: '?c=C9&s=sign&errorCode=4001&errorMessage=User%20rejected', href: '', port: '51367' };
  const no = await mount(); await settle();
  expect(no.querySelector('[data-testid="hq-link-err"]').textContent).toContain('User rejected');
});
