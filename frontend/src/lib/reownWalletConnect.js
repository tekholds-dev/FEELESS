import { createAppKit } from '@reown/appkit/react';
import { EthersAdapter } from '@reown/appkit-adapter-ethers';
import { SolanaAdapter } from '@reown/appkit-adapter-solana/react';
import {
  arbitrum,
  avalanche,
  base,
  bsc,
  cronos,
  mainnet,
  optimism,
  polygon,
  solana,
  unichain,
  worldchain,
  zksync,
  zora,
} from '@reown/appkit/networks';

const projectId = process.env.REACT_APP_REOWN_PROJECT_ID;
const namespaceFor = type => (type === 'solana' ? 'solana' : 'eip155');
const networks = [mainnet, base, bsc, arbitrum, avalanche, polygon, optimism, zksync, zora, cronos, unichain, worldchain, solana];
const appKit = projectId && typeof window !== 'undefined'
  ? createAppKit({
    adapters: [new EthersAdapter(), new SolanaAdapter()],
    networks,
    defaultNetwork: solana,
    projectId,
    metadata: {
      name: 'FEELESS',
      description: 'Connect a self-custody wallet to FEELESS.',
      url: window.location.origin,
      icons: [`${window.location.origin}/favicon.svg`],
    },
    features: { analytics: false, email: false, socials: [] },
    themeMode: 'dark',
  })
  : null;

const requireAppKit = () => {
  if (!appKit) {
    throw new Error('Mobile wallet connection is not configured for this preview.');
  }
  return appKit;
};

async function readSession(kit, type) {
  const namespace = namespaceFor(type);
  const account = kit.getAccount(namespace);
  const provider = kit.getProvider(namespace);
  if (!account?.isConnected || !account.address || !provider) return null;

  const chainId = type === 'evm'
    ? await provider.request({ method: 'eth_chainId' }).catch(() => kit.getChainId())
    : undefined;
  return {
    address: account.address,
    provider,
    chainId,
    name: kit.getWalletInfo(namespace)?.name || 'WalletConnect',
  };
}

export async function connectWalletConnect(type) {
  if (!['solana', 'evm'].includes(type)) throw new Error('Choose Solana or EVM to connect.');
  const kit = requireAppKit();
  await kit.ready();
  const namespace = namespaceFor(type);
  const alreadyConnected = await readSession(kit, type);
  if (alreadyConnected) return alreadyConnected;

  return new Promise((resolve, reject) => {
    let settled = false;
    let checking = false;
    let modalWasOpen = Boolean(kit.getState()?.open);
    let closedDuringHandoff = false;
    let accountState = kit.getAccount(namespace);
    let timeout;
    const unsubscribers = [];

    const finish = async (error, session) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      unsubscribers.forEach(unsubscribe => unsubscribe?.());
      if (error) reject(error);
      else resolve(session);
    };

    const check = async state => {
      if (state) accountState = state;
      if (settled || checking || !accountState?.isConnected || !accountState.address) return;
      checking = true;
      try {
        const session = await readSession(kit, type);
        if (session) await finish(null, session);
      } catch (error) {
        await finish(error);
      } finally {
        checking = false;
      }
    };

    const inspectClosedModal = () => {
      if (settled) return;
      if (document.visibilityState !== 'visible') {
        closedDuringHandoff = true;
        return;
      }
      window.setTimeout(() => {
        if (settled) return;
        if (document.visibilityState !== 'visible') {
          closedDuringHandoff = true;
          return;
        }
        void check();
        window.setTimeout(() => {
          if (settled) return;
          if (document.visibilityState !== 'visible') {
            closedDuringHandoff = true;
          } else if (!checking) {
            void finish(new Error('Wallet connection cancelled.'));
          }
        }, 1800);
      }, 300);
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible' && closedDuringHandoff) {
        closedDuringHandoff = false;
        inspectClosedModal();
      }
    };

    unsubscribers.push(kit.subscribeAccount(state => { void check(state); }, namespace));
    unsubscribers.push(kit.subscribeProviders(() => { void check(); }));
    unsubscribers.push(kit.subscribeState(state => {
      if (state.open) {
        modalWasOpen = true;
      } else if (modalWasOpen) {
        modalWasOpen = false;
        inspectClosedModal();
      }
    }));
    document.addEventListener('visibilitychange', onVisibilityChange);
    timeout = window.setTimeout(() => {
      void finish(new Error('Wallet connection timed out. You can try again.'));
    }, 5 * 60 * 1000);

    void check();
    kit.open({ view: 'Connect', namespace }).catch(error => { void finish(error); });
  });
}

export async function getWalletConnectSession(type) {
  if (!appKit || !['solana', 'evm'].includes(type)) return null;
  const kit = appKit;
  await kit.ready();
  return readSession(kit, type);
}

export async function disconnectWalletConnect(type) {
  if (!appKit) return;
  await appKit.disconnect(namespaceFor(type));
}

export async function subscribeWalletConnectSession(type, onSession) {
  if (!appKit) return () => {};
  const kit = appKit;
  const namespace = namespaceFor(type);
  await kit.ready();
  let alive = true;
  let accountState = kit.getAccount(namespace);
  let syncing = false;

  const publish = async state => {
    if (state) accountState = state;
    if (!alive || syncing) return;
    if (!accountState?.isConnected || !accountState.address) {
      if (accountState?.status === 'disconnected') onSession(null);
      return;
    }
    const provider = kit.getProvider(namespace);
    if (!provider) return;
    syncing = true;
    try {
      const chainId = type === 'evm'
        ? await provider.request({ method: 'eth_chainId' }).catch(() => kit.getChainId())
        : undefined;
      if (alive) {
        onSession({
          address: accountState.address,
          provider,
          chainId,
          name: kit.getWalletInfo(namespace)?.name || 'WalletConnect',
        });
      }
    } finally {
      syncing = false;
    }
  };

  const unsubscribeAccount = kit.subscribeAccount(state => { void publish(state); }, namespace);
  const unsubscribeProviders = kit.subscribeProviders(() => { void publish(); });
  return () => {
    alive = false;
    unsubscribeAccount?.();
    unsubscribeProviders?.();
  };
}
