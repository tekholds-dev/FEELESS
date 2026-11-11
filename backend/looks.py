"""🎨 LOOKS (owner 2026-11-11: "add more advanced palettes … users can't copy from our files but have access to build the best"). Pure.

A look re-skins the whole site: surfaces, lines, text, the brand family (accent, its bright and deep shades, the gradient tail, a tint, a dark)
and a third light for the ambient layer. PLASMA is the default. The four FREE looks ship in the site bundle (anyone may wear them, signed in
or not). The ADVANCED looks' colour sets are sent only to wallets that unlocked them (FEELESS staff, or $1,000+ held across $FEE coins), so
they are not in the public bundle to lift. Everyone sees their name, line and four swatches."""

FREE, HOLDER = 'free', 'holder'

# id: (name, tier, line, ambient, tokens)
LOOKS = {
    'plasma': ('Plasma', FREE, 'Violet to hot pink plasma on deep space. Liquid gradients, glowing glass.', 'plasma',
               {'bg': '#08051a', 's1': '#120b2c', 's2': '#1a1140', 'line': '#2a1f55', 'lineHi': '#4b3596', 'text': '#f2eeff', 'dim': '#aaa1c9',
                'accent': '#9b6bff', 'hi': '#b48cff', 'deep': '#7c4dff', 'tail': '#ff6fbf', 'tint': '#c9a8ff', 'dark': '#5b33c9', 'ink': '#12081f', 'third': '#3ee7ff'}),
    'molten': ('Molten', FREE, 'Molten gold and ember orange on black metal. Rising sparks, heat glow.', 'molten',
               {'bg': '#0b0704', 's1': '#170f08', 's2': '#22160c', 'line': '#3a2a12', 'lineHi': '#7a5418', 'text': '#fff4e2', 'dim': '#cdb393',
                'accent': '#ffb020', 'hi': '#ffc95a', 'deep': '#e0780f', 'tail': '#ff5a1f', 'tint': '#ffe08a', 'dark': '#a8560a', 'ink': '#2a1400', 'third': '#ffe08a'}),
    'neon': ('Neon Grid', FREE, 'Cyber terminal: cyan and magenta on a moving grid, scanlines, glitch.', 'neon',
             {'bg': '#02060b', 's1': '#061019', 's2': '#0a1826', 'line': '#0d3340', 'lineHi': '#00a8b8', 'text': '#e6fbff', 'dim': '#86aebd',
              'accent': '#00f0ff', 'hi': '#6ff7ff', 'deep': '#00b8d4', 'tail': '#ff2bd6', 'tint': '#a8fbff', 'dark': '#00788a', 'ink': '#00141a', 'third': '#faff00'}),
    'holo': ('Holo Chrome', FREE, 'Iridescent ice chrome, frosted glass, slow holographic shimmer.', 'holo',
             {'bg': '#06080d', 's1': '#0d121c', 's2': '#141b29', 'line': '#26324a', 'lineHi': '#5a6f99', 'text': '#f3f7ff', 'dim': '#a3b1c8',
              'accent': '#8fd3ff', 'hi': '#b6e3ff', 'deep': '#6fb6f0', 'tail': '#c7a6ff', 'tint': '#ffc6ec', 'dark': '#4f86b8', 'ink': '#0d1020', 'third': '#ffc6ec'}),
    'aurora': ('Aurora', HOLDER, 'Northern lights: teal and violet curtains drifting over a polar night.', 'aurora',
               {'bg': '#030d12', 's1': '#06181f', 's2': '#0a222b', 'line': '#12363f', 'lineHi': '#1f8a86', 'text': '#ecfffb', 'dim': '#9cc4c0',
                'accent': '#3ef2c9', 'hi': '#7bffe0', 'deep': '#1fc9a6', 'tail': '#8b6bff', 'tint': '#b8fff0', 'dark': '#11806a', 'ink': '#02140f', 'third': '#c06bff'}),
    'bloodmoon': ('Blood Moon', HOLDER, 'Crimson moon over black silk, silver edges, a slow pulse of red light.', 'bloodmoon',
                  {'bg': '#0c0405', 's1': '#1a080b', 's2': '#240c10', 'line': '#3d1419', 'lineHi': '#8a2230', 'text': '#fff0f0', 'dim': '#d1a7ab',
                   'accent': '#ff2e4d', 'hi': '#ff6b7f', 'deep': '#c2102c', 'tail': '#ff8a3d', 'tint': '#ffc2ca', 'dark': '#8a0f22', 'ink': '#1a0306', 'third': '#e8e6f0'}),
    'vapor': ('Vapor Sunset', HOLDER, 'Retro sunset: pink sun, cyan horizon and a synth grid rolling in.', 'vapor',
              {'bg': '#0d0618', 's1': '#1a0d2e', 's2': '#24123f', 'line': '#3d2366', 'lineHi': '#7a3fb8', 'text': '#fff0fb', 'dim': '#d6b3e0',
               'accent': '#ff71ce', 'hi': '#ff9fe0', 'deep': '#b967ff', 'tail': '#01cdfe', 'tint': '#fffb96', 'dark': '#8a3fd0', 'ink': '#1a0626', 'third': '#05ffa1'}),
    'ghost': ('Ghost', HOLDER, 'Monochrome glass: white light on graphite, nothing but form and motion.', 'ghost',
              {'bg': '#0a0a0c', 's1': '#141418', 's2': '#1c1c22', 'line': '#2c2c34', 'lineHi': '#5c5c6a', 'text': '#fafafa', 'dim': '#a6a6b0',
               'accent': '#f5f5f7', 'hi': '#ffffff', 'deep': '#d0d0d8', 'tail': '#9a9aa8', 'tint': '#e8e8ee', 'dark': '#77777f', 'ink': '#0a0a0c', 'third': '#ffffff'}),
}
DEFAULT = 'plasma'


def allowed(look_id, eligible):
    """May this wallet wear it? Free looks: anyone. Advanced: only an unlocked wallet."""
    row = LOOKS.get(look_id)
    return bool(row) and (row[1] == FREE or bool(eligible))


def catalog(eligible):
    """→ every look's card. Its full colour set only where this wallet may wear it (an advanced look's palette never leaves for a locked wallet)."""
    out = []
    for k, (name, tier, line, amb, t) in LOOKS.items():
        ok = allowed(k, eligible)
        out.append({'id': k, 'name': name, 'tier': tier, 'line': line, 'ambient': amb, 'swatch': [t['accent'], t['tail'], t['third'], t['bg']],
                    'locked': not ok, **({'tokens': dict(t)} if ok else {})})
    return out


def wear(look_id, eligible):
    """→ (id, tokens, ambient) to apply, or None when the look is unknown or locked for this wallet."""
    if not allowed(look_id, eligible):
        return None
    name, tier, line, amb, t = LOOKS[look_id]
    return {'id': look_id, 'name': name, 'ambient': amb, 'tokens': dict(t)}
