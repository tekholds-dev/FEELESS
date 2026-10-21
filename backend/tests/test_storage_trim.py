

def test_build_cache_keeps_recent_files_only():
    import storage_trim as st
    now = 10 * 86400
    files = [('old', 5, now - 4 * 86400), ('new', 5, now - 3600)]
    assert st.plan_build_cache(files, now) == ['old']
