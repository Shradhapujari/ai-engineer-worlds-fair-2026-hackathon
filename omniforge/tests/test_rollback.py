from omniforge.healer.rollback import AuditLog, CircuitBreaker, kill_switch_engaged


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_breaker_allows_within_cap():
    cb = CircuitBreaker(max_changes=2, window_seconds=60, clock=FakeClock())
    assert cb.allow()
    cb.record()
    assert cb.allow()


def test_breaker_denies_over_cap():
    cb = CircuitBreaker(max_changes=2, window_seconds=60, clock=FakeClock())
    cb.record()
    cb.record()
    assert not cb.allow()


def test_breaker_window_expiry_restores_capacity():
    clock = FakeClock()
    cb = CircuitBreaker(max_changes=1, window_seconds=10, clock=clock)
    cb.record()
    assert not cb.allow()
    clock.t = 11  # window passed
    assert cb.allow()


def test_kill_switch_via_env(monkeypatch):
    monkeypatch.delenv("OMNIFORGE_KILL", raising=False)
    monkeypatch.delenv("OMNIFORGE_KILL_FILE", raising=False)
    assert not kill_switch_engaged()
    monkeypatch.setenv("OMNIFORGE_KILL", "1")
    assert kill_switch_engaged()


def test_kill_switch_via_flag_file(monkeypatch, tmp_path):
    monkeypatch.delenv("OMNIFORGE_KILL", raising=False)
    flag = tmp_path / "STOP"
    monkeypatch.setenv("OMNIFORGE_KILL_FILE", str(flag))
    assert not kill_switch_engaged()
    flag.write_text("")
    assert kill_switch_engaged()


def test_audit_log_is_append_only(tmp_path):
    log = AuditLog(str(tmp_path / "audit.jsonl"))
    log.record({"status": "healed", "signature": "a"})
    log.record({"status": "rolled_back", "signature": "b"})
    entries = log.entries()
    assert len(entries) == 2
    assert [e["status"] for e in entries] == ["healed", "rolled_back"]
    assert all("ts" in e for e in entries)


def test_audit_entries_empty_when_no_file(tmp_path):
    assert AuditLog(str(tmp_path / "missing.jsonl")).entries() == []
