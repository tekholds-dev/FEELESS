import { timelineSteps } from './TradeTimeline';

test('the timeline walks quoted → signed → broadcast → confirmed and marks a failure', () => {
  const t = { quotedAt: 1000, signedAt: 3000, signer: 'Wa11etXYZ', wallet: 'Phantom', sentAt: 3500, signature: 'sig123456', state: 'submitted' };
  const s = timelineSteps(t);
  expect(s.map(x => x.done)).toEqual([true, true, true, false]);
  expect(s[1].note).toContain('Phantom Wa11…tXYZ');
  expect(timelineSteps({ ...t, state: 'confirmed', doneAt: 5000 })[3].done).toBe(true);
  expect(timelineSteps({ ...t, state: 'failed' })[3]).toMatchObject({ bad: true, label: 'Failed on-chain — nothing moved' });
});
