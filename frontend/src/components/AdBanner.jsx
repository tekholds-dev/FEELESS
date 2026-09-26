import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';

// Creator-managed promos. Clearly labelled; dismissible for the session; counts views/clicks.
export function AdBanner({ placement = 'banner' }) {
  const [ads, setAds] = useState([]);
  const [i, setI] = useState(0);
  const [hidden, setHidden] = useState(() => { try { return sessionStorage.getItem(`feeless:ad-hide:${placement}`) === '1'; } catch { return false; } });
  useEffect(() => { fetch(`/api/reputation/ads?placement=${placement}`).then(r => r.json()).then(d => setAds(d.ads || [])).catch(() => {}); }, [placement]);
  useEffect(() => { if (ads.length < 2) return undefined; const t = setInterval(() => setI(x => (x + 1) % ads.length), 8000); return () => clearInterval(t); }, [ads.length]);
  const ad = ads[i];
  useEffect(() => { if (ad && !hidden) fetch(`/api/reputation/ads/${ad.id}/event?kind=view`, { method: 'POST' }).catch(() => {}); }, [ad?.id, hidden]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!ad || hidden) return null;
  const click = () => fetch(`/api/reputation/ads/${ad.id}/event?kind=click`, { method: 'POST', keepalive: true }).catch(() => {});
  const external = /^https:/.test(ad.url || '');
  return <div className={`ad-banner ad-${placement}`} data-testid={`ad-${placement}`}>
    <em className="ad-tag">{ad.sponsor ? `Sponsored · ${ad.sponsor}` : 'FEELESS'}</em>
    {ad.imageUrl && <img src={ad.imageUrl} alt="" />}
    <a href={ad.url || '#'} onClick={click} target={external ? '_blank' : undefined} rel={external ? 'noopener noreferrer sponsored' : undefined}><b>{ad.title}</b>{ad.text && <span>{ad.text}</span>}</a>
    <button type="button" aria-label="Hide" onClick={() => { setHidden(true); try { sessionStorage.setItem(`feeless:ad-hide:${placement}`, '1'); } catch { /* ignore */ } }}><X size={13} /></button>
  </div>;
}
