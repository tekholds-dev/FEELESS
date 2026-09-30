import { relayConnection, signSend } from './launchRail';

// Metaplex Core, signed by the owner's wallet (no API key). Metaplex's own library builds the instructions; the
// existing signSend() simulates, asks the wallet once per transaction and confirms through the FEELESS RPC relay.
// Loaded only when the NFT section opens.
async function kit() {
  const [{ web3, connection }, core, umiBundle, umiCore, adapters] = await Promise.all([relayConnection(), import('@metaplex-foundation/mpl-core'),
    import('@metaplex-foundation/umi-bundle-defaults'), import('@metaplex-foundation/umi'), import('@metaplex-foundation/umi-web3js-adapters')]);
  return { web3, connection, core, umiBundle, umiCore, adapters };
}

function umiFor(k, owner) {
  const umi = k.umiBundle.createUmi(connectionUrl(k.connection)).use(k.core.mplCore());
  const me = k.umiCore.createNoopSigner(k.umiCore.publicKey(owner));
  return umi.use(k.umiCore.signerIdentity(me));
}
const connectionUrl = c => c.rpcEndpoint || c._rpcEndpoint;

function toTx(k, ixs, owner) {
  const tx = new k.web3.Transaction();
  ixs.forEach(ix => tx.add(k.adapters.toWeb3JsInstruction(ix)));
  tx.feePayer = new k.web3.PublicKey(owner);
  return tx;
}

export async function coreCreateCollection({ provider, owner, name, uri, royaltyBps = 0, onStatus }) {
  const k = await kit();
  const umi = umiFor(k, owner);
  const kp = k.web3.Keypair.generate();
  const collection = k.umiCore.createNoopSigner(k.umiCore.publicKey(kp.publicKey.toBase58()));
  const plugins = royaltyBps > 0 ? [{ type: 'Royalties', basisPoints: royaltyBps, creators: [{ address: k.umiCore.publicKey(owner), percentage: 100 }], ruleSet: k.core.ruleSet('None') }] : [];
  const ixs = k.core.createCollection(umi, { collection, name, uri, plugins }).getInstructions();
  onStatus?.('Simulating the collection…');
  const signature = await signSend(k.web3, k.connection, provider, toTx(k, ixs, owner), new k.web3.PublicKey(owner), [kp], onStatus);
  return { address: kp.publicKey.toBase58(), signature };
}

// One NFT per wallet, 3 per transaction (one wallet approval each), numbered from `start`.
export async function coreDrop({ provider, owner, collection, name, uriFor, recipients, start = 1, onStatus }) {
  const k = await kit();
  const umi = umiFor(k, owner);
  const col = { publicKey: k.umiCore.publicKey(collection) };
  const results = [];
  for (let i = 0; i < recipients.length; i += 3) {
    const chunk = recipients.slice(i, i + 3);
    const kps = chunk.map(() => k.web3.Keypair.generate());
    const ixs = chunk.flatMap((to, j) => k.core.create(umi, { asset: k.umiCore.createNoopSigner(k.umiCore.publicKey(kps[j].publicKey.toBase58())), collection: col,
      name: `${name} #${start + i + j}`, uri: uriFor(start + i + j), owner: k.umiCore.publicKey(to) }).getInstructions());
    onStatus?.(`Minting ${i + 1}–${i + chunk.length} of ${recipients.length}…`);
    const signature = await signSend(k.web3, k.connection, provider, toTx(k, ixs, owner), new k.web3.PublicKey(owner), kps, onStatus);
    results.push({ signature, assets: chunk.map((to, j) => ({ address: kps[j].publicKey.toBase58(), owner: to })) });
  }
  return results;
}
