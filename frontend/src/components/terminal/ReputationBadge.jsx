import React from 'react';
import { ShieldCheck, ShieldQuestion, ShieldAlert, Shield } from 'lucide-react';
import { useReputation, BADGE_LABEL } from '../../lib/reputation';

const ICON = { trusted: ShieldCheck, building: Shield, unproven: ShieldQuestion, flagged: ShieldAlert };

export const ReputationBadge = ({ pair, compact = false }) => {
  const rep = useReputation(pair);
  if (!rep || rep.creator === null || rep.score == null) {
    return compact ? null : <span className="reputation-badge badge-unknown" title="Creator identity unavailable for this chain or mint."><ShieldQuestion size={11} />Unrated</span>;
  }
  const Icon = ICON[rep.badge] || Shield;
  const label = BADGE_LABEL[rep.badge] || 'Unrated';
  const detail = `${label} · ${rep.tokenCount} token${rep.tokenCount === 1 ? '' : 's'} tracked · ${rep.ruggedCount} flagged · score ${rep.score}/100`;
  return <span className={`reputation-badge badge-${rep.badge}`} title={detail} data-testid="reputation-badge"><Icon size={11} />{compact ? rep.score : label}</span>;
};
