from __future__ import annotations

import json
import math
import re
from decimal import Decimal

from plugin_hub_api.schemas import JsonValue

FNV1A64_PATTERN = re.compile(r"^fnv1a64:[0-9a-f]{16}$")
FNV1A64_OFFSET = 0xCBF29CE484222325
FNV1A64_PRIME = 0x100000001B3
UINT64_MASK = (1 << 64) - 1


def fnv1a64_payload_hash(payload: dict[str, JsonValue]) -> str:
    canonical = _stable_stringify(payload)
    digest = FNV1A64_OFFSET
    utf16 = canonical.encode("utf-16-le", errors="surrogatepass")
    for index in range(0, len(utf16), 2):
        code_unit = int.from_bytes(utf16[index : index + 2], "little")
        digest ^= code_unit
        digest = (digest * FNV1A64_PRIME) & UINT64_MASK
    return f"fnv1a64:{digest:016x}"


def extension_payload_hash_matches(
    payload: dict[str, JsonValue],
    claimed_hash: str,
) -> bool:
    return bool(
        FNV1A64_PATTERN.fullmatch(claimed_hash)
        and fnv1a64_payload_hash(payload) == claimed_hash
    )


def _stable_stringify(value: JsonValue) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _javascript_number_string(value)
    if isinstance(value, list):
        return f"[{','.join(_stable_stringify(item) for item in value)}]"
    return "{" + ",".join(
        f"{json.dumps(key, ensure_ascii=False)}:{_stable_stringify(value[key])}"
        for key in sorted(value)
    ) + "}"


def _javascript_number_string(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("payload_hash_number_must_be_finite")
    if value == 0:
        return "0"
    absolute = abs(value)
    representation = repr(value).lower()
    if 1e-6 <= absolute < 1e21:
        fixed = format(Decimal(representation), "f")
        return fixed.rstrip("0").rstrip(".") if "." in fixed else fixed
    if "e" not in representation:
        return representation
    mantissa, exponent = representation.split("e", maxsplit=1)
    exponent_value = int(exponent)
    sign = "+" if exponent_value >= 0 else ""
    return f"{mantissa}e{sign}{exponent_value}"
