"""🎨 LOOKS (owner 2026-11-11: "add more advanced palettes … users can't copy from our files but have access to build the best"). Pure.

A look re-skins the whole site (owner 2026-11-12: Obsidian in Feeless Green is the default; every older look is one Classic row): surfaces, lines, text, the brand family (accent, its bright and deep shades, the gradient tail, a tint, a dark)
and a third light for the ambient layer. The four FREE looks ship in the site bundle (anyone may wear them, signed in
or not). The ADVANCED looks' colour sets are sent only to wallets that unlocked them (FEELESS staff, or $1,000+ held across $FEE coins), so
they are not in the public bundle to lift. Everyone sees their name, line and four swatches."""

FEELESS, FREE, HOLDER, ELITE = 'feeless', 'free', 'holder', 'elite'   # FEELESS = the owner's pick (2026-11-12): Obsidian · Desk · Pit in Feeless Green, the main row; ELITE (owner 2026-11-11: "grown man options, no kiddy cartoon") is open to everyone

# id: (name, tier, line, ambient, tokens). logoHue = the CSS hue-rotate (measured by eye, 2026-11-11) that turns the green logo art into the look's accent
_GREEN = {'accent': '#19e68c', 'hi': '#4df0a8', 'deep': '#0fbf72', 'tail': '#2ad4c8', 'tint': '#a6f5d0', 'dark': '#08995a', 'ink': '#04140c', 'third': '#4aa3ff', 'logoHue': 8, 'edition': 'elite'}
LOOKS = {
    # 🟢 THE PICK (owner 2026-11-12, look lab v2): one green, three layouts. layout = <html data-layout> (styles/looks.css): obsidian = the trade is the page,
    # desk = menu bar + clock + window chrome + your rank / quests widgets + a dock, pit = the coin's room chat beside the chart on Trade.
    'obsidian': ('Obsidian', FEELESS, 'Near-black, hairlines, one giant number. Calm and expensive; the trade is the whole page.', 'obsidian',
                 {'bg': '#09090b', 's1': '#111114', 's2': '#18181c', 'line': '#1f1f23', 'lineHi': '#3a3a41', 'text': '#eeeef1', 'dim': '#86868f', **_GREEN, 'layout': 'obsidian'}),
    'desk': ('Desk', FEELESS, 'The agent desk look on the whole site: glass panels, small dense type, a smoke / aurora / grid / film background, the menu bar, your rank and quests as widgets and a dock.', 'desk',
             {'bg': '#07080c', 's1': '#12141b', 's2': '#191c25', 'line': '#1e2129', 'lineHi': '#3a3e4b', 'text': '#eceef4', 'dim': '#868b99', **_GREEN, 'layout': 'desk'}),
    'pit': ('Pit', FEELESS, "The trading floor: the coin's room chat runs beside the candles, with the room's live trades. Your crew is here.", 'pit',
            {'bg': '#08090b', 's1': '#101215', 's2': '#171a1e', 'line': '#1e2125', 'lineHi': '#3a3e45', 'text': '#ecedef', 'dim': '#858a92', **_GREEN, 'layout': 'pit'}),
    'carbon': ('Carbon', FEELESS, 'Graphite and one indigo line. Quiet surfaces, sharp type, nothing that moves without a reason.', 'carbon',
               {'bg': '#0b0c0e', 's1': '#111216', 's2': '#17181d', 'line': '#23252b', 'lineHi': '#3d404a', 'text': '#f7f8f8', 'dim': '#8a8f98', 'accent': '#5e6ad2', 'hi': '#7c86e8', 'deep': '#4a55c0', 'tail': '#8b93ff', 'tint': '#b4baf5', 'dark': '#3a438f', 'ink': '#ffffff', 'third': '#26b5ce', 'logoHue': 75, 'edition': 'elite'}),
}
DEFAULT = 'obsidian'
# 🧹 Slice 34 (owner 2026-11-20): only Obsidian (default), Desk, Pit and Carbon stay. Anyone still wearing a retired look wears Obsidian.
RETIRED = frozenset({'plasma', 'molten', 'neon', 'holo', 'aurora', 'bloodmoon', 'vapor', 'ghost', 'amber', 'titanium', 'ledger'})


def allowed(look_id, eligible):
    """May this wallet wear it? Free looks: anyone. Advanced: only an unlocked wallet."""
    row = LOOKS.get(look_id)
    return bool(row) and (row[1] in (FEELESS, FREE, ELITE) or bool(eligible))


def catalog(eligible):
    """→ every look's card. Its full colour set only where this wallet may wear it (an advanced look's palette never leaves for a locked wallet)."""
    out = []
    for k, (name, tier, line, amb, t) in LOOKS.items():
        ok = allowed(k, eligible)
        out.append({'id': k, 'name': name, 'tier': tier, 'line': line, 'ambient': amb, 'swatch': [t['accent'], t['tail'], t['third'], t['bg']],
                    'locked': not ok, **({'tokens': dict(t)} if ok else {})})
    return out


def wear(look_id, eligible):
    """→ (id, tokens, ambient) to apply, or None when the look is unknown or locked for this wallet. A retired look → Obsidian."""
    if look_id in RETIRED:
        look_id = DEFAULT
    if not allowed(look_id, eligible):
        return None
    name, tier, line, amb, t = LOOKS[look_id]
    return {'id': look_id, 'name': name, 'ambient': amb, 'tokens': dict(t)}
