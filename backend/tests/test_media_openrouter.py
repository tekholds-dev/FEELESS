"""🎬 PoC media on OpenRouter (owner 2026-11-10): viral presets with real samples, the job shape OpenRouter's /videos really uses
(checked with real calls the same day), and FEELESS's own key only for staff agents, capped at $2 a day."""
import media_gen as mg


def test_presets_are_viral_formats_with_real_samples_prices_and_seconds():
    c = mg.catalog({'openrouter'})
    ids = [p['id'] for p in c['presets']]
    assert ids == ['baby-dance', 'hotel-lobby', 'faceless-avatar', 'ai-vs-handmade', 'ai-will-replace-you']
    for p in c['presets']:
        assert p['sample'].startswith('/media/samples/') and p['usd'] > 0 and p['ready']
    assert c['pick'] == {'image': 'or-nano-banana', 'video': 'or-grok-lite'}
    assert not any(p['ready'] for p in mg.catalog(set())['presets'])          # nothing linked, not staff: nothing runs
    assert all(p['ready'] for p in mg.catalog(set(), house=True)['presets'])   # staff: FEELESS's key


def test_fill_puts_the_folder_words_in_the_format():
    prompt, model, kind = mg.fill('hotel-lobby', 'a coin called   $FEE   pumping')
    assert 'hotel lobby' in prompt and '$FEE pumping' in prompt and model == 'or-veo-lite' and kind == 'video'
    try:
        mg.fill('nope', 'x'); assert False
    except ValueError:
        pass


def test_openrouter_video_job_shape_matches_its_api():
    meth, url, heads, body = mg.submit_req('openrouter', 'google/veo-3.1-lite', 'cat', 'sk-or-x', 'or-veo-lite')
    assert (meth, url) == ('POST', 'https://openrouter.ai/api/v1/videos') and heads['Authorization'] == 'Bearer sk-or-x'
    assert body == {'model': 'google/veo-3.1-lite', 'prompt': 'cat', 'duration': 4, 'resolution': '720p', 'aspect_ratio': '9:16', 'generate_audio': True}   # Veo takes 4/6/8 s only
    hd = mg.handle_of('openrouter', {'id': 'gen-vid-1', 'polling_url': 'https://openrouter.ai/api/v1/videos/gen-vid-1', 'status': 'pending'})
    assert hd['result'] == 'https://openrouter.ai/api/v1/videos/gen-vid-1/content'
    assert mg.state_of('openrouter', {'status': 'pending'})[0] == 'running'
    assert mg.state_of('openrouter', {'status': 'completed'}) == ('done', '')
    assert mg.state_of('openrouter', {'status': 'failed', 'error': 'Video generation failed'}) == ('failed', 'Video generation failed')
    try:
        mg.handle_of('openrouter', {'error': {'message': 'Duration 5s is not supported'}}); assert False
    except ValueError as e:
        assert 'Duration' in str(e)


def test_a_model_on_an_unlinked_provider_is_refused_never_swapped():
    try:
        mg.choose('or-kling3', 'video', {'fal'}); assert False
    except ValueError as e:
        assert 'OpenRouter' in str(e)
    assert mg.choose(None, 'video', {'fal'})[0] == 'fal-wan22-5b'      # the user's own account comes first
    assert mg.choose(None, 'video', set(), house=True)[0] == 'or-grok-lite'


def test_house_spend_is_booked_per_day(tmp_path, monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'MEDIA_HOUSE_PATH', tmp_path / 'mh.json')
    assert fs._media_house_spent() == 0
    fs._media_house_add(0.15); fs._media_house_add(0.25)
    assert abs(fs._media_house_spent() - 0.40) < 1e-9
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-or-house'); monkeypatch.setenv('FEELESS_ADMIN_WALLETS', 'STAFFWALLET')
    assert fs._media_house({'isLeader': True}) and not fs._media_house({'id': 'x'})
