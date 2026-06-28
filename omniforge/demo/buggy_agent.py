"""Demo agent calling the fake weather vendor. Reads 'temp_c'.
When the vendor breaks (renames the field), this raises KeyError — the crash
OmniForge catches and heals in later phases.
"""
from omniforge.demo import fake_vendor_api


def answer_weather(city: str) -> str:
    data = fake_vendor_api.get_weather(city)
    temp = data["temp_c"]  # breaks when vendor renames the field
    return f"It's {temp}°C in {data['city']}."
