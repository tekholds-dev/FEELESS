// Devnet: point FUSE Card at Raydium CP-Swap DEVNET, keeper = this CLI wallet (devnet only). Safe to re-run.
import * as anchor from "@anchor-lang/core";
import idl from "../target/idl/fuse_card.json";
const RAYDIUM_DEVNET = new anchor.web3.PublicKey("DRaycpLY18LhpbydsBWbVJtxpNv9oXPgjRSfpF2bWpYb");
(async () => {
  const provider = anchor.AnchorProvider.env(); anchor.setProvider(provider);
  const program = new anchor.Program(idl as anchor.Idl, provider) as any;
  const [config] = anchor.web3.PublicKey.findProgramAddressSync([Buffer.from("config")], program.programId);
  const me = provider.wallet.publicKey;
  const sig = (await provider.connection.getAccountInfo(config))
    ? await program.methods.setConfig(me, false, RAYDIUM_DEVNET, 100).accounts({ admin: me, config }).rpc()
    : await program.methods.initConfig(me, RAYDIUM_DEVNET, 100).accounts({ admin: me }).rpc();
  const c = await program.account.config.fetch(config);
  console.log(JSON.stringify({ tx: sig, config: config.toBase58(), swapProgram: c.swapProgram.toBase58(), keeper: c.keeper.toBase58(), maxSlippageBps: c.maxSlippageBps, paused: c.paused }));
})().catch(e => { console.error(String(e)); process.exit(1); });
