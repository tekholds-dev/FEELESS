import React, { useState } from 'react';
import { EarnBoard, EarnFiling } from '../components/command/EarnDesk';
import FIX from './ecoEarnFixture.json';   // 💼 Slice 16: Happy's real TEST earn run (2026-11-20): its board as read from the public feeds + the filed earn PoEco, as feecats.json holds them
import '../styles/ecoFolder.css';

// 🧪 DEV ONLY (`/dev/ecoearn`, never in a production build): PoEco's earn board and filing on Happy's REAL TEST run. Every tap is answered here
// (the page has no owner sign-in), so nothing reaches the server and nothing is sent: an approve here moves the stage in this page only.
// ?filing opens the filing first · ?approved shows it after the owner's approve · ?day = day theme.
export default function EcoEarnHarness() {
  const q = window.location.search; if (/day/.test(q)) document.body.classList.add('theme-day');
  const [f, setF] = useState(/approved/.test(q) ? { ...FIX.folder, stage: 'bid_approved', stages: [...FIX.folder.stages, { stage: 'bid_approved', by: 'owner', at: FIX.folder.at + 60 }] } : FIX.folder);
  const [open, setOpen] = useState(/filing|approved/.test(q)); const [log, setLog] = useState([]);
  const act = async b => { setLog(l => [...l, JSON.stringify(b)].slice(-4)); if (b.op === 'earn_go') setF(x => ({ ...x, stage: b.tools.stage, stages: [...x.stages, { stage: b.tools.stage, by: 'owner', at: Math.round(Date.now() / 1000) }] })); };
  return <div className="eco-prf" style={{ padding: 16, maxWidth: 1180, margin: '0 auto', display: 'grid', gap: 12 }} data-testid="ecoearn-harness">
    <small className="m-label">HARNESS · Happy’s real TEST earn run · PoEco #{FIX.folder.n} {FIX.folder.id} · board read {new Date(FIX.view.board.at * 1000).toISOString().slice(0, 16)}Z · nothing reaches the server here</small>
    {open ? <EarnFiling f={f} onBack={() => setOpen(false)} busy={false} act={act} /> : <EarnBoard v={FIX.view} busy={false} onFind={() => setLog(l => [...l, 'earn_find (harness: not sent)'])} onBid={() => setOpen(true)} />}
    <pre style={{ fontSize: 11, opacity: 0.7, whiteSpace: 'pre-wrap' }} data-testid="harness-log">{log.join('\n')}</pre>
  </div>;
}
