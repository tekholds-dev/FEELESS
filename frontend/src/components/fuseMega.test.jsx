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

test('Lab: a copied card shows who earns from it and Clear stops copying', async () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  const { FuseLab } = require('./FuseLab');
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ pools: [] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  const incoming = { n: 1, legs: [{ pairAddress: 'P1', symbol: 'A', chainId: 'solana' }, { pairAddress: 'P2', symbol: 'B', chainId: 'solana' }], sol: 0, copyOf: 'U1', owner: '@chad', copyPct: 10 };
  await act(async () => { createRoot(el).render(<FuseLab runnerPicks={[]} onRunnerPicks={() => {}} incoming={incoming} />); });
  expect(el.querySelector('[data-testid="fl-copy"]').textContent).toContain("Copying @chad's card");
  expect(el.querySelector('[data-testid="fl-copy"]').textContent).toContain('10% of the FEELESS fee you pay');
  await act(async () => { el.querySelector('[aria-label="Stop copying"]').click(); });
  expect(el.querySelector('[data-testid="fl-copy"]')).toBeNull();
});

test('runner rows go live: mcap scales with the live price, round move from entry, else live 5m', () => {
  const { liveRunner } = require('./FuseLab');
  const r = liveRunner({ section: 'hot', price: 1, mcap: 10000, chg1h: 50 }, { price: 1.2, m5: 3.5 });
  expect(r).toMatchObject({ live: true, mcap: 12000, move: 3.5, moveLabel: '5M LIVE' });
  expect(liveRunner({ section: 'round', price: 1, entry: 0.5, mcap: 1 }, { price: 1, m5: 0 }).move).toBe(100);
  expect(liveRunner({ section: 'hot', chg1h: 7, mcap: 5 }, undefined)).toMatchObject({ live: false, move: 7, moveLabel: '1H' });
});

test('season countdown reads d/h/m', () => {
  const { left } = require('./FusePage');
  expect(left(3 * 86400 + 4 * 3600)).toBe('3d 4h'); expect(left(2 * 3600 + 5 * 60)).toBe('2h 5m'); expect(left(-5)).toBe('0m');
});

test('card plan: runners start with lane exits, empty limits are dropped, plan rides on Fuse in', async () => {
  const { defaultLegLimits, planBody, CardPlan } = require('./FuseLab');
  expect(defaultLegLimits([{ pairAddress: 'P', runner: false }, { pairAddress: 'R', runner: true }])).toEqual({ R: { tp: 50, sl: 30 } });
  expect(planBody({ at: 50, mode: 'swap', onProfit: 'compound', legs: { R: { tp: '50', sl: '' }, P: { tp: '', sl: '' } } }))
    .toEqual({ at: 50, mode: 'swap', onProfit: 'compound', legs: { R: { tp: 50, sl: null } } });
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ yieldLevels: [50, 100], swapDropPct: 25 }) }));
  let plan = { at: null, onProfit: 'collect', mode: 'hold', legs: { R: { tp: 50, sl: 30 } } };
  function Host() { const [p, setP] = React.useState(plan); plan = p; return <CardPlan legs={[{ pairAddress: 'R', symbol: 'RUN', runner: true }]} plan={p} setPlan={setP} />; }
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<Host />); }); await act(async () => new Promise(r => setTimeout(r, 0)));
  expect(el.querySelector('[data-testid="plan-tp-R"]').value).toBe('50');
  await act(async () => { el.querySelector('[data-testid="plan-at-100"]').click(); el.querySelector('[data-testid="plan-onProfit-compound"]').click(); });
  expect(plan.at).toBe(100); expect(plan.onProfit).toBe('compound');
});

test('a Fuse panel opened in a background tab still loads (only repeat polls pause while hidden)', async () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  const { FuseSeason } = require('./FusePage');
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ week: 1, endsAt: 9e9, cards: 0, board: [], boostPct: 10, past: [] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FuseSeason />); }); await act(async () => new Promise(r => setTimeout(r, 0)));
  expect(el.querySelector('[data-testid="fuse-season"]').className).not.toContain('is-loading');
  delete document.hidden;
});

