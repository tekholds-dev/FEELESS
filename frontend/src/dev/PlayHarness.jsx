import React, { useState } from 'react';
import PocPlay from '../components/command/PocPlay';

// 🧪 DEV ONLY (`/dev/play`, never in a production build): the POC-PLAY playground on a local picture. ?video = a local clip,
// ?day = the day theme. Save here only proves the hand-off (it keeps the PNG on this page); the real Save files into a proof.
export default function PlayHarness() {
  const q = new URLSearchParams(window.location.search); if (q.has('day')) document.body.classList.add('theme-day');
  const [saved, setSaved] = useState(null); const [open, setOpen] = useState(true);
  const media = [{ id: 'a', kind: 'image', url: '/agent-demo/a4.jpg', label: 'Shot A' }, { id: 'b', kind: 'image', url: '/assets/feeless-logo-256.png', label: 'Logo' }];
  return <main style={{ padding: 16 }}>
    {open ? <PocPlay src={q.has('video') ? '/backdrops/creek.mp4' : '/agent-demo/t1.jpg'} kind={q.has('video') ? 'video' : 'image'} from="mdev" title="Dev picture" media={media}
      onSave={async (url, frame) => { setSaved({ frame, kb: Math.round(url.length * 0.75 / 1024) }); }} onClose={() => setOpen(false)} />
      : <button type="button" className="m-btn" onClick={() => setOpen(true)}>Open playground</button>}
    {saved ? <p data-testid="dev-saved">saved {saved.frame} · {saved.kb} KB</p> : null}
  </main>;
}
