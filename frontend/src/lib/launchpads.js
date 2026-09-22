export const LAUNCHPADS = [
  { id: 'feeless-launch', name: 'Launch on FEELESS', symbol: 'F', chainId: 'solana', color: '#14F195', lat: -18, lng: 132, url: '/terminal/launch', description: 'Bring a verified launch to the FEELESS network.', tag: 'FEELESS NATIVE', dexIds: [], isFeelessLaunch: true },
  { id: 'pump', name: 'Pump.fun', symbol: 'P', chainId: 'solana', color: '#34efad', lat: 25, lng: -78, url: process.env.REACT_APP_PUMP_URL, description: 'The home of Solana memecoins.', tag: 'MEME CULTURE', dexIds: ['pump', 'pumpswap', 'pump-fun', 'pump_fun'] },
  { id: 'bonk', name: 'LetsBONK', symbol: 'B', chainId: 'solana', color: '#f5b747', lat: -6, lng: -46, url: 'https://letsbonk.fun/', description: 'Community-first launches on Solana.', tag: 'COMMUNITY', dexIds: [] },
  { id: 'raydium', name: 'LaunchLab', symbol: 'R', chainId: 'solana', color: '#84a5ff', lat: 46, lng: 25, url: 'https://raydium.io/launchpad/', description: 'Token launches from the Raydium ecosystem.', tag: 'RAYDIUM', dexIds: ['raydium-launchlab'] },
  { id: 'meteora', name: 'Meteora', symbol: 'M', chainId: 'solana', color: '#ed8a60', lat: -30, lng: 22, url: 'https://launch.meteora.ag/', description: 'Launch infrastructure and dynamic liquidity.', tag: 'LIQUIDITY', dexIds: ['meteora', 'meteora-dlmm', 'meteora-dbc', 'meteora-damm-v2'] },
  { id: 'moonit', name: 'Moonit', symbol: '☾', chainId: 'solana', color: '#e6ef9f', lat: 4, lng: 152, url: 'https://moon.it/', description: 'Community tokens, from idea to orbit.', tag: 'FAIR LAUNCH', dexIds: ['moonit'] },
  { id: 'four', name: 'Four.meme', symbol: '4', chainId: 'bsc', color: '#efce5c', lat: 48, lng: 93, url: 'https://four.meme/en', description: 'Memecoin discovery on BNB Chain.', tag: 'BNB CHAIN', dexIds: ['four-meme', 'four_meme'] },
];

export const META_LAUNCH_STEPS = [
  { id: 'token', label: 'Token creation' },
  { id: 'liquidity', label: 'Initial liquidity' },
  { id: 'fee', label: 'Fee policy' },
  { id: 'holder', label: 'Holder allocation' },
  { id: 'airdrop', label: 'Airdrop distribution' },
];

export function getLaunchProviderConfig() {
  const env = typeof process !== 'undefined' ? process.env : {};
  const apiUrl = (env.REACT_APP_LAUNCH_API_URL || '').trim().replace(/\/+$/, '');
  const rpcUrl = (env.REACT_APP_SOLANA_RPC_URL || env.REACT_APP_LAUNCH_RPC_URL || '').trim();
  const approved = env.REACT_APP_LAUNCH_PROVIDER_APPROVED === 'true'
    || env.REACT_APP_LAUNCH_PROVIDER_STATUS === 'approved';
  const providerName = (env.REACT_APP_LAUNCH_PROVIDER_NAME || 'Approved launch provider').trim();
  const network = (env.REACT_APP_LAUNCH_NETWORK || 'Solana mainnet-beta').trim();
  return { apiUrl, rpcUrl, approved, providerName, network };
}

export function getLaunchProviderReadiness() {
  const config = getLaunchProviderConfig();
  return {
    ...config,
    ready: Boolean(config.apiUrl && config.rpcUrl && config.approved),
    providerReady: Boolean(config.apiUrl && config.approved),
    rpcReady: Boolean(config.rpcUrl),
    rpcHost: config.rpcUrl ? safeHost(config.rpcUrl) : '',
  };
}

function safeHost(value) {
  try { return new URL(value).host; } catch { return 'Configured RPC'; }
}

const STEP_ALIASES = {
  token_creation: 'token',
  create_token: 'token',
  initial_liquidity: 'liquidity',
  add_liquidity: 'liquidity',
  fee_policy: 'fee',
  configure_fees: 'fee',
  holder_allocation: 'holder',
  allocate_holders: 'holder',
  airdrop_distribution: 'airdrop',
  distribute_airdrop: 'airdrop',
};

function normalizeStepId(value) {
  return STEP_ALIASES[value] || value;
}

function explorerCluster(network) {
  const normalized = String(network || '').toLowerCase();
  if (normalized.includes('devnet')) return 'devnet';
  if (normalized.includes('testnet')) return 'testnet';
  if (normalized.includes('localnet')) return 'custom';
  return 'mainnet-beta';
}

export function getSolanaExplorerUrl(value, type = 'tx', network = getLaunchProviderConfig().network) {
  if (typeof value !== 'string' || !value.trim()) return null;
  return `https://explorer.solana.com/${type}/${encodeURIComponent(value.trim())}?cluster=${explorerCluster(network)}`;
}

export function getLaunchMint(plan) {
  return plan?.mint
    || plan?.createdMint
    || plan?.tokenMint
    || plan?.launch?.mint
    || plan?.token?.mint
    || plan?.result?.mint
    || null;
}

function decodeTransaction(value) {
  if (typeof value !== 'string' || !value) throw new Error('Provider returned an empty transaction.');
  const bytes = Uint8Array.from(atob(value), character => character.charCodeAt(0));
  return bytes;
}

