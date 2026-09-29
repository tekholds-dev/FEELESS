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
