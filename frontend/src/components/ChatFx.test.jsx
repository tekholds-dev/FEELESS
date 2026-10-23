import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChatFx, ChatThemePicker, chatTheme, canUse, CHAT_THEMES } from './ChatFx';
import { moodOf, roomPair } from '../lib/coinMood';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('tiers: 4 free, 4 more at $5 of $FEE, 5 more at $100; a theme you lost falls back to Live', () => {
  expect(CHAT_THEMES.filter(([, , usd]) => usd === 0).map(([id]) => id)).toEqual(['neural', 'live', 'fee', 'candles', 'off']);
  expect(CHAT_THEMES.filter(([, , usd]) => usd === 5)).toHaveLength(4);
  expect(CHAT_THEMES.filter(([, , usd]) => usd === 100)).toHaveLength(5);
  expect(canUse('depth', 4.99)).toBe(false); expect(canUse('depth', 5)).toBe(true); expect(canUse('aurora', 1e9)).toBe(false);   // a retired theme is gone for good
  expect(canUse('lava', 0, ['lava'])).toBe(true);   // badge perks still unlock their theme
  expect(canUse('vortex', 99)).toBe(false); expect(canUse('vortex', 100)).toBe(true);
  const prefs = { themes: { 'coin-solana-PoolAAAAAAAAAAAAAAAAAAAAA-trenches': 'vortex' } };
  expect(chatTheme(prefs, 'coin-solana-PoolAAAAAAAAAAAAAAAAAAAAA-trenches', 250)).toBe('vortex');  // kept per coin room
  expect(chatTheme(prefs, 'coin-solana-PoolAAAAAAAAAAAAAAAAAAAAA-trenches', 20)).toBe('live');
  expect(chatTheme(prefs, 'solana-general', 0)).toBe('live');
});

test('live mood follows the coin: pump / dump / snipers cleared / calm', () => {
  expect(moodOf({ priceChange: { m5: 4 } })).toBe('pump');
  expect(moodOf({ priceChange: { h1: -12 } })).toBe('dump');
  expect(moodOf({ priceChange: { m5: 0.5 } }, { sniperWallets: ['a'], snipersHoldingPct: 0 })).toBe('clear');
  expect(moodOf({ priceChange: {} })).toBe('calm');
  expect(roomPair('coin-solana-84EGAwMQhs4Jnz3dEdxvVuk3fPD3g5qA8zyskPTZkRMZ-trenches')).toEqual({ chain: 'solana', pair: '84EGAwMQhs4Jnz3dEdxvVuk3fPD3g5qA8zyskPTZkRMZ' });
  expect(roomPair('solana-general')).toBeNull();
});

test('every theme shows the FEE mark and its drawn scene; Plain shows nothing', () => {
  const host = document.createElement('div'); document.body.appendChild(host);
  const root = createRoot(host);
  for (const [id] of CHAT_THEMES.filter(([t]) => t !== 'off')) {
    act(() => root.render(<ChatFx theme={id} room="solana-general" />));
    expect(host.querySelector('[data-testid="chat-fx"]').className).toContain(`fx-${id}`);
    expect(host.querySelector('.chat-fx-logo').getAttribute('src')).toBe('/assets/feeless-logo.png');
  }
  // 🎨 redrawn scenes (2026-10-22): real drawn art, motion on whole layers
  act(() => root.render(<ChatFx theme="candles" />)); expect(host.querySelectorAll('.cfx-candles.near rect').length).toBe(96);   // 24 candles × 4 seamless copies
  expect(host.querySelector('.cfx-candles.far')).not.toBeNull(); expect(host.querySelector('.cfx-last').textContent).toBe('LAST');
  act(() => root.render(<ChatFx theme="depth" />)); expect(host.querySelector('.cfx-depth .bid')).not.toBeNull(); expect(host.querySelectorAll('.cfx-book i').length).toBe(16);
  act(() => root.render(<ChatFx theme="vortex" />)); expect(host.querySelectorAll('.cfx-orbit img').length).toBe(3); expect(host.querySelectorAll('.cfx-ring').length).toBe(4);
  act(() => root.render(<ChatFx theme="tape" />)); expect(host.querySelectorAll('.cfx-col').length).toBe(3); expect(host.querySelector('.cfx-roll em').textContent).toMatch(/^[▲▼] \$/);
  act(() => root.render(<ChatFx theme="radar" />)); expect(host.querySelectorAll('.cfx-blip').length).toBe(5); expect(host.querySelector('.cfx-sweep')).not.toBeNull();
  act(() => root.render(<ChatFx theme="moon" />)); expect(host.querySelector('.cfx-flyx .cfx-flyy .cfx-rocket svg')).not.toBeNull();
  act(() => root.render(<ChatFx theme="gold" />)); expect(host.querySelectorAll('.cfx-vault .bolt').length).toBe(16); expect(host.querySelectorAll('.cfx-bars .bar').length).toBe(6);
  act(() => root.render(<ChatFx theme="flow" />)); expect(host.querySelectorAll('.cfx-ride b').length).toBe(15); expect(host.querySelectorAll('.cfx-ride b.whale').length).toBe(4);
  act(() => root.render(<ChatFx theme="off" />));
  expect(host.querySelector('[data-testid="chat-fx"]')).toBeNull();
});

test('the picker: live mini rooms by tier, locked tiles say how close you are, a pick saves this room only', () => {
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host); let saved = null;
  act(() => root.render(<ChatThemePicker prefs={{ themes: { other: 'gold' } }} setPrefs={p => { saved = p; }} room="brain" feeUsd={7} unlocked={['vortex']} />));
  expect(host.querySelector('[data-testid="chat-theme-depth"]').disabled).toBe(false);
  expect(host.querySelector('[data-testid="chat-theme-moon"]').disabled).toBe(true);
  expect(host.querySelector('[data-testid="chat-theme-vortex"]').disabled).toBe(false);   // badge perk
  expect(host.textContent).toContain('$7 / $100 held');
  act(() => host.querySelector('[data-testid="chat-theme-radar"]').click());
  expect(saved).toEqual({ themes: { other: 'gold', brain: 'radar' } });
});
