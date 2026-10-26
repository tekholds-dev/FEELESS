import { copyText, installClipboard, legacyCopy } from './clipboard';

describe('clipboard (iPhone Safari over http has no navigator.clipboard)', () => {
  test('falls back to a synchronous execCommand copy when the context is insecure', async () => {
    document.execCommand = jest.fn(() => true);
    const was = window.isSecureContext;
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: false });
    await expect(copyText('So1aNaMint')).resolves.toBeUndefined();
    expect(document.execCommand).toHaveBeenCalledWith('copy');
    expect(document.querySelector('textarea')).toBeNull();   // the helper textarea is cleaned up
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: was });
  });

  test('rejects (so call sites can toast) when the browser blocks every route', async () => {
    document.execCommand = jest.fn(() => false);
    expect(legacyCopy('x')).toBe(false);
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: false });
    await expect(copyText('x')).rejects.toThrow(/blocked/);
  });

  test('installs navigator.clipboard.writeText where none exists', () => {
    installClipboard();
    expect(typeof navigator.clipboard.writeText).toBe('function');
  });
});
