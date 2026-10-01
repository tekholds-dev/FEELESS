import { walletTags } from './coinIntel';

test('tape tags: dev, sniper, bundle and big non-program holders, each with its reason', () => {
  const tags = walletTags({ creator: 'Dev1', sniperWallets: ['Snp1'], bundledWallets: ['Bnd1', 'Dev1'],
    topHolders: [{ owner: 'Pool', pct: 13, kind: 'program' }, { owner: 'Whl1', pct: 4.25 }, { owner: 'Tiny', pct: 0.4 }] });
  expect(tags.get('Dev1').map(t => t.label)).toEqual(['DEV', 'BUNDLE']);
  expect(tags.get('Snp1')[0]).toMatchObject({ label: 'SNIPER', tone: 'bad', why: 'Bought in the launch block(s)' });
  expect(tags.get('Whl1')[0].label).toBe('TOP 4.3%');
  expect(tags.has('Pool')).toBe(false);
  expect(tags.has('Tiny')).toBe(false);
  expect(walletTags(null).size).toBe(0);
});
