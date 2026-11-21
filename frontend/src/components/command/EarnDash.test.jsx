import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { EarnDash } from './EarnDash';
import { EarnBoard, EarnFiling } from './EarnDesk';

// 💼 Slice 28: the PoEco desk opens on an earning dashboard; a skill tap, a feed row's "What it takes" and Start this job each send the wired op.
jest.mock('./EcoLive', () => ({ EcoLive: () => <div data-testid="eco-live-stub" /> }));
const NEEDS = { minds: [{ model: 'qwen/qwen3.8-max', name: 'qwen3.8-max', calls: 2, usd: 0.01 }, { model: 'local/ossy', name: 'ossy', calls: 2, usd: 0, local: true }],
  calls: 4, cost: 0.01, days: 2, ourHours: 4, humanHours: 11.4, humanRate: 35, rivals: 2, avgBid: 250, kits: ['Bid Desk', 'Faceless Work Check'] };
const ROW = { id: 'superteam:w1', src: 'superteam', title: 'Write an article on Solana priority fees', url: 'https://superteam.fun/earn/listing/w1', cat: 'writing', pay: '400 USDC', payUsd: 400,
  daysLeft: 6, rivals: 2, score: 80, parts: { fit: 30, pay: 16, deadline: 20, profit: 14 }, expProfit: 93.19, cost: 0.01, chance: 0.233,
  real: { humanHours: 11.4, humanRate: 35, minDays: 2, priceLo: 240, priceHi: 400 }, competes: { ok: true, few: true, clear: true, fast: true, why: ['2 bids so far (few)', 'clear scope'] }, needs: NEEDS };
const DASH = { found: 12, feed: 1, expUsd: 310.5, waiting: 1, sentOut: 0, inWork: 1, paidUsd: 120, mindsUsd: 0.11, netUsd: 119.89, paidN: 1, lost: 1, curve: [{ net: -0.01 }, { net: 119.89 }],
  calls: { n: 3, right: 1, wrong: 1, open: 1 } };
const EARNS = [{ id: 'e1', n: 4, kind: 'earn', stage: 'bid', cost: 0.018, listing: ROW, platform: { name: 'Superteam Earn' }, bid: { price: 380, days: 2, realistic: { ok: true } } },
  { id: 'e3', n: 2, kind: 'earn', stage: 'paid', cost: 0.03, listing: ROW, graded: { result: 'paid', paidUsd: 120, cost: 0.07, profit: 119.93, why: 'paid $120.00' } }];
const V = { board: { at: Date.now() / 1000, best: [ROW], feed: [ROW], kept: 1, seen: 80, skill: '', skills: { writing: 13, code: 30 }, out: [] }, dash: DASH, earns: EARNS, platforms: [] };
const MARKET = [{ id: 'm1', n: 1, kind: 'market', q: 'Which pool turns over more?', rule: 'higher turnover wins', graded: 'right' }];

let box, root;
beforeEach(() => { box = document.createElement('div'); document.body.appendChild(box); root = createRoot(box); try { localStorage.clear(); } catch { /* none */ } });
afterEach(() => { act(() => root.unmount()); box.remove(); });
const q = id => box.querySelector(`[data-testid="${id}"]`);

test('it opens on the earning dashboard: jobs, bids to approve, work, money paid vs minds, market calls', () => {
  act(() => root.render(<EarnDash v={V} rows={MARKET} busy={false} call={() => {}} onBid={() => {}} onOpen={() => {}} />));
  expect(q('edb-net').textContent).toBe('$120');
  expect(q('edb-money').textContent).toContain('$0.11 minds');
  expect(q('edb-found').textContent).toContain('12');
  expect(q('edb-found').textContent).toContain('1 AI can win');
  expect(q('edb-waiting').textContent).toContain('1');
  expect(q('edb-work').textContent).toContain('1 paid · 1 lost');
  expect(q('edb-calls').textContent).toContain('1–1');
});

test('one tap by skill re-sorts the board with no new read, and Find me work reads the feeds', () => {
  const sent = [];
  act(() => root.render(<EarnDash v={V} rows={[]} busy={false} call={b => sent.push(b)} onBid={() => {}} onOpen={() => {}} />));
  expect(q('edb-skill-code').textContent).toContain('30');
  act(() => { q('edb-skill-code').click(); });
  act(() => { q('edb-read').click(); });
  expect(sent).toEqual([{ op: 'earn_find', tools: { skill: 'code', fresh: false } }, { op: 'earn_find', tools: { skill: '' } }]);
});

