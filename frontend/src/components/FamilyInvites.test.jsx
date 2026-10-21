import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { InviteInbox, validWallet, inviteAgo } from './FamilyInvites';

test('wallet check + ago words', () => {
  expect(validWallet('So11111111111111111111111111111111111111112')).toBe(true);
  expect(validWallet('hello')).toBe(false);
  expect(inviteAgo(0, 120)).toBe('2m ago');
  expect(inviteAgo(0, 7200)).toBe('2h ago');
});

test('the inbox lists each invite with accept / decline; accept waits while you are in a family', () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => { root.render(<InviteInbox invites={[{ cid: 'c1', tag: 'SIC', name: 'Sicario', members: 2, seats: 5, by: 'AAAA…BBBB', at: Date.now() / 1000 }]} inFamily addr="A" sess="S" />); });
  expect(el.textContent).toContain('[SIC] Sicario');
  expect(el.querySelector('[data-testid="invite-accept-c1"]').disabled).toBe(true);
  expect(el.querySelector('[data-testid="invite-decline-c1"]').disabled).toBe(false);
  act(() => root.unmount());
});
