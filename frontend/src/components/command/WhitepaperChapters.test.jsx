import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { WhitepaperChapters, poolLoss, shelfOf, splitChapter } from './WhitepaperChapters';

jest.mock('../../hooks/useMarket', () => ({ useMarket: () => ({ data: null }) }));
jest.mock('motion/react', () => { const R = require('react'); const passthrough = new Proxy({}, { get: (_, tag) => ({ initial, animate, whileInView, viewport, transition, onViewportEnter, ...p }) => R.createElement(tag, p) }); return { motion: passthrough, useInView: () => false, useScroll: () => ({ scrollYProgress: 0 }), useSpring: v => v, AnimatePresence: ({ children }) => children }; });

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

test('every chapter is open with every word, and the risks are always there', async () => {
  const el = await mount(); const q = t => el.querySelector(`[data-testid="${t}"]`);
  expect(q('whitepaper-chapter-1').textContent).toContain('It costs $60 in fees.'); expect(q('whitepaper-chapter-2').tagName).toBe('SECTION'); expect(q('whitepaper-chapter-3').textContent.length).toBeGreaterThan(5);
  expect(q('wpc-risk-line').textContent).toContain('lose all its value'); expect(el.querySelector('details')).toBeNull();
});

test('a pool position loses by the real maths', () => {
  expect(poolLoss(0)).toBeCloseTo(0); expect(poolLoss(-50)).toBeCloseTo(-0.0572, 3); expect(poolLoss(100)).toBeCloseTo(-0.0572, 3);
});
