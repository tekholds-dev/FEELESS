import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { toast } from 'sonner';
import { renderShareGif, renderShareCard, DESIGNS } from '../lib/shareGif';
import { CardFx } from './CardFx';

// 🖼 Share card: opens at once as a STILL card (crisp PNG) that spins 180° into place; 🎞 turns it into the animated GIF when
// asked. Pick a design, download or native-share. Rendered in the browser; nothing is uploaded.
export function ShareGifButton({ card, label = '🖼 Share', className = 'btn-outline' }) {
  const [busy, setBusy] = useState(false);
  const [gif, setGif] = useState(null);          // {blob, url, kind: 'png' | 'gif', n} — n re-keys the spin
  const [theme, setTheme] = useState(card.theme || 'royal');
  useEffect(() => () => gif && URL.revokeObjectURL(gif.url), [gif]);
  const make = async (e, th = theme, kind = 'png') => {
    e?.preventDefault(); e?.stopPropagation();
    setBusy(kind);
    try {
      const blob = await (kind === 'gif' ? renderShareGif : renderShareCard)({ ...card, theme: th === 'royal' ? undefined : th });
      if (!blob) throw new Error('empty');
      setGif(g => ({ blob, url: URL.createObjectURL(blob), kind, n: (g?.n || 0) + 1 }));
    } catch { toast.error('Could not render the card on this device.'); } finally { setBusy(false); }
  };
  useEffect(() => { if (!gif) return undefined; const esc = e => e.key === 'Escape' && setGif(null); window.addEventListener('keydown', esc); return () => window.removeEventListener('keydown', esc); }, [gif]);
  const ext = gif?.kind === 'gif' ? 'gif' : 'png';
  const name = `feeless-${(card.title || 'card').replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.${ext}`;
  const file = gif && new File([gif.blob], name, { type: `image/${ext}` });
  const canShare = !!file && !!navigator.canShare?.({ files: [file] });
  return <>
    <button type="button" className={className} disabled={!!busy} onClick={make} data-testid="share-gif">{busy ? 'Rendering…' : label}</button>
    {gif && createPortal(<div className="gif-overlay" role="dialog" aria-label="Share card" onPointerDown={e => e.target === e.currentTarget && setGif(null)}>
      <div className="gif-card cfx-host"><CardFx kind="embers" tone={card.tone === 'down' ? 'down' : undefined} />
        <div className="gif-stage"><img key={gif.n} className="gif-spin" src={gif.url} alt={card.title} data-testid="share-img" data-kind={gif.kind} /></div>
        <div className="m-seg gif-designs" role="radiogroup" aria-label="Card design">{DESIGNS.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={theme === k} className={theme === k ? 'active' : ''} disabled={!!busy}
          onClick={e => { setTheme(k); make(e, k, 'png'); }} data-testid={`gif-design-${k}`}>{busy && theme === k ? '…' : l}</button>)}</div><footer>
        <small>{gif.blob.size >= 1048576 ? `${(gif.blob.size / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(gif.blob.size / 1024))} KB`} · {gif.kind === 'gif' ? 'GIF' : 'still'}</small>
        <a className="btn-primary" href={gif.url} download={name} data-testid="share-download">⬇ Download</a>
        {canShare && <button type="button" className="btn-outline" onClick={() => navigator.share({ files: [file], title: card.title }).catch(() => {})}>Share…</button>}
        <button type="button" className="btn-outline" disabled={!!busy} onClick={e => make(e, theme, gif.kind === 'gif' ? 'png' : 'gif')} data-testid="share-animate"
          data-tip={gif.kind === 'gif' ? 'Back to the still card' : 'Render the animated GIF (takes a few seconds)'}>{busy === 'gif' ? 'Rendering…' : gif.kind === 'gif' ? '🖼 Still' : '🎞 Animate'}</button>
        <button type="button" className="btn-outline" onClick={() => setGif(null)}>Close</button>
      </footer></div>
    </div>, document.body)}
  </>;
}
