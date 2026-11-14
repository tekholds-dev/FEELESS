import React, { useState } from 'react';
import PocPlay from '../components/command/PocPlay';
import WeekBoard from '../components/command/WeekBoard';
import WEEKS from './weekFixture.json';   // the 3 week plans OSSY + G4 really wrote for GLINT and filed as PoCs, 2026-11-14

// 🧪 DEV ONLY (`/dev/play`, never in a production build): the POC-PLAY playground on a local picture. ?video = a local clip,
// ?day = the day theme. ?week = the Week board on the real GLINT plans (Save only answers here). Save here only proves the hand-off (it keeps the PNG on this page); the real Save files into a proof.
export default function PlayHarness() {
  const q = new URLSearchParams(window.location.search); if (q.has('day')) document.body.classList.add('theme-day');
  const [saved, setSaved] = useState(null); const [open, setOpen] = useState(true);
  const media = [{ id: 'a', kind: 'image', url: '/agent-demo/a4.jpg', label: 'Shot A' }, { id: 'b', kind: 'image', url: '/assets/feeless-logo-256.png', label: 'Logo' }];
  if (q.has('week')) return <main style={{ padding: 16, maxWidth: 1180 }}><WeekBoard cat={{ id: 'dev' }} wsId="dev" pocs={WEEKS} media={[]} work={async (_c, x) => (x.op === 'week_save' ? { pocFolders: WEEKS.map(f => (f.id === x.job ? { ...f, week: { ...f.week, ...x.cap, edited: 1 } } : f)) } : { ok: true })} /></main>;
  return <main style={{ padding: 16 }}>
    {open ? <PocPlay src={q.has('video') ? '/backdrops/creek.mp4' : '/agent-demo/t1.jpg'} kind={q.has('video') ? 'video' : 'image'} from="mdev" title="Dev picture" media={media}
      onSave={async (url, frame) => { setSaved({ frame, kb: Math.round(url.length * 0.75 / 1024) }); }} onClose={() => setOpen(false)} />
      : <button type="button" className="m-btn" onClick={() => setOpen(true)}>Open playground</button>}
    {saved ? <p data-testid="dev-saved">saved {saved.frame} · {saved.kb} KB</p> : null}
  </main>;
}