export async function requestMetaLaunchPlan(form, wallet) {
  const readiness = getLaunchProviderReadiness();
  if (!readiness.ready) throw new Error('An approved launch provider and Solana RPC are required.');
  if (!wallet?.address || wallet.chain !== 'solana') throw new Error('A Solana wallet is required to prepare this deployment.');
  const response = await fetch(`${readiness.apiUrl}/prepare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      wallet: wallet.address,
      chain: wallet.chain,
      launch: {
        name: form.name.trim(),
        symbol: form.symbol.trim().toUpperCase(),
        supply: form.supply,
        decimals: Number(form.decimals),
        liquidityPair: form.liquidityPair,
        liquidityAmount: form.liquidityAmount,
        buyTax: Number(form.buyTax),
        sellTax: Number(form.sellTax),
        holderAllocation: Number(form.holderAllocation),
        airdropAmount: Number(form.airdropAmount),
        airdropRecipients: form.airdropRecipients.split(/[\n,]+/).map(value => value.trim()).filter(Boolean),
      },
    }),
  });
  let data;
  try { data = await response.json(); } catch { data = null; }
  if (!response.ok) throw new Error(data?.detail || data?.error || 'The launch provider could not prepare this deployment.');
  if (data?.provider?.approved === false) throw new Error('The launch provider has not approved this deployment.');
  if (!Array.isArray(data?.transactions) || !data.transactions.length) throw new Error('The launch provider returned no transactions.');
  const returnedSteps = new Set(data.transactions.map(item => normalizeStepId(item.id || item.type)));
  const missingSteps = META_LAUNCH_STEPS.filter(step => !returnedSteps.has(step.id));
  if (missingSteps.length) throw new Error(`The launch provider did not prepare: ${missingSteps.map(step => step.label).join(', ')}.`);
  return data;
}

function transactionPayer(transaction) {
  if (transaction?.message?.staticAccountKeys?.[0]) return transaction.message.staticAccountKeys[0].toBase58();
  return transaction?.feePayer?.toBase58?.() || null;
}

export async function executeMetaLaunchPlan(plan, { provider, wallet, onStep }) {
  if (!provider?.signTransaction) throw new Error('A wallet signer is required to deploy.');
  if (wallet?.chain !== 'solana') throw new Error('Connect a Solana wallet to deploy on FEELESS.');
  if (provider.publicKey?.toString() && provider.publicKey.toString() !== wallet.address) {
    throw new Error('Connected Phantom account changed. Reconnect and review the launch again.');
  }

  const { Connection, VersionedTransaction, Transaction } = await import('@solana/web3.js');
  const config = getLaunchProviderConfig();
  const connection = new Connection(config.rpcUrl, 'confirmed');
  const transactions = plan.transactions.map((item, index) => ({
    ...item,
    id: normalizeStepId(item.id || item.type || META_LAUNCH_STEPS[index]?.id || `transaction-${index + 1}`),
    label: item.label || META_LAUNCH_STEPS.find(step => step.id === normalizeStepId(item.id || item.type))?.label || `Transaction ${index + 1}`,
  }));
  const results = [];

  for (const item of transactions) {
    onStep?.(item.id, { state: 'pending', label: item.label });
    let signature;
    try {
      const bytes = decodeTransaction(item.transaction || item.serializedTransaction);
      let transaction;
      try { transaction = VersionedTransaction.deserialize(bytes); }
      catch { transaction = Transaction.from(bytes); }
      if (transactionPayer(transaction) !== wallet.address) {
        throw new Error(`${item.label} is not assigned to the connected wallet.`);
      }
      const signed = await provider.signTransaction(transaction);
      if (!signed?.serialize) throw new Error(`${item.label} was not signed by the wallet.`);
      signature = await connection.sendRawTransaction(signed.serialize(), { skipPreflight: false });
      onStep?.(item.id, { state: 'pending', label: item.label, signature });
      const confirmation = await connection.confirmTransaction(signature, 'confirmed');
      if (confirmation?.value?.err) {
        const result = { id: item.id, label: item.label, state: 'failed', signature, detail: `${item.label} failed on-chain.` };
        results.push(result);
        onStep?.(item.id, result);
        return { state: 'failed', results, detail: result.detail };
      }
      if (!confirmation?.value) {
        const result = { id: item.id, label: item.label, state: 'pending', signature, detail: `${item.label} was submitted; confirmation is still pending.` };
        results.push(result);
        onStep?.(item.id, result);
        return { state: 'pending', results, detail: result.detail };
      }
      const result = {
        id: item.id,
        label: item.label,
        state: 'confirmed',
        signature,
        explorerUrl: getSolanaExplorerUrl(signature, 'tx', config.network),
      };
      results.push(result);
      onStep?.(item.id, result);
    } catch (error) {
      const message = error?.code === 4001 ? 'Wallet approval declined.' : error?.message || `${item.label} failed.`;
      const result = { id: item.id, label: item.label, state: signature ? 'pending' : 'failed', signature, detail: message };
      results.push(result);
      onStep?.(item.id, result);
      return { state: result.state, results, detail: message };
    }
  }
  return { state: 'confirmed', results, mint: getLaunchMint(plan) };
}

export const launchpadEcosystem = pad => ({ ...pad, isLaunchpad: true, website: pad.url,
  platforms: [{ name: pad.name, url: pad.url, type: 'launch' },
    { name: 'Discover pools', url: `/terminal/discover?chain=${pad.chainId}`, type: 'analytics' }] });

export function matchesPad(pair, id) {
  const pad = LAUNCHPADS.find(p => p.id === id);
  if (!pad) return true;
  return pair.chainId === pad.chainId && pad.dexIds.includes(pair.dexId?.toLowerCase());
}