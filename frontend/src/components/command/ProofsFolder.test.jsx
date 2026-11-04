import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ProofsFolder, proofRows, reasonOf } from './ProofsFolder';

const D = {
  powFolders: [{ id: 'p1', n: 15, name: 'PoW #15', sym: 'DOG', status: 'closed', at: 1000, soldAt: 3000, pnlSol: -0.01, pnlPct: -18, why: 'stop: -18%', whys: { 0: 'Momentum and low dev hold', 1: '{"pick":2,"why":"Deepest pool' }, shots: [{ file: 'a.jpg', site: 'jup.ag', n: 1 }], loop: { n: 4, past: [{ sym: 'CAT', pct: 5 }], skipped: [{ sym: 'XDG', like: '#9 $AAA' }] } }],
  popFolders: [{ id: 'q1', n: 2, status: 'closed', at: 2000, closedAt: 2500, market: 'SOL', side: 'long', roePct: 12, calls: [{ name: 'qwen', side: 'long', market: 'SOL', why: 'trend' }] }, { id: 'q2', n: 3, status: 'closed', at: 1500, noTrade: true, why: 'the minds split', calls: [] }],
  pobFolders: [{ id: 'b1', n: 1, status: 'closed', at: 4000, topic: 'lakers parlays', graded: 'wrong', agreed: ['Lakers ML'], calls: [{ name: 'opus', picks: [{ pick: 'Lakers ML' }] }], shots: [{ file: 'm0_0.jpg', site: 'espn.com' }], loop: { n: 2, past: [{ n: 0, mark: 'right' }] } }],
};

test('🏆 every proof in one timeline, newest first, each in its own unit, never added together', () => {
  const rows = proofRows(D);
  expect(rows.map(r => r.id)).toEqual(['b1', 'p1', 'q1', 'q2']);
  expect(rows.map(r => r.state)).toEqual(['loss', 'loss', 'win', 'none']);
  expect(rows.find(r => r.id === 'p1').shown).toBe('-18.0%');
  expect(rows.find(r => r.id === 'q1').shown).toBe('+12.0% paper');
  expect(rows.find(r => r.id === 'b1').shown).toBe('wrong');
  expect(rows.find(r => r.id === 'q2').shown).toBe('no trade');
});

test('🏆 a raw model reply shows its sentence, never its JSON', () => {
  expect(reasonOf('{"pick":2,"why":"Deepest pool')).toBe('Deepest pool');
  expect(reasonOf('plain words')).toBe('plain words');
  expect(reasonOf('{"pick":2}')).toBe('');
});

test('🏆 the folder draws three parts, opens the decisions and snapshots at the time, and filters', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const opened = [];
  await act(async () => { root.render(<ProofsFolder cat={{ id: 'c1' }} d={D} onOpenFolder={k => opened.push(k)} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  ['pfx-ring', 'pfx-3d', 'pfx-orbit'].forEach(id => expect(q(id)).toBeTruthy());
  expect(q('pfx-ring').textContent).toContain('2 lost');
  await act(async () => { q('pfx-entry-p1').querySelector('.pfx-e-h').click(); });
  const open = q('pfx-entry-p1').textContent;
  expect(open).toContain('Momentum and low dev hold'); expect(open).toContain('Deepest pool'); expect(open).not.toContain('{"pick"');
  expect(q('pfx-skipped').textContent).toContain('$XDG (#9 $AAA)');
  expect(q('pfx-entry-p1').querySelector('.pfx-gallery img').getAttribute('src')).toContain('/api/cats/c1/powshot/p1/a.jpg');
  await act(async () => { q('pfx-open-folder').click(); }); expect(opened).toEqual(['pow']);
  await act(async () => { q('pfx-lens-pob').click(); });
  expect(q('pfx-entry-p1')).toBeNull(); expect(q('pfx-entry-b1')).toBeTruthy();
  await act(async () => { root.unmount(); }); el.remove();
});

test('🏆 no proofs says what to type', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ProofsFolder cat={{ id: 'c1' }} d={{}} />); });
  expect(el.querySelector('[data-testid="pfx-empty"]').textContent).toContain('file a PoW');
  await act(async () => { root.unmount(); }); el.remove();
});

test('⌨ the bar over a sign-in window sends words and keys into it, and only the owner\'s words', async () => {
  const { SignInFrame } = require('./SiteDoor');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const calls = [];
  const work = jest.fn(async (_, b) => { calls.push(b); return b.op === 'mail_read' ? { mail: [{ code: '482911' }] } : { ok: true }; });
  await act(async () => { root.render(<SignInFrame live={{ site: 'pump.fun', live: 'https://x/' }} cat={{ id: 'c' }} work={work} d={{ mailbox: { address: 'a@b.co' } }} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('sd-type-send').disabled).toBe(true);
  await act(async () => { const i = q('sd-type-text'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(i, 'hello'); i.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { q('sd-type-send').click(); });
  expect(calls.at(-1)).toEqual({ op: 'signin_type', text: 'hello' }); expect(q('sd-type-text').value).toBe('');
  await act(async () => { q('sd-key-Tab').click(); }); expect(calls.at(-1)).toEqual({ op: 'signin_type', job: 'Tab' });
  await act(async () => { q('sd-type-email').click(); }); expect(calls.at(-1)).toEqual({ op: 'signin_type', text: 'a@b.co' });
  await act(async () => { q('sd-type-code').click(); });
  await act(async () => { await Promise.resolve(); });
  expect(calls.at(-1)).toEqual({ op: 'signin_type', text: '482911' });
  await act(async () => { root.unmount(); }); el.remove();
});

test('🛒 the order card answers through the same door as typing', async () => {
  const { SiteTradeCard } = require('./SiteDoor');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const calls = [];
  const work = jest.fn(async (_, b) => { calls.push(b); return { siteTrade: null }; });
  await act(async () => { root.render(<SiteTradeCard cat={{ id: 'c' }} d={{ siteTrade: { side: 'buy', usd: 1, sym: 'BONK', site: 'pump.fun', pool: 80000, ageS: 7200, run1h: 4 } }} setD={() => {}} work={work} />); });
  expect(el.textContent).toContain('Buy $1.00 of $BONK on pump.fun');
  await act(async () => { el.querySelector('[data-testid="site-trade-yes"]').click(); });
  expect(calls[0]).toEqual({ op: 'site_trade', job: 'yes' });
  await act(async () => { root.unmount(); }); el.remove();
});
