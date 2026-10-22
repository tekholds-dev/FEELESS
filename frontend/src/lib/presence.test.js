import { readMode, setMode, PRESENCE_MODES } from './presence';

test('your status is remembered in this browser and falls back to online', () => {
  localStorage.removeItem('feeless.presence'); expect(readMode()).toBe('online');
  setMode('invisible'); expect(readMode()).toBe('invisible');
  localStorage.setItem('feeless.presence', 'hacked'); expect(readMode()).toBe('online');
  expect(PRESENCE_MODES.map(m => m[0])).toEqual(['online', 'away', 'invisible']);
});
