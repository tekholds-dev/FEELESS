import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({}) }));
jest.mock('../lib/push', () => ({}));
// eslint-disable-next-line import/first
import { NotificationList } from './Social';

const mount = ui => { const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host); act(() => root.render(ui)); return host; };

test('groups snipers-out alerts into one dropdown with a clickable coin and its market cap', () => {
  const now = Date.now() / 1000;
  const host = mount(<NotificationList items={[
    { id: 'a', kind: 'snipers', text: 'Every sniper on your coin FEE has sold out', url: '/terminal/chat?pair=P1', at: now, read: false, meta: { symbol: 'FEE', name: 'Feeless', mcap: 1_250_000 } },
    { id: 'b', kind: 'snipers', text: 'Every sniper on your coin CAT has sold out', url: '/terminal/chat?pair=P2', at: now, read: true },
    { id: 'c', kind: 'dm', text: 'hi', url: '/x', at: now, read: false },
  ]} />);
  const group = host.querySelector('[data-testid="np-snipers"]');
  expect(group.querySelector('summary').textContent).toContain('2 coins');
  const rows = group.querySelectorAll('.np-sniper');
  expect(rows).toHaveLength(2);
  expect(rows[0].querySelector('.np-coin').getAttribute('href')).toBe('/terminal/chat?pair=P1');
  expect(rows[0].textContent).toContain('$FEE');
  expect(rows[0].textContent).toContain('MC $1.25M');
  expect(rows[0].querySelector('.np-buy').getAttribute('href')).toBe('/terminal/chat?pair=P1&buy=1');
  expect(rows[1].textContent).toContain('$CAT'); // older alert: ticker recovered from its text
  expect(host.querySelectorAll('.np-item')).toHaveLength(1);
});

test('a watched wallet buy opens a pre-quoted Quick trade', () => {
  const host = document.createElement('div');
  act(() => createRoot(host).render(<NotificationList items={[{ id: 'w1', kind: 'watch', text: '👁 Dev bought $CAT ($1,200)', url: '/terminal/chat?chain=solana&pair=P9', at: Date.now() / 1000, read: false }]} />));
  const row = host.querySelector('[data-testid="np-watch"]');
  expect(row.querySelector('.np-buy').getAttribute('href')).toBe('/terminal/chat?chain=solana&pair=P9&buy=1');
});

test('three or more of one kind collapse into a dropdown; fewer stay as rows', () => {
  const now = Date.now() / 1000;
  const host = document.createElement('div');
  const items = [1, 2, 3].map(i => ({ id: `m${i}`, kind: 'mention', text: `@you mention ${i}`, url: '/x', at: now - i, read: i > 1 }))
    .concat([{ id: 'd1', kind: 'dm', text: 'hey', url: '/dm', at: now, read: false }]);
  act(() => createRoot(host).render(<NotificationList items={items} />));
  const g = host.querySelector('[data-testid="np-group-mention"]');
  expect(g.querySelector('summary').textContent).toContain('Mentions · 3');
  expect(g.querySelector('.np-count').textContent).toBe('1');
  expect(host.querySelector('[data-testid="np-group-dm"]')).toBeNull();
  expect(host.querySelectorAll('a.k-dm')).toHaveLength(1);
});

test('one alert stream: Trading / Social lenses, and each trading alert cites its source', () => {
  const now = Date.now() / 1000;
  const host = mount(<NotificationList items={[
    { id: 'a', kind: 'alert', text: 'WIF volume spike', url: '/?coin=solana:P', at: now, read: false, meta: { source: '5m vs 24h volume (DexScreener)' } },
    { id: 'f', kind: 'feecat', text: 'Fee bought BONK', url: '/x', at: now, read: false, meta: { source: 'FeeCat trade post' } },
    { id: 'd', kind: 'dm', text: 'gm', url: '/y', at: now, read: false },
  ]} />);
  const texts = () => [...host.querySelectorAll('.np-item p')].map(p => p.textContent);
  expect(texts()).toHaveLength(3);
  expect(host.querySelector('[data-testid="np-why"]').textContent).toBe('source · 5m vs 24h volume (DexScreener)');
  act(() => host.querySelector('[data-testid="np-lens-trading"]').click());
  expect(texts().join('|')).not.toContain('gm');
  expect(texts()).toHaveLength(2);
  act(() => host.querySelector('[data-testid="np-lens-social"]').click());
  expect(texts()).toEqual(['gm']);
});
