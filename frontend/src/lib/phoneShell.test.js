import { installPhoneShell, isLockable } from './phoneShell';
test('a phone locks the page to the usable height, a desktop does not, and it cleans up', () => {
  const vv = { height: 500, offsetTop: 10, addEventListener: jest.fn(), removeEventListener: jest.fn() };
  const w = { innerWidth: 390, innerHeight: 844, visualViewport: vv, matchMedia: () => ({ matches: true }), scrollTo: jest.fn(), addEventListener: jest.fn(), removeEventListener: jest.fn(), dispatchEvent: jest.fn() };
  expect(isLockable(w)).toBe(true); expect(isLockable({ innerWidth: 1440, matchMedia: () => ({ matches: false }) })).toBe(false); expect(isLockable({ innerWidth: 900, matchMedia: () => ({ matches: false }) })).toBe(false);
  const stop = installPhoneShell(w, document);
  expect(document.body.classList.contains('phone-lock')).toBe(true); expect(document.documentElement.style.getPropertyValue('--app-vh')).toBe('500px'); expect(document.body.classList.contains('phone-kb')).toBe(true);
  stop(); expect(document.body.classList.contains('phone-lock')).toBe(false);
});
