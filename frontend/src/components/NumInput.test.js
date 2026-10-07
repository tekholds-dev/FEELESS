import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import NumInput, { commaNum, stripNum } from './NumInput';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const type = (el, v) => act(() => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); });

test('commas are display only: 1250000.5 shows 1,250,000.5 and comes back plain', () => {
  expect(commaNum('1250000.5')).toBe('1,250,000.5'); expect(commaNum(1000)).toBe('1,000'); expect(commaNum('999')).toBe('999');
  expect(commaNum('1000.')).toBe('1,000.'); expect(commaNum('-12345')).toBe('-12,345'); expect(commaNum('0.00001234')).toBe('0.00001234');
  expect(commaNum('')).toBe(''); expect(commaNum('off')).toBe('off'); expect(commaNum('1e-7')).toBe('1e-7');
  expect(stripNum('1,250,000.5')).toBe('1250000.5');
});

test('a number box shows commas, hands plain digits to onChange and keeps a half-typed decimal', () => {
  const seen = [];
  function Box() { const [v, setV] = React.useState(1000); return <NumInput type="number" data-testid="n" placeholder="80000" value={v} onChange={e => { seen.push(e.target.value); setV(Number(e.target.value)); }} />; }
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  act(() => root.render(<Box />));
  const el = host.querySelector('[data-testid=n]');
  expect(el.value).toBe('1,000'); expect(el.type).toBe('text'); expect(el.placeholder).toBe('80,000');
  act(() => el.focus());
  type(el, '1,2500'); expect(seen.pop()).toBe('12500'); expect(el.value).toBe('12,500');
  type(el, '12,500.'); expect(seen.pop()).toBe('12500.'); expect(el.value).toBe('12,500.');   // the parent stores 12500, the dot stays
  type(el, '12,500.5x'); expect(seen.pop()).toBe('12500.5'); expect(el.value).toBe('12,500.5');   // letters never get in
  act(() => root.unmount()); host.remove();
});

test('an uncontrolled box gives onBlur the plain number', () => {
  let out = null;
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  act(() => root.render(<NumInput type="number" defaultValue={2500} onBlur={e => { out = Number(e.target.value); }} />));
  const el = host.querySelector('input'); expect(el.value).toBe('2,500');
  act(() => el.focus()); type(el, '30000'); act(() => el.blur());
  expect(out).toBe(30000); expect(el.value).toBe('30,000');
  act(() => root.unmount()); host.remove();
});
