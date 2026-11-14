import React, { useEffect, useState } from 'react';
import Duel from '../components/command/Duel';

// 🧪 DEV ONLY (`/dev/duel[?day]`, never in a production build): the AGX-4 duel with a sample two-mind answer, for look checks. A tap here files nothing.
const JOB = { id: 'dev', minds: [{ model: 'openrouter/claude-haiku-latest', answer: 'Buy $BONK on a dip: liquidity up 2x in 24h, 40% of supply with the top 10 is normal for its age. Starter size, stop at -25%.' },
  { model: 'local/glm-5.3-flash', answer: 'Skip $BONK for now — the dev wallet sold 12% today and liquidity is thin under 90k. Wait for a reclaim of 0.000021.' }] };
export default function DuelHarness() {
  const [pick, setPick] = useState(); const q = new URLSearchParams(window.location.search);
  useEffect(() => { if (q.has('day')) document.body.classList.add('theme-day'); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  return <div style={{ minHeight: '100vh', padding: 16, background: 'var(--m-bg)' }}><Duel job={JOB} pick={pick} onPick={async i => setPick(i)} /></div>;
}
