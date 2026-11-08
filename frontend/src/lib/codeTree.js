// 🌳 A built page as a tree of files (owner 2026-11-07: "the Code tab shows each page or the code tree, and that tree can be saved").
// index.html is the page exactly as built and runs on its own; pages/, styles/ and scripts/ are the same code split out to read.
const clean = s => String(s || '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 32);

export function codeTree(html) {
  const src = String(html || ''); const files = [{ path: 'index.html', group: 'Page', text: src }];
  if (!src || typeof DOMParser === 'undefined') return files;
  const doc = new DOMParser().parseFromString(src, 'text/html'); const seen = new Set();
  const name = (el, i) => { let n = clean(el.getAttribute('data-page') && !/^\d+$/.test(el.getAttribute('data-page')) ? el.getAttribute('data-page') : el.id || el.querySelector('h1,h2')?.textContent) || `page-${i + 1}`; while (seen.has(n)) n += '-2'; seen.add(n); return n; };
  const pages = [...doc.querySelectorAll('[data-page]')]; const parts = pages.length ? pages : [...doc.querySelectorAll('body > main, body > section[id], body > div > section[id]')];
  parts.forEach((el, i) => files.push({ path: `pages/${name(el, i)}.html`, group: 'Pages', text: el.outerHTML }));
  [...doc.querySelectorAll('style')].forEach((el, i) => el.textContent.trim() && files.push({ path: `styles/style-${i + 1}.css`, group: 'Styles', text: el.textContent.trim() }));
  [...doc.querySelectorAll('script:not([src])')].forEach((el, i) => el.textContent.trim() && files.push({ path: `scripts/script-${i + 1}.js`, group: 'Scripts', text: el.textContent.trim() }));
  const kits = [...doc.querySelectorAll('script[src], link[rel=stylesheet][href]')].map(el => el.getAttribute('src') || el.getAttribute('href'));
  if (kits.length) files.push({ path: 'kits.txt', group: 'Kits', text: kits.join('\n') });
  return files;
}

// 📦 A plain zip (stored, no compression) so the whole tree saves as one file with nothing to install.
const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
const crc32 = b => { let c = 0xffffffff; for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
export function zipBytes(files) {
  const enc = new TextEncoder(); const out = []; const dir = []; let at = 0;
  const u16 = v => [v & 255, (v >>> 8) & 255]; const u32 = v => [v & 255, (v >>> 8) & 255, (v >>> 16) & 255, (v >>> 24) & 255];
  files.forEach(f => {
    const name = enc.encode(f.path); const data = enc.encode(f.text); const c = crc32(data);
    const head = [...u32(0x04034b50), ...u16(20), ...u16(0x0800), ...u16(0), ...u16(0), ...u16(0x21), ...u32(c), ...u32(data.length), ...u32(data.length), ...u16(name.length), ...u16(0)];
    out.push(new Uint8Array(head), name, data);
    dir.push(new Uint8Array([...u32(0x02014b50), ...u16(20), ...u16(20), ...u16(0x0800), ...u16(0), ...u16(0), ...u16(0x21), ...u32(c), ...u32(data.length), ...u32(data.length), ...u16(name.length), ...u16(0), ...u16(0), ...u16(0), ...u16(0), ...u32(0), ...u32(at)]), name);
    at += head.length + name.length + data.length;
  });
  const size = dir.reduce((n, p) => n + p.length, 0);
  const parts = [...out, ...dir, new Uint8Array([...u32(0x06054b50), ...u16(0), ...u16(0), ...u16(files.length), ...u16(files.length), ...u32(size), ...u32(at), ...u16(0)])];
  const all = new Uint8Array(parts.reduce((n, p) => n + p.length, 0)); let o = 0; parts.forEach(p => { all.set(p, o); o += p.length; });
  return all;
}
export const zipFiles = files => new Blob([zipBytes(files)], { type: 'application/zip' });
