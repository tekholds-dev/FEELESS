import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { HqVitals } from './ccTabInfo';

test('every HQ tab vitals tile shows a real number or a dash, never NaN, and fills its ring by value / of', async () => {
  document.body.classList.add('fx-lite');   // no count-up animation in the test
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HqVitals tiles={[{ label: 'Open', value: 3, of: 4 }, { label: 'Price', value: 0.000012, pre: '$', dec: 6 }, { label: 'Days left', value: null }, { label: 'Views', value: 12500, spark: [1, 4, 2] }]} />); });
  const t = [...el.querySelectorAll('[data-testid="hq-vital"]')].map(x => x.textContent);
  expect(t[0]).toContain('3'); expect(t[0]).toContain('/ 4'); expect(t[1]).toContain('$0.000012'); expect(t[2]).toContain('—'); expect(t[3]).toContain('12.5K');
  expect(el.textContent).not.toMatch(/NaN|undefined/); expect(el.querySelector('.hqv-spark polyline')).not.toBeNull();
  expect(el.querySelector('.fg').style.strokeDasharray.startsWith(String(2 * Math.PI * 16 * 0.75).slice(0, 5))).toBe(true);
});
