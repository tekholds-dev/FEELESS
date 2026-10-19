import { cleanLook, lookVars, handleUrl, DEFAULT_LOOK } from './feedLook';

test('a stored look is cleaned: bad values fall back, handles lose @ and junk', () => {
  const c = cleanLook({ bg: 'nope', font: 'mono', size: 'xl', accent: 'pink', handles: { x: '@deg en<script>', reddit: '' } });
  expect(c).toMatchObject({ bg: 'royal', font: 'mono', size: 'xl', accent: 'pink', density: 'comfy', handles: { x: 'degenscript' } });
  expect(cleanLook(null)).toEqual(DEFAULT_LOOK);
});

test('a look becomes CSS variables and classes; a handle becomes its public profile link', () => {
  const v = lookVars({ bg: 'nebula', font: 'serif', size: 'l', accent: 'ice', density: 'tight' });
  expect(v.cls).toBe('fx-bg-nebula fx-d-tight');
  expect(v.style['--fx-size']).toBe('17px');
  expect(v.style['--fx-accent']).toBe('#5ad7ff');
  expect(handleUrl('x', 'feeless')).toBe('https://x.com/feeless');
  expect(handleUrl('x', '')).toBeNull();
});
