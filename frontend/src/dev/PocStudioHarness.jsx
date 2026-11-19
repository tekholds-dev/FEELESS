import React, { useState } from 'react';
import PocStudio from '../components/command/PocStudio';
import REAL from './pocStudioFixture.json';   // 🎬 Slice 5: Sicario's real TEST PoC (its filed folder, as feecats.json holds it), 2026-11-18
import '../styles/features.css';

// 🧪 DEV ONLY (`/dev/pocstudio`, never in a production build): the PoC content studio on Sicario's REAL filed TEST PoC, its real files served by
// the backend. `work` here is a fake: nothing reaches the server, so nothing can ever post from this page. ?posted shows the after-approve
// state (reads at 24 h / 7 d) on the same folder, clearly marked as a fixture. ?day = day theme.
const SVCS = [{ id: 'uploadpost', name: 'Upload-Post', site: 'https://upload-post.com', keys: '', how: 'Upload-Post › API keys.', platforms: ['x', 'tiktok', 'youtube', 'instagram', 'bluesky', 'threads', 'linkedin'], thread: true, saved: true },
  { id: 'zernio', name: 'Zernio', site: 'https://zernio.com', keys: '', how: 'Zernio › Settings › API keys.', platforms: ['x', 'tiktok', 'youtube', 'instagram', 'bluesky', 'threads', 'linkedin', 'facebook'], thread: false, saved: false },
  { id: 'ayrshare', name: 'Ayrshare', site: 'https://ayrshare.com', keys: '', how: 'Ayrshare › API Key.', platforms: ['x', 'tiktok', 'youtube', 'instagram', 'bluesky', 'threads', 'linkedin', 'facebook'], thread: true, saved: false }];
const POSTED = { svc: 'uploadpost', approvedBy: 'owner', approvedAt: 1, at: 1, sent: 2, platforms: { tiktok: { ok: true, piece: 'video', url: 'https://www.tiktok.com/' }, x: { ok: true, piece: 'image', url: 'https://x.com/' } } };
const READS = { reads: [{ key: 'h24', label: '24 h', views: 1840, engagement: 61, grade: { verdict: 'on pace', cpm: 0 } }], last: { key: 'h24', views: 1840, engagement: 61, grade: { verdict: 'on pace', cpm: 0 } } };

export default function PocStudioHarness() {
  const q = window.location.search; if (/day/.test(q)) document.body.classList.add('theme-day');
  const [f, setF] = useState(/posted/.test(q) ? { ...REAL, posted: POSTED, reach: READS } : REAL); const [log, setLog] = useState([]);
  const work = async (_id, body) => {
    setLog(l => [...l, body].slice(-4));
    if (body.op === 'poc_accounts') return body.tools?.svc ? { accounts: [{ platform: 'tiktok', name: 'fixture' }, { platform: 'x', name: 'fixture' }] } : { services: SVCS };
    if (body.op === 'poc_goal') { const n = { ...f, studio: { ...f.studio, goal: { ...f.studio.goal, type: body.tools.type, target: body.tools.target, by: 'owner' } } }; setF(n); return { pocFolders: [n] }; }
    throw new Error('Harness only: nothing posts from this page.');
  };
  return <div style={{ padding: 16, maxWidth: 1180, margin: '0 auto', display: 'grid', gap: 10 }} data-testid="pocstudio-harness">
    <small className="m-label">HARNESS · Sicario’s real TEST PoC #{REAL.n} ({REAL.id}) · nothing reaches the server here</small>
    <PocStudio cat={{ id: 'sicario' }} f={f} work={work} onFolders={rows => rows[0] && setF(rows[0])} />
    <pre style={{ fontSize: 11, opacity: 0.7, whiteSpace: 'pre-wrap' }} data-testid="harness-log">{log.map(x => JSON.stringify(x)).join('\n')}</pre>
  </div>;
}
