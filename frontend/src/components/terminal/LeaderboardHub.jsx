import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useWallet } from '../../hooks/useWallet';
import { Season, useQuests } from '../QuestBoard';
import { Crews } from '../Crews';
import { FamiliaBackdrop, SCENES } from '../FamiliaBackdrop';

// One Leaderboard tab, four lenses (like Radar): Familia, season XP, callers, participation.
// ?lens= keeps the view in the URL so links land on the right board.
const LENSES = [['crews', '🌹 Familia'], ['season', '🏆 Season XP'], ['callers', '📣 Callers'], ['crew', '🫡 Participation']];   // MOB & Rewards: Familia first

export function LeaderboardHub({ callers, crew }) {   // ⚔ Trench wars lens removed (owner, 2026-10-21) — family wars live inside La Familia
  const [params, setParams] = useSearchParams();
  const { wallet } = useWallet() || {};
  const [me] = useQuests(wallet?.address);
  const lens = LENSES.some(([id]) => id === params.get('lens')) ? params.get('lens') : 'crews';
  const [scene, setScene] = useState('home');   // 🎬 Familia's tab → its own scene behind the whole page
  const fam = lens === 'crews';
  return <section className={`radar-page ${fam ? `is-familia s-${scene}` : ''}`} data-testid="leaderboard-hub">
    {fam ? <FamiliaBackdrop scene={scene} /> : null}
    <div className="radar-head"><div><span className="m-label">{fam ? 'LA FAMILIA' : 'LEADERBOARD'}</span>{fam ? <h1 key={scene}>{SCENES[scene]?.[0] || 'La Familia'}<small>{SCENES[scene]?.[1]}</small></h1> : <h1>Who's running the trenches.</h1>}</div>
      <div className="m-seg" role="tablist" aria-label="Leaderboard">{LENSES.map(([id, label]) => <button key={id} type="button" role="tab" aria-selected={lens === id} className={lens === id ? 'active' : ''} data-testid={`lb-${id}`} onClick={() => setParams({ lens: id })}>{label}</button>)}</div></div>
    {lens === 'season' ? <Season me={me} /> : lens === 'callers' ? callers : lens === 'crews' ? <Crews onScene={setScene} /> : crew}
  </section>;
}
