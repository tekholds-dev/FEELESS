import { fvgs, magnets, gunLine, germ, edgeRead, toolRead, toggleChartTool, getChartTools, CHART_TOOLS } from './chartTools';

const k = (t, o, h, l, c) => [t, o, h, l, c, 1];
// flat base → a jump that leaves a gap → two equal highs → a 9% dip
const base = Array.from({ length: 10 }, (_, i) => k(i, 1, 1.02, 0.98, 1));
const run = [k(10, 1, 1.05, 0.99, 1.04), k(11, 1.04, 1.3, 1.04, 1.28), k(12, 1.28, 1.5, 1.2, 1.45)];            // gap: 1.05 → 1.20
const top = [k(13, 1.45, 1.6, 1.4, 1.5), k(14, 1.5, 1.52, 1.42, 1.45), k(15, 1.45, 1.5, 1.4, 1.48), k(16, 1.48, 1.6, 1.44, 1.5), k(17, 1.5, 1.53, 1.43, 1.46), k(18, 1.46, 1.5, 1.42, 1.45), k(19, 1.45, 1.47, 1.4, 1.44)];
const cs = [...base, ...run, ...top];

test('fvg: finds the open gap, shrinks it when price trades into it, drops it once filled', () => {
  const big = c => fvgs(c).find(x => x.bot === 1.05); expect(fvgs(cs).length).toBeLessThanOrEqual(3); expect(big(cs)).toMatchObject({ dir: 'up', bot: 1.05, top: 1.2 });
  expect(big([...cs, k(20, 1.44, 1.45, 1.1, 1.12)])).toMatchObject({ bot: 1.05, top: 1.1 });               // half filled
  expect(fvgs([...cs, k(20, 1.44, 1.45, 1.0, 1.02)]).filter(x => x.dir === 'up' && x.bot === 1.05)).toEqual([]);   // traded through = gone
});

test('magnets: equal highs nobody took are ONE strong magnet above; a taken high is not a magnet', () => {
  const m = magnets(cs); const above = m.filter(x => x.side === 'above');
  expect(above[0]).toMatchObject({ price: 1.6, hits: 2 }); expect(above[0].distPct).toBeGreaterThan(10);
  expect(magnets([...cs, k(20, 1.44, 1.7, 1.44, 1.5), k(21, 1.5, 1.52, 1.45, 1.5), k(22, 1.5, 1.51, 1.45, 1.5)]).filter(x => x.price === 1.6)).toEqual([]);
});

test('gun line: the swing high overhead is the trigger; once price is above every swing high it reads fired', () => {
  expect(gunLine(cs)).toMatchObject({ price: 1.6, fired: false });
  const broke = [...cs, k(20, 1.44, 1.7, 1.44, 1.68), k(21, 1.68, 1.75, 1.6, 1.72), k(22, 1.72, 1.9, 1.7, 1.88), k(23, 1.88, 1.92, 1.8, 1.9), k(24, 1.9, 1.99, 1.85, 1.98)];
  expect(gunLine(broke).fired).toBe(true);
});

test('germ: the base candle of the biggest run; closing under it = lost', () => {
  const g = germ(cs); expect(g.runPct).toBeGreaterThan(50); expect(g.bot).toBeLessThanOrEqual(0.99); expect(g.lost).toBe(false);
  expect(germ([...cs, k(20, 1.44, 1.45, 0.9, 0.92)]).lost).toBe(true);
  expect(germ(base)).toBeNull();                                                                                // no run = no germ
});

test('meta edge: one read with a score, plain reasons and a plan; a dead chart scores low; toolRead draws only what is on', () => {
  const e = edgeRead(cs); expect(e.score).toBeGreaterThanOrEqual(45); expect(e.why.join(' ')).toContain('off its high'); expect(e.plan.length).toBeGreaterThan(5);
  const dead = edgeRead([...cs, k(20, 1.44, 1.45, 0.8, 0.82), k(21, 0.82, 0.85, 0.7, 0.72)]); expect(dead.verdict).toBe('none'); expect(dead.why.join(' ')).toContain('lost its germ');
  expect(edgeRead(base.slice(0, 5))).toBeNull();
  expect(toolRead(cs, [])).toBeNull();
  const only = toolRead(cs, ['gun']); expect(only.gun.price).toBe(1.6); expect(only.fvg).toEqual([]); expect(only.edge).toBeNull();
  const all = toolRead(cs, ['edge']); expect(all.fvg.length).toBeGreaterThan(0); expect(all.germ).not.toBeNull(); expect(all.edge.score).toBe(e.score);
});

test('one remembered choice for every chart', () => {
  expect(CHART_TOOLS.map(t => t[0])).toEqual(['fvg', 'magnet', 'gun', 'germ', 'edge']);
  window.localStorage.clear(); expect(getChartTools()).toEqual([]);
  toggleChartTool('fvg'); toggleChartTool('gun'); toggleChartTool('nope'); expect(getChartTools()).toEqual(['fvg', 'gun']);
  expect(JSON.parse(window.localStorage.getItem('feeless.chartTools'))).toEqual(['fvg', 'gun']);
  toggleChartTool('fvg'); expect(getChartTools()).toEqual(['gun']); toggleChartTool('gun');
});
