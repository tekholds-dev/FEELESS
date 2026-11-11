import { isCrashNoise } from './PanelBoundary';

test('🧹 SITE-1: dev hot-reload noise and /dev fixture pages are never filed as crashes; a real crash always is', () => {
  const dev = process.env.NODE_ENV; process.env.NODE_ENV = 'development';
  expect(isCrashNoise(new TypeError('_s is not a function'), '', '/terminal')).toBe(true);
  expect(isCrashNoise(new TypeError("Cannot read properties of undefined (reading 'call')"), '', '/')).toBe(true);
  expect(isCrashNoise('Module build failed (from ./node_modules/babel-loader)', '', '/familia')).toBe(true);
  expect(isCrashNoise(new Error('Loading chunk vendors-node_modules_x failed.'), '', '/familia')).toBe(true);
  expect(isCrashNoise(new Error('useNavigate() may be used only in the context of a <Router>'), '', '/dev/city')).toBe(true);
  expect(isCrashNoise(new ReferenceError('txt is not defined'), 'at CrewHQ', '/familia/family')).toBe(false);
  process.env.NODE_ENV = 'production';
  expect(isCrashNoise(new TypeError('_s is not a function'), '', '/terminal')).toBe(false);   // in production every crash is filed
  process.env.NODE_ENV = dev;
});
