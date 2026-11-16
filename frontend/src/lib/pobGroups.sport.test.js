import { sportOf, teamsOf, sportLabel } from './pobGroups';
import { logoFor } from './teamLogos';

test('a filing names its sport and its two teams', () => {
  const x = { topic: 'Thunder vs Kings team to win', games: [{ sport: 'nba', label: 'Thunder at Kings' }] };
  expect(sportOf(x)).toBe('nba'); expect(sportLabel('nba')).toBe('NBA'); expect(teamsOf(x)).toEqual(['Thunder', 'Kings']);
  expect(sportOf({ topic: 'best NBA picks tonight' })).toBe('nba'); expect(sportOf({ topic: 'Jets vs Chiefs' })).toBe('other');
  expect(teamsOf({ topic: 'Jets vs Chiefs' })).toEqual(['Jets', 'Chiefs']); expect(sportOf({})).toBe('chips');
  expect(logoFor({ thunder: 'u' }, 'Thunder')).toBe('u'); expect(logoFor({}, 'X')).toBeNull();
});
