from omniforge.healer.scanner import scan, MAX_DIFF_LINES
from omniforge.models.schemas import Patch


def _patch(diff: str) -> Patch:
    return Patch(
        id="p1", incident_id="i1", root_cause="rc",
        unified_diff=diff, repro_test="def test(): assert True",
    )


CLEAN_DIFF = """--- a/buggy_agent.py
+++ b/buggy_agent.py
@@ -1,2 +1,2 @@
 def answer(d):
-    return d["temp_c"]
+    return d["temperature_celsius"]
"""


def test_clean_patch_passes():
    res = scan(_patch(CLEAN_DIFF), scope_files={"buggy_agent.py"})
    assert res.passed
    assert res.reasons == []


def test_out_of_scope_file_rejected():
    res = scan(_patch(CLEAN_DIFF), scope_files={"other.py"})
    assert not res.passed
    assert any("out-of-scope" in r for r in res.reasons)


def test_self_edit_rejected():
    diff = CLEAN_DIFF.replace("buggy_agent.py", "omniforge/healer/scanner.py")
    res = scan(_patch(diff), scope_files={"scanner.py"})
    assert not res.passed
    assert any("OmniForge's own code" in r for r in res.reasons)


def test_demo_dir_is_not_self_edit():
    diff = CLEAN_DIFF.replace("buggy_agent.py", "omniforge/demo/buggy_agent.py")
    res = scan(_patch(diff), scope_files={"buggy_agent.py"})
    assert res.passed, res.reasons


def test_oversized_diff_rejected():
    body = "\n".join(f"+    x{i} = {i}" for i in range(MAX_DIFF_LINES + 5))
    diff = f"--- a/buggy_agent.py\n+++ b/buggy_agent.py\n@@ -1 +1,{MAX_DIFF_LINES+5} @@\n{body}\n"
    res = scan(_patch(diff), scope_files={"buggy_agent.py"})
    assert not res.passed
    assert any("too large" in r for r in res.reasons)


def test_dangerous_sink_eval_rejected():
    diff = CLEAN_DIFF.replace(
        '+    return d["temperature_celsius"]', "+    return eval(d['expr'])"
    )
    res = scan(_patch(diff), scope_files={"buggy_agent.py"})
    assert not res.passed
    assert any("eval()" in r for r in res.reasons)


def test_dangerous_sink_os_system_rejected():
    diff = CLEAN_DIFF.replace(
        '+    return d["temperature_celsius"]', "+    os.system('rm -rf /')"
    )
    res = scan(_patch(diff), scope_files={"buggy_agent.py"})
    assert not res.passed
    assert any("os.system()" in r for r in res.reasons)


def test_shell_true_rejected():
    diff = CLEAN_DIFF.replace(
        '+    return d["temperature_celsius"]',
        "+    subprocess.run(cmd, shell=True)",
    )
    res = scan(_patch(diff), scope_files={"buggy_agent.py"})
    assert not res.passed
    assert any("shell=True" in r for r in res.reasons)


def test_new_network_import_rejected():
    diff = CLEAN_DIFF.replace(
        '+    return d["temperature_celsius"]', "+import socket"
    )
    res = scan(_patch(diff), scope_files={"buggy_agent.py"})
    assert not res.passed
    assert any("disallowed import: socket" in r for r in res.reasons)


def test_static_scan_injected_finding_rejects():
    def fake_static(sources):
        return ["bandit HIGH: B102 exec used"]

    res = scan(
        _patch(CLEAN_DIFF),
        scope_files={"buggy_agent.py"},
        patched_sources={"buggy_agent.py": "x = 1"},
        static_scan=fake_static,
    )
    assert not res.passed
    assert any("bandit HIGH" in r for r in res.reasons)


def test_static_scan_skipped_without_sources():
    called = []

    def fake_static(sources):
        called.append(True)
        return ["should not run"]

    res = scan(_patch(CLEAN_DIFF), scope_files={"buggy_agent.py"},
               static_scan=fake_static)
    assert res.passed
    assert called == []
