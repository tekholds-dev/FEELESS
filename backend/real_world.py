"""🌍 REAL WORLD, NOW — the 3D studio's first shelf (owner 2026-11-15: "clean the 3d playground … add real stuff used today! like every new
phone fresh and ready to model … i wona see a 3d iphone fold option … real world stuff should show first").

Each card is a real product people use today. `base` is what the free CC0 library really holds closest to it (checked against the local index
2026-11-15); `brief` is what the agent builds from that base — a fresh, creative remix, never a copy of a brand's official file. Products too new
for any free model (iPhone Duo, Galaxy Z Fold 8) start from the closest real model and say so. Release facts were checked on the web the same day:
iPhone Duo + iPhone 18 Pro (Apple, Sept 2026), Galaxy Z Fold 8 (Samsung, July 2026), Pixel 11 Pro Fold (Google, Aug 2026). Pure.
"""

SHELF = (
    ('phones', 'Phones', (
        ('iphone-duo', 'iPhone Duo', 'Apple · Sept 2026 · book-style foldable', 'galaxy z flip', 'Apple\'s first foldable, the iPhone Duo: a 7.6 inch book-style foldable that opens into one thin slab. Remix it: a bold new colourway and a product hero shot'),
        ('iphone-18-pro', 'iPhone 18 Pro', 'Apple · Sept 2026', 'iphone 13 pro max', 'An iPhone 18 Pro concept: flat titanium edges, a big camera plateau. Reimagine it as a limited drop'),
        ('galaxy-fold-8', 'Galaxy Z Fold 8', 'Samsung · July 2026', 'galaxy z flip', 'A Galaxy Z Fold 8 concept, half open on a pedestal, the hinge as the hero'),
        ('pixel-11-fold', 'Pixel 11 Pro Fold', 'Google · Aug 2026', 'galaxy z flip', 'A Pixel 11 Pro Fold concept with a camera bar across the back, in a soft pastel'),
        ('iphone-x', 'iPhone X', 'Apple · the classic notch', 'iphone x', 'The iPhone X, the phone that started the notch, as a museum piece'),
    )),
    ('sneakers', 'Sneakers', (
        ('nb-997', 'New Balance 997', 'Made in USA runner', 'new balance 997', 'A New Balance 997 colourway nobody has dropped yet, floating over a gallery plinth'),
        ('converse', 'Chuck Taylor', 'Converse classic', 'converse chuck', 'A Chuck Taylor redesign for a coin launch, with the ticker on the heel'),
        ('runner', 'Daily runner', 'Any sneaker brand', 'sneaker', 'A brand-new sneaker silhouette for an up-and-coming brand'),
    )),
    ('gaming', 'Gaming', (
        ('ps2', 'PlayStation 2', 'Sony · the best seller ever', 'playstation 2', 'A PlayStation 2 reimagined as a 2026 console, same soul, new shell'),
        ('gameboy', 'Game Boy', 'Nintendo classic', 'game boy classic', 'A Game Boy remix in clear neon plastic'),
        ('gamepad', 'Controller', 'Any console', 'gamepad', 'A controller for a game that does not exist yet'),
        ('quest', 'Quest headset', 'Meta VR', 'oculus quest', 'A VR headset concept, lighter, with a halo strap'),
        ('rtx', 'RTX graphics card', 'NVIDIA GeForce', 'rtx 3070', 'A graphics card as a luxury object, lit like a watch ad'),
    )),
    ('audio', 'Audio + wearables', (
        ('airpods-pro', 'AirPods Pro', 'Apple', 'airpods pro', 'AirPods Pro in a colour Apple never made, case open'),
        ('sony-xm', 'Studio headphones', 'Sony MDR', 'sony mdr', 'Studio headphones as a streetwear accessory'),
        ('apple-watch', 'Apple Watch', 'Apple', 'apple watch', 'An Apple Watch band collab for a coin community'),
    )),
    ('tech', 'Laptops + desk', (
        ('macbook', 'MacBook Pro', 'Apple', 'macbook pro', 'A MacBook Pro on a clean desk, a trader\'s battle station'),
        ('imac', 'iMac', 'Apple', 'imac', 'An iMac in a bold new colour for a creator studio'),
        ('drone', 'Mini drone', 'Camera drone', 's9 mini drone', 'A camera drone in flight over a product launch'),
    )),
    ('drinks', 'Cans + bottles', (
        ('soda', 'Soda can', 'Any drink brand', 'soda can', 'An energy drink can for a coin, with its logo wrapped around it'),
        ('cola', 'Cola can', 'Classic cola shape', 'cola can', 'A cola can redesign for a summer drop'),
    )),
    ('wear', 'Streetwear', (
        ('hoodie', 'Hoodie', 'Merch staple', 'hoodie free', 'A merch hoodie for an agent, its name across the chest'),
        ('skate', 'Skateboard', 'Street deck', 'skateboard globe', 'A skate deck with art made by an agent'),
    )),
)
CATS = tuple((k, label) for k, label, _ in SHELF)


def cards():
    """Every card, real-world first order kept. Pure."""
    return [{'id': i, 'name': n, 'line': line, 'base': base, 'brief': brief, 'cat': k} for k, _, items in SHELF for i, n, line, base, brief in items]


def resolve(cards_, search):
    """Each card with the free model it starts from. `search(query)` → rows from the CC0 library; a card with no base model is dropped, never faked."""
    out = []
    for c in cards_:
        rows = search(c['base']) or []
        if rows:
            r = rows[0]
            mine = {w for w in c['name'].lower().split() if len(w) > 2}
            out.append({**c, 'model': {'id': r['id'], 'name': r['name'], 'thumb': r.get('thumb')}, 'remix': not any(w in r['name'].lower() for w in mine)})   # remix: it starts from the closest free model, not itself
    return out
