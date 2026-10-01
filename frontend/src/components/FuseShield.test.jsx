import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FuseCard } from './FuseCard';
import { BotShield } from './command/BotShield';
import { FuseDeck } from './FuseDeck';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { error: () => {}, success: () => {} } }));
jest.mock('./CaseFile', () => ({ investigate: () => {} }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await tick(0); return el; };

test('champion card: pools on the front, flip button shows why it won', async () => {
  const c = { pools: ['a', 'b'], fitness: 91, bornGen: 4, parts: { grade: 'A', aprScore: 50, momentum24h: 2, calm: 80, feeDragPct: 1, impactLegs: 0 },
    legs: [{ pairAddress: 'a', symbol: 'AAA', weight: 60, liquidityUsd: 2e6 }, { pairAddress: 'b', symbol: 'BBB', weight: 40, liquidityUsd: 5e5 }] };
  const el = await mount(<FuseCard c={c} style="degen" rank={0} />);
  expect(el.textContent).toContain('AAA · BBB'); expect(el.textContent).toContain('GEN 04');
  await act(async () => { el.querySelector('[data-testid="fuse-card-flip-0"]').click(); });
  expect(el.querySelector('[data-testid="fuse-card-flip-0"]').getAttribute('aria-label')).toBe('Show front');
  expect(el.textContent).toContain('$20 IN · LAST 24H');
});

test('bot shield lists cited flags and a Clear goes to the server', async () => {
  const call = jest.fn(async (path, opts) => (opts ? { ok: true } : { scanned: 3, counts: { bot: 1, watch: 0, clean: 2 }, engines: { reward_farmer: 1 },
    rows: [{ address: 'Farm111111111111111111111111111111111111111', score: 80, verdict: 'bot', hits: [{ engine: 'reward_farmer', score: 80, evidence: [{ claim: '19 daily check-ins, 0 trades', source: 'Quest check-ins' }] }] }] }));
  const el = await mount(<BotShield call={call} />); await tick(10);
  expect(el.textContent).toContain('1 bots');
  await act(async () => { el.querySelector('.bsh-sum').click(); });
  expect(el.textContent).toContain('19 daily check-ins, 0 trades');
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent === 'Clear (human)').click(); });
  expect(JSON.parse(call.mock.calls.find(c => c[1])[1].body)).toEqual({ address: 'Farm111111111111111111111111111111111111111', action: 'cleared' });
});

test('deck ribbon shows real P&L and an honest outlook', async () => {
  const call = jest.fn(async () => ({ book: { pnlUsd: 3.2, positions: 4, winners: 3, losers: 1 }, outlook: { proven: false, note: 'No strategy has 3 settled arena runs yet' }, published: 2, bloodline: [], blockedCuts: 1 }));
  const el = await mount(<FuseDeck call={call} panels={[['lab', 'Lab', <p key="x">L</p>, 'blurb']]} />); await tick(10);
  expect(el.textContent).toContain('$3.20'); expect(el.textContent).toContain('unproven');
});

test('card crest walks the logo fallback chain, then the glyph', async () => {
  const { MetaCard } = require('./cards/MetaCard');
  const el = await mount(<MetaCard card={{ key: 'k', kind: 'fuse', title: 'T', rarity: 'rare', glyph: 'A', art: ['https://x/a.png', 'https://x/b.png'] }} />);
  const img = () => el.querySelector('.mc-crest image');
  expect(img().getAttribute('href')).toBe('https://x/a.png');
  await act(async () => { img().dispatchEvent(new Event('error')); });
  expect(img().getAttribute('href')).toBe('https://x/b.png');
  await act(async () => { img().dispatchEvent(new Event('error')); });
  expect(img()).toBeNull(); expect(el.querySelector('.mc-crest text').textContent).toBe('A');
});

test('card math: each leg $ slice × its 24h move, minus fee drag', () => {
  const { cardMath } = require('./FuseCard');
  const m = cardMath({ parts: { feeDragPct: 1 }, legs: [{ pairAddress: 'a', weight: 60, change24h: 10 }, { pairAddress: 'b', weight: 40, change24h: -5 }] }, 20);
  expect(m.legs[0].usd).toBe(12); expect(m.legs[0].pnl).toBeCloseTo(1.2); expect(m.legs[1].pnl).toBeCloseTo(-0.4);
  expect(m.gross).toBeCloseTo(0.8); expect(m.fees).toBeCloseTo(0.2); expect(m.end).toBeCloseTo(20.6);
});

test('owned card revalues held tokens at the live price; sold legs keep their realized $', () => {
  const { revalue } = require('./FuseCard');
  const r = { legs: [{ pairAddress: 'A', usd: 10, tokens: 60, realizedUsd: 8, valueUsd: 18 }, { pairAddress: 'B', usd: 5, soldUsd: 6, valueUsd: 6 }] };
  const out = revalue(r, new Map([['A', { price: 0.5 }], ['B', { price: 99 }]]));
  expect(out.legs[0].valueUsd).toBe(38); expect(out.legs[0].priceNow).toBe(0.5);       // 60 × 0.5 + 8 realized
  expect(out.legs[1].valueUsd).toBe(6); expect(out.valueUsd).toBe(44); expect(Math.round(out.pnlPct)).toBe(193);
});
