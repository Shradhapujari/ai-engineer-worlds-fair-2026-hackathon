import pytest

from omniforge.healer.patcher import apply_unified_diff, PatchApplyError

SOURCE = '''def answer(d):
    return "temp=" + str(d["temp_c"])
'''

DIFF = '''--- a/guard_target.py
+++ b/guard_target.py
@@ -1,2 +1,2 @@
 def answer(d):
-    return "temp=" + str(d["temp_c"])
+    return "temp=" + str(d["temperature_celsius"])
'''


def test_apply_unified_diff_produces_patched_source():
    out = apply_unified_diff(SOURCE, DIFF, filename="guard_target.py")
    assert 'd["temperature_celsius"]' in out
    assert 'd["temp_c"]' not in out


def test_apply_bad_diff_raises():
    bad = "this is not a diff"
    with pytest.raises(PatchApplyError):
        apply_unified_diff(SOURCE, bad, filename="guard_target.py")


def test_apply_diff_with_full_repo_path():
    # the model often emits the full repo path; we apply against the basename
    full_path = '''--- a/omniforge/demo/guard_target.py
+++ b/omniforge/demo/guard_target.py
@@ -1,2 +1,2 @@
 def answer(d):
-    return "temp=" + str(d["temp_c"])
+    return "temp=" + str(d["temperature_celsius"])
'''
    out = apply_unified_diff(SOURCE, full_path, filename="guard_target.py")
    assert 'd["temperature_celsius"]' in out


def test_apply_zero_context_hunk_via_patch_fallback():
    # Gemini often emits hunks with no surrounding context — git apply rejects
    # these, the GNU patch fallback handles them.
    zero_ctx = '''--- a/guard_target.py
+++ b/guard_target.py
@@ -2,1 +2,1 @@
-    return "temp=" + str(d["temp_c"])
+    return "temp=" + str(d["temperature_celsius"])
'''
    out = apply_unified_diff(SOURCE, zero_ctx, filename="guard_target.py")
    assert 'd["temperature_celsius"]' in out
    assert 'd["temp_c"]' not in out


def test_apply_diff_that_does_not_match_raises():
    mismatch = '''--- a/guard_target.py
+++ b/guard_target.py
@@ -1,2 +1,2 @@
 def answer(d):
-    return "NOTHING LIKE THE SOURCE"
+    return "x"
'''
    with pytest.raises(PatchApplyError):
        apply_unified_diff(SOURCE, mismatch, filename="guard_target.py")
