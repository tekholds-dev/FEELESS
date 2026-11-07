// 🎬 The editor's media stays on this device. Blobs in IndexedDB, so a refresh does not lose a project. It fails quietly: a private window simply keeps them until it closes.
const DB = 'feeless-media'; const STORE = 'blobs';
const open = () => new Promise((res, rej) => { try { const r = indexedDB.open(DB, 1); r.onupgradeneeded = () => r.result.createObjectStore(STORE); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); } catch (e) { rej(e); } });
const run = async (mode, fn) => { const db = await open(); return new Promise((res, rej) => { const t = db.transaction(STORE, mode); const q = fn(t.objectStore(STORE)); t.oncomplete = () => { db.close(); res(q?.result); }; t.onerror = () => { db.close(); rej(t.error); }; }); };
export const putMedia = (key, blob) => run('readwrite', s => s.put(blob, key)).catch(() => null);
export const getMedia = key => run('readonly', s => s.get(key)).catch(() => null);
export const dropMedia = key => run('readwrite', s => s.delete(key)).catch(() => null);