test('an old board is read again on open (a live feed), a fresh one is not', () => {
  const sent = [];
  act(() => root.render(<EarnDash v={{ ...V, board: { ...V.board, at: Date.now() / 1000 - 3 * 3600, skill: 'writing' } }} rows={[]} busy={false} call={b => sent.push(b)} onBid={() => {}} onOpen={() => {}} />));
  expect(sent).toEqual([{ op: 'earn_find', tools: { skill: 'writing' } }]);
});

test('what it takes to win shows the minds, models, cost, time, competition and chance before he starts', () => {
  const bids = [];
  act(() => root.render(<EarnDash v={V} rows={[]} busy={false} call={() => {}} onBid={id => bids.push(id)} onOpen={() => {}} />));
  expect(q(`edb-win-${ROW.id}`)).toBeNull();
  act(() => { q('edb-more-0').click(); });
  const w = q(`edb-win-${ROW.id}`).textContent;
  expect(w).toContain('qwen3.8-max'); expect(w).toContain('free'); expect(w).toContain('4)');
  expect(w).toContain('2 days'); expect(w).toContain('≈11.4 h'); expect(w).toContain('$35/h');
  expect(w).toContain('2 already bid'); expect(w).toContain('avg bid $250'); expect(w).toContain('23% chance'); expect(w).toContain('$240–$400');
  act(() => { q(`edb-start-${ROW.id}`).click(); });
  expect(bids).toEqual([ROW.id]);   // → the 3-step start wizard (Slice 33), never a bare send
});

test('the tabs: bids & work opens a filing, paid shows the ledger with fees kept off, market calls list the calls', () => {
  const opened = [];
  act(() => root.render(<EarnDash v={V} rows={MARKET} busy={false} call={() => {}} onBid={() => {}} onOpen={f => opened.push(f.id)} />));
  act(() => { q('edb-tab-pipe').click(); });
  expect(q('edb-pipe-e1').textContent).toContain('Waiting for your approve');
  expect(q('edb-pipe-e3')).toBeNull();
  act(() => { q('edb-pipe-e1').click(); });
  act(() => { q('edb-tab-paid').click(); });
  expect(q('edb-paid').textContent).toContain('fees stay on each receipt');
  act(() => { q('edb-paid-e3').click(); });
  act(() => { q('edb-tab-calls').click(); });
  expect(q('edb-call-m1').textContent).toContain('RIGHT');
  act(() => { q('edb-tab-books').click(); });
  expect(q('eco-live-stub')).not.toBeNull();
  expect(opened).toEqual(['e1', 'e3']);
});

test('every board row opens what it takes; the board keeps Draft bid', () => {
  const calls = [];
  act(() => root.render(<EarnBoard v={V} busy={false} onFind={() => {}} onBid={id => calls.push(id)} />));
  act(() => { q('ern-more-0').click(); });
  expect(q(`edb-win-${ROW.id}`).textContent).toContain('Minds & models');
  act(() => { q('ern-bid-0').click(); });
  expect(calls).toEqual([ROW.id]);
});

test('a filing shows the job in its own words and says when a bid is not realistic', () => {
  const f = { id: 'e9', n: 9, kind: 'earn', stage: 'bid', listing: { ...ROW, desc: 'x '.repeat(200) + 'work from site dimensions you provide?' }, platform: { name: 'Freelancer.com' }, kept: 0, cost: 0.02,
    bid: { bid: 'b', price: 1200, days: 2, daysAsked: 1, realistic: { ok: false, why: 'promises 1 day; realistic is at least 2' } },
    bids: [{ mind: 0, score: 40, bid: 'b', plan: [], why: [] }, { mind: 1, score: 20, bid: 'c', plan: [], why: [] }] };
  act(() => root.render(<EarnFiling f={f} onBack={() => {}} busy={false} act={() => {}} />));
  expect(q('ern-desc').textContent).toContain('work from site dimensions you provide?');
  act(() => { q('ern-desc-more').click(); });
  expect(q('ern-desc').className).toContain('is-more');
  expect(q('ern-unreal-0').textContent).toContain('at least 2');
  expect(q('ern-bid-mind-0').textContent).toContain('(it said 1)');
});
