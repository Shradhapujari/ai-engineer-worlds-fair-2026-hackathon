"""Fake weather vendor. Breakable on demand: flip BROKEN to rename a field,
simulating a vendor schema change that crashes the agent (demo §8 step 2).
"""

# Flip True live during the demo to break the vendor schema.
BROKEN = False

_DATA = {"london": 14, "tokyo": 22, "nyc": 18}


def get_weather(city: str) -> dict:
    """Return current weather. Stable schema uses 'temp_c'.
    When BROKEN, the field is renamed to 'temperature_celsius' — the kind of
    breaking change a real vendor ships without warning.
    """
    temp = _DATA.get(city.lower(), 20)
    if BROKEN:
        return {"city": city, "temperature_celsius": temp, "unit": "C"}
    return {"city": city, "temp_c": temp, "unit": "C"}
