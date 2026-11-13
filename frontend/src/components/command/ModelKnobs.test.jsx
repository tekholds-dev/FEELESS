import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { ModelKnobs } from './ModelKnobs';

const QWEN = { id: 'qwen/q', name: 'Qwen: Max', efforts: ['high', 'low'], defaultEffort: 'high',
  knobs: [{ key: 'temperature', label: 'Temperature', kind: 'slider', min: 0, max: 2, step: 0.1, default: 0.2, help: '' }, { key: 'seed', label: 'Seed', kind: 'int', min: 0, max: 9, default: 0, help: '' }] };

async function mount(el) { const host = document.createElement('div'); document.body.appendChild(host); await act(async () => { createRoot(host).render(el); }); return host; }

test('a model shows only its own knobs, and a change goes back per key', async () => {
  const onChange = jest.fn();
  const host = await mount(<ModelKnobs model={QWEN} value={{}} onChange={onChange} testid="k" />);
  expect(host.textContent).toContain('2 knobs');
  await act(async () => { host.querySelector('.mkn-head').click(); });
  expect(host.querySelectorAll('.mkn-row').length).toBe(3);   // effort + temperature + seed — nothing else
  const range = host.querySelector('input[type="range"]');
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  await act(async () => { setter.call(range, '0.7'); range.dispatchEvent(new Event('input', { bubbles: true })); });
  expect(onChange).toHaveBeenLastCalledWith({ temperature: 0.7 });
});

test('a model with no knobs shows a clean default', async () => {
  const host = await mount(<ModelKnobs model={{ id: 'b', name: 'Bare', knobs: [], efforts: [] }} testid="k" />);
  expect(host.textContent).toContain('Provider defaults');
  expect(host.querySelector('.mkn-head')).toBeNull();
});
