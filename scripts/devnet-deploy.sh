#!/usr/bin/env bash
# FUSE Card → DEVNET (GO_LIVE B·3). Plain build only (never fast-twap). Needs ~3 devnet SOL on your Solana CLI wallet:
#   https://faucet.solana.com  (paste the address this script prints)
set -euo pipefail
cd "$(dirname "$0")/../contracts/fuse_vault"
ME=$(solana-keygen pubkey ~/.config/solana/id.json)
echo "Deployer: $ME   devnet balance: $(solana balance -u devnet)"
anchor build -p fuse_card                                   # plain build (no --features): the 300s TWAP window
solana program deploy -u devnet target/deploy/fuse_card.so --program-id target/deploy/fuse_card-keypair.json
echo "Deployed fuse_card $(solana-keygen pubkey target/deploy/fuse_card-keypair.json) on devnet."
echo "Next: init_config(keeper, swap_program = DRaycpLY18LhpbydsBWbVJtxpNv9oXPgjRSfpF2bWpYb, max_slippage_bps = 100), open one card on a devnet Raydium pool."
