import React, { useState } from 'react';
import '../index.css';
import { MediaCard } from '../components/command/MediaStudio';

// 🧪 /dev/wire — a finished PoC picture on a fixture proof, so the 🧩 Wireframe board opens on real Excalidraw. Save adds a version locally (no server).
const MD = { id: 'm1', kind: 'image', status: 'done', url: '/kits/remotion.webp', label: 'Launch poster', prompt: 'A neon cat poster for the FEECAT launch week', provider: 'openrouter', at: Date.now() / 1000 };
export default function WireHarness() {
  const [doc, setDoc] = useState({ id: 'j1', messages: [{ by: 'Fee', media: MD }] });
  const work = async (_id, body) => ({ doc: { ...doc, messages: [...doc.messages, { by: 'Fee', text: `Saved a ${body.tools?.template} version (${Math.round(String(body.text).length / 1024)} KB).` }] } });
  return <main style={{ padding: 16, maxWidth: 520 }}>
    {doc.messages.map((m, i) => m.media ? <MediaCard key={i} m={m} cat={{ id: 'c1' }} doc={doc} work={work} setDoc={setDoc} /> : <p key={i} data-testid="wire-saved">{m.text}</p>)}
  </main>;
}
