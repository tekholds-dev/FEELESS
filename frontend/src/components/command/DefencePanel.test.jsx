import { classBar } from './DefencePanel';
import { approvalLine } from '../../lib/revoke';

test('the stores bar shares the data folder by kind, biggest first', () => {
  const b = classBar({ cache: { mb: 60, n: 20 }, money: { mb: 30, n: 5 }, log: { mb: 10, n: 8 } });
  expect(b.map(x => x.k)).toEqual(['cache', 'money', 'log']); expect(b[0].w).toBeCloseTo(0.6); expect(classBar(null)).toEqual([]);
});

test('an approval reads as who can move how much of what', () => {
  expect(approvalLine({ delegate: 'DRAINERxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx9999', amount: '1000', mint: 'MINTyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy1111', balance: '1000' }))
    .toBe('DRAI…9999 can move 1000 of MINT…1111 (you hold 1000)');
});
