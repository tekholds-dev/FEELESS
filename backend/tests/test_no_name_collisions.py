"""Guard: no backend module may bind one top-level name to both a value and a function / class, or define a function twice (2026-10-22: a
new `_block_view()` for the family block silently replaced the blocklist's `_block_view` cache dict — pyflakes misses it because the first
binding was in use; 4 tests caught it, nothing in the code did). A deliberate wrapper marks its re-definition `# noqa: F811`."""
import ast
import collections
import pathlib


def test_no_top_level_name_is_bound_twice():
    bad = []
    for f in sorted(pathlib.Path(__file__).resolve().parents[1].glob('*.py')):
        src = f.read_text()
        lines = src.splitlines()
        seen = collections.defaultdict(list)
        for node in ast.parse(src, str(f)).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if 'noqa: F811' not in lines[node.lineno - 1]:
                    seen[node.name].append(('def', node.lineno))
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                    if isinstance(t, ast.Name):
                        seen[t.id].append(('val', node.lineno))
        for name, kinds in seen.items():
            ks = [k for k, _ in kinds]
            if ks.count('def') > 1 or ('def' in ks and 'val' in ks):
                bad.append(f'{f.name}: {name} bound at {[ln for _, ln in kinds]}')
    assert bad == []


def test_no_module_alias_points_at_two_modules():
    # 2026-10-22: `import prompt_studio as _ps` sat above an older `import pick_style as _ps` — the later import won and the studio called
    # pick_style.clean_active (caught by a test, missed by pyflakes and the guard above)
    bad = []
    for f in sorted(pathlib.Path(__file__).resolve().parents[1].glob('*.py')):
        mods = collections.defaultdict(set)
        for node in ast.parse(f.read_text(), str(f)).body:   # module level: an import inside a function only shadows inside it
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    if a.asname:
                        mods[a.asname].add(((node.module + '.') if isinstance(node, ast.ImportFrom) and node.module else '') + a.name)
        bad += [f'{f.name}: {k} = {sorted(v)}' for k, v in mods.items() if len(v) > 1]
    assert bad == []
