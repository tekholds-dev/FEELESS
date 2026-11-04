import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { WhitepaperChapters, shelfOf, splitChapter } from './WhitepaperChapters';

jest.mock('./FeeBack', () => ({ FeeBackFlow: () => null }));
jest.mock('./FeeCommand', () => ({ Tokenomics: () => null }));
global.IS_REACT_ACT_ENVIRONMENT = true;
const TEXT = 'FEELESS never signs. It costs $60 in fees. Fee-Back is not yield.';
const CH = [{ id: 'c1', number: 1, title: 'Executive Summary', text: TEXT }, { id: 'c2', number: 2, title: 'FUSE Cards', text: 'Cards hold coins. Fees stay apart.' }, { id: 'c3', number: 3, title: 'Risk Factors', text: 'Cryptoassets can lose all value. Markets fail.' }, { id: 'c4', number: 4, title: 'A New Chapter', text: 'Nobody placed it.' }];
async function mount() { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<WhitepaperChapters chapters={CH} />); }); return el; }

test('splitting a chapter keeps every word', () => {
  const { lead, points } = splitChapter(TEXT);
  expect(lead).toBe('FEELESS never signs.');
  expect([lead, ...points].join(' ')).toBe(TEXT);
});

test('a chapter nobody placed still shows', () => {
  expect(shelfOf('A New Chapter')).toBe('start');
  expect(shelfOf('Risk Factors')).toBe('risk');
});

test('shelves show their chapters, the risk line is on every shelf, and risks are never folded', async () => {
  const el = await mount(); const q = t => el.querySelector(`[data-testid="${t}"]`);
  expect(q('whitepaper-chapter-1').textContent).toContain('It costs $60 in fees.');
  expect(q('whitepaper-chapter-4')).not.toBeNull(); expect(q('whitepaper-chapter-2')).toBeNull();
  expect(q('wpc-risk-line').textContent).toContain('lose all its value');
  await act(async () => { q('wpc-shelf-product').click(); });
  expect(q('whitepaper-chapter-2').tagName).toBe('DETAILS'); expect(q('wpc-risk-line')).not.toBeNull();
  await act(async () => { q('wpc-risk-line').querySelector('button').click(); });
  expect(q('whitepaper-chapter-3').tagName).toBe('SECTION'); expect(q('whitepaper-chapter-3').textContent).toContain('Markets fail.');
  expect(q('wpc-shelf-risk').getAttribute('aria-checked')).toBe('true');
});
