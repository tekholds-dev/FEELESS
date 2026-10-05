// One sitewide safety net for images (coin logos come from IPFS and random hosts and fail often):
// 1) IPFS link → retry once on a second gateway; 2) otherwise show a neutral coin mark, never the
// browser's broken-image icon. Cover/background images just hide so their gradient shows through.
const GATEWAYS = ['https://ipfs.io/ipfs/', 'https://cloudflare-ipfs.com/ipfs/', 'https://gateway.pinata.cloud/ipfs/', 'https://cf-ipfs.com/ipfs/', 'https://nftstorage.link/ipfs/'];
const PLACEHOLDER = 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#15d16a"/><stop offset="1" stop-color="#0b5f45"/></linearGradient></defs><circle cx="20" cy="20" r="19" fill="url(#g)" opacity=".35"/><circle cx="20" cy="20" r="11" fill="none" stroke="#7df9d0" stroke-opacity=".7" stroke-width="2"/></svg>');

function ipfsCid(src) {
  const m = src.match(/\/ipfs\/([^?#]+)/) || src.match(/^https?:\/\/([a-z0-9]{46,})\.ipfs\.[^/]+\/?(.*)$/i);
  return m ? (m[2] !== undefined ? `${m[1]}${m[2] ? `/${m[2]}` : ''}` : m[1]) : null;
}

export function installImageFallback() {
  document.addEventListener('error', e => {
    const img = e.target;
    if (!(img instanceof HTMLImageElement) || img.dataset.fbDone || img.dataset.fbSkip) return;
    if (img.closest('[data-img-hide], .xp-cover')) { img.style.display = 'none'; img.dataset.fbDone = '1'; return; }
    const cid = ipfsCid(img.currentSrc || img.src || '');
    const tried = Number(img.dataset.fbTry || 0);
    if (cid && tried < 2) {
      img.dataset.fbTry = String(tried + 1);
      const next = GATEWAYS.find(g => !(img.src || '').startsWith(g) && !(img.dataset.fbUsed || '').includes(g));
      if (next) { img.dataset.fbUsed = `${img.dataset.fbUsed || ''} ${next}`; img.src = next + cid; return; }
    }
    img.dataset.fbDone = '1';
    img.src = PLACEHOLDER;
  }, true);
}
