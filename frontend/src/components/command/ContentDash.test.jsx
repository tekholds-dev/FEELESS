import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { ContentDash } from './ProofTools';

// 📣 PoC creator flow: real clips from YouTube and Bluesky, a source switch, one tap writes the filing.
const D = { trends: { 'Hacker News': ['A long headline'] }, clips: [
  { src: 'youtube', text: 'Pirate token hunt', by: 'jmancurly', views: 9111, likes: null, thumb: 't1', url: 'https://www.youtube.com/watch?v=qdo5oCHDJnM' },
  { src: 'bluesky', text: 'Salzburg', by: 'a.bsky.social', likes: 282, reposts: 37, thumb: 't2', url: 'https://bsky.app/profile/a/post/1' }] };

async function mount(onCommand) {
  const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box);
  await act(async () => root.render(<ContentDash d={D} onCommand={onCommand} />));
  return box;
}

test('youtube shows views and no fake like count; bluesky shows likes', async () => {
  const box = await mount(() => {}); const text = box.textContent;
  expect(text).toContain('▶ 9.1K'); expect(text).not.toContain('♥ 0'); expect(text).toContain('♥ 282'); expect(text).toContain('jmancurly · YouTube');
});

test('the source switch filters clips and Write the angle files it in the chat box', async () => {
  const said = []; const box = await mount(t => said.push(t)); const q = id => box.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('ptl-csrc-bluesky').click(); });
  expect(box.textContent).not.toContain('Pirate token hunt');
  await act(async () => { q('ptl-clip-go-0').click(); });
  expect(said[0]).toMatch(/^file a poc on the angle behind this trending clip: "Salzburg"/);
});
