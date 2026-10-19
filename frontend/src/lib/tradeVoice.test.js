import { speakText, pickSystemVoice, VOICES } from './tradeVoice';

test('four voices, each line made speakable and wrapped in its own slang', () => {
  expect(VOICES.map(v => v.key)).toEqual(['gangster', 'mob', 'announcer', 'gremlin']);
  const t = speakText('🚀 $BONK up 12% https://x.com/a', 'mob', 0);
  expect(t).toBe('Hey, capisce, BONK up 12 percent fuggedaboutit.');
  expect(speakText('🔥', 'gangster')).toBe('');
});

test('the preferred system voice wins, else any English voice', () => {
  expect(pickSystemVoice('gremlin', [{ name: 'Samantha', lang: 'en-US' }, { name: 'Zarvox', lang: 'en-US' }]).name).toBe('Zarvox');
  expect(pickSystemVoice('mob', [{ name: 'Kyoko', lang: 'ja-JP' }, { name: 'Karen', lang: 'en-AU' }]).name).toBe('Karen');
});
