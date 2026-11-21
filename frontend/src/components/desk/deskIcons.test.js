import fs from 'fs';
import path from 'path';
import { AGENT_RAIL, LOG_DRAWERS, DRAWER_ICON } from '../command/CatWorkbench';
import { FEE_RAIL_ICON, FEE_DRAWER_ICON } from '../command/FeeDeskLook';

// 🧊 Slice 34 icon audit: on every desk, each rail item and each cabinet drawer wears its OWN real 3D icon (no two share one), and every
// icon is a real file we serve (a missing name would fall back to an emoji). The agent desk's key drawers (creds, api) are DRAWER_ICON.
const has = n => fs.existsSync(path.join(__dirname, '../../../public/icons3d', `${n}.webp`));
const dupes = xs => xs.filter((x, i) => xs.indexOf(x) !== i);

test('the agent desk: rail + every drawer, one icon each, all real', () => {
  const rail = AGENT_RAIL.filter(r => r.length > 1).map(r => r[3]);
  const drawers = [...LOG_DRAWERS.map(r => r[3]), ...Object.values(DRAWER_ICON)];
  const all = [...rail, ...drawers];
  expect(dupes(all)).toEqual([]);
  expect(all.filter(n => !n || !has(n))).toEqual([]);
});

test("Fee's desk: rail folders + drawers, one icon each, all real", () => {
  const rail = ['computer', 'folder-new', 'target', 'chat-bubble', ...Object.values(FEE_RAIL_ICON)];   // desk, whole desktop, living print, agent prompts
  const all = [...rail, ...Object.values(FEE_DRAWER_ICON)];
  expect(dupes(all)).toEqual([]);
  expect(all.filter(n => !has(n))).toEqual([]);
});
