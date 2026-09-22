import fs from 'fs';
import path from 'path';

const css = fs.readFileSync(path.join(__dirname, 'terminal.css'), 'utf8');

function hexRgb(hex) {
  const value = hex.replace('#', '');
  const expanded = value.length === 3 ? value.split('').map(char => char + char).join('') : value;
  return [0, 2, 4].map(index => parseInt(expanded.slice(index, index + 2), 16) / 255);
}

function luminance(hex) {
  return hexRgb(hex).map(channel => channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4)
    .reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index], 0);
}

function contrast(foreground, background) {
  const lighter = Math.max(luminance(foreground), luminance(background));
  const darker = Math.min(luminance(foreground), luminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

test('defines a daylight black and green hierarchy with readable contrast', () => {
  expect(contrast('#10251a', '#ffffff')).toBeGreaterThanOrEqual(12);
  expect(contrast('#40654f', '#ffffff')).toBeGreaterThanOrEqual(5);
  expect(contrast('#08764e', '#ffffff')).toBeGreaterThanOrEqual(4.5);
  expect(contrast('#07583c', '#d8f4e3')).toBeGreaterThanOrEqual(4.5);
  expect(contrast('#07583c', '#ffffff')).toBeGreaterThanOrEqual(7);
  expect(contrast('#805b00', '#fff8e1')).toBeGreaterThanOrEqual(4.5);
});

test('keeps the daylight layer scoped and covers shared surfaces and focus states', () => {
  expect(css).toContain('body.theme-day{');
  expect(css).toContain('--day-ink:#10251a');
  expect(css).toContain('--day-muted:#40654f');
  expect(css).toContain('--day-green:#08764e');
  expect(css).toContain('body.theme-day .feeless-dialog');
  expect(css).toContain('body.theme-day .globe-webgl-fallback');
  expect(css).toContain('.globe-terminal-cta');
  expect(css).toContain('body.theme-day .globe-terminal-cta');
  expect(css).toContain('body.theme-day button:focus-visible');
  expect(css).toContain('body.theme-day .market-error');
});

test('preserves the existing night palette outside the daylight scope', () => {
  expect(css).toContain(':root{--mint:#00e9a0;--mint-bright:#20ffb4;--ink:#070c0b');
  expect(css).toContain('.terminal-header{height:82px');
  expect(css).toContain('background:#070d0b');
});