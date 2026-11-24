from importlib.metadata import distribution

import trading_bot


def test_installed_package_imports() -> None:
    assert trading_bot.__name__ == "trading_bot"
    assert distribution("ai-trading-model").version
