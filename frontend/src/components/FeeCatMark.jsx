import { useFeeLook } from '../lib/feeLeader';
import React from 'react';
import { Panther } from './Panther';

// 🐆 Fee's mark = the PANTHER's head (owner, 2026-10-20: "FeeCat is a black panther, not the alien cats"). Same props as before so every use
// site keeps working: `variant` maps to a coat, `colors` ([fur, accent]) paints a user's own cat, `animate` false = a still mark.
const VARIANT_COAT = { mint: null, gold: 'gold', rose: 'pink', violet: 'shadow', ghost: 'snow' };

export function FeeCatMark({ size = 40, variant = 'mint', animate = true, className = '', colors, label, pattern = null, gear = null, eyes = null, full = false, gesture }) {
  // 🎨 a plain mark IS Fee → she wears the creator's saved look (lib/feeLeader.useFeeLook); a mark given its own colours / pattern / gear is a build preview
  const fee = !colors && !pattern && !gear && !eyes && variant === 'mint'; const look = useFeeLook(fee);
  return <Panther size={size} crop={full ? undefined : 'head'} coat={(look?.coat) || VARIANT_COAT[variant] || undefined} colors={colors} label={label || 'Fee, the FEELESS panther'} pattern={pattern || look?.pattern || null} gear={gear || look?.gear || null} eyes={eyes || look?.eyes || null} gesture={gesture || undefined}
    className={`feecat-mark${animate ? '' : ' is-still'} ${className}`} />;
}
