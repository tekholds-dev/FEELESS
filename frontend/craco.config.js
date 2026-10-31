// craco.config.js
const path = require("path");
require("dotenv").config();

// Check if we're in development/preview mode (not production build)
// Craco sets NODE_ENV=development for start, NODE_ENV=production for build
const isDevServer = process.env.NODE_ENV !== "production";
const previewApiPort = process.env.PREVIEW_API_PORT;

// Environment variable overrides
const config = {
  enableHealthCheck: process.env.ENABLE_HEALTH_CHECK === "true",
};

function makeDevServerV5Compatible(devServerConfig) {
  const {
    https,
    onAfterSetupMiddleware,
    onBeforeSetupMiddleware,
    onListening,
    setupMiddlewares,
    ...compatibleConfig
  } = devServerConfig;

  compatibleConfig.server =
    typeof https === "object"
      ? { type: "https", options: https }
      : https
        ? "https"
        : "http";
  compatibleConfig.headers = {
    ...compatibleConfig.headers,
    "Cross-Origin-Resource-Policy": "same-origin",
  };
  // Replit serves the app through a proxied preview hostname. CRA's default
  // host allow-list rejects that hostname with "Invalid Host header".
  compatibleConfig.host = "0.0.0.0";
  compatibleConfig.allowedHosts = "all";

  if (onBeforeSetupMiddleware || setupMiddlewares) {
    compatibleConfig.setupMiddlewares = (middlewares, devServer) => {
      if (onBeforeSetupMiddleware) {
        onBeforeSetupMiddleware(devServer);
      }

      return setupMiddlewares
        ? setupMiddlewares(middlewares, devServer)
        : middlewares;
    };
  }

  compatibleConfig.onListening = (devServer) => {
    devServer.close ??= (callback) => devServer.stopCallback(callback);

    if (onListening) {
      onListening(devServer);
    }
    if (onAfterSetupMiddleware) {
      onAfterSetupMiddleware(devServer);
    }
  };

  return compatibleConfig;
}

// Conditionally load health check modules only if enabled
let WebpackHealthPlugin;
let setupHealthEndpoints;
let healthPluginInstance;

if (config.enableHealthCheck) {
  WebpackHealthPlugin = require("./plugins/health-check/webpack-health-plugin");
  setupHealthEndpoints = require("./plugins/health-check/health-endpoints");
  healthPluginInstance = new WebpackHealthPlugin();
}

let webpackConfig = {
  eslint: {
    configure: {
      extends: ["plugin:react-hooks/recommended"],
      rules: {
        "react-hooks/rules-of-hooks": "error",
        "react-hooks/exhaustive-deps": "warn",
      },
    },
  },
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    configure: (webpackConfig) => {
      // Metaplex ships source maps that point at .ts files it doesn't publish: skip them (quiet, faster builds).
      webpackConfig.ignoreWarnings = [...(webpackConfig.ignoreWarnings || []), /Failed to parse source map/, { module: /node_modules[\\/](ox|viem)[\\/]/, message: /Critical dependency/ }];   // viem / ox load an optional dep by expression — harmless

      // Add ignored patterns to reduce watched directories
        webpackConfig.watchOptions = {
          ...webpackConfig.watchOptions,
          ignored: [
            '**/node_modules/**',
            '**/.git/**',
            '**/build/**',
            '**/dist/**',
            '**/coverage/**',
            '**/public/**',
        ],
      };

      // 🧹 webpack's own build cache (it reached 1.6 GB): versions unused for 3 days are dropped.
      if (webpackConfig.cache && typeof webpackConfig.cache === 'object') webpackConfig.cache = { ...webpackConfig.cache, maxAge: 3 * 24 * 3600 * 1000 };

      // Meteora's SDK ships .mjs files that import extensionless paths; allow that for .mjs only.
      webpackConfig.module.rules.push({ test: /\.m?js$/, include: /node_modules[\\/]@meteora-ag/, resolve: { fullySpecified: false } });
      // Anchor only requires Node's 'util' on its non-browser branch; browsers use TextEncoder/Decoder.
      webpackConfig.resolve.fallback = { ...webpackConfig.resolve.fallback, util: false };

      // Add health check plugin to webpack if enabled
      if (config.enableHealthCheck && healthPluginInstance) {
        webpackConfig.plugins.push(healthPluginInstance);
      }

      // These published packages reference source files that are not included in
      // their npm distributions. Excluding only those packages keeps build logs
      // useful without disabling source maps for the application.
      const sourceMapRule = webpackConfig.module.rules.find((rule) =>
        String(rule.loader || '').includes('source-map-loader')
      );
      if (sourceMapRule) {
        sourceMapRule.exclude = [
          ...(Array.isArray(sourceMapRule.exclude) ? sourceMapRule.exclude : sourceMapRule.exclude ? [sourceMapRule.exclude] : []),
          /node_modules[\\/]@solana[\\/]buffer-layout/,
          /node_modules[\\/]@coral-xyz/,
          /node_modules[\\/]superstruct/,
        ];
      }

      return webpackConfig;
    },
  },
};

webpackConfig.devServer = (devServerConfig) => {
  // Release browser checks can run beside the managed preview. CRA derives
  // this proxy array from package.json, so retarget it only when an isolated
  // preview API port was explicitly provided.
  if (previewApiPort && Array.isArray(devServerConfig.proxy)) {
    devServerConfig.proxy = devServerConfig.proxy.map((proxy) => ({
      ...proxy,
      target: `http://127.0.0.1:${previewApiPort}`,
    }));
  }

  // Add health check endpoints if enabled
  if (config.enableHealthCheck && setupHealthEndpoints && healthPluginInstance) {
    const originalSetupMiddlewares = devServerConfig.setupMiddlewares;

    devServerConfig.setupMiddlewares = (middlewares, devServer) => {
      // Call original setup if exists
      if (originalSetupMiddlewares) {
        middlewares = originalSetupMiddlewares(middlewares, devServer);
      }

      // Setup health endpoints
      setupHealthEndpoints(devServer, healthPluginInstance);

      return middlewares;
    };
  }

  return devServerConfig;
};

const configureDevServer = webpackConfig.devServer;
webpackConfig.devServer = (devServerConfig) =>
  makeDevServerV5Compatible(configureDevServer(devServerConfig));

// Jest's resolver doesn't follow package.json "exports" subpaths (webpack does): map the one Metaplex needs.
webpackConfig.jest = {
  configure: (jestConfig) => ({
    ...jestConfig,
    // UI tests wait on real timers (polls, animations): under a busy CPU a 5s default timed out at random → flaky suites.
    testTimeout: 30000,
    moduleNameMapper: {
      ...(jestConfig.moduleNameMapper || {}),
      '^@metaplex-foundation/umi/serializers$': '<rootDir>/node_modules/@metaplex-foundation/umi/dist/cjs/serializers.cjs',
    },
  }),
};

module.exports = webpackConfig;
