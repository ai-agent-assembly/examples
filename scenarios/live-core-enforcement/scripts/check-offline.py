#!/usr/bin/env python3
"""Offline-safe validation for the live-core-enforcement example.

CI for this repo runs with bare runtimes and **no** gateway, so it cannot run
the real end-to-end flow (that needs a real aa-runtime + aa-gateway — see the
README). This check is what CI *can* honestly assert offline:

  1. agent.py parses and compiles (valid Python, no syntax errors),
  2. agent.py imports the *real* SDK entrypoint (no stand-in/shim), and
  3. policy.yaml is valid YAML with the expected section-based `tools` shape
     (read_file allowed, delete_file denied).

It deliberately does NOT call init_assembly — doing so would try to reach a
gateway. It only validates the example is well-formed and faithful to the SDK.
"""
from __future__ import annotations

import ast
import pathlib
import sys

SCENARIO = pathlib.Path(__file__).resolve().parent.parent
AGENT = SCENARIO / "python-agent" / "agent.py"
POLICY = SCENARIO / "policy.yaml"


def _check_agent_parses() -> list[str]:
    errors: list[str] = []
    source = AGENT.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(AGENT))
    except SyntaxError as exc:  # pragma: no cover - failure path
        return [f"agent.py does not parse: {exc}"]

    # It must import the REAL SDK entrypoint, not define a local shim.
    imports_real_sdk = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "agent_assembly"
        and any(alias.name == "init_assembly" for alias in node.names)
        for node in ast.walk(tree)
    )
    if not imports_real_sdk:
        errors.append("agent.py must import init_assembly from the real agent_assembly SDK")
    return errors


def _check_policy() -> list[str]:
    errors: list[str] = []
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        # PyYAML absent in a bare runtime: do a minimal structural check instead
        # of failing the offline smoke for a missing optional dependency.
        text = POLICY.read_text(encoding="utf-8")
        if "delete_file" not in text or "allow: false" not in text:
            errors.append("policy.yaml must deny delete_file (allow: false)")
        if "read_file" not in text or "allow: true" not in text:
            errors.append("policy.yaml must allow read_file (allow: true)")
        return errors

    data = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    tools = (data or {}).get("tools")
    if not isinstance(tools, dict):
        return ["policy.yaml is missing a section-based `tools` mapping"]
    if tools.get("read_file", {}).get("allow") is not True:
        errors.append("policy.yaml must allow read_file")
    if tools.get("delete_file", {}).get("allow") is not False:
        errors.append("policy.yaml must deny delete_file")
    return errors


def main() -> int:
    errors = _check_agent_parses() + _check_policy()
    if errors:
        print("Offline validation FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("Offline validation passed:")
    print("  - agent.py parses and imports the real agent_assembly SDK")
    print("  - policy.yaml is a valid section-based policy (read_file allow, delete_file deny)")
    print("\nNote: the real allow/deny flow needs a live aa-runtime + aa-gateway.")
    print("      Run `bash scripts/start.sh` with Docker to exercise it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
