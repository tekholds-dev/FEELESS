// 🔗 shared reads (lib/sharedJson) must never carry one test's answer into the next
beforeEach(() => { require('./lib/sharedJson')._resetShared(); });
// 🛰 the agent hub is ONE store for the page: a test must never read the snapshot / stream state of the test before it
afterEach(() => { try { require('./lib/agentHub').hubReset(); } catch (e) { /* the hub was never loaded in this file */ } });
