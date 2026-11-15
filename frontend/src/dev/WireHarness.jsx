import React, { useState } from 'react';
import '../index.css';
import { MediaButton, MediaCard } from '../components/command/MediaStudio';

// 🧪 /dev/wire — a finished PoC picture on a fixture proof, so the 🧩 Wireframe board opens on real Excalidraw. Save adds a version locally (no server).
// ?swap — the composer's 🎭 Swap into a clip panel on fixtures (the character + one clip; fal.ai "linked"); nothing reaches a provider.
const MD = { id: 'm1', kind: 'image', status: 'done', url: '/kits/remotion.webp', label: 'Launch poster', prompt: 'A neon cat poster for the FEECAT launch week', provider: 'openrouter', at: Date.now() / 1000 };
const CLIP = { id: 'mclip', kind: 'video', status: 'done', clip: true, label: 'Dance trend', secs: 9.6, fps: 30, provider: 'upload', at: Date.now() / 1000 };
const SWAP = [{ id: 'fal-wan-replace', label: 'Wan 2.2 Animate · Replace', why: 'Swaps the person in your clip for the character: same scene, camera, light and moves', rate: 0.06, by: 'frames', ready: true },
  { id: 'fal-kling3-motion', label: 'Kling 3.0 Motion Control', why: "The character does your clip's exact moves, in the character picture's own scene", rate: 0.126, by: 'seconds', ready: true }];
const PROV = { fal: { name: 'fal.ai' }, replicate: { name: 'Replicate' }, openrouter: { name: 'OpenRouter' } };
export default function WireHarness() {
  const swap = window.location.search.includes('swap');
  const [doc, setDoc] = useState({ id: 'j1', messages: [{ by: 'Fee', media: MD }], ...(swap ? { character: { mid: 'm1', url: MD.url } } : {}) });
  const work = async (_id, body) => (body.op === 'media_models' ? { models: [], linked: ['fal'], pick: {}, providers: PROV, presets: [], swap: SWAP, swapMaxS: 15 }
    : { doc: { ...doc, messages: [...doc.messages, { by: 'Fee', text: `Saved a ${body.tools?.template} version (${Math.round(String(body.text).length / 1024)} KB).` }] } });
  if (swap) return <main style={{ padding: 16, maxWidth: 560 }}><MediaButton cat={{ id: 'c1' }} row={{ id: 'w1' }} work={work} doc={{ ...doc, messages: [...doc.messages, { by: 'You', media: CLIP }] }} setDoc={setDoc} /></main>;
  return <main style={{ padding: 16, maxWidth: 520 }}>
    {doc.messages.map((m, i) => m.media ? <MediaCard key={i} m={m} cat={{ id: 'c1' }} doc={doc} work={work} setDoc={setDoc} /> : <p key={i} data-testid="wire-saved">{m.text}</p>)}
  </main>;
}
