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

const candles = createProxyMiddleware('/api/candles', { target: 'http://127.0.0.1:5099', changeOrigin: true, ws: true });
app.use('/api/reputation', createProxyMiddleware({ target: 'http://127.0.0.1:5077', changeOrigin: true }));
app.use('/api/cats', createProxyMiddleware({ target: 'http://127.0.0.1:5088', changeOrigin: true }));
app.use(candles);
app.use('/api', createProxyMiddleware({ target: 'http://127.0.0.1:5001', changeOrigin: true }));

app.use(compression());
// hashed bundles cache for a year; index.html never (a rebuild shows on the next reload)
app.use(express.static(build, { index: false, setHeaders: (res, p) => res.setHeader('Cache-Control', /\/static\//.test(p) ? 'public, max-age=31536000, immutable' : 'no-cache') }));
app.get(/.*/, (_req, res) => { res.setHeader('Cache-Control', 'no-cache'); res.sendFile(path.join(build, 'index.html')); });

const server = app.listen(port, '127.0.0.1', () => console.log(`⚡ FEELESS fast mode on http://localhost:${port}`));
server.on('upgrade', candles.upgrade);   // live price stream (websocket)