test('profile ⚛️ Fuse score shows the ring and every cited part (incl. reputation)', async () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  const { FuseScore } = require('./FusePage');
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ score: 79, perf: 59, rep: 20, cards: 2, parts: [{ label: 'Season medals: 🥇', points: 15 }, { label: 'Reputation (trust 80/100)', points: 20 }] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FuseScore address="Aaaa1111111111111111111111111111111111111111" />); }); await act(async () => new Promise(r => setTimeout(r, 0)));
  const s = el.querySelector('[data-testid="fuse-score"]');
  expect(s.textContent).toContain('79'); expect(s.textContent).toContain('reputation 20/25'); expect(s.textContent).toContain('Reputation (trust 80/100)');
});

test('replay: each coin as % from its entry, the card as the average, markers placed on the 24h axis', () => {
  const { replayPaths } = require('./FusePage');
  const d = { from: 0, to: 100, legs: [{ symbol: 'A', entry: 1, series: [[0, 1], [50, 1.5], [100, 2]] }, { symbol: 'B', series: [[0, 2], [100, 1]] }], markers: [{ at: 50, kind: 'swap', label: 'swap' }] };
  const g = replayPaths(d, 600, 160);
  expect(g.lines.map(l => [l.symbol, l.last])).toEqual([['A', 100], ['B', -50]]);
  expect(g.last).toBe(25); expect(g.marks[0].x).toBe(300); expect(g.lines[0].d.startsWith('M0.0 ')).toBe(true);
});

test('the 🧬 is a real 3D helix: 10 rungs, each on its own phase', () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  const { DnaHelix } = require('./FusePage');
  const el = document.createElement('div'); document.body.appendChild(el);
  act(() => { createRoot(el).render(<DnaHelix />); });
  const rungs = el.querySelectorAll('[data-testid="dna3d"] > i');
  expect(rungs).toHaveLength(10); expect(rungs[3].style.getPropertyValue('--i')).toBe('3'); expect(rungs[0].querySelectorAll('b')).toHaveLength(2);
});

test('auto-set TP/SL presets fill every coin (runners by lane), and the bond meter lights box by box', () => {
  const { applyPreset } = require('./FuseLab');
  const legs = [{ pairAddress: 'P' }, { pairAddress: 'R', runner: true }];
  expect(applyPreset(legs, 'degen')).toEqual({ P: { tp: 100, sl: 40 }, R: { tp: 100, sl: 40 } });
  expect(applyPreset(legs, 'lanes')).toEqual({ P: { tp: 30, sl: 15 }, R: { tp: 50, sl: 30 } });
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  const { BondMeter } = require('./FusePage');
  const el = document.createElement('div'); document.body.appendChild(el);
  act(() => { createRoot(el).render(<BondMeter checks={[{ id: 'a', label: 'x', ok: true }, { id: 'b', label: 'y', ok: false }]} />); });
  expect(el.textContent).toContain('bond 1/2'); expect(el.querySelectorAll('i.on')).toHaveLength(1);
  act(() => { createRoot(el).render(<BondMeter checks={[{ id: 'a', label: 'x', ok: true }]} />); });
});

test('Cmd Ctr engine: stronger config listed with reasons, one click applies the merged values', async () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  const { EngineSuggest } = require('./command/FuseAdminSettings');
  const call = jest.fn(async (path) => (path === '/admin/runners/suggest' ? { cfg: { minMcap: 8000, roundSize: 5 }, suggestions: [{ key: 'minMcap', now: 8000, to: 12000, why: 'bots' }],
    lanes: { scalp: { n: 5, avgPct: -3, winRate: 20, losingDays: 3 } }, weights: { scalp: 0.5 } } : { ok: true }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<EngineSuggest call={call} />); });
  expect(el.textContent).toContain('Stronger config found · 1 settings'); expect(el.textContent).toContain('scalp -3% · ×0.5');
  await act(async () => { el.querySelector('[data-testid="engine-apply"]').click(); });
  expect(call).toHaveBeenCalledWith('/admin/runners/config', { method: 'POST', body: JSON.stringify({ cfg: { minMcap: 12000, roundSize: 5 } }) });
});

test('lab runners lens: ⚠️ NEW runners sit right after the round (never duplicated)', () => {
  const { runnerSections } = require('./FuseLab');
  const rows = runnerSections({ round: [{ mint: 'A', passing: true }], runners: [{ mint: 'B', vol1h: 5 }], newRunners: [{ mint: 'N', why: ['12m old'] }, { mint: 'B' }] });
  expect(rows.map(r => [r.mint, r.section])).toEqual([['A', 'round'], ['N', 'new'], ['B', 'hot']]);
  expect(rows[1].isNew).toBe(true);
});
