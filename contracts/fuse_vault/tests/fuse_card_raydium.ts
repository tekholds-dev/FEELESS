// FUSE Card v0.3 × the REAL Raydium CP-Swap program on a local validator (built with CPSWAP_LOCALNET_ADMIN = this wallet).
// Proves: the keeper trades only through Raydium, the trigger reads Raydium's own TWAP (a one-block pump can't fire a TP), min_out
// uses the pool's real fee tier, and the proceeds land in the OWNER's wallet. Run: see the README "Raydium integration".
import * as anchor from "@anchor-lang/core";
import { Program } from "@anchor-lang/core";
import { assert } from "chai";
import { FuseCard } from "../target/types/fuse_card";
import raydiumIdl from "./idl/raydium_cp_swap.json";

const { PublicKey, Keypair, SystemProgram, Transaction, TransactionInstruction, LAMPORTS_PER_SOL } = anchor.web3;
const BN = anchor.BN;
const TOKEN = new PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
const ATA = new PublicKey("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL");
const POOL_FEE_RECEIVER = new PublicKey("DNXgeM9EiiaAbaWvwjHj9fQQLAX5ZsfHyvmYUNRAdNC8");   // cloned from mainnet by the validator
const MINT_SIZE = 82, ACCOUNT_SIZE = 165, DEC = 6, E9 = 1_000_000_000;
const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

