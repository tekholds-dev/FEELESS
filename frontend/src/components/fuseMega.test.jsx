import { legCaps, cardFee } from './FuseLab';
import { bundleExample } from './command/FuseAdminSettings';
import { vaultStatus } from './command/CommandCenter';
import { TIER_FX, stageTier, runnerLegs } from './FusePage';

jest.mock('react-router-dom', () => ({ Link: ({ children, ...p }) => <a {...p}>{children}</a>, useNavigate: () => jest.fn(), useLocation: () => ({ pathname: '/' }) }), { virtual: true });

test('leg caps: traders 3 pools + 3 runners, Cmd Ctr 12 legs any mix', () => {
  expect(legCaps(false)).toEqual({ pools: 3, runners: 3, total: 6 });
  expect(legCaps(true)).toEqual({ pools: 12, runners: 12, total: 12 });
});

test('card pricing: flat per coin, capped % on tiny legs, normal % on big legs', () => {
  const pr = { swapBps: 100, bundle: { on: true, perLegUsd: 0.1, maxPct: 5, maxLegUsd: 50 } };
  expect(cardFee([{ usd: 20 }, { usd: 20 }, { usd: 20 }], pr)).toBeCloseTo(0.3);
  expect(cardFee([{ usd: 0.5 }], pr)).toBeCloseTo(0.025);                 // 5% cap
  expect(cardFee([{ usd: 100 }], pr)).toBeCloseTo(1);                     // > $50 leg → normal 1%
  expect(bundleExample(pr.bundle, 20, 100)).toBeCloseTo(0.1);
});

test('vault wallet status: saved / unsaved / invalid / missing', () => {
  const w = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU';
  expect(vaultStatus(w, w)[0]).toBe('ok'); expect(vaultStatus(w, '')[0]).toBe('warn');
  expect(vaultStatus('nope', '')[1]).toBe('Not a Solana address'); expect(vaultStatus('', '')[0]).toBe('bad');
});

test('arena tiers are hard-coded and the stage burns at its hottest card', () => {
  expect(TIER_FX.blazing.embers).toBeGreaterThan(TIER_FX.hot.embers);
  expect(stageTier([{ activity: { tier: 'warm' } }, { activity: { tier: 'hot' } }])).toBe('hot');
  expect(stageTier([])).toBe('calm');
  expect(runnerLegs([{ mint: 'A', symbol: 'A' }, { mint: 'B', symbol: 'B', pairAddress: 'pB' }, { mint: 'C', symbol: 'C' }]).map(l => [l.pairAddress, l.weight])).toEqual([['A', 33.33], ['pB', 33.33], ['C', 33.33]]);
});

test('lab runners lens: this round (failing = blocked) · hot now (not in round, busiest first) · watching (blocked)', () => {
  const { runnerSections } = require('./FuseLab');
  const rows = runnerSections({ round: [{ mint: 'A', passing: true, move: 12 }, { mint: 'B', passing: false, gates: ['dev 18%'] }],
    runners: [{ mint: 'A', vol1h: 9 }, { mint: 'C', vol1h: 5 }, { mint: 'D', vol1h: 50 }], watching: [{ mint: 'Z', gates: ['top10 41%'] }] });
  expect(rows.map(r => [r.mint, r.section, r.blocked || ''])).toEqual([['A', 'round', ''], ['B', 'round', 'dev 18%'], ['D', 'hot', ''], ['C', 'hot', ''], ['Z', 'watch', 'top10 41%']]);
});

test('round age reads m / h / d', () => {
  const { ago } = require('./RunnersPanel');
  const now = Date.now() / 1000;
  expect(ago(now - 300)).toBe('5m'); expect(ago(now - 3 * 3600)).toBe('3h'); expect(ago(now - 5 * 86400)).toBe('5d');
});

test('switching the Lab lens to 🏃 Runners never renders the old pool rows as runners (crash guard)', async () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  const { FuseLab } = require('./FuseLab');
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  const D = { round: [{ mint: 'A', symbol: 'A', passing: false, move: null, gates: ['left the live feed'] }], runners: [], watching: [{ mint: 'Z', symbol: 'Z', gates: ['top10'] }] };
  global.fetch = jest.fn(async u => ({ ok: true, json: async () => (String(u).includes('discover') ? D : String(u).includes('pricing') ? {} : { pools: [{ pairAddress: 'P1', symbol: 'SOL', quote: 'USDC', dex: 'ray', liquidityUsd: 1e6, volume24h: 1e5, aprEst: 10, change24h: 1, chainId: 'solana' }] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FuseLab runnerPicks={[]} onRunnerPicks={() => {}} />); });
  await act(async () => { [...el.querySelectorAll('[role=radio]')].find(b => b.textContent.includes('Runners')).click(); });
  await act(async () => new Promise(r => setTimeout(r, 20)));
  expect(el.querySelector('[data-testid="fl-runner-A"]').disabled).toBe(true);
  expect(el.textContent).toContain('left the live feed');
});
