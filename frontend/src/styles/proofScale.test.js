// 🔎 NOTHING BIG IN ANY PROOF TYPE (owner 2026-11-20 night, screenshots: "everything in every proof type is big asf"). Slice 34 puts every proof
// folder, filing and workspace on the Desk look's scale: body 12.5–13 px, labels 10.5 px caps, numbers 15–17 px mono, titles ≤ 14 px, and NO font
// over 19 px. Every font / font-size in every proof sheet is read here (px, rem and each end of a clamp()), so a big number can't creep back in.
const fs = require('fs');
const path = require('path');

const SHEETS = ['ecoFolder.css', 'eco.css', 'ecoDesk.css', 'pobDash.css', 'pocBoard.css', 'pocDash.css', 'pocEditor.css', 'pocStudio.css', 'pocWatch.css', 'popDash.css',
  'popDesk.css', 'powDash.css', 'proofDrawer.css', 'proofFile.css', 'proofKit.css', 'proofLive.css', 'proofRooms.css', 'proofTools.css', 'proofVisuals.css', 'proofWorkspace.css',
  'proofsFolder.css', 'psInspect.css', 'startWizard.css', 'stashBrain.css', 'trackRecord.css', 'trueRecord.css', 'clipFarm.css', 'proofPicker.css',
  'earnDesk.css', 'earnStake.css', 'earnTicker.css', 'gitFolder.css', 'comp2.css', 'compDash.css', 'compExplain.css', 'compGrow.css', 'compVoice.css', 'compWatch.css'];
// a monitor's own content, not page type: the hub number is SVG text in viewBox units (it scales with its ring)
const ALLOW = [/\.ppk-hub/];
const MAX = 19;

function oversized(css) {
  const out = [];
  const flat = css.replace(/\/\*[\s\S]*?\*\//g, '');
  for (const [, sel, body] of flat.matchAll(/([^{}]*)\{([^{}]*)\}/g)) {
    if (ALLOW.some(r => r.test(sel))) continue;
    for (const [, val] of body.matchAll(/font(?:-size)?\s*:\s*([^;}]*)/g)) {
      const px = [...val.matchAll(/(?<![\w.-])(\d+(?:\.\d+)?)px/g)].map(m => Number(m[1]));
      const rem = [...val.matchAll(/(\d+(?:\.\d+)?)rem/g)].map(m => Number(m[1]) * 16);
      const big = [...px, ...rem].filter(v => v > MAX);
      if (big.length) out.push(`${sel.trim().slice(-60)} → ${big.join(', ')}px`);
    }
  }
  return out;
}

test.each(SHEETS)('%s keeps every font at 19 px or under', f => {
  expect(oversized(fs.readFileSync(path.join(__dirname, f), 'utf8'))).toEqual([]);
});

test('the check itself finds a big number, a big clamp end and a big rem', () => {
  expect(oversized('.a b { font: 800 30px var(--f-mono); } .b { font-size: clamp(14px, 2vw, 26px); } .c { font-size: 1.5rem; } .ok { font: 600 17px/1.2 x; }')).toHaveLength(3);
});

test('a filing scrolls inside its own pane: a child never shrinks to fit (PoC #14 was cut off at the bottom)', () => {
  const css = fs.readFileSync(path.join(__dirname, 'proofWorkspace.css'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  expect(css).toMatch(/\.pws-work-in\s*{[^}]*overflow:\s*auto/);
  expect(css).toMatch(/\.pws-work-in > \*\s*{[^}]*flex:\s*1 0 auto/);
  expect(css).toMatch(/\.pws-pane-in\s*{[^}]*overflow:\s*auto/);
});
