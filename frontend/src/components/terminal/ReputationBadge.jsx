import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, ShieldQuestion, ShieldAlert, Shield } from 'lucide-react';
import { useReputation, BADGE_LABEL } from '../../lib/reputation';

const ICON = { trusted: ShieldCheck, building: Shield, unproven: ShieldQuestion, flagged: ShieldAlert };

export const ReputationBadge = ({ pair, compact = false }) => {
  const rep = useReputation(pair);
  const navigate = useNavigate();
  if (!rep || rep.creator === null || rep.score == null) {
    return compact ? null : <span className="reputation-badge badge-unknown" title="Creator identity unavailable for this chain or mint."><ShieldQuestion size={11} />Unrated</span>;
  }
  const Icon = ICON[rep.badge] || Shield;
  const label = BADGE_LABEL[rep.badge] || 'Unrated';
  const clones = rep.cloneCount || 0;
  const detail = `${label} · ${rep.tokenCount} token${rep.tokenCount === 1 ? '' : 's'} tracked · ${rep.ruggedCount} flagged${clones ? ` · ${clones} same-ticker relaunches` : ''} · score ${rep.score}/100`;
  const openCreator = event => { event.stopPropagation(); event.preventDefault(); if (rep.creator) navigate(`/terminal/reputation/${pair.chainId}/${rep.creator}`); };
  const badge = <span className={`reputation-badge badge-${rep.badge} is-link`} title={`${detail} · click for the creator's full profile`} data-testid="reputation-badge" role="link" tabIndex={0} onClick={openCreator} onKeyDown={e => e.key === 'Enter' && openCreator(e)}><Icon size={11} />{compact ? rep.score : label}</span>;
  if (clones < 2) return badge;
  return <span className="reputation-badge-group">{badge}<span className="clone-chip" title="This creator keeps relaunching the same ticker — a clone-spam pattern. Check the exact contract.">⚠ {clones} clones</span></span>;
};
