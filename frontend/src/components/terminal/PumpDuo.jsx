import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DuoFloor } from './DuoFloor';
import { ChatRoom } from './CommunityRail';
import { useWorkspace } from '../../hooks/useWorkspace';

// 💊📱📱 PUMP RADAR on a Duo / fold / sideways phone (owner 2026-10-28): the radar is a full-screen split app — the coin you picked charted on one
// half (Quick trade · Dip / Rip · tape · its chat), the LAUNCHES dock on the other (the live intake + NEW · HOT · RUNNERS, tap = the chart, in
// place). Same Duo app as the Trenches floor (DuoFloor mode="pump"), its own dock, backdrop and saved tab.
export function PumpDuo({ newFeed, trendingFeed, wide }) {
  const nav = useNavigate(); const { selectPair } = useWorkspace();
  const pairs = trendingFeed?.data?.pairs || []; const newPairs = newFeed?.data?.pairs || [];
  const [pick, setPick] = useState(null);
  const pair = pick || pairs[0] || newPairs[0] || null;
  if (!pair) return null;
  return <DuoFloor mode="pump" pair={pair} pairs={pairs} newPairs={newPairs} wide={wide} onPick={p => { setPick(p); selectPair?.(p); }} onBack={() => nav('/terminal')}
    chat={<ChatRoom large pairs={pairs} newPairs={newPairs} selectedPair={pair} />} />;
}
