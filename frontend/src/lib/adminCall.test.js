import { hqSign } from './adminCall';

test('✍ one HQ prompt for many polls; a decline quiets the polls but a button can still ask', async () => {
  let n = 0; let t = 1000;
  const sign = jest.fn(() => { n += 1; return new Promise((ok, no) => setTimeout(() => (n === 1 ? no(new Error('rejected')) : ok('SIG')), 5)); });
  const now = () => t;
  const all = await Promise.allSettled([hqSign('A', sign, true, now), hqSign('A', sign, true, now), hqSign('A', sign, true, now)]);
  expect(sign).toHaveBeenCalledTimes(1); expect(all.every(r => r.status === 'rejected')).toBe(true);   // three polls → ONE prompt
  await expect(hqSign('A', sign, true, now)).rejects.toThrow('Sign in to HQ');                         // quiet after a decline
  expect(sign).toHaveBeenCalledTimes(1);
  await expect(hqSign('A', sign, false, now)).resolves.toMatchObject({ sig: 'SIG' });                  // a button may still ask
  t += 6 * 60 * 1000;
});
