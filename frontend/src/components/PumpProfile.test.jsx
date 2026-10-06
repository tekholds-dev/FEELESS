import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const PROF = { mint: 'ABCpump', name: 'Super Kitty', symbol: 'SK', image: 'https://img/x.png', description: 'a cat', links: [{ type: 'x', url: 'https://x.com/sk' }], creator: 'Dev1111111111111111111111111111111',
  graduated: true, mcapUsd: 200000, athUsd: 400000, offAthPct: -50, vol1hUsd: 47040, liqUsd: 43806, replies: 12, live: true, ageH: 2, url: 'https://pump.fun/coin/ABCpump' };

test('pump profile: the coin\'s full Pump record (links, creator, graduated, cap vs ATH) on a live card backdrop; nothing for a coin Pump does not know', async () => {
  global.fetch = jest.fn(async u => ({ ok: true, json: async () => (String(u).includes('ABCpump') ? PROF : {}) }));
  const { PumpProfile } = require('./PumpProfile'); const { CARD_FX } = require('./CardFx');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<><PumpProfile mint="ABCpump" /><PumpProfile mint="Unknown1111" /></>); });
  await act(async () => { await Promise.resolve(); });
  const all = el.querySelectorAll('[data-testid="pump-profile"]');
  expect(all.length).toBe(1);
  const t = all[0].textContent;
  for (const s of ['$SK', 'Super Kitty', 'graduated', '🔴 live', '$200.0K', '$400.0K', '-50%', '💬 12', 'a cat', '𝕏', 'dev Dev1…1111']) expect(t).toContain(s);
  expect(all[0].querySelector('a.pp-dev').getAttribute('href')).toBe('/terminal/profile/Dev1111111111111111111111111111111');
  expect(all[0].querySelector('[data-testid="cfx-beam"]')).toBeTruthy(); expect(all[0].className).toContain('cfx-host');
  expect(CARD_FX).toEqual(['aurora', 'grid', 'beam', 'embers']);
});
