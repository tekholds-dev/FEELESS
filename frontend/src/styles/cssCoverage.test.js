// NEVER DEAD STYLE (owner, 2026-10-15: the Agents tab rendered as unstyled text twice — a "dead CSS" pass deleted 197 lines of agentDesk.css
// whose classes the components still used, and the Gens boxes had no rules at all). cssHygiene catches a rule nobody uses; THIS catches a
// class a component uses that no stylesheet defines. Every Agents / HQ cockpit component is checked; a wrapper styled only through its
// children goes in WRAPPERS with a reason.
const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, '..');
const walk = d => fs.readdirSync(d, { withFileTypes: true }).flatMap(e => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const css = walk(SRC).filter(f => f.endsWith('.css')).map(f => fs.readFileSync(f, 'utf8')).join('\n');
const defined = new Set([...css.matchAll(/\.(-?[A-Za-z_][\w-]*)/g)].map(m => m[1]));

const FILES = ['AgentDesk', 'AgentCockpit', 'AgentScreens', 'LifeLens', 'OfficeBoard', 'OfficeEdge', 'CockpitControls', 'SeatOps', 'CoachTape',
  'IntakeBand', 'VitalBoard', 'AiChat', 'AiDecisions', 'TeachBox', 'MySeat', 'KernelBoard'].map(n => path.join(SRC, 'components', 'command', `${n}.jsx`)).filter(f => fs.existsSync(f));
const WRAPPERS = new Set(['agd-ctl', 'agd-log', 'oed-launch', 'oed-missed', 'oed-review', 'tch-k']);   // hooks for tests / children-styled wrappers

const classesOf = src => {
  const out = new Set();
  for (const m of src.matchAll(/className=(?:"([^"]+)"|\{`([^`]+)`\})/g)) {
    (m[1] || m[2]).replace(/\$\{[^}]*\}/g, ' ').split(/\s+/).filter(w => /^[a-z][\w-]*[a-z0-9]$/i.test(w) && !w.startsWith('is-')).forEach(w => out.add(w));
  }
  return out;
};

test.each(FILES.map(f => [path.basename(f), f]))('%s: every class it renders has a style', (_name, file) => {
  const missing = [...classesOf(fs.readFileSync(file, 'utf8'))].filter(c => !defined.has(c) && !WRAPPERS.has(c));
  expect(missing).toEqual([]);
});
