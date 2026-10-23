// 🌹 Familia stays its own lazy app chunk (task D, 2026-10-23: the terminal page used to download Familia's 401 KB on every load)
const fs = require('fs');
const path = require('path');

jest.mock('../components/Crews', () => ({ Crews: () => null }), { virtual: false });

test('loadFamilia starts the Familia chunk once and reuses it (hover + click = one download)', async () => {
  const { loadFamilia } = require('./familiaLoad');
  const a = loadFamilia(); const b = loadFamilia();
  expect(a).toBe(b); await expect(a).resolves.toHaveProperty('Crews');
});

test('nothing outside Familia imports the full Familia app statically — light pieces come from CrewCard.jsx', () => {
  const root = path.join(__dirname, '..');
  const walk = d => fs.readdirSync(d, { withFileTypes: true }).flatMap(e => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
  const familia = /(Crews|Family[A-Z]\w*|FeeCity3D|CityAvenue|PoolHub|NightVault|FamiliaTrade|FamiliaHud|MobScene|FamilyRoom|FamilyInvites|FamilyWars|FamilyHQ|StreetChat|RepMarkets|Realtor|FamiliaOverwatch)\.jsx$/;
  const offenders = walk(root).filter(f => /\.jsx?$/.test(f) && !/\.test\./.test(f) && !familia.test(f) && !f.includes(`${path.sep}dev${path.sep}`))
    .filter(f => /import\s+[^;]*from\s+'[./]*(components\/)?Crews'/.test(fs.readFileSync(f, 'utf8')));
  expect(offenders.map(f => path.relative(root, f))).toEqual([]);
});
