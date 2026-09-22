import React, { useEffect, useState } from 'react';
import { Globe2 } from 'lucide-react';
import { FeelessMark } from './FeelessLogo';

export default function LaunchpadLogo({ launchpad, size = 48 }) {
  const source = launchpad?.logoUrl || launchpad?.logo || '';
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [source]);

  return <span
    className="launchpad-logo"
    style={{ width: size, height: size, '--logo-accent': launchpad?.color || '#14F195' }}
    data-testid={`launchpad-logo-${launchpad?.id || 'unknown'}`}
    aria-label={`${launchpad?.name || 'Launchpad'} logo`}
  >
    {launchpad?.isFeelessLaunch
      ? <FeelessMark size={Math.max(24, size - 10)} glow={false} />
      : source && !failed
        ? <img src={source} alt="" onError={() => setFailed(true)} />
        : <Globe2 size={Math.round(size * 0.42)} aria-hidden="true" />}
  </span>;
}