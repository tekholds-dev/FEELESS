import { withStart } from './FeeCatWidget';

jest.mock('react-router-dom', () => ({ Link: ({ children }) => children, useNavigate: () => jest.fn() }), { virtual: true });

test('after a reload the song resumes where it was (YouTube / SoundCloud), fresh songs start at 0', () => {
  expect(withStart({ kind: 'youtube', src: 'https://www.youtube.com/embed/x?autoplay=1' }, 95)).toBe('https://www.youtube.com/embed/x?autoplay=1&start=95');
  expect(withStart({ kind: 'soundcloud', src: 'https://w.soundcloud.com/player/?url=u' }, 40)).toBe('https://w.soundcloud.com/player/?url=u#t=40s');
  expect(withStart({ kind: 'youtube', src: 'y' }, 1)).toBe('y');
  expect(withStart({ kind: 'spotify', src: 's' }, 50)).toBe('s');
});
