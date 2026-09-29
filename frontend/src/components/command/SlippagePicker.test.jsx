import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { SlippagePicker } from './SlippagePicker';

const mount = ui => { const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host); act(() => root.render(ui)); return host; };
const type = (input, value) => act(() => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value); input.dispatchEvent(new Event('input', { bubbles: true })); });

test('offers 0.5 / 1 / 5% presets and a custom percent capped at 50%', () => {
  const onChange = jest.fn();
  const host = mount(<SlippagePicker value="50" onChange={onChange} />);
  expect([...host.querySelectorAll('button')].map(b => b.textContent)).toEqual(['0.5%', '1%', '5%']);
  act(() => host.querySelector('[data-testid="slippage-500"]').click());
  expect(onChange).toHaveBeenLastCalledWith('500');
  const input = host.querySelector('input');
  type(input, '12.5');
  expect(onChange).toHaveBeenLastCalledWith('1250');
  onChange.mockClear();
  type(input, '80');
  expect(onChange).not.toHaveBeenCalled();
});

test('warns at 10% or more', () => {
  const host = mount(<SlippagePicker value="1000" onChange={() => {}} />);
  expect(host.querySelector('.slip-warn')).not.toBeNull();
});
