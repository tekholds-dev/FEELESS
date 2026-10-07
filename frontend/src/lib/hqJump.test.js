import { HQ_JUMPS, jumpSearch } from './hqJump';

test('wallet profiles is the first hit for the words an owner types', () => {
  ['profiles', 'wallet profiles', 'pfp', 'circle profile'].forEach(q => expect(jumpSearch(q)[0].panel).toBe('profiles'));
});
test('every typed word must match; empty finds nothing; tabs passed in are searchable', () => {
  expect(jumpSearch('')).toEqual([]);
  expect(jumpSearch('zzz nothing')).toEqual([]);
  expect(jumpSearch('rpc')[0].label).toMatch(/RPC/);
  expect(jumpSearch('lag', [...HQ_JUMPS, { label: 'Lag catcher', words: '', tab: 'latency' }])[0].tab).toBe('latency');
});
test('every jump names a tab and a unique label', () => {
  expect(new Set(HQ_JUMPS.map(j => j.label)).size).toBe(HQ_JUMPS.length);
  HQ_JUMPS.forEach(j => expect(j.tab).toBeTruthy());
});
