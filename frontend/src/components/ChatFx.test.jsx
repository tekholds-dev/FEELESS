import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChatFx, chatTheme, canUse, CHAT_THEMES } from './ChatFx';
import { moodOf, roomPair } from '../lib/coinMood';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('tiers: 4 free, 4 more at $5 of $FEE, 5 more at $100; a theme you lost falls back to Live', () => {
  expect(CHAT_THEMES.filter(([, , usd]) => usd === 0).map(([id]) => id)).toEqual(['live', 'fee', 'feerain', 'off']);
  expect(CHAT_THEMES.filter(([, , usd]) => usd === 5)).toHaveLength(4);
  expect(CHAT_THEMES.filter(([, , usd]) => usd === 100)).toHaveLength(5);
  expect(canUse('aurora', 4.99)).toBe(false); expect(canUse('aurora', 5)).toBe(true);
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

test('every theme shows the FEE mark; FEE rain drops logos; Plain shows nothing', () => {
  const host = document.createElement('div'); document.body.appendChild(host);
  const root = createRoot(host);
  for (const [id] of CHAT_THEMES.filter(([t]) => t !== 'off')) {
    act(() => root.render(<ChatFx theme={id} room="solana-general" />));
    expect(host.querySelector('[data-testid="chat-fx"]').className).toContain(`fx-${id}`);
    expect(host.querySelector('.chat-fx-logo').getAttribute('src')).toBe('/assets/feeless-logo.png');
  }
  act(() => root.render(<ChatFx theme="feerain" />));
  expect(host.querySelectorAll('.chat-fx-drop').length).toBe(7);
  act(() => root.render(<ChatFx theme="off" />));
  expect(host.querySelector('[data-testid="chat-fx"]')).toBeNull();
});
