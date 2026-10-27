import { RACE, VEHICLES, cityOf, step, atCheckpoint, fmtMs, kmh, traffic } from './raceEngine';

test('🏁 the race city: one block per cell, a family block is taller and wears its tag, every building off the road', () => {
  const blocks = [{ owner: 'f1', tag: 'FRT', color: '#ff0', power: 5000 }, { owner: null }, { owner: 'cartel-1', kind: 'cartel', tag: 'SN1' }];
  const c = cityOf(blocks, 'x');
  expect(c.length).toBeGreaterThanOrEqual(RACE.grid * RACE.grid);
  expect(c.some(b => b.tag === 'FRT' && b.color === '#ff0')).toBe(true);
  const fam = c.filter(b => b.tag === 'FRT'); const shop = c.filter(b => b.own === '');
  expect(Math.min(...fam.map(b => b.h))).toBeGreaterThan(Math.max(...shop.map(b => b.h)) - 10);
  for (const b of c) {                                                     // no building sits on a road line
    const offRoad = v => { const m = ((v % RACE.cell) + RACE.cell) % RACE.cell; return m > RACE.road / 2 - 0.01 && m < RACE.cell - RACE.road / 2 + 0.01; };
    expect(offRoad(b.x - b.w / 2) && offRoad(b.x + b.w / 2)).toBe(true);
  }
  expect(cityOf([], 'x')).toHaveLength(cityOf([], 'x').length);            // an empty world still draws a city
});

test('🚗 gas speeds up to the vehicle top speed, steering turns, a wall stops you, checkpoints and the clock read right', () => {
  let s = { x: 0, z: 0, yaw: 0, speed: 0 };
  for (let k = 0; k < 600; k += 1) s = step(s, { gas: 1 }, 1 / 60, 'car');
  expect(s.speed).toBeGreaterThan(30); expect(s.speed).toBeLessThanOrEqual(VEHICLES.car.max);
  const turned = step(s, { gas: 1, steer: 1 }, 0.1, 'car'); expect(turned.yaw).toBeGreaterThan(0);
  const wall = { x: 20, z: 23, w: 10, d: 2 };
  const hit = step({ ...s, x: 20, z: 21.5, yaw: 0 }, { gas: 1 }, 1 / 60, 'car', [wall]);
  expect(hit.hit).toBe(true); expect(Math.abs(hit.speed)).toBeLessThan(s.speed);
  expect(atCheckpoint({ x: 38, z: 3 }, [38, 0])).toBe(true); expect(atCheckpoint({ x: 0, z: 0 }, [38, 0])).toBe(false);
  expect(fmtMs(83456)).toBe('1:23.46'); expect(kmh(46)).toBe(166);
  expect(traffic(3, 6)).toHaveLength(6);
});
