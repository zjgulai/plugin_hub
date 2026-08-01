from plugin_hub_api.payload_hashes import (
    _javascript_number_string,
    extension_payload_hash_matches,
    fnv1a64_payload_hash,
)


def test_fnv1a64_payload_hash_matches_extension_canonicalization() -> None:
    payload = {
        "review_id": "R123",
        "rating": 2,
        "body": "The product worked for two weeks.",
        "captured_at": "2026-06-05T00:00:00+00:00",
    }

    assert fnv1a64_payload_hash(payload) == "fnv1a64:7aa27c8952a9a1b4"
    assert extension_payload_hash_matches(payload, "fnv1a64:7aa27c8952a9a1b4") is True
    assert extension_payload_hash_matches(payload, "fnv1a64:0000000000000000") is False


def test_fnv1a64_payload_hash_uses_javascript_utf16_code_units() -> None:
    digest = fnv1a64_payload_hash({"body": "quiet \U0001f600"})

    assert digest == "fnv1a64:76e7dcb3bb6520ca"


def test_fnv1a64_payload_hash_formats_integer_valued_javascript_numbers() -> None:
    payload = {
        "name": "t3_thread123",
        "id": "thread123",
        "title": "Best grinder for espresso?",
        "selftext": "I want a quieter grinder under $300.",
        "author": "buyer_researcher",
        "created_utc": 1780602718.0,
        "score": 42,
    }

    assert fnv1a64_payload_hash(payload) == "fnv1a64:0be342c1c88acf1a"


def test_javascript_number_string_uses_shortest_large_integral_float_digits() -> None:
    assert _javascript_number_string(1.2345678901234568e20) == "123456789012345680000"
