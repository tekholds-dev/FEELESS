import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeeOwnerBar, feeLook, walletWord } from './FeeOwnerBar';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../../lib/adminCall', () => ({ useAdmin: () => ({ isAdmin: false }) }));
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: null }) }));

test('👑 the creator bar: hidden from users, 🎨 STYLE FEE dresses her (one signed save), 👛 FEE\'S WALLET opens her real switch', async () => {
  expect(feeLook({ name: 'FeeCat', look: { gear: 'crown' } })).toMatchObject({ coat: 'black', gear: 'crown', name: 'FeeCat', aura: 'royal' });
  expect(walletWord({ mode: 'real', realWallet: 'W', proposals: [{ status: 'pending', until: 9e12, at: 1 }] })).toBe('REAL · 1 to sign');
  expect(walletWord({})).toBe('PAPER · go real');
  const cat = { id: 'leader', name: 'FeeCat', isLeader: true, look: { coat: 'black' } };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FeeOwnerBar cat={cat} />); });
  expect(el.querySelector('[data-testid="fee-owner-bar"]')).toBeNull();                        // a user never sees it
  const posted = [];
  global.fetch = jest.fn((u, o) => { if (!o?.body) return Promise.resolve({ ok: true, json: () => Promise.resolve({ amount: 1.25, decimals: 9 }) });   // the wallet card's live SOL balance
    posted.push([u, JSON.parse(o.body)]); return Promise.resolve({ ok: true, json: () => Promise.resolve({ cat: { ...cat, look: JSON.parse(o.body).look } }) }); });
  await act(async () => { root.render(<FeeOwnerBar cat={cat} devOwner devAddress="OWNERW" />); });
  expect(el.querySelector('[data-testid="fob-wallet"]').textContent).toContain('PAPER · go real');
  await act(async () => { el.querySelector('[data-testid="fob-style"]').click(); });
  await act(async () => { document.querySelector('[data-testid="fob-gear-crown"]').click(); });
  await act(async () => { document.querySelector('[data-testid="fob-coat-gold"]').click(); });
  expect(document.querySelector('[data-testid="fob-gear-crown"]').getAttribute('aria-checked')).toBe('true');
  await act(async () => { document.querySelector('[data-testid="fob-save"]').click(); });
  expect(posted[0][0]).toBe('/api/cats/leader/action');
  expect(posted[0][1]).toMatchObject({ action: 'look', address: 'OWNERW', session: 'dev', look: { coat: 'gold', gear: 'crown', name: 'FeeCat' } });
  expect(document.querySelector('[data-testid="fob-msg"]').textContent).toContain('wears it now');
  await act(async () => { document.querySelector('.fob-x').click(); });
  await act(async () => { el.querySelector('[data-testid="fob-wallet"]').click(); });
  expect(document.querySelector('[data-testid="fob-pop-wallet"] [data-testid="cat-real"]')).not.toBeNull();
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const wc = document.querySelector('[data-testid="fob-pop-wallet"] [data-testid="cr-wallet"]');   // 👛 her wallet: address + copy + live balance + vitals
  expect(wc).not.toBeNull(); expect(wc.textContent).toContain('1.2500 SOL'); expect(wc.querySelector('[data-testid="cr-copy"]')).not.toBeNull();
  act(() => root.unmount()); document.body.innerHTML = ''; delete global.fetch;
});
