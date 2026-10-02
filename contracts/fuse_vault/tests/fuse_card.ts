// FUSE Card v0.1 on a local validator: every rule that protects a card owner's coins.
// SPL Token instructions are hand-built (no spl-token dependency): create mint, token accounts, mint-to.
import * as anchor from "@anchor-lang/core";
import { Program } from "@anchor-lang/core";
import { assert } from "chai";
import { FuseCard } from "../target/types/fuse_card";
import { MockAmm } from "../target/types/mock_amm";

const { PublicKey, Keypair, SystemProgram, Transaction, TransactionInstruction, LAMPORTS_PER_SOL } = anchor.web3;
const BN = anchor.BN;
const TOKEN = new PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
const MINT_SIZE = 82, ACCOUNT_SIZE = 165, DEC = 6;

describe("fuse_card v0.1", () => {
  anchor.setProvider(anchor.AnchorProvider.env());
  const provider = anchor.getProvider() as anchor.AnchorProvider;
  const program = anchor.workspace.fuseCard as Program<FuseCard>;
  const amm = anchor.workspace.mockAmm as Program<MockAmm>;
  let QUOTE: anchor.web3.PublicKey;   // the card's quote coin (wSOL stand-in)
  const conn = provider.connection;
  const admin = provider.wallet as anchor.Wallet;
  const keeper = Keypair.generate(); const alice = Keypair.generate(); const mallory = Keypair.generate();
  const [config] = PublicKey.findProgramAddressSync([Buffer.from("config")], program.programId);
  const cardOf = (owner: anchor.web3.PublicKey, id: number) =>
    PublicKey.findProgramAddressSync([Buffer.from("card"), owner.toBuffer(), new BN(id).toArrayLike(Buffer, "le", 8)], program.programId)[0];
  const fails = async (p: Promise<unknown>, msg: string) => { try { await p; assert.fail("should have failed"); } catch (e: any) { assert.include(String(e), msg); } };
  const fund = async (k: anchor.web3.Keypair, sol: number) => { const s = await conn.requestAirdrop(k.publicKey, sol * LAMPORTS_PER_SOL); await conn.confirmTransaction(s, "confirmed"); };

  // ---- hand-built SPL Token helpers ----
  const u64 = (n: number | bigint) => { const b = Buffer.alloc(8); b.writeBigUInt64LE(BigInt(n)); return b; };
  async function newMint(): Promise<anchor.web3.PublicKey> {
    const m = Keypair.generate();
    const tx = new Transaction().add(
      SystemProgram.createAccount({ fromPubkey: admin.publicKey, newAccountPubkey: m.publicKey, lamports: await conn.getMinimumBalanceForRentExemption(MINT_SIZE), space: MINT_SIZE, programId: TOKEN }),
      new TransactionInstruction({ programId: TOKEN, keys: [{ pubkey: m.publicKey, isSigner: false, isWritable: true }],
        data: Buffer.concat([Buffer.from([20, DEC]), admin.publicKey.toBuffer(), Buffer.from([0])]) }));   // InitializeMint2
    await provider.sendAndConfirm(tx, [m]);
    return m.publicKey;
  }
  async function tokenAccount(mint: anchor.web3.PublicKey, owner: anchor.web3.PublicKey): Promise<anchor.web3.PublicKey> {
    const a = Keypair.generate();
    const tx = new Transaction().add(
      SystemProgram.createAccount({ fromPubkey: admin.publicKey, newAccountPubkey: a.publicKey, lamports: await conn.getMinimumBalanceForRentExemption(ACCOUNT_SIZE), space: ACCOUNT_SIZE, programId: TOKEN }),
      new TransactionInstruction({ programId: TOKEN, keys: [{ pubkey: a.publicKey, isSigner: false, isWritable: true }, { pubkey: mint, isSigner: false, isWritable: false }],
        data: Buffer.concat([Buffer.from([18]), owner.toBuffer()]) }));                                    // InitializeAccount3
    await provider.sendAndConfirm(tx, [a]);
    return a.publicKey;
  }
  async function mintTo(mint: anchor.web3.PublicKey, dest: anchor.web3.PublicKey, amount: number) {
    await provider.sendAndConfirm(new Transaction().add(new TransactionInstruction({ programId: TOKEN,
      keys: [{ pubkey: mint, isSigner: false, isWritable: true }, { pubkey: dest, isSigner: false, isWritable: true }, { pubkey: admin.publicKey, isSigner: true, isWritable: false }],
      data: Buffer.concat([Buffer.from([7]), u64(amount)]) })));                                              // MintTo
  }
  const balance = async (acc: anchor.web3.PublicKey) => Number((await conn.getTokenAccountBalance(acc)).value.amount);

  const off = { autoTp: false, autoCompound: false, swapMode: false, profitAtBps: 0, slMode: 0 };
  const leg = (mint: anchor.web3.PublicKey, kind: number, tp = 0, sl = 0) => ({ mint, kind, tpBps: tp, slBps: sl });
  let mints: anchor.web3.PublicKey[] = [];
  let card: anchor.web3.PublicKey, aliceTok: anchor.web3.PublicKey, vaultTok: anchor.web3.PublicKey, malloryTok: anchor.web3.PublicKey;
  const move = (fn: "depositLeg" | "withdrawLeg", idx: number, amount: number, o: any = {}) =>
    (fn === "depositLeg" ? (program.methods as any).depositLeg(idx, new BN(amount), new BN(amount)) : (program.methods as any).withdrawLeg(idx, new BN(amount))).accounts({ owner: alice.publicKey, card, ownerToken: aliceTok, cardVault: vaultTok, mint: mints[0], tokenProgram: TOKEN, ...o }).signers([o.signer || alice]).rpc();
  const keeperReturn = (amount: number, reason: number, o: any = {}) =>
    program.methods.keeperReturn(0, new BN(amount), reason).accounts({ keeper: keeper.publicKey, config, card, ownerToken: aliceTok, cardVault: vaultTok, mint: mints[0], tokenProgram: TOKEN, ...o } as any).signers([o.signer || keeper]).rpc();

  before(async () => {
    await Promise.all([fund(keeper, 1), fund(alice, 5), fund(mallory, 2)]);
    mints = [];
    for (let i = 0; i < 13; i++) mints.push(await newMint());
    QUOTE = await newMint();
  });

  it("config: admin + keeper, only the admin can change it", async () => {
    if (await conn.getAccountInfo(config)) await program.methods.setConfig(keeper.publicKey, false, amm.programId, 100).accounts({ admin: admin.publicKey, config } as any).rpc();   // the Raydium suite may have run first
    else await program.methods.initConfig(keeper.publicKey, amm.programId, 100).accounts({ admin: admin.publicKey } as any).rpc();
    const c = await program.account.config.fetch(config);
    assert.ok(c.admin.equals(admin.publicKey)); assert.ok(c.keeper.equals(keeper.publicKey)); assert.equal(c.paused, false);
    await fails(program.methods.setConfig(mallory.publicKey, false, amm.programId, 100).accounts({ admin: mallory.publicKey, config } as any).signers([mallory]).rpc(), "Error");
  });

  it("caps are hard-coded: traders 3 pools + 3 runners, no duplicates; HQ up to 12 in any mix", async () => {
    const tooMany = [leg(mints[0], 0), leg(mints[1], 0), leg(mints[2], 0), leg(mints[3], 0)];
    await fails(program.methods.openCard(new BN(9), tooMany, off, QUOTE).accounts({ owner: alice.publicKey } as any).signers([alice]).rpc(), "TooManyLegs");
    await fails(program.methods.openCard(new BN(9), [leg(mints[0], 0), leg(mints[0], 1)], off, QUOTE).accounts({ owner: alice.publicKey } as any).signers([alice]).rpc(), "DuplicateLeg");
    await fails(program.methods.openCard(new BN(9), [leg(mints[0], 0)], { ...off, profitAtBps: 1234 }, QUOTE).accounts({ owner: alice.publicKey } as any).signers([alice]).rpc(), "BadProfitLevel");
    const twelve = mints.slice(0, 12).map((m, i) => leg(m, i % 2));
    await program.methods.openCard(new BN(1), twelve, off, QUOTE).accounts({ owner: admin.publicKey } as any).rpc();
    const big = await program.account.card.fetch(cardOf(admin.publicKey, 1));
    assert.equal(big.legCount, 12); assert.equal(big.adminCard, true);
    await fails(program.methods.openCard(new BN(2), mints.slice(0, 13).map(m => leg(m, 0)), off, QUOTE).accounts({ owner: admin.publicKey } as any).rpc(), "Error");
  });

  it("deposit + withdraw: coins sit in the card's own account; only the owner's account can receive them", async () => {
    await program.methods.openCard(new BN(7), [leg(mints[0], 1, 5000, 2500), leg(mints[1], 0), leg(mints[2], 0)], off, QUOTE).accounts({ owner: alice.publicKey } as any).signers([alice]).rpc();
    card = cardOf(alice.publicKey, 7);
    aliceTok = await tokenAccount(mints[0], alice.publicKey);
    vaultTok = await tokenAccount(mints[0], card);                       // owned by the card PDA — no private key
    malloryTok = await tokenAccount(mints[0], mallory.publicKey);
    await mintTo(mints[0], aliceTok, 1_000_000);
    await move("depositLeg", 0, 600_000);
    assert.equal(await balance(vaultTok), 600_000); assert.equal((await program.account.card.fetch(card)).legs[0].held.toNumber(), 600_000);
    await fails(move("withdrawLeg", 0, 10, { ownerToken: malloryTok }), "NotOwnerAccount");       // never to someone else
    await fails(move("withdrawLeg", 0, 700_000), "InsufficientHeld");
    await fails(move("withdrawLeg", 0, 10, { mint: mints[1] }), "WrongMint");
    await move("withdrawLeg", 0, 100_000);
    assert.equal(await balance(aliceTok), 500_000); assert.equal(await balance(vaultTok), 500_000);
  });

  it("keeper: only when the owner switched auto on, only back to the owner, never while paused", async () => {
    await fails(keeperReturn(10, 1), "AutomationOff");                                     // auto TP is off
    await fails(program.methods.setToggles({ ...off, autoTp: true }).accounts({ owner: mallory.publicKey, card } as any).signers([mallory]).rpc(), "Error");   // only the owner
    await program.methods.setToggles({ ...off, autoTp: true, profitAtBps: 5000 }).accounts({ owner: alice.publicKey, card } as any).signers([alice]).rpc();
    await fails(keeperReturn(10, 1, { keeper: mallory.publicKey, signer: mallory }), "AutomationOff");   // not the configured keeper
    await fails(keeperReturn(10, 1, { ownerToken: malloryTok }), "NotOwnerAccount");
    await fails(keeperReturn(10, 4), "AutomationOff");                                     // auto-compound still off
    await fails(keeperReturn(10, 9), "BadReason");
    await keeperReturn(200_000, 1);                                                        // take-profit → owner's wallet
    assert.equal(await balance(aliceTok), 700_000); assert.equal(await balance(vaultTok), 300_000);
    await program.methods.setConfig(keeper.publicKey, true, amm.programId, 100).accounts({ admin: admin.publicKey, config } as any).rpc();
    await fails(keeperReturn(10, 3), "Paused");
    await move("withdrawLeg", 0, 50_000);                                                  // the owner can ALWAYS exit, even paused
    await program.methods.setConfig(keeper.publicKey, false, amm.programId, 100).accounts({ admin: admin.publicKey, config } as any).rpc();
    await program.methods.setToggles({ ...off, autoCompound: true, profitAtBps: 2500 }).accounts({ owner: alice.publicKey, card } as any).signers([alice]).rpc();
    await keeperReturn(50_000, 4);                                                         // auto-compound: standing order, to the owner
    assert.equal(await balance(aliceTok), 800_000);
  });

  it("close: only an empty card closes, rent back to the owner", async () => {
    await fails(program.methods.closeCard().accounts({ owner: alice.publicKey, card } as any).signers([alice]).rpc(), "NotEmpty");
    await move("withdrawLeg", 0, 200_000);
    await program.methods.closeCard().accounts({ owner: alice.publicKey, card } as any).signers([alice]).rpc();
    assert.isNull(await conn.getAccountInfo(card));
    assert.equal(await balance(aliceTok), 1_000_000);                                      // every token came home
  });

  // ---- v0.2: the keeper TRADES — only on-chain triggers, only the whitelisted swap program, payouts only to the owner ----
  describe("keeper trading (v0.2, mock AMM)", () => {
    const bob = Keypair.generate();
    let COIN: anchor.web3.PublicKey, pool: anchor.web3.PublicKey, poolCoin: anchor.web3.PublicKey, poolQuote: anchor.web3.PublicKey;
    let bobCoin: anchor.web3.PublicKey, bobQuote: anchor.web3.PublicKey, cardB: anchor.web3.PublicKey, cardCoin: anchor.web3.PublicKey, cardQuote: anchor.web3.PublicKey;
    let adminCoin: anchor.web3.PublicKey, adminQuote: anchor.web3.PublicKey;
    const E9 = 1_000_000_000;
    const out = (ain: bigint, rin: bigint, rout: bigint) => { const a = ain * 9970n; return (a * rout) / (rin * 10000n + a); };
    const bal = async (k: anchor.web3.PublicKey) => BigInt((await conn.getTokenAccountBalance(k)).value.amount);
    // a market move: the admin trades against the pool (sell = coin → quote pushes the price down)
    const trade = async (amount: number, sell: boolean) => amm.methods.swap(new BN(amount), new BN(1), sell)
      .accounts({ user: admin.publicKey, pool, vaultA: poolCoin, vaultB: poolQuote, userIn: sell ? adminCoin : adminQuote, userOut: sell ? adminQuote : adminCoin, tokenProgram: TOKEN } as any).rpc();
    const accs = (o: any = {}) => ({ keeper: keeper.publicKey, config, card: cardB, coinMint: COIN, quoteMint: QUOTE, cardCoin, cardQuote, ownerQuote: bobQuote,
      pool, poolCoinVault: poolCoin, poolQuoteVault: poolQuote, swapProgram: amm.programId, tokenProgram: TOKEN, ...o });
    const minSell = async (amount: number) => (out(BigInt(amount), await bal(poolCoin), await bal(poolQuote)) * 995n) / 1000n;
    const minBuy = async (amount: number) => (out(BigInt(amount), await bal(poolQuote), await bal(poolCoin)) * 995n) / 1000n;
    const sell = (amount: number, min: bigint, reason: number, o: any = {}) =>
      program.methods.keeperSell(0, new BN(amount), new BN(min.toString()), reason).accounts(accs(o) as any).signers([o.signer || keeper]).rpc();
    const buy = (amount: number, min: bigint, reason: number) =>
      program.methods.keeperBuy(0, new BN(amount), new BN(min.toString()), reason).accounts(accs() as any).signers([keeper]).rpc();
    const legOf = async () => (await program.account.card.fetch(cardB)).legs[0];

    before(async () => {
      await fund(bob, 2);
      COIN = await newMint();
      [pool] = PublicKey.findProgramAddressSync([Buffer.from("pool"), COIN.toBuffer(), QUOTE.toBuffer()], amm.programId);
      poolCoin = await tokenAccount(COIN, pool); poolQuote = await tokenAccount(QUOTE, pool);
      await amm.methods.initPool(poolCoin, poolQuote).accounts({ payer: admin.publicKey, mintA: COIN, mintB: QUOTE } as any).rpc();
      await mintTo(COIN, poolCoin, E9); await mintTo(QUOTE, poolQuote, E9);                    // price 1 quote per coin
      adminCoin = await tokenAccount(COIN, admin.publicKey); adminQuote = await tokenAccount(QUOTE, admin.publicKey);
      await mintTo(COIN, adminCoin, 5 * E9); await mintTo(QUOTE, adminQuote, 5 * E9);
      // Bob's card: one runner, TP +50%, SL −25%, auto on, stops PAY OUT; he deposits 100M coins bought at 100M quote
      await program.methods.openCard(new BN(20), [leg(COIN, 1, 5000, 2500)], { ...off, autoTp: true }, QUOTE).accounts({ owner: bob.publicKey } as any).signers([bob]).rpc();
      cardB = cardOf(bob.publicKey, 20);
      bobCoin = await tokenAccount(COIN, bob.publicKey); bobQuote = await tokenAccount(QUOTE, bob.publicKey);
      cardCoin = await tokenAccount(COIN, cardB); cardQuote = await tokenAccount(QUOTE, cardB);
      await mintTo(COIN, bobCoin, 100_000_000);
      await program.methods.depositLeg(0, new BN(100_000_000), new BN(100_000_000)).accounts({ owner: bob.publicKey, card: cardB, ownerToken: bobCoin, cardVault: cardCoin, mint: COIN, tokenProgram: TOKEN } as any).signers([bob]).rpc();
    });

    it("take-profit only fires when the POOL says +50% — then the SOL lands in the owner's wallet", async () => {
      await fails(sell(50_000_000, await minSell(50_000_000), 1), "NotTriggered");          // price 1.0: no TP
      await trade(260_000_000, false);                                                       // buyers push price ≈ +50%
      await fails(sell(50_000_000, 1n, 1), "SlippageTooLoose");                              // keeper can't accept a bad price
      const before = await bal(bobQuote); const min = await minSell(50_000_000);
      await sell(50_000_000, min, 1);
      assert.isTrue((await bal(bobQuote)) - before >= min);                                  // paid to Bob, ≥ min_out
      assert.equal((await legOf()).held.toNumber(), 50_000_000);
    });

    it("only the whitelisted swap program and the real pool vaults can be used", async () => {
      await fails(sell(1_000, 1n, 1, { swapProgram: program.programId }), "BadSwapProgram");
      await fails(sell(1_000, 1n, 1, { poolQuoteVault: adminQuote }), "BadPool");
      await fails(sell(1_000, 1n, 1, { ownerQuote: adminQuote }), "NotOwnerAccount");        // payout never to anyone else
      await fails(sell(1_000, 1n, 1, { keeper: mallory.publicKey, signer: mallory }), "AutomationOff");
    });

    it("stop in PARK mode: sold to SOL, parked on the card, bought back only once price is back at entry", async () => {
      await program.methods.setToggles({ ...off, autoTp: true, slMode: 1 }).accounts({ owner: bob.publicKey, card: cardB } as any).signers([bob]).rpc();
      await fails(sell(10_000_000, await minSell(10_000_000), 2), "NotTriggered");          // still up: no stop
      await trade(900_000_000, true);                                                        // sellers dump it under −25%
      const before = await bal(bobQuote);
      await sell(50_000_000, await minSell(50_000_000), 2);
      const l = await legOf();
      assert.equal(l.held.toNumber(), 0); assert.isAbove(l.parked.toNumber(), 0);
      assert.equal(await bal(bobQuote), before);                                             // parked, not paid out
      await fails(buy(l.parked.toNumber(), await minBuy(l.parked.toNumber()), 5), "NotTriggered");   // below entry: wait
      await trade(1_200_000_000, false);                                                     // buyers come back over entry
      await buy(l.parked.toNumber(), await minBuy(l.parked.toNumber()), 5);
      const back = await legOf();
      assert.equal(back.parked.toNumber(), 0); assert.isAbove(back.held.toNumber(), 0);
    });

    it("HOLD mode never sells on a stop; the owner can always pull parked SOL and the coins", async () => {
      await program.methods.setToggles({ ...off, autoTp: true, slMode: 2 }).accounts({ owner: bob.publicKey, card: cardB } as any).signers([bob]).rpc();
      await trade(2_500_000_000, true);
      await fails(sell(1_000_000, await minSell(1_000_000), 2), "AutomationOff");
      const l = await legOf();
      await program.methods.withdrawLeg(0, l.held).accounts({ owner: bob.publicKey, card: cardB, ownerToken: bobCoin, cardVault: cardCoin, mint: COIN, tokenProgram: TOKEN } as any).signers([bob]).rpc();
      await program.methods.closeCard().accounts({ owner: bob.publicKey, card: cardB } as any).signers([bob]).rpc();
      assert.isNull(await conn.getAccountInfo(cardB));
    });
  });
});
