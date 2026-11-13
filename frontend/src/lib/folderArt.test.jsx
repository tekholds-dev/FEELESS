import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { FolderArt, folderGlyph } from './folderArt';
import { DESK_DEFAULTS, FOLDER_LOOKS } from '../components/command/DeskShell';
import { FOLD_INTO } from '../components/command/CatWorkbench';

const paint = async el => { const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box); await act(async () => root.render(el)); return { box, done: () => act(() => root.unmount()) }; };

test('📁 a folder carries the classic line icon AND the outline drawing; the proof folders light their LED', async () => {
  const { box, done } = await paint(<><FolderArt k="pow" /><FolderArt k="wallet" /><FolderArt ic="👎" file /></>);
  expect(box.querySelectorAll('.fa-cl svg')).toHaveLength(3);
  expect(box.querySelectorAll('svg.fa')).toHaveLength(3);
  expect(box.querySelectorAll('.fa-led')).toHaveLength(1);   // pow only
  expect(box.querySelector('.fa-file .lucide-thumbs-down')).not.toBeNull();
  done();
});

test('📁 every desk folder key gets its own line icon, an unknown one falls back to a plain folder', () => {
  expect(folderGlyph('pow')).not.toBe(folderGlyph('pop'));
  expect(folderGlyph('nope', '')).toBe(folderGlyph('nope2', ''));
});

test('⚙ Folder look: classic by default, four looks (Night added 2026-11-13); 📺 Watch is its own desk folder again', () => {
  expect(DESK_DEFAULTS.folderLook).toBe('classic');
  expect(FOLDER_LOOKS.map(r => r[0])).toEqual(['classic', 'outline', 'mono', 'night']);
  expect(FOLD_INTO.watch).toBeUndefined();
});
