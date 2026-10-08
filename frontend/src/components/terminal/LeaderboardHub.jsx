import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { useWallet } from '../../hooks/useWallet';
import { Season, useQuests } from '../QuestBoard';
import { Crews } from '../Crews';

// One Leaderboard tab, five lenses (like Radar): season XP, callers, trench wars, crews, participation.
// ?lens= keeps the view in the URL so links land on the right board.
const LENSES = [['season', '🏆 Season XP'], ['callers', '📣 Callers'], ['wars', '⚔️ Trench wars'], ['crews', '🛡 Crews'], ['crew', '🫡 Participation']];

export function LeaderboardHub({ wars, callers, crew }) {
  const [params, setParams] = useSearchParams();
  const { wallet } = useWallet() || {};
  const [me] = useQuests(wallet?.address);
  const lens = LENSES.some(([id]) => id === params.get('lens')) ? params.get('lens') : 'season';
  return <section className="radar-page" data-testid="leaderboard-hub">
    <div className="radar-head"><div><span className="m-label">LEADERBOARD</span><h1>Who's running the trenches.</h1></div>
      <div className="m-seg" role="tablist" aria-label="Leaderboard">{LENSES.map(([id, label]) => <button key={id} type="button" role="tab" aria-selected={lens === id} className={lens === id ? 'active' : ''} data-testid={`lb-${id}`} onClick={() => setParams({ lens: id })}>{label}</button>)}</div></div>
    {lens === 'season' ? <Season me={me} /> : lens === 'callers' ? callers : lens === 'wars' ? wars : lens === 'crews' ? <Crews /> : crew}
  </section>;
}
