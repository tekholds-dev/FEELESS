import { KIT_KIND } from './ProofKit';

// Owner 2026-11-14: the PoB window's READS FIRST listed every proof type's kits. Each proof window shows only its own kind.
test('every proof window reads only its own kits', () => {
  expect(KIT_KIND.pob).toBe('pob'); expect(KIT_KIND.bids).toBe('pob');
  expect(KIT_KIND.poc).toBe('poc'); expect(KIT_KIND.content).toBe('poc');
  expect(KIT_KIND.pow).toBe('pow'); expect(KIT_KIND.pop).toBe('pop'); expect(KIT_KIND.build).toBe('pos');
  expect(Object.values(KIT_KIND)).not.toContain('all');
});
