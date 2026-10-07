import { sharedJson, markFresh, _resetShared } from './sharedJson';

test('callers asking for the same URL at once share ONE request; a fresh read after an owner action starts a new one', async () => {
  _resetShared();
  let n = 0;
  global.fetch = jest.fn(async () => { n += 1; return { ok: true, json: async () => ({ n }) }; });
  const [a, b, c] = await Promise.all([sharedJson('/x'), sharedJson('/x'), sharedJson('/x')]);
  expect(global.fetch).toHaveBeenCalledTimes(1);                      // the Fuse page fetched /fuses/prime 4× at once
  expect(a).toBe(b); expect(b).toBe(c);
  await sharedJson('/x'); expect(global.fetch).toHaveBeenCalledTimes(1);   // inside maxAge → the same answer
  markFresh();
  const f = await sharedJson('/x', { fresh: true });                   // after an owner action → a new read
  expect(global.fetch).toHaveBeenCalledTimes(2); expect(f.n).toBe(2);
  await sharedJson('/y'); expect(global.fetch).toHaveBeenCalledTimes(3);   // another URL is its own request
});

test('a failed read is never served to the next caller', async () => {
  _resetShared();
  global.fetch = jest.fn().mockRejectedValueOnce(new Error('down')).mockResolvedValue({ ok: true, json: async () => ({ ok: 1 }) });
  await expect(sharedJson('/z')).rejects.toThrow('down');
  await new Promise(r => setTimeout(r, 0));
  expect(await sharedJson('/z')).toEqual({ ok: 1 });
});
