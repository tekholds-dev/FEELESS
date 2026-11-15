// ⚡ FAST MODE: serves the PRODUCTION build (minified, no StrictMode double-fetch, no hot-reload overhead) with the same /api proxy
// as the dev server (frontend/src/setupProxy.js — keep the two in step). Started by scripts/serve-fast.sh; never touches the dev server.
const path = require('path');
const fe = path.join(__dirname, '..', 'frontend');
const req = m => require(path.join(fe, 'node_modules', m));
const express = req('express');
const compression = req('compression');
const { createProxyMiddleware } = req('http-proxy-middleware');

const port = Number(process.env.FAST_PORT || 51368);
const build = path.join(fe, 'build');
const app = express();

// same routes as setupProxy.js: xfwd so the services see the real caller (guard.request_ip), and every websocket (arena rooms, cat streams, live prices)
const arena = createProxyMiddleware('/api/reputation/arena/ws', { target: 'http://127.0.0.1:5077', changeOrigin: true, xfwd: true, ws: true });
const cats = createProxyMiddleware('/api/cats', { target: 'http://127.0.0.1:5088', changeOrigin: true, xfwd: true, ws: true });
const candles = createProxyMiddleware('/api/candles', { target: 'http://127.0.0.1:5099', changeOrigin: true, xfwd: true, ws: true });
app.use(arena);
app.use('/api/reputation', createProxyMiddleware({ target: 'http://127.0.0.1:5077', changeOrigin: true, xfwd: true }));
app.use(cats);
app.use(candles);
app.use('/api', createProxyMiddleware({ target: 'http://127.0.0.1:5001', changeOrigin: true, xfwd: true }));

app.use(compression());
// hashed bundles cache for a year; index.html never (a rebuild shows on the next reload)
app.use(express.static(build, { index: false, setHeaders: (res, p) => res.setHeader('Cache-Control', /\/static\//.test(p) ? 'public, max-age=31536000, immutable' : 'no-cache') }));
app.get(/.*/, (_req, res) => { res.setHeader('Cache-Control', 'no-cache'); res.sendFile(path.join(build, 'index.html')); });

const server = app.listen(port, '127.0.0.1', () => console.log(`⚡ FEELESS fast mode on http://localhost:${port}`));
server.on('upgrade', (req, socket, head) => {   // live price stream, cat streams, arena rooms
  const u = req.url || '';
  (u.startsWith('/api/reputation/arena/ws') ? arena : u.startsWith('/api/cats') ? cats : candles).upgrade(req, socket, head);
});
