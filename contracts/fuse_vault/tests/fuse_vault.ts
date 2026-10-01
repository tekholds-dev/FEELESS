// FUSE Vault v0.1 on a local validator: every rule that protects money.
import * as anchor from "@anchor-lang/core";
import { Program } from "@anchor-lang/core";
import { assert } from "chai";
import { FuseVault } from "../target/types/fuse_vault";

const { PublicKey, Keypair, SystemProgram, LAMPORTS_PER_SOL } = anchor.web3;
const BN = anchor.BN;

describe("fuse_vault v0.1", () => {
  anchor.setProvider(anchor.AnchorProvider.env());
  const provider = anchor.getProvider() as anchor.AnchorProvider;
  const program = anchor.workspace.fuseVault as Program<FuseVault>;
  const conn = provider.connection;

  const vaultId = new BN(Date.now() % 1_000_000);
  const [vault] = PublicKey.findProgramAddressSync([Buffer.from("vault"), vaultId.toArrayLike(Buffer, "le", 8)], program.programId);
  const [vaultSol] = PublicKey.findProgramAddressSync([Buffer.from("vault_sol"), vault.toBuffer()], program.programId);
  const depositorOf = (u: anchor.web3.PublicKey) => PublicKey.findProgramAddressSync([Buffer.from("depositor"), vault.toBuffer(), u.toBuffer()], program.programId)[0];
  const alice = Keypair.generate(); const bob = Keypair.generate(); const feeWallet = Keypair.generate(); const stranger = Keypair.generate();
  const pools = [
    { pool: Keypair.generate().publicKey, kind: 0, weightBps: 4000, capBps: 200, rangeBps: 0 },     // v2 SOL-USDC
    { pool: Keypair.generate().publicKey, kind: 1, weightBps: 4000, capBps: 200, rangeBps: 2000 },  // v3 FEELESS-SOL ±20%
    { pool: Keypair.generate().publicKey, kind: 0, weightBps: 2000, capBps: 100, rangeBps: 0 },     // v2 PAID-SOL
  ];
  const cfg = (o = {}) => ({ keeper: provider.wallet.publicKey, feeWallet: feeWallet.publicKey, pools, mgmtBps: 0, perfBps: 1000, ...o });
  const fund = async (k: anchor.web3.Keypair, sol: number) => { const sig = await conn.requestAirdrop(k.publicKey, sol * LAMPORTS_PER_SOL); await conn.confirmTransaction(sig, "confirmed"); };
  const deposit = (u: anchor.web3.Keypair, lamports: number) => program.methods.deposit(new BN(lamports)).accounts({ user: u.publicKey, vault, vaultSol } as any).signers([u]).rpc();
  const withdraw = (u: anchor.web3.Keypair, shares: number) => program.methods.withdraw(new BN(shares)).accounts({ user: u.publicKey, vault, vaultSol, depositor: depositorOf(u.publicKey), owner: u.publicKey } as any).signers([u]).rpc();
  const fails = async (p: Promise<unknown>, msg: string) => { try { await p; assert.fail("should have failed"); } catch (e: any) { assert.include(String(e), msg); } };

  before(async () => { await Promise.all([fund(alice, 20), fund(bob, 20), fund(stranger, 2), fund(feeWallet, 1)]); });

  it("initializes with 3 pools (v2 + v3) and on-chain fee caps", async () => {
    await fails(program.methods.initialize(new BN(vaultId.toNumber() + 1), cfg({ perfBps: 9000 })).accounts({ admin: provider.wallet.publicKey } as any).rpc(), "FeeTooHigh");
    await program.methods.initialize(vaultId, cfg()).accounts({ admin: provider.wallet.publicKey } as any).rpc();
    const v = await program.account.vault.fetch(vault);
    assert.equal(v.poolCount, 3); assert.equal(v.pools[1].kind, 1); assert.equal(v.perfBps, 1000);
    assert.ok(v.feeWallet.equals(feeWallet.publicKey));
  });

  it("only the admin can change config or pause", async () => {
    await fails(program.methods.setPaused(true).accounts({ admin: stranger.publicKey, vault } as any).signers([stranger]).rpc(), "Unauthorized");
    await fails(program.methods.configure(cfg({ pools: [...pools, pools[0]] })).accounts({ admin: provider.wallet.publicKey, vault } as any).rpc(), "BadPoolCount");
  });

  it("deposits mint shares at NAV; yield raises NAV without diluting anyone", async () => {
    await deposit(alice, 5 * LAMPORTS_PER_SOL);
    let a = await program.account.depositor.fetch(depositorOf(alice.publicKey));
    assert.equal(a.shares.toNumber(), 5 * LAMPORTS_PER_SOL);                        // first deposit 1:1
    // yield: 5 SOL lands in the vault (stand-in for pool fees) → NAV 10, 5 shares → 2 SOL/share
    const tx = new anchor.web3.Transaction().add(SystemProgram.transfer({ fromPubkey: bob.publicKey, toPubkey: vaultSol, lamports: 5 * LAMPORTS_PER_SOL }));
    await provider.sendAndConfirm(tx, [bob]);
    await deposit(bob, 4 * LAMPORTS_PER_SOL);
    const b = await program.account.depositor.fetch(depositorOf(bob.publicKey));
    assert.equal(b.shares.toNumber(), 2 * LAMPORTS_PER_SOL);                        // 4 SOL at 2 SOL/share
  });

  it("performance fee goes only to the configured fee wallet, only above the high-water mark", async () => {
    await fails(program.methods.collectFees().accounts({ vault, vaultSol, feeWallet: stranger.publicKey } as any).rpc(), "WrongFeeWallet");
    await program.methods.collectFees().accounts({ vault, vaultSol, feeWallet: feeWallet.publicKey } as any).rpc();   // first call sets the mark
    const before = await conn.getBalance(feeWallet.publicKey);
    const tx = new anchor.web3.Transaction().add(SystemProgram.transfer({ fromPubkey: bob.publicKey, toPubkey: vaultSol, lamports: 1.4 * LAMPORTS_PER_SOL }));
    await provider.sendAndConfirm(tx, [bob]);                                        // +1.4 SOL yield on 14 SOL NAV
    await program.methods.collectFees().accounts({ vault, vaultSol, feeWallet: feeWallet.publicKey } as any).rpc();
    const got = (await conn.getBalance(feeWallet.publicKey)) - before;
    assert.approximately(got, 0.14 * LAMPORTS_PER_SOL, 1000);                        // 10% of the 1.4 SOL gain
    const again = await conn.getBalance(feeWallet.publicKey);
    await program.methods.collectFees().accounts({ vault, vaultSol, feeWallet: feeWallet.publicKey } as any).rpc();
    assert.equal(await conn.getBalance(feeWallet.publicKey), again);                  // no new gain → no fee
  });

  it("withdraw pays SOL at NAV; can't take more than you own; pause stops deposits but never exits", async () => {
    await fails(withdraw(alice, 6 * LAMPORTS_PER_SOL), "InsufficientShares");
    await fails(program.methods.withdraw(new BN(1)).accounts({ user: stranger.publicKey, vault, vaultSol, depositor: depositorOf(alice.publicKey), owner: alice.publicKey } as any).signers([stranger]).rpc(), "Error");
    await program.methods.setPaused(true).accounts({ admin: provider.wallet.publicKey, vault } as any).rpc();
    await fails(deposit(bob, LAMPORTS_PER_SOL), "Paused");
    const before = await conn.getBalance(alice.publicKey);
    await withdraw(alice, 5 * LAMPORTS_PER_SOL);
    const got = (await conn.getBalance(alice.publicKey)) - before;
    assert.isAbove(got, 9.5 * LAMPORTS_PER_SOL);                                     // her 5 shares grew with the yield
    const v = await program.account.vault.fetch(vault);
    assert.equal(v.totalShares.toNumber(), 2 * LAMPORTS_PER_SOL);                    // only bob's shares remain
  });
});
