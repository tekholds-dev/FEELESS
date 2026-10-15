import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AiActivity, pulse } from './AiActivity';

jest.mock('../CoinDrawer', () => ({ openCoin: jest.fn() }));
test('the activity pane lists every model event and filters by kind', async () => {
  const now = Date.now() / 1000;
  expect(pulse([{ at: now - 10 }, { at: now - 10 }, { at: now - 400 }], now).slice(-2)).toEqual([1, 2]);
  const items = [{ at: now - 5, kind: 'read', icon: '😈', title: 'DEVIL read $X → CAUTION', who: 'DESKTOP AI', tone: 'bad', mint: 'M' }, { at: now - 9, kind: 'play', icon: '🧪', title: 'made: card', tone: 'ice' }];
  const call = jest.fn(() => Promise.resolve({ items }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<AiActivity call={call} />); });
  await act(async () => { await Promise.resolve(); });
  expect(el.querySelectorAll('.cac-list li')).toHaveLength(2);
  await act(async () => { el.querySelector('[data-testid="cac-k-play"]').click(); });
  expect(el.querySelectorAll('.cac-list li')).toHaveLength(1);
  expect(call).toHaveBeenCalledWith('/admin/ai/activity');
});
