import { errorText } from './api';

test('turns server validation errors into readable text instead of [object Object]', () => {
  expect(errorText({ detail: 'Nope' }, 400)).toBe('Nope');
  expect(errorText({ detail: [{ loc: ['body', 'platformFeeBps'], msg: 'Input should be less than or equal to 255' }] }, 422)).toBe('platformFeeBps: Input should be less than or equal to 255');
  expect(errorText({}, 500)).toBe('Request failed (500)');
});
