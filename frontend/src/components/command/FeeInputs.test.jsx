import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { TradePreview, UnitInput } from './FeeInputs';

const mount = ui => { const host = document.createElement('div'); document.body.appendChild(host); act(() => createRoot(host).render(ui)); return host; };

test('per-trade preview: what you earn and what the trader pays, in dollars', () => {
  const host = mount(<TradePreview feeBps={150} tipLamports={200000} solUsd={100} />);
  const cells = [...host.querySelectorAll('.tp-rows span')].map(s => s.textContent);
  expect(cells[0]).toContain('$1.50'); // 1 SOL = $100 → 1.5%
  expect(cells[0]).toContain('1.50%');
  expect(host.querySelector('.tp-rows .total').textContent).toContain('$1.52'); // 1.50 + 0.02 tip + 0.0005 network
});

test('number box shows commas and the chip switches SOL ↔ USD on click', () => {
  const onChange = jest.fn();
  const host = mount(<UnitInput value="70000000" onChange={onChange} suffix={['= 0.07 SOL', '= $7.00']} />);
  expect(host.querySelector('input').value).toBe('70,000,000');
  const chip = host.querySelector('.unit-chip');
  expect(chip.textContent).toContain('0.07 SOL');
  act(() => chip.click());
  expect(chip.textContent).toContain('$7.00');
});

test('fee table: your cut on $1 / $10 / $100 / $1000, before and after holder discounts', () => {
  const { FeeTable } = require('./FeeInputs');
  const host = mount(<FeeTable feeBps={500} discounts={{ 1: 1, 2: 10, 3: 20 }} />);
  const rows = [...host.querySelectorAll('tbody tr')].map(r => [...r.children].map(td => td.textContent));
  expect(rows[0]).toEqual(['$1', '5.0¢', '5.0¢', '4.5¢', '4.0¢']);
  expect(rows[3]).toEqual(['$1,000', '$50.00', '$49.50', '$45.00', '$40.00']);
});
