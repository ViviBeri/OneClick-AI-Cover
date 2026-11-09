"""Contract tests for the opt-in real conversion workflow."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_real_conversion_requires_and_forwards_model_trust_acknowledgement():
    source = (ROOT / "scripts" / "e2e_conversion.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    trust_guard = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "environ"
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "os"
        and any(
            isinstance(arg, ast.Constant) and arg.value == "MODEL_TRUST_CONFIRMED"
            for arg in node.args
        )
        for node in ast.walk(tree)
    )
    assert trust_guard, "The workflow must require MODEL_TRUST_CONFIRMED."

    generate_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "app"
        and node.func.attr == "generate"
    ]
    assert len(generate_calls) == 1, "Expected exactly one app.generate call."

    trust_keyword = next(
        (keyword for keyword in generate_calls[0].keywords if keyword.arg == "trust_confirmed"),
        None,
    )
    assert trust_keyword is not None
    assert isinstance(trust_keyword.value, ast.Constant) and trust_keyword.value.value is True
