import { hqWrite, hqBusyNow } from './hqBusy';

test('⏳ an HQ write marks the clicked button busy, a double click is ONE request, and it clears when the server answers', async () => {
  document.body.innerHTML = '<button id="b">💵 Top up</button>';
  const btn = document.getElementById('b');
  let done; let calls = 0;
  const send = () => { calls += 1; return new Promise(r => { done = r; }); };
  btn.click();
  const a = hqWrite('POST /topup {"usd":2}', send);
  const b = hqWrite('POST /topup {"usd":2}', send);            // the second click while the first is in flight
  expect(a).toBe(b);
  await Promise.resolve();
  expect(calls).toBe(1); expect(btn.getAttribute('aria-busy')).toBe('true'); expect(hqBusyNow()).toMatchObject({ n: 1, label: '💵 Top up' });
  done({ ok: true });
  await expect(a).resolves.toEqual({ ok: true });
  expect(btn.hasAttribute('aria-busy')).toBe(false); expect(hqBusyNow().n).toBe(0);
  const fail = hqWrite('POST /x', () => Promise.reject(new Error('refused')));
  await expect(fail).rejects.toThrow('refused'); expect(hqBusyNow().n).toBe(0);    // a refusal clears it too
  expect(hqWrite(null, () => 7)).toBe(7);                                          // reads are never tracked
});
