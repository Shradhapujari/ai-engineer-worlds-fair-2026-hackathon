from omniforge.memory.signature import normalize, signature_hash

TB_RUN1 = '''Traceback (most recent call last):
  File "/home/app/demo/buggy_agent.py", line 12, in answer_weather
    temp = data["temp_c"]
KeyError: 'temp_c'
<object at 0x7f9a1c2d3e40>'''

TB_RUN2 = '''Traceback (most recent call last):
  File "/var/omniforge/demo/buggy_agent.py", line 47, in answer_weather
    temp = data["temp_c"]
KeyError: 'temp_c'
<object at 0x55b3df881a90>'''

TB_OTHER = '''Traceback (most recent call last):
  File "/home/app/demo/buggy_agent.py", line 12, in answer_weather
    x = 1 / 0
ZeroDivisionError: division by zero'''


def test_normalize_strips_line_numbers_addrs_paths():
    n = normalize(TB_RUN1)
    assert "line 12" not in n
    assert "0x7f9a1c2d3e40" not in n
    assert "/home/app/" not in n
    assert "KeyError" in n          # the meaningful part survives


def test_same_error_different_run_same_hash():
    assert signature_hash(TB_RUN1) == signature_hash(TB_RUN2)


def test_different_error_different_hash():
    assert signature_hash(TB_RUN1) != signature_hash(TB_OTHER)


def test_hash_is_stable_hex():
    h = signature_hash(TB_RUN1)
    assert isinstance(h, str) and len(h) == 64  # sha256 hexdigest
