import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { EarnBoard, EarnFiling } from './EarnDesk';

// 💼 Slice 16: the earn board shows the best faceless listings with expected profit; a filing moves only on the owner's taps (a TEST needs his tick).
const ROW = { id: 'algora:1', src: 'algora', title: 'Fix tx.origin phishing', url: 'https://github.com/o/r/issues/1', cat: 'code', pay: '$700', payUsd: 700, daysLeft: null, rivals: 54,
  score: 76, parts: { fit: 30, pay: 17, deadline: 20, profit: 9 }, expProfit: 48.26, cost: 0.02, chance: 0.07 };
const V = { board: { at: 1, best: [ROW], kept: 1, seen: 90, out: [{ why: 'needs a face or a place', n: 37 }] },
  platforms: [{ id: 'algora', name: 'Algora', in: true, terms: 'each repo sets its AI rule', how: 'from his own GitHub' }, { id: 'upwork', name: 'Upwork', in: false, why: 'no public feed' }] };
const F = { id: 'earn1', n: 2, kind: 'earn', stage: 'bid', test: { by: 'Claude' }, listing: { ...ROW, hours: 6 }, platform: { name: 'Algora', how: 'from his own GitHub' }, cost: 0.018, kept: 0,
  bid: { bid: 'The kept bid. Drafted with AI help.' }, bids: [{ mind: 0, score: 91, bid: 'The kept bid.', plan: ['a', 'b'], why: ['120 words'] }, { mind: 1, score: 60, bid: 'Other.', plan: [], why: [] }] };

let box, root;
beforeEach(() => { box = document.createElement('div'); document.body.appendChild(box); root = createRoot(box); });
afterEach(() => { act(() => root.unmount()); box.remove(); });
const q = id => box.querySelector(`[data-testid="${id}"]`);

test('the board shows the best listing, its expected profit, what was left out and the terms', () => {
  const calls = [];
  act(() => root.render(<EarnBoard v={V} busy={false} onFind={() => calls.push('find')} onBid={id => calls.push(id)} />));
  expect(q('ern-verdict').textContent).toContain('Fix tx.origin phishing');
  expect(q('ern-verdict').textContent).toContain('$48');
  expect(q('ern-out').textContent).toContain('37 needs a face or a place');
  expect(q('ern-terms').textContent).toContain('1 platforms kept, 1 out');
  act(() => { q('ern-bid-0').click(); q('ern-find').click(); });
  expect(calls).toEqual(['algora:1', 'find']);
});

test('a TEST filing approves only on purpose and nothing else is offered before the approve', () => {
  const sent = [];
  act(() => root.render(<EarnFiling f={F} onBack={() => {}} busy={false} act={b => sent.push(b)} />));
  expect(q('ern-bid-mind-0').textContent).toContain('KEPT');
  expect(q('ern-bid-mind-1').textContent).toContain('NOT KEPT');
  expect(q('ern-approve').disabled).toBe(true);
  expect(q('ern-sent')).toBeNull(); expect(q('ern-paid')).toBeNull();
  act(() => { q('ern-real').click(); });
  act(() => { q('ern-approve').click(); });
  expect(sent).toEqual([{ op: 'earn_go', job: 'earn1', tools: { stage: 'bid_approved', real: true } }]);
});

test('after the approve it offers copy, the listing and I sent it; a paid filing shows its grade', () => {
  const sent = [];
  act(() => root.render(<EarnFiling f={{ ...F, test: null, stage: 'bid_approved' }} onBack={() => {}} busy={false} act={b => sent.push(b)} />));
  act(() => { q('ern-sent').click(); });
  expect(sent[0]).toEqual({ op: 'earn_go', job: 'earn1', tools: { stage: 'sent' } });
  act(() => root.render(<EarnFiling f={{ ...F, test: null, stage: 'paid', graded: { result: 'paid', profit: 699.96, why: 'paid $700.00, the minds cost $0.0400; fees $70.00 stay on the receipt' } }} onBack={() => {}} busy={false} act={() => {}} />));
  expect(q('ern-grade').textContent).toContain('PAID');
  expect(q('ern-grade').textContent).toContain('fees $70.00 stay on the receipt');
});
