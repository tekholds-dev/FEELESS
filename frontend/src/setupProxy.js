const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function (app) {
  app.use('/api/reputation', createProxyMiddleware({ target: 'http://127.0.0.1:5077', changeOrigin: true }));
  app.use('/api/cats', createProxyMiddleware({ target: 'http://127.0.0.1:5088', changeOrigin: true }));
  app.use('/api/candles', createProxyMiddleware({ target: 'http://127.0.0.1:5099', changeOrigin: true }));
  app.use('/api', createProxyMiddleware({ target: 'http://127.0.0.1:5001', changeOrigin: true }));
};
