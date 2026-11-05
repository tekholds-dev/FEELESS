import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ProofStamp, ProofsList } from './ProofStamp';
import { RecoveryKit } from './RecoveryKit';
import { ProofTools } from './ProofTools';

async function mount(node) { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await act(async () => { await Promise.resolve(); await Promise.resolve(); }); return el; }
const row = (i, extra = {}) => ({ id: `p${i}`, kind: 'PoW', label: `$C${i}`, agent: 'Happy', pct: 60, at: i, stamp: { state: 'proved' }, ...extra });
afterEach(() => { delete global.fetch; });

test('PROOFS shows the newest 5, the dropdown holds up to 20, and a sent proof carries txn, link and receipt', async () => {
  const rows = Array.from({ length: 25 }, (_, i) => row(i)); rows[0].sent = { sol: 0.1, sig: 'ABCDEFGHIJKLMNOPQRSTUV', link: 'https://solscan.io/tx/ABC', receipt: '/api/cats/receipt/ABC' };
  const el = await mount(<ProofsList rows={rows} />);
  expect(el.querySelector('header b').textContent).toBe('PROOFS');
  expect(el.querySelectorAll('.clx-proofs > ol > li')).toHaveLength(5); expect(el.querySelectorAll('details ol > li')).toHaveLength(15);
  const s = el.querySelector('[data-testid="clx-sent-p0"]'); expect(s.querySelector('img').src).toContain('/api/cats/receipt/ABC'); expect(s.textContent).toContain('ABCDEFGHIJ'); expect(s.querySelector('a[href*="solscan"]')).not.toBeNull();
});
test('stamps say what they are', async () => {
  const el = await mount(<><ProofStamp s={{ state: 'proved' }} /><ProofStamp s={{ state: 'not' }} /><ProofStamp s={{ state: 'live' }} /><ProofStamp s={{ state: 'waiting', dueAt: Date.now() / 1000 + 7200 }} /></>);
  expect(el.textContent).toContain('PROVED'); expect(el.textContent).toContain('NOT PROVED'); expect(el.textContent).toContain('LIVE'); expect(el.textContent).toContain('STAMP IN 2h');
});
test('recovery words show once, hide after saving, and rotating asks first', async () => {
  global.fetch = jest.fn(async (u, o) => ({ ok: true, json: async () => ({ kind: JSON.parse(o.body).text, secret: 'one two three four five six seven eight nine ten eleven twelve', kit: { phrase: { set: true, at: 100 }, key: { set: false } } }) }));
  const el = await mount(<RecoveryKit cat={{ id: 'c' }} />); const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('recovery-make-phrase').click(); });
  expect(q('recovery-show').querySelectorAll('.stp-words li')).toHaveLength(12); expect(q('recovery-done')).toBeNull();
  await act(async () => { q('recovery-saved').click(); }); await act(async () => { q('recovery-done').click(); });
  expect(q('recovery-show')).toBeNull(); expect(el.textContent).not.toContain('eleven');
  await act(async () => { q('recovery-make-phrase').click(); });
  expect(global.fetch).toHaveBeenCalledTimes(1); expect(q('recovery-yes-phrase')).not.toBeNull();
});
test('Fee has no recovery kit', async () => { expect((await mount(<RecoveryKit cat={{ id: 'leader', isLeader: true }} />)).querySelector('[data-testid="recovery-kit"]')).toBeNull(); });
test('the PoB dash: sports, teams, and a parlay tap goes to the chat box only', async () => {
  const DATA = { sports: [['nfl', 'NFL'], ['nba', 'NBA']], teams: ['Kansas City Chiefs'], games: [{ id: '1', state: 'pre', status: 'Sun', teams: [{ name: 'A', short: 'Ay', chance: 0.8 }, { name: 'B', short: 'Bee', chance: 0.2 }] }], legs: [{ game: '1', pick: 'Ay to beat Bee', chance: 0.8 }], parlays: [{ legs: ['Ay to beat Bee', 'Cee to beat Dee'], chance: 0.6, pays: 1.67 }], sources: [{ name: 'ESPN', use: 'Games', on: true }, { name: 'The Odds API', use: 'needs a key', on: false }] };
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => DATA })); const sent = [];
  const el = await mount(<ProofTools kind="bids" onCommand={c => sent.push(c)} />);
  expect(el.textContent).toContain('60%'); expect(el.textContent).toContain('not a promise');
  await act(async () => { el.querySelector('[data-testid="ptl-parlay"]').click(); }); expect(sent).toEqual(['file a pob Ay to beat Bee and Cee to beat Dee']);
  await act(async () => { el.querySelector('[data-testid="ptl-sport-nba"]').click(); }); expect(global.fetch.mock.calls.at(-1)[0]).toContain('sport=nba');
  expect(el.querySelector('.ptl-src .is-on').textContent).toContain('ESPN');
});
test('a dash that cannot read says so', async () => {
  global.fetch = jest.fn(async () => ({ ok: false })); const el = await mount(<ProofTools kind="pop" />);
  expect(el.textContent).toContain('could not be read');
});
