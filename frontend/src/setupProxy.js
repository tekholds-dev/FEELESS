const { createProxyMiddleware } = require('http-proxy-middleware');
const mainApi = `http://127.0.0.1:${process.env.PREVIEW_API_PORT || 5001}`;

// xfwd: the services see the real caller in X-Forwarded-For (guard.request_ip), not 127.0.0.1 for everyone (audit 2026-11-12 #4)
module.exports = function (app) {
  app.use(createProxyMiddleware('/api/reputation/arena/ws', { target: 'http://127.0.0.1:5077', changeOrigin: true, xfwd: true, ws: true }));   // 🎯 Strike Zone online rooms
  app.use('/api/reputation', createProxyMiddleware({ target: 'http://127.0.0.1:5077', changeOrigin: true, xfwd: true }));
  app.use(createProxyMiddleware('/api/cats', { target: 'http://127.0.0.1:5088', changeOrigin: true, xfwd: true, ws: true }));   // 🔴 a stream goes over a socket
  // Context form so websocket upgrades (live price stream) are proxied too.
  app.use(createProxyMiddleware('/api/candles', { target: 'http://127.0.0.1:5099', changeOrigin: true, xfwd: true, ws: true }));
  app.use('/api', createProxyMiddleware({ target: mainApi, changeOrigin: true, xfwd: true }));
};
