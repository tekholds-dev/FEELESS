jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn(), Link: () => null, useLocation: () => ({ pathname: '/' }) }), { virtual: true });
// eslint-disable-next-line import/first
import { resumeFrom, withStart } from './FeeCatWidget';

test('a refresh resumes like YouTube: same song, same second, still playing (or still paused)', () => {
  expect(resumeFrom({ i: 2, playing: true, pos: 95.7 }, 4)).toEqual({ i: 2, playing: true, pos: 95 });
  expect(resumeFrom({ i: 1, playing: false, pos: 40 }, 4)).toEqual({ i: 1, playing: false, pos: 40 });   // paused stays paused at its spot
  expect(resumeFrom({ i: 9, playing: true, pos: 40 }, 4)).toEqual({ i: 0, playing: true, pos: 0 });      // song removed → first song from the top
  expect(resumeFrom({ i: 0, playing: true, startedAt: 1 }, 2)).toEqual({ i: 0, playing: true, pos: 0 }); // old save (no pos) → top of the song
  expect(resumeFrom(null, 3)).toEqual({ i: 0, playing: false, pos: 0 });
  expect(withStart({ kind: 'youtube', src: 'https://www.youtube.com/embed/x?autoplay=1' }, resumeFrom({ i: 0, playing: true, pos: 95 }, 1).pos)).toContain('&start=95');
});