describe("fuse_card v0.3 × Raydium CP-Swap", () => {
  anchor.setProvider(anchor.AnchorProvider.env());
  const provider = anchor.getProvider() as anchor.AnchorProvider;
  const conn = provider.connection;
  const admin = provider.wallet as anchor.Wallet;
  const program = anchor.workspace.fuseCard as Program<FuseCard>;
  const ray = new Program(raydiumIdl as anchor.Idl, provider) as any;
  const keeper = Keypair.generate(); const bob = Keypair.generate();
  const [config] = PublicKey.findProgramAddressSync([Buffer.from("config")], program.programId);
  const cardOf = (owner: anchor.web3.PublicKey, id: number) =>
    PublicKey.findProgramAddressSync([Buffer.from("card"), owner.toBuffer(), new BN(id).toArrayLike(Buffer, "le", 8)], program.programId)[0];
  const pda = (seeds: Buffer[]) => PublicKey.findProgramAddressSync(seeds, ray.programId)[0];
  const fails = async (p: Promise<unknown>, msg: string) => { let err = ""; try { await p; } catch (e: any) { err = String(e) + " " + (e?.logs || []).join(" | "); } if (!err.includes(msg)) throw new Error(`expected ${msg}, got: ${err.slice(0, 900) || "success"}`); };
  const u64 = (n: number | bigint) => { const b = Buffer.alloc(8); b.writeBigUInt64LE(BigInt(n)); return b; };
  const bal = async (k: anchor.web3.PublicKey) => BigInt((await conn.getTokenAccountBalance(k)).value.amount);

  async function newMint() {
    const m = Keypair.generate();
    await provider.sendAndConfirm(new Transaction().add(
      SystemProgram.createAccount({ fromPubkey: admin.publicKey, newAccountPubkey: m.publicKey, lamports: await conn.getMinimumBalanceForRentExemption(MINT_SIZE), space: MINT_SIZE, programId: TOKEN }),
      new TransactionInstruction({ programId: TOKEN, keys: [{ pubkey: m.publicKey, isSigner: false, isWritable: true }], data: Buffer.concat([Buffer.from([20, DEC]), admin.publicKey.toBuffer(), Buffer.from([0])]) })), [m]);
    return m.publicKey;
  }
  async function tokenAccount(mint: anchor.web3.PublicKey, owner: anchor.web3.PublicKey) {
    const a = Keypair.generate();
    await provider.sendAndConfirm(new Transaction().add(
      SystemProgram.createAccount({ fromPubkey: admin.publicKey, newAccountPubkey: a.publicKey, lamports: await conn.getMinimumBalanceForRentExemption(ACCOUNT_SIZE), space: ACCOUNT_SIZE, programId: TOKEN }),
      new TransactionInstruction({ programId: TOKEN, keys: [{ pubkey: a.publicKey, isSigner: false, isWritable: true }, { pubkey: mint, isSigner: false, isWritable: false }], data: Buffer.concat([Buffer.from([18]), owner.toBuffer()]) })), [a]);
    return a.publicKey;
  }
  const mintTo = (mint: anchor.web3.PublicKey, dest: anchor.web3.PublicKey, amount: number) => provider.sendAndConfirm(new Transaction().add(new TransactionInstruction({ programId: TOKEN,
    keys: [{ pubkey: mint, isSigner: false, isWritable: true }, { pubkey: dest, isSigner: false, isWritable: true }, { pubkey: admin.publicKey, isSigner: true, isWritable: false }], data: Buffer.concat([Buffer.from([7]), u64(amount)]) })));

  let COIN: anchor.web3.PublicKey, QUOTE: anchor.web3.PublicKey, coinIs0 = true;
  let ammConfig: anchor.web3.PublicKey, pool: anchor.web3.PublicKey, auth: anchor.web3.PublicKey, observation: anchor.web3.PublicKey;
  let coinVault: anchor.web3.PublicKey, quoteVault: anchor.web3.PublicKey, adminCoin: anchor.web3.PublicKey, adminQuote: anchor.web3.PublicKey;
  let card: anchor.web3.PublicKey, cardCoin: anchor.web3.PublicKey, cardQuote: anchor.web3.PublicKey, bobCoin: anchor.web3.PublicKey, bobQuote: anchor.web3.PublicKey;

  // the market trades on Raydium (buy = quote → coin pushes the price up)
  const trade = (amount: number, buy: boolean) => ray.methods.swapBaseInput(new BN(amount), new BN(0)).accountsPartial({
    payer: admin.publicKey, authority: auth, ammConfig, poolState: pool, inputTokenAccount: buy ? adminQuote : adminCoin, outputTokenAccount: buy ? adminCoin : adminQuote,
    inputVault: buy ? quoteVault : coinVault, outputVault: buy ? coinVault : quoteVault, inputTokenProgram: TOKEN, outputTokenProgram: TOKEN,
    inputTokenMint: buy ? QUOTE : COIN, outputTokenMint: buy ? COIN : QUOTE, observationState: observation }).rpc();
  // hold the price for `secs`: tiny round-trips so Raydium keeps writing observations (TWAP catches up)
  const hold = async (secs: number) => { const end = Date.now() + secs * 1000; while (Date.now() < end) { await trade(1_000, true); await trade(1_000, false); await sleep(4000); } };
  const expected = (ain: bigint, rin: bigint, rout: bigint) => { const a = ain * 9975n; return (a * rout) / (rin * 10000n + a); };   // 0.25% fee tier
  const accs = (o: any = {}) => ({ keeper: keeper.publicKey, config, card, coinMint: COIN, quoteMint: QUOTE, cardCoin, cardQuote, ownerQuote: bobQuote, poolState: pool,
    cpmmAuthority: auth, ammConfig, coinVault, quoteVault, observation, swapProgram: ray.programId, tokenProgram: TOKEN, ...o });
  const minSell = async (amount: number) => (expected(BigInt(amount), await bal(coinVault), await bal(quoteVault)) * 995n) / 1000n;
  const sell = (amount: number, min: bigint, o: any = {}) =>
    program.methods.keeperSellCpmm(0, new BN(amount), new BN(min.toString()), 1).accounts(accs(o) as any).signers([keeper]).rpc();

  before(async () => {
    for (const k of [keeper, bob]) { const s = await conn.requestAirdrop(k.publicKey, 2 * LAMPORTS_PER_SOL); await conn.confirmTransaction(s, "confirmed"); }
    const a = await newMint(), b = await newMint();
    [COIN, QUOTE] = [a, b];
    coinIs0 = Buffer.compare(COIN.toBuffer(), QUOTE.toBuffer()) < 0;
    const [m0, m1] = coinIs0 ? [COIN, QUOTE] : [QUOTE, COIN];
    // Raydium: our own fee tier (0.25%, no protocol / fund / creator fee) and a 1:1 COIN/QUOTE pool with 1B each side
    const idx = Math.floor(Math.random() * 60000) + 100;
    ammConfig = pda([Buffer.from("amm_config"), Buffer.from([idx >> 8, idx & 255])]);
    await ray.methods.createAmmConfig(idx, new BN(2500), new BN(0), new BN(0), new BN(0), new BN(0)).accountsPartial({ owner: admin.publicKey, ammConfig, systemProgram: SystemProgram.programId }).rpc();
    auth = pda([Buffer.from("vault_and_lp_mint_auth_seed")]);
    pool = pda([Buffer.from("pool"), ammConfig.toBuffer(), m0.toBuffer(), m1.toBuffer()]);
    const lp = pda([Buffer.from("pool_lp_mint"), pool.toBuffer()]);
    const v0 = pda([Buffer.from("pool_vault"), pool.toBuffer(), m0.toBuffer()]), v1 = pda([Buffer.from("pool_vault"), pool.toBuffer(), m1.toBuffer()]);
    observation = pda([Buffer.from("observation"), pool.toBuffer()]);
    [coinVault, quoteVault] = coinIs0 ? [v0, v1] : [v1, v0];
    adminCoin = await tokenAccount(COIN, admin.publicKey); adminQuote = await tokenAccount(QUOTE, admin.publicKey);
    await mintTo(COIN, adminCoin, 10 * E9); await mintTo(QUOTE, adminQuote, 10 * E9);
    const lpAta = PublicKey.findProgramAddressSync([admin.publicKey.toBuffer(), TOKEN.toBuffer(), lp.toBuffer()], ATA)[0];
    await ray.methods.initialize(new BN(E9), new BN(E9), new BN(0)).accountsPartial({
      creator: admin.publicKey, ammConfig, authority: auth, poolState: pool, token0Mint: m0, token1Mint: m1, lpMint: lp,
      creatorToken0: coinIs0 ? adminCoin : adminQuote, creatorToken1: coinIs0 ? adminQuote : adminCoin, creatorLpToken: lpAta,
      token0Vault: v0, token1Vault: v1, createPoolFee: POOL_FEE_RECEIVER, observationState: observation,
      tokenProgram: TOKEN, token0Program: TOKEN, token1Program: TOKEN, associatedTokenProgram: ATA, systemProgram: SystemProgram.programId, rent: anchor.web3.SYSVAR_RENT_PUBKEY,
    }).preInstructions([anchor.web3.ComputeBudgetProgram.setComputeUnitLimit({ units: 400_000 })]).rpc();
    // FUSE Card: the ONLY swap program the keeper may use is now Raydium CP-Swap
    if (await conn.getAccountInfo(config)) await program.methods.setConfig(keeper.publicKey, false, ray.programId, 100).accounts({ admin: admin.publicKey, config } as any).rpc();
    else await program.methods.initConfig(keeper.publicKey, ray.programId, 100).accounts({ admin: admin.publicKey } as any).rpc();
    // Bob's card: one runner, TP +50%, auto TP on; 100M coins bought at 100M quote (entry price 1.0)
    await program.methods.openCard(new BN(77), [{ mint: COIN, kind: 1, tpBps: 5000, slBps: 2500 }], { autoTp: true, autoCompound: false, swapMode: false, profitAtBps: 0, slMode: 0 }, QUOTE)
      .accounts({ owner: bob.publicKey } as any).signers([bob]).rpc();
    card = cardOf(bob.publicKey, 77);
    bobCoin = await tokenAccount(COIN, bob.publicKey); bobQuote = await tokenAccount(QUOTE, bob.publicKey);
    cardCoin = await tokenAccount(COIN, card); cardQuote = await tokenAccount(QUOTE, card);
    await mintTo(COIN, bobCoin, 100_000_000);
    await program.methods.depositLeg(0, new BN(100_000_000), new BN(100_000_000)).accounts({ owner: bob.publicKey, card, ownerToken: bobCoin, cardVault: cardCoin, mint: COIN, tokenProgram: TOKEN } as any).signers([bob]).rpc();
  });

  it("no TWAP history yet → the keeper can't trade", async () => {
    await fails(sell(10_000_000, await minSell(10_000_000)), "NotTriggered");
  });

  it("a one-block pump can't fire the take-profit: spot is far from Raydium's TWAP", async () => {
    await hold(55);                       // ≥45s of observations at price ≈ 1.0
    await trade(260_000_000, true);       // buyers push spot ≈ +55% in one go
    await fails(sell(50_000_000, await minSell(50_000_000)), "NotTriggered");
  });

  it("once the TWAP agrees (+50% held), the TP sells THROUGH Raydium and pays the owner", async () => {
    await hold(70);                       // the new price holds long enough for the time-weighted price to catch up
    await fails(sell(50_000_000, 1n), "SlippageTooLoose");                       // min_out can't be looser than the pool's real fee tier
    const before = await bal(bobQuote); const min = await minSell(50_000_000);
    await sell(50_000_000, min);
    assert.isTrue((await bal(bobQuote)) - before >= min);                        // landed in Bob's wallet, ≥ min_out
    assert.equal((await program.account.card.fetch(card)).legs[0].held.toNumber(), 50_000_000);
  });

  it("only Raydium (the whitelisted program) and this pool's own vaults / oracle can be used", async () => {
    await fails(sell(1_000, 1n, { swapProgram: program.programId }), "BadSwapProgram");
    await fails(sell(1_000, 1n, { quoteVault: adminQuote }), "BadPool");
    await fails(sell(1_000, 1n, { observation: pool }), "BadPool");
    await fails(sell(1_000, 1n, { ownerQuote: adminQuote }), "NotOwnerAccount");
  });
});
