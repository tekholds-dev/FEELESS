import { isPhoneLike, startEco, setFullFx, FULL_KEY } from './eco';

test('phones and the Duo are eco devices; desktops, laptops and big touch screens are not', () => {
  const iphone = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1';
  expect(isPhoneLike({ coarse: true, ua: iphone, w: 466, h: 678 })).toBe(true);                       // Duo folded
  expect(isPhoneLike({ coarse: true, ua: iphone, w: 890, h: 626 })).toBe(true);                       // Duo open
  expect(isPhoneLike({ coarse: true, ua: 'Mozilla/5.0 (Linux; Android 14) Chrome/120 Mobile', w: 412, h: 915 })).toBe(true);
  expect(isPhoneLike({ coarse: true, ua: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605', w: 1024, h: 1366 })).toBe(true);   // iPadOS
  expect(isPhoneLike({ coarse: false, ua: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120', w: 1512, h: 982 })).toBe(false);  // Mac
  expect(isPhoneLike({ coarse: true, ua: 'Mozilla/5.0 (Windows NT 10.0) Chrome/120', w: 1920, h: 1080 })).toBe(false);                     // touch laptop
});

test('eco marks the body (animations stay — lite is the user\'s own switch); Full effects takes it off and is remembered', () => {
  window.matchMedia = q => ({ matches: q === '(pointer: coarse)', addEventListener() {}, removeEventListener() {} });
  Object.defineProperty(window.screen, 'width', { value: 390, configurable: true }); Object.defineProperty(window.screen, 'height', { value: 844, configurable: true });
  localStorage.removeItem(FULL_KEY); document.body.className = '';
  expect(startEco()).toBe(true); expect(document.body.classList.contains('fx-eco')).toBe(true); expect(document.body.classList.contains('fx-lite')).toBe(false);
  setFullFx(true); expect(document.body.className).toBe(''); expect(startEco()).toBe(false);
  setFullFx(false); expect(document.body.classList.contains('fx-eco')).toBe(true);
});
