const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function (app) {
  app.use('/api/reputation', createProxyMiddleware({ target: 'http://127.0.0.1:5077', changeOrigin: true }));
  app.use('/api/cats', createProxyMiddleware({ target: 'http://127.0.0.1:5088', changeOrigin: true }));
  // Context form so websocket upgrades (live price stream) are proxied too.
  app.use(createProxyMiddleware('/api/candles', { target: 'http://127.0.0.1:5099', changeOrigin: true, ws: true }));
  app.use('/api', createProxyMiddleware({ target: 'http://127.0.0.1:5001', changeOrigin: true }));
};
