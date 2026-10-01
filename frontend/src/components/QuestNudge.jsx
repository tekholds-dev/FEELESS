import React from 'react';
import { Link } from 'react-router-dom';
import { useWallet } from '../hooks/useWallet';
import { useQuests } from './QuestBoard';

// One slim strip on busy tabs (Trenches): today's next unfinished quest, its progress and XP, one tap to Badges.
// Hidden when you're done for the day or not connected — never a nag.
export function QuestNudge({ prefer = ['trade', 'volume', 'call', 'case', 'chat', 'checkin'] }) {
  const { wallet } = useWallet() || {};
  const [d] = useQuests(wallet?.address);
  const tasks = d?.quests?.daily?.tasks || [];
  const q = prefer.map(id => tasks.find(t => t.id === id && !t.done)).find(Boolean);
  if (!q) return null;
  const left = tasks.filter(t => !t.done).length;
  return <Link to="/terminal/badges" className="quest-nudge" data-testid="quest-nudge">
    <span className="m-label">DAILY QUEST</span><b>{q.label}</b><small>{Math.min(q.have, q.target)}/{q.target}</small><em>+{q.xp} XP</em>
    <small className="m-dim">{left} left today · 🔥 {d.metrics?.streak || 0}</small></Link>;
}
