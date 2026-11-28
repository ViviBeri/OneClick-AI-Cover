"""Conformance tests for the RFC 8785 canonicalization boundary."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import pytest
import rfc8785

from oneclick_cover.canonicalization import (
    NonAsciiObjectKeyError,
    canonicalize,
    hash_canonical,
    is_canonicalizable,
)

FIXTURES = Path(__file__).parent / "fixtures" / "jcs"


def test_rfc8785_appendix_b_number_vectors_match_fixed_bytes_and_hashes():
    fixture = json.loads((FIXTURES / "appendix_b_numbers.json").read_text(encoding="utf-8"))

    for vector in fixture["vectors"]:
        number = struct.unpack(">d", bytes.fromhex(vector["ieee754"]))[0]
        expected = vector["expected"].encode("ascii")
        assert canonicalize(number) == expected, vector["name"]
        assert hash_canonical(number) == vector["expected_sha256"], vector["name"]


def test_rfc8785_section_3_sample_matches_fixed_canonical_bytes_and_hash():
    fixture = json.loads((FIXTURES / "canonicalization_sample.json").read_text(encoding="utf-8"))
    expected = fixture["canonical"].encode("utf-8")

    actual = canonicalize(fixture["input"])
    assert actual == expected
    assert hashlib.sha256(expected).hexdigest() == fixture["sha256"]
    assert hash_canonical(fixture["input"]) == fixture["sha256"]


def test_canonicalization_is_utf8_without_bom_or_trailing_newline():
    result = canonicalize({"z": "café", "a": "value"})
    assert result == '{"a":"value","z":"café"}'.encode("utf-8")
    assert not result.startswith(b"\xef\xbb\xbf")
    assert not result.endswith(b"\n")


def test_nested_non_ascii_object_key_fixture_raises_typed_error():
    fixture = json.loads(
        (FIXTURES / "non_ascii_object_key.json").read_text(encoding="utf-8")
    )
    with pytest.raises(NonAsciiObjectKeyError, match="ASCII"):
        canonicalize(fixture["input"])
    assert not is_canonicalizable(fixture["input"])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numbers_are_rejected(value):
    with pytest.raises(rfc8785.CanonicalizationError):
        canonicalize(value)
    assert not is_canonicalizable(value)


def test_invalid_unicode_surrogate_is_rejected():
    with pytest.raises(rfc8785.CanonicalizationError):
        canonicalize({"value": "\ud800"})


def test_unsupported_python_values_are_rejected():
    assert not is_canonicalizable({"value": object()})
    assert not is_canonicalizable({1: "non-string key"})


def test_canonical_round_trip_is_idempotent():
    value = {"z": [3, {"b": True, "a": "é"}], "a": None}
    first = canonicalize(value)
    reparsed = json.loads(first.decode("utf-8"))
    assert canonicalize(reparsed) == first


def test_object_keys_are_sorted_recursively_and_array_order_is_preserved():
    value = {"z": [{"b": 2, "a": 1}, 0], "a": 3}
    assert canonicalize(value) == b'{"a":3,"z":[{"a":1,"b":2},0]}'
