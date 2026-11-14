import fs from 'fs';
import path from 'path';

// STYLE-1: colours live in the sheet's page-token palette (`:root{/* page tokens (STYLE-1) */--T0:#hex;…}`); read the sheet with them resolved
const raw = fs.readFileSync(path.join(__dirname, 'terminal.css'), 'utf8');
const pal = Object.fromEntries([...((raw.match(/:root\s*\{\s*\/\* page tokens \(STYLE-1\) \*\/[^}]*\}/) || [''])[0]).matchAll(/(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})/g)].map(m => [m[1], m[2]]));
const css = raw.replace(/var\((--[\w-]+)\)/g, (m, k) => pal[k] || m);

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
  expect(contrast('#4d5853', '#ffffff')).toBeGreaterThanOrEqual(5);
  expect(contrast('#414b47', '#ffffff')).toBeGreaterThanOrEqual(7);   // the muted ink that actually paints
  expect(contrast('#121715', '#ffffff')).toBeGreaterThanOrEqual(7);   // 🟢 2026-10-23 official-green sweep: neutral ink, no grey-green
  expect(contrast('#08764e', '#ffffff')).toBeGreaterThanOrEqual(4.5);
  expect(contrast('#07583c', '#d8f4e3')).toBeGreaterThanOrEqual(4.5);
  expect(contrast('#07583c', '#ffffff')).toBeGreaterThanOrEqual(7);
  expect(contrast('#805b00', '#fff8e1')).toBeGreaterThanOrEqual(4.5);
});

test('keeps the daylight layer scoped and covers shared surfaces and focus states', () => {
  expect(css).toContain('body.theme-day{');
  // the values the page paints: terminal.css used to set these, then override them later in the sheet (STYLE-1 cut the dead first copies)
  expect(css).toContain('--day-ink:#121715');
  expect(css).toContain('--day-muted:#414b47');
  expect(css).toContain('--day-green:#08764e');
  expect(css).toContain('body.theme-day .feeless-dialog');
  expect(css).toContain('body.theme-day .globe-webgl-fallback');
  expect(css).toContain('.globe-terminal-cta');
  expect(css).toContain('body.theme-day .globe-terminal-cta');
  expect(css).toContain('body.theme-day button:focus-visible');
  expect(css).toContain('body.theme-day .market-error');
});

test('keeps the official night palette (PLASMA on deep space, owner 2026-11-11) outside the daylight scope', () => {
  expect(css).toContain(':root{--mint:#9b6bff;--mint-bright:#b48cff;--ink:#08051a');
  expect(css).toMatch(/\.terminal-header\{[^}]*height:64px!important/);   // what paints (an earlier 82px was always overridden)
  expect(css).toContain('background:#090b0a');   // the header: near-black, no green tint
});

test('keeps ambient backgrounds theme-aware and motion-safe', () => {
  const appCss = fs.readFileSync(path.join(__dirname, '..', 'App.css'), 'utf8');
  expect(appCss).toContain('.ambient-background');
  expect(appCss).toContain('body.theme-day .ambient-background');
  expect(appCss).toContain('body.reduced-motion-setting .ambient-background');
  expect(appCss).toContain('@media (prefers-reduced-motion: reduce)');
  expect(appCss).toContain('pointer-events: none');
  expect(appCss).toContain('width: clamp(220px, 32vw, 560px)');
});