"""🔑 What FEELESS still needs from a human (owner list, K01): which provider keys exist, by name only, and what each one unlocks.
'Set' means a value is present. It says nothing about balance, plan or quota: nothing is called from here. A value or a hint of one never leaves this file."""

PROVIDERS = [
    ('Helius RPC', 'Solana reads, trade tape, charts', ('HELIUS_RPC_URL', 'HELIUS_API_KEY'), 'any', 'dashboard.helius.dev'),
    ('Alchemy RPC', 'Backup Solana RPC and candles', ('ALCHEMY_API_KEY',), 'all', 'dashboard.alchemy.com'),
    ('Jupiter keys', 'Swaps, prices and Lend, past the free rate limit', ('JUPITER_API_KEY', 'JUPITER_READ_KEY'), 'any', 'portal.jup.ag'),
    ('OpenRouter', 'Paid models for agents', ('OPENROUTER_API_KEY',), 'all', 'openrouter.ai'),
    ('Groq', 'Free backup model', ('GROQ_API_KEY',), 'all', 'console.groq.com'),
    ('Steel', 'Agent cloud browsers', ('STEEL_API_KEY',), 'all', 'steel.dev'),
    ('Browserless', 'First browser fallback', ('BROWSERLESS_API_KEY',), 'all', 'browserless.io'),
    ('Browserbase', 'Second browser fallback', ('BROWSERBASE_API_KEY', 'BROWSERBASE_PROJECT_ID'), 'all', 'browserbase.com'),
    ('Circle', 'FEELESS wallets', ('CIRCLE_API_KEY',), 'all', 'console.circle.com'),
    ('Dropbox', 'Agent cloud storage', ('DROPBOX_APP_KEY', 'DROPBOX_APP_SECRET'), 'all', 'dropbox.com/developers'),
    ('Google Drive', 'Agent cloud storage', ('GOOGLE_OAUTH_CLIENT_ID', 'GOOGLE_OAUTH_CLIENT_SECRET'), 'all', 'console.cloud.google.com'),
    ('Public site URL', 'Agent Pass, sign-in callbacks, Mini App', ('PUBLIC_SITE_URL',), 'all', 'your host'),
    ('DFlow', 'Kalshi trading on the Perps desk', ('DFLOW_API_KEY',), 'all', 'dflow.net'),
    ('SnapTrade', 'Any-broker link', ('SNAPTRADE_CLIENT_ID', 'SNAPTRADE_CONSUMER_KEY'), 'all', 'snaptrade.com'),
    ('LaunchLab', 'LaunchLab launches', ('LAUNCHLAB_API_URL',), 'all', 'raydium.io'),
    ('X sign-in', 'Sign in with X', ('X_CLIENT_ID', 'X_CLIENT_SECRET'), 'all', 'developer.x.com'),
    ('Telegram', 'Bots, group posts, Mini App', ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_GROUP_ID', 'TELEGRAM_APP_URL'), 'all', 'BotFather'),
    ('Pump callouts', 'Pump callouts in the chart rail', ('PUMP_CALLOUT_TOKEN',), 'all', 'pump.fun'),
    ('Crypto.com', 'Crypto.com Exchange door', ('CRYPTO_COM_API_KEY', 'CRYPTO_COM_API_SECRET'), 'all', 'crypto.com/exchange'),
]


def status(env):
    """→ rows for HQ, not-ready first. Names and booleans only."""
    rows = []
    for name, unlocks, keys, rule, where in PROVIDERS:
        have = [k for k in keys if env.get(k)]
        ready = bool(have) if rule == 'any' else len(have) == len(keys)
        rows.append({'name': name, 'unlocks': unlocks, 'ready': ready, 'keys': list(keys), 'missing': [] if ready else [k for k in keys if not env.get(k)], 'where': where})
    rows.sort(key=lambda r: r['ready'])
    return {'rows': rows, 'ready': sum(r['ready'] for r in rows), 'total': len(rows)}


KEYS = {k for _, _, keys, _, _ in PROVIDERS for k in keys}


def clean_key(name, value):
    """A key the owner typed → (name, value), or ValueError. Only names on the list above, one line, no spaces at the edges. Pure."""
    name = str(name or ''); value = str(value or '').strip()
    if name not in KEYS:
        raise ValueError('That is not a provider key.')
    if not value or len(value) > 4096 or any(c in value for c in '\r\n\0'):
        raise ValueError('That value does not look right.')
    return name, value
