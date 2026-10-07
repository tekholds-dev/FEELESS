// 🔗 shared reads (lib/sharedJson) must never carry one test's answer into the next
beforeEach(() => { require('./lib/sharedJson')._resetShared(); });
