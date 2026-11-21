import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FEELESS_LOOKS, LOCAL_LOOKS, applyLook, localLook, lookMap } from '../lib/looks';
import { remapText } from './HolderTheme';
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: null }) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('🎨 a look maps Plasma\'s own colours to its own, alpha kept; price-up colours are not touched', () => {
  const m = lookMap(FEELESS_LOOKS.carbon.tokens);
  const out = remapText('.a{color:#9b6bff;background:#08061a55;border:1px solid rgba(155, 107, 255, .4)}.up{color:#3ee58a}', m);
  expect(out).toBe('.a{color:#5e6ad2;background:#0b0c0e55;border:1px solid rgba(94, 106, 210, .4)}.up{color:#3ee58a}');
});

test('🎨 wearing a look sets the meta tokens and the ambient on <html>; Plasma puts the site back', () => {
  applyLook(FEELESS_LOOKS.carbon); const r = document.documentElement;
  expect(r.dataset.look).toBe('carbon'); expect(r.style.getPropertyValue('--m-accent')).toBe('#5e6ad2'); expect(r.style.getPropertyValue('--ink')).toBe('#0b0c0e');
  applyLook(null);
  expect(r.dataset.look).toBeUndefined(); expect(r.style.getPropertyValue('--m-accent')).toBe('');
});

test('🎨 the picker shows free looks to wear and advanced ones locked with what unlocks them; a tap wears it and keeps it on this device', async () => {
  const looks = [...Object.values(LOCAL_LOOKS).map(l => ({ id: l.id, name: l.name, tier: 'feeless', line: 'x', ambient: l.ambient, swatch: ['#111111', '#222222', '#333333', '#000000'], tokens: l.tokens, locked: false })),
    { id: 'aurora', name: 'Aurora', tier: 'holder', line: 'y', ambient: 'aurora', swatch: ['#3ef2c9', '#8b6bff', '#c06bff', '#030d12'], locked: true }];
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ looks, eligible: false, minUsd: 1000 }) }));
  const { LookPicker } = require('./LookPicker');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<LookPicker />); }); await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('look-aurora').textContent).toContain('ADVANCED'); expect(el.textContent).toContain('unlock at $1,000');
  await act(async () => { q('look-aurora').click(); }); expect(document.documentElement.dataset.look).toBeUndefined();   // locked: nothing applies
  localStorage.removeItem('feeless.look');
  await act(async () => { q('look-carbon').click(); }); expect(document.documentElement.dataset.look).toBe('carbon'); expect(q('look-carbon').textContent).toContain('WEARING');
  expect(localStorage.getItem('feeless.look')).toBe('carbon');   // the tap itself keeps it (2026-11-15): it survives the next page
  await act(async () => { q('look-save').click(); }); expect(localStorage.getItem('feeless.look')).toBe('carbon');
  applyLook(null); el.remove();
});

test('🟢 the owner\'s pick: Obsidian green is the default; Desk and Pit set the layout; Plasma clears it', () => {
  const { FEELESS_LOOKS, DEFAULT_LOOK } = require('../lib/looks'); const r = document.documentElement;
  expect(DEFAULT_LOOK.id).toBe('obsidian'); expect(DEFAULT_LOOK.tokens.accent).toBe('#19e68c');
  applyLook(FEELESS_LOOKS.desk); expect(r.dataset.layout).toBe('desk'); expect(r.dataset.edition).toBe('elite'); expect(r.style.getPropertyValue('--m-accent')).toBe('#19e68c');
  applyLook(FEELESS_LOOKS.pit); expect(r.dataset.layout).toBe('pit');
  applyLook(null); expect(r.dataset.layout).toBeUndefined();
  expect(Object.keys(LOCAL_LOOKS)).toEqual(['obsidian', 'desk', 'pit', 'carbon']);   // Slice 34: only these four stay
  localStorage.setItem('feeless.look', 'molten'); expect(localLook()).toBeNull(); localStorage.removeItem('feeless.look');   // a retired pick → the default (Obsidian)
});
