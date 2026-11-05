import { DEFAULT_SCENE, SCENE_H, SCENE_W, chatLines, layout, mindLines, safeLine } from './liveScene';

const inside = b => b.x >= 0 && b.y >= 0 && b.x + b.w <= SCENE_W && b.y + b.h <= SCENE_H;
test('the agent sits in the chosen corner and nothing leaves the frame', () => {
  for (const corner of ['left', 'right']) for (const size of ['s', 'm', 'l']) for (const minds of [true, false]) for (const chat of [true, false]) for (const monitors of [true, false]) {
    const L = layout({ corner, size, minds, chat, monitors });
    expect(corner === 'left' ? L.agent.x < SCENE_W / 2 : L.agent.x > SCENE_W / 2).toBe(true);
    [L.agent, ...L.screens, L.minds, L.chat].filter(Boolean).forEach(b => expect(inside(b)).toBe(true));
    expect(L.screens.length).toBe(monitors ? 2 : 0); expect(!!L.minds).toBe(minds); expect(!!L.chat).toBe(chat);
  }
});
test('chat is off until chosen, and an email or phone number never reaches the stream', () => {
  expect(DEFAULT_SCENE.chat).toBe(false);
  expect(safeLine('mail joe@x.co or (415) 555-0134')).toBe('mail 🔒 or 🔒');
  const rows = [{ by: 'you', text: 'hi joe@x.co' }, { by: 'cats', text: '🗣 MIND A proposes X' }];
  expect(chatLines(rows)).toEqual(['Owner: hi 🔒']); expect(mindLines(rows)).toEqual(['MIND A proposes X']);
});
