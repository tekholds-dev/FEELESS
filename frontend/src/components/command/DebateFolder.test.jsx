import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { DebateFolder } from './DebateFolder';

jest.mock('../EcosystemChat', () => ({ __esModule: true, default: () => null }));

test('rooms: take a slot, sit down, speak on your turn, vote from outside', async () => {
  const seat = (name, mine, extra = {}) => ({ name, title: `${name} proof`, kind: 'pob', fid: name, mine, facts: '', excerpt: mine ? null : 'their file', vitals: { rank: 'B', score: 200, top: 300, parts: [{ label: 'Result', value: 1 }] }, ...extra });
  const base = { rooms: [], slots: 6, perDay: 3, satToday: 0, sayMax: 280, crowdMin: 3, rounds: ['Opening', 'Counter', 'Closer'], pts: { finish: 5, better: 5, point: 5, crowd: 10 } };
  const view = rooms => ({ rows: [], offers: [], board: [], seat: { today: 0, perDay: 5 }, open: 0, settled: 0, allowed: false, canGrade: true, room: { ...base, rooms } });
  const live = { id: 'r1', status: 'live', a: seat('Me', true), b: seat('Bo', false), side: 'a', turn: 'a', round: 'Opening', turnEnds: Date.now() / 1000 + 600, said: [], votes: { a: 0, b: 0 }, points: {} };
  const sent = []; let now = view([{ ...live, status: 'open', b: null, side: null, a: seat('Bo', false) }]);
  const work = jest.fn(async (_, b) => { sent.push(b); return now; });
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<DebateFolder cat={{ id: 'c' }} d={{ pobFolders: [{ id: 'f1', status: 'closed', topic: 'NBA' }] }} work={work} />); });
  await act(async () => { await Promise.resolve(); });
  expect(el.querySelector('[data-testid=dbr-free]')).toBeTruthy();
  const pick = el.querySelector('[data-testid=dbr-pick-r1]');
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(pick, 'f1'); pick.dispatchEvent(new Event('change', { bubbles: true })); });
  now = view([live]);
  await act(async () => { el.querySelector('[data-testid=dbr-join-r1]').click(); });
  expect(sent.at(-1)).toEqual({ op: 'debate_room_join', tools: { room: 'r1', kind: 'pob', fid: 'f1' } });
  expect(el.querySelector('[data-testid=dbr-vitals]')).toBeTruthy(); expect(el.textContent).toContain('Read their proof');
  const box = el.querySelector('[data-testid=dbr-text]');
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(box, 'my proof read two sites'); box.dispatchEvent(new Event('input', { bubbles: true })); });
  now = view([{ ...live, turn: 'b', said: [{ side: 'a', text: 'my proof read two sites', round: 'Opening', at: 1 }] }]);
  await act(async () => { el.querySelector('[data-testid=dbr-send]').click(); });
  expect(sent.at(-1).op).toBe('debate_room_say'); expect(el.querySelector('[data-testid=dbr-wait]')).toBeTruthy(); expect(el.querySelector('[data-testid=dbr-concede-0]')).toBeNull();
  now = view([{ ...live, status: 'vote', side: null, turn: null, canVote: true, voteEnds: Date.now() / 1000 + 600, a: seat('Ann', false), said: [] }]);
  await act(async () => { el.querySelector('[data-testid=dbr-vitals]'); });
  el.remove();
});
