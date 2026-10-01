import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { toast } from 'sonner';
import { renderShareGif, DESIGNS } from '../lib/shareGif';

// "Share GIF": renders the animated card, previews it, and offers download / native share.
export function ShareGifButton({ card, label = '🎞 Share GIF', className = 'btn-outline' }) {
  const [busy, setBusy] = useState(false);
  const [gif, setGif] = useState(null);
  const [theme, setTheme] = useState(card.theme || 'royal');
  useEffect(() => () => gif && URL.revokeObjectURL(gif.url), [gif]);
  const make = async (e, th = theme) => {
    e?.preventDefault(); e?.stopPropagation();
    setBusy(true);
    try { const blob = await renderShareGif({ ...card, theme: th === 'royal' ? undefined : th }); if (!blob) throw new Error('empty'); setGif({ blob, url: URL.createObjectURL(blob) }); } catch { toast.error('Could not render the GIF on this device.'); } finally { setBusy(false); }
  };
  const name = `feeless-${(card.title || 'card').replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.gif`;
  const file = gif && new File([gif.blob], name, { type: 'image/gif' });
  const canShare = !!file && !!navigator.canShare?.({ files: [file] });
  return <>
    <button type="button" className={className} disabled={busy} onClick={make} data-testid="share-gif">{busy ? 'Rendering…' : label}</button>
    {gif && createPortal(<div className="gif-overlay" role="dialog" aria-label="Share GIF" onPointerDown={e => e.target === e.currentTarget && setGif(null)}>
      <div className="gif-card"><img src={gif.url} alt={card.title} />
        <div className="m-seg gif-designs" role="radiogroup" aria-label="GIF design">{DESIGNS.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={theme === k} className={theme === k ? 'active' : ''} disabled={busy}
          onClick={e => { setTheme(k); make(e, k); }} data-testid={`gif-design-${k}`}>{busy && theme === k ? '…' : l}</button>)}</div><footer>
        <small>{(gif.blob.size / 1048576).toFixed(1)} MB · GIF</small>
        <a className="btn-primary" href={gif.url} download={name}>⬇ Download</a>
        {canShare && <button type="button" className="btn-outline" onClick={() => navigator.share({ files: [file], title: card.title }).catch(() => {})}>Share…</button>}
        <button type="button" className="btn-outline" onClick={() => setGif(null)}>Close</button>
      </footer></div>
    </div>, document.body)}
  </>;
}
