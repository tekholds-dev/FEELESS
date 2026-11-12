import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FREE_LOOKS, applyLook, lookMap } from '../lib/looks';
import { remapText } from './HolderTheme';
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: null }) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('🎨 a look maps Plasma\'s own colours to its own, alpha kept; price-up colours are not touched', () => {
  const m = lookMap(FREE_LOOKS.molten.tokens);
  const out = remapText('.a{color:#9b6bff;background:#08061a55;border:1px solid rgba(155, 107, 255, .4)}.up{color:#3ee58a}', m);
  expect(out).toBe('.a{color:#ffb020;background:#0b070455;border:1px solid rgba(255, 176, 32, .4)}.up{color:#3ee58a}');
});

test('🎨 wearing a look sets the meta tokens and the ambient on <html>; Plasma puts the site back', () => {
  applyLook(FREE_LOOKS.neon); const r = document.documentElement;
  expect(r.dataset.look).toBe('neon'); expect(r.style.getPropertyValue('--m-accent')).toBe('#00f0ff'); expect(r.style.getPropertyValue('--ink')).toBe('#02060b');
  applyLook(FREE_LOOKS.plasma);
  expect(r.dataset.look).toBeUndefined(); expect(r.style.getPropertyValue('--m-accent')).toBe('');
});

test('🎨 the picker shows free looks to wear and advanced ones locked with what unlocks them; a tap previews, save keeps it on this device', async () => {
  const looks = [...Object.values(FREE_LOOKS).map(l => ({ id: l.id, name: l.name, tier: 'free', line: 'x', ambient: l.ambient, swatch: ['#111111', '#222222', '#333333', '#000000'], tokens: l.tokens, locked: false })),
    { id: 'aurora', name: 'Aurora', tier: 'holder', line: 'y', ambient: 'aurora', swatch: ['#3ef2c9', '#8b6bff', '#c06bff', '#030d12'], locked: true }];
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ looks, eligible: false, minUsd: 1000 }) }));
  const { LookPicker } = require('./LookPicker');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<LookPicker />); }); await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('look-aurora').textContent).toContain('ADVANCED'); expect(el.textContent).toContain('unlock at $1,000');
  await act(async () => { q('look-aurora').click(); }); expect(document.documentElement.dataset.look).toBeUndefined();   // locked: nothing applies
  await act(async () => { q('look-molten').click(); }); expect(document.documentElement.dataset.look).toBe('molten'); expect(q('look-molten').textContent).toContain('WEARING');
  await act(async () => { q('look-save').click(); }); expect(localStorage.getItem('feeless.look')).toBe('molten');
  applyLook(null); el.remove();
});

test('🟢 the owner\'s pick: Obsidian green is the default; Desk and Pit set the layout; Plasma clears it', () => {
  const { FEELESS_LOOKS, DEFAULT_LOOK } = require('../lib/looks'); const r = document.documentElement;
  expect(DEFAULT_LOOK.id).toBe('obsidian'); expect(DEFAULT_LOOK.tokens.accent).toBe('#19e68c');
  applyLook(FEELESS_LOOKS.desk); expect(r.dataset.layout).toBe('desk'); expect(r.dataset.edition).toBe('elite'); expect(r.style.getPropertyValue('--m-accent')).toBe('#19e68c');
  applyLook(FEELESS_LOOKS.pit); expect(r.dataset.layout).toBe('pit');
  applyLook(FREE_LOOKS.plasma); expect(r.dataset.layout).toBeUndefined();
});
