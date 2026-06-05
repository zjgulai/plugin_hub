import plugin_hub_api


def test_api_package_imports() -> None:
    assert plugin_hub_api.__doc__ == "Plugin Hub API package."
