import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Messenger, groupMsgs } from './Messenger';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('a run by one sender within 5 min is one group, a new day gets a separator', () => {
  const t = Date.now() / 1000;
  const g = groupMsgs([{ id: 1, from: 'ME', at: t - 100 }, { id: 2, from: 'ME', at: t - 50 }, { id: 3, from: 'P', at: t - 40 }], 'P');
  expect(g.filter(x => x.day).length).toBe(1);
  expect(g.filter(x => x.items).map(x => [x.me, x.items.length])).toEqual([[true, 2], [false, 1]]);
});

test('the inbox draws on <body> (never under the profile), lists chats, sends on Enter', async () => {
  const send = jest.fn(); const setText = jest.fn();
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => {
    createRoot(host).render(<Messenger mine wallet={{ address: 'ME' }} session="s" threads={[{ peer: 'P', handle: 'feereserve', last: { text: 'Yurr', at: Date.now() / 1000 } }]}
      withPeer="P" setWith={() => {}} msgs={[{ id: 1, from: 'P', text: 'Yurr check 7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr', at: Date.now() / 1000 }]}
      text="gm" setText={setText} send={send} policy="requests" prefs={() => Promise.resolve()} setThreads={() => {}} endRef={{ current: null }} onClose={() => {}} />);
  });
  const box = document.body.querySelector('[data-testid="profile-dm"]');
  expect(box.parentElement).toBe(document.body);
  expect(box.textContent).toContain('@feereserve');
  expect(box.querySelector('.msx-ca').getAttribute('href')).toContain('/terminal/coin/solana/7GCi');
  await act(async () => { box.querySelector('[data-testid="dm-input"]').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); });
  expect(send).toHaveBeenCalled();
});
