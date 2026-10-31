"""🎫 THE AGENT PASS (owner 2026-10-31): a numbered Metaplex Core NFT for one agent, minted to its OWNER's wallet (never the agent's), after its
recovery PIN is confirmed. The owner's wallet builds, pays and signs it in the browser (lib/metaplexCore.js); FEELESS never holds it.
· a one-time mint fee to the FEELESS fee wallet, in the same transaction — HQ sets it, default 2× what Solana charges for the asset
· a 10% royalty to the FEELESS fee wallet on every resale, written into the asset; its update authority is the fee wallet, so no holder can
  strip the royalty before a sale (secure resale here later, or on any marketplace that honours Core royalties)
· the server only records a Pass it has checked on-chain: the owner signed, the fee reached FEELESS, a Core asset was created, no error.
Pure, tested (tests/test_agent_pass.py)."""

CORE_PROGRAM = 'CoREENxT6tW1HoK8ypY1SxRMZTcVPm7R94rH4PZNhX7d'
SYSTEM_PROGRAM = '11111111111111111111111111111111'
ROYALTY_BPS = 1000            # 10% to FEELESS on every resale
ASSET_BYTES = 420             # a Core asset with the Royalties plugin + a ~60-char name + ~90-char uri (rent is paid once, by the owner)
TX_FEE_LAMPORTS = 10_000      # signature + a little priority
FEE_MULT = 2                  # the default mint fee: 2× the provider's cost


def provider_lamports(rent_lamports):
    """What Solana itself charges for one Pass: the asset's rent + the network fee."""
    return int(rent_lamports or 0) + TX_FEE_LAMPORTS


def fee_lamports(provider, override=0):
    """FEELESS's one-time mint fee: HQ's own number when set (> 0), else FEE_MULT × the provider's cost."""
    return int(override) if int(override or 0) > 0 else int(provider) * FEE_MULT


def name_of(number, agent_name):
    return f"FEELESS Agent #{int(number):04d} · {str(agent_name or 'Agent')[:28]}"[:60]


def metadata(site, cat, number, image_url):
    """The Pass's metadata JSON (hosted next to coin launches' token-meta): its picture, number and record — never a secret."""
    b = cat.get('brainsCfg') or {}
    return {'name': name_of(number, cat.get('name')), 'symbol': 'FAGENT', 'image': image_url,
            'description': f"The Agent Pass for @{cat.get('handle') or 'agent'} on FEELESS — whoever holds it holds the agent.",
            'external_url': f"{site}/terminal/feecat/agents?agent={cat.get('id')}",
            'attributes': [{'trait_type': 'Number', 'value': int(number)}, {'trait_type': 'Kind', 'value': b.get('kind') or 'trading'},
                           {'trait_type': 'Minds', 'value': ' + '.join(str(m).split('/')[-1] for m in (b.get('brains') or [])[:2]) or 'rules'},
                           {'trait_type': 'Level', 'value': int(cat.get('level') or 1)}],
            'properties': {'files': [{'uri': image_url, 'type': 'image/png'}], 'category': 'image'}}


def _keys(tx):
    msg = ((tx or {}).get('transaction') or {}).get('message') or {}
    return [k.get('pubkey') if isinstance(k, dict) else k for k in msg.get('accountKeys') or []], msg


def check_mint(tx, owner, fee_wallet, fee, asset):
    """A jsonParsed getTransaction → None when it is a good Pass mint, else what is wrong (shown to the owner)."""
    if not tx:
        return 'That transaction was not found yet — wait a few seconds and confirm again.'
    if (tx.get('meta') or {}).get('err'):
        return 'That transaction failed on-chain — nothing was minted.'
    keys, msg = _keys(tx)
    signers = [k.get('pubkey') for k in msg.get('accountKeys') or [] if isinstance(k, dict) and k.get('signer')]
    if owner not in signers:
        return 'That mint was not signed by this agent\'s owner wallet.'
    if asset not in keys:
        return 'That transaction did not create this Pass.'
    ixs = msg.get('instructions') or []
    if not any(ix.get('programId') == CORE_PROGRAM for ix in ixs):
        return 'That is not a Metaplex Core mint.'
    paid = sum(int(((ix.get('parsed') or {}).get('info') or {}).get('lamports') or 0) for ix in ixs
               if ix.get('programId') == SYSTEM_PROGRAM and (ix.get('parsed') or {}).get('type') == 'transfer'
               and ((ix.get('parsed') or {}).get('info') or {}).get('source') == owner and ((ix.get('parsed') or {}).get('info') or {}).get('destination') == fee_wallet)
    if paid < int(fee):
        return 'The mint fee did not reach FEELESS in that transaction.'
    return None
