"""Phase 0 smoke test: agent works, then break the vendor and show the crash.
Healing loop arrives in Phase 1+. Run: python -m omniforge.demo.run_demo
"""
from omniforge.demo import buggy_agent, fake_vendor_api


def main() -> None:
    print("1) Agent working:")
    print("  ", buggy_agent.answer_weather("london"))

    print("2) Break vendor live (rename field):")
    fake_vendor_api.BROKEN = True
    try:
        print("  ", buggy_agent.answer_weather("london"))
    except KeyError as e:
        print(f"   CRASH — KeyError: {e}  (this is what OmniForge will heal)")


if __name__ == "__main__":
    main()
