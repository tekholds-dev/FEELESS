"""🖼 SITE-2: coin logos at the size they are shown, not 940 px for a 22 px row."""
import io

from PIL import Image


def test_a_big_logo_becomes_a_small_webp_and_a_small_or_unreadable_one_is_left_alone():
    import reputation_service as rs
    big = io.BytesIO(); Image.new('RGB', (940, 940), (20, 200, 100)).save(big, 'PNG')
    out = rs._logo_thumb(big.getvalue(), 64)
    assert out and len(out) < len(big.getvalue()) and Image.open(io.BytesIO(out)).size == (64, 64) and Image.open(io.BytesIO(out)).format == 'WEBP'
    small = io.BytesIO(); Image.new('RGB', (48, 48)).save(small, 'PNG')
    assert rs._logo_thumb(small.getvalue(), 64) is None
    assert rs._logo_thumb(b'<svg xmlns="http://www.w3.org/2000/svg"/>', 64) is None
    assert rs.LOGO_THUMBS == (64, 128, 256)
