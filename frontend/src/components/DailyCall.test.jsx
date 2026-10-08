import { fmtLeft, pctText, lastLine } from './DailyCall';

test('the clock, moves and the last result read plainly', () => {
  expect(fmtLeft(3725)).toBe('62:05'); expect(fmtLeft(-4)).toBe('00:00'); expect(fmtLeft(59.9)).toBe('00:59');
  expect(pctText(12.345)).toBe('+12.3%'); expect(pctText(-0.5)).toBe('-0.50%'); expect(pctText(null)).toBe('—');
  expect(lastLine({ symbol: 'ABC', winner: 'M', moves: { M: 8.2 }, mine: 'M', won: true })).toBe('✅ $ABC led the last hour (+8.20%) — you called it.');
  expect(lastLine({ symbol: 'ABC', winner: 'M', moves: { M: 8.2 }, mine: 'X', won: false })).toContain('Your call missed');
  expect(lastLine({ symbol: 'ABC', winner: 'M', moves: {}, mine: null, won: false })).toBe('$ABC led the last hour.'); expect(lastLine(null)).toBe('');
});
