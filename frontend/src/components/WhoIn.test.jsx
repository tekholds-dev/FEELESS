import { tagInfo, resultLine } from './WhoIn';

test('tags read in plain words and results never invent a number', () => {
  expect(tagInfo('sniper')[0]).toContain('sniper'); expect(tagInfo('dev')[1]).toMatch(/creator/); expect(tagInfo('weird')[0]).toBe('weird');
  expect(resultLine({ in: true, ret: null })).toBe('still in'); expect(resultLine({ in: false, ret: null })).toBe('in & out');
  expect(resultLine({ in: false, ret: 2 })).toBe('out · +200%'); expect(resultLine({ in: true, ret: -0.25 })).toBe('still in · -25.0%');
});
