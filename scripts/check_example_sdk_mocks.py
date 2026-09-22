#!/usr/bin/env python3
"""Assert no Python example test patches a *private* part of the SDK, and that
the examples all patch the same seam. AAASM-6156.

WHY THIS EXISTS
---------------
Every Python example's smoke test monkey-patched
``agent_assembly.core.assembly._register_adapters`` with ``return_value=[]`` so
``init_assembly(mode="sdk-only")`` could run with no adapters installed. That
helper is private, and in SDK ``0.0.1rc7`` it started returning a 2-tuple. The
examples had pinned the old shape, so a single SDK upgrade broke 16 of the 18
Python examples at once, each reporting ``not enough values to unpack
(expected 2, got 0)`` — a message about a mock, for a change that broke no
documented contract.

A private helper's return shape is not a contract, so nothing stops it moving
again. This gate makes the *next* such change impossible to introduce quietly,
in two ways:

* ``EX-MOCK-01`` / ``EX-MOCK-02`` — an example may not patch a private
  ``agent_assembly`` attribute or reach through a private module. Public seams
  (``AdapterRegistry.get_available_adapters_by_priority``) carry a documented
  contract that does not move with the SDK's internals.
* ``EX-MOCK-03`` — every example that patches an ``agent_assembly`` seam must
  patch the *same* one. The original defect was not just a stale mock, it was
  the same stale mock copied into 16 directories; updating 15 of them and
  missing one is the drift this rule reports by name.

Run against the tracked example tests:

    python3 scripts/check_example_sdk_mocks.py
    python3 scripts/check_example_sdk_mocks.py --root .

Exit 0 = clean, 1 = a blocking finding. Its own unit tests live in
``scripts/test_check_example_sdk_mocks.py`` and are run first by the workflow,
because a checker whose parser silently stops matching reports a clean tree it
never read.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

SDK_ROOT = "agent_assembly"

# Directory globs holding the Python examples' own tests. Both layouts are
# real: `python/<framework>/tests/` and `scenarios/<scenario>/python/tests/`.
TEST_GLOBS = (
    "python/*/tests/**/*.py",
    "scenarios/*/python/tests/**/*.py",
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule_id: str
    message: str


@dataclass(frozen=True)
class PatchSite:
    path: str
    line: int
    target: str | None  # dotted `agent_assembly...` target, None if not resolvable


def _dotted(node: ast.expr) -> str | None:
    """`a.b.c` as a string, for Name/Attribute chains only."""
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))


def _sdk_bindings(tree: ast.AST) -> dict[str, str]:
    """Local names bound to something inside the SDK, mapped to the dotted path
    they denote.

    Deliberately not scope-aware: these imports sit *inside* the test functions
    (the examples import the SDK lazily so collection works without it), and a
    module-scope-only walk would see none of them.
    """
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == SDK_ROOT or alias.name.startswith(SDK_ROOT + "."):
                    bindings[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module != SDK_ROOT and not module.startswith(SDK_ROOT + "."):
                continue
            for alias in node.names:
                bindings[alias.asname or alias.name] = f"{module}.{alias.name}"
    return bindings


def _patch_names(tree: ast.AST) -> set[str]:
    """Local names that refer to ``unittest.mock.patch``, however imported or
    aliased (`patch`, `mock_patch`, `mock.patch`, ...)."""
    names: set[str] = {"patch", "mock.patch", "unittest.mock.patch"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in {"unittest.mock", "mock"}:
            for alias in node.names:
                if alias.name == "patch":
                    names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"unittest.mock", "mock"} and alias.asname:
                    names.add(f"{alias.asname}.patch")
    return names


def _string_value(node: ast.expr) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _private_segment(dotted: str) -> str | None:
    """The first private segment of a dotted path below the SDK root, if any.

    ``agent_assembly.core.assembly._register_adapters`` -> ``_register_adapters``
    ``agent_assembly.adapters.registry.AdapterRegistry`` -> None
    """
    segments = dotted.split(".")
    if not segments or segments[0] != SDK_ROOT:
        return None
    for segment in segments[1:]:
        if segment.startswith("_") and not segment.startswith("__"):
            return segment
    return None


def scan_text(path: str, source: str) -> tuple[list[Finding], list[PatchSite]]:
    """Findings, plus every SDK patch site seen — the sites feed EX-MOCK-03."""
    tree = ast.parse(source, filename=path)
    bindings = _sdk_bindings(tree)
    patchers = _patch_names(tree)

    findings: list[Finding] = []
    sites: list[PatchSite] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = _dotted(node.func)
        if callee is None:
            continue

        target: str | None = None
        unresolved = False

        if callee.endswith(".object") and callee[: -len(".object")] in patchers:
            # patch.object(<obj>, "<attr>", ...)
            if len(node.args) < 2:
                continue
            owner = _dotted(node.args[0])
            owner_path = bindings.get(owner) if owner else None
            if owner_path is None:
                continue  # not an SDK object; not this gate's business
            attribute = _string_value(node.args[1])
            if attribute is None:
                unresolved = True
                target = f"{owner_path}.<computed>"
            else:
                target = f"{owner_path}.{attribute}"
        elif callee in patchers:
            # patch("<dotted.target>", ...)
            if not node.args:
                continue
            literal = _string_value(node.args[0])
            if literal is None:
                continue
            if literal != SDK_ROOT and not literal.startswith(SDK_ROOT + "."):
                continue
            target = literal
        else:
            continue

        sites.append(PatchSite(path, node.lineno, None if unresolved else target))

        if unresolved:
            findings.append(
                Finding(
                    path,
                    node.lineno,
                    "EX-MOCK-04",
                    f"patches {target} — the attribute name is computed, so this gate "
                    "cannot tell whether it is private. Pass a string literal.",
                )
            )
            continue

        private = _private_segment(target)
        if private is None:
            continue

        rule = "EX-MOCK-01" if target.rsplit(".", 1)[-1] == private else "EX-MOCK-02"
        detail = (
            f"patches the private attribute {private!r}"
            if rule == "EX-MOCK-01"
            else f"reaches through the private module {private!r}"
        )
        findings.append(
            Finding(
                path,
                node.lineno,
                rule,
                f"{detail} via {target}. A private helper's signature and return shape "
                "are not a contract — AAASM-6156 is what happens when they move "
                "(rc.7 made _register_adapters return a 2-tuple and every example that "
                "had pinned the old shape failed at once). Patch a documented seam, "
                "e.g. AdapterRegistry.get_available_adapters_by_priority.",
            )
        )

    return findings, sites


def discover_test_files(root: Path) -> list[str]:
    seen: set[str] = set()
    for pattern in TEST_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                seen.add(path.relative_to(root).as_posix())
    return sorted(seen)


def check_consistency(sites: list[PatchSite]) -> list[Finding]:
    """EX-MOCK-03: one set of seams across all examples, or name the divergent ones.

    Compares each *file's* set of SDK patch targets, not individual sites — an
    example that patches two public seams is doing something legitimate, while an
    example patching a different seam from its 15 siblings is the drift this rule
    is for. Files patching nothing are ignored rather than counted as a third
    opinion: not every example needs a seam.
    """
    per_file: dict[str, set[str]] = {}
    for site in sites:
        if site.target is not None:
            per_file.setdefault(site.path, set()).add(site.target)
    if len(per_file) < 2:
        return []

    groups: dict[frozenset[str], list[str]] = {}
    for path, targets in per_file.items():
        groups.setdefault(frozenset(targets), []).append(path)
    if len(groups) == 1:
        return []

    majority = max(groups, key=lambda seams: (len(groups[seams]), sorted(seams)))
    majority_text = ", ".join(sorted(majority))
    findings: list[Finding] = []
    for seams, paths in groups.items():
        if seams == majority:
            continue
        for path in sorted(paths):
            line = min(s.line for s in sites if s.path == path and s.target is not None)
            findings.append(
                Finding(
                    path,
                    line,
                    "EX-MOCK-03",
                    f"patches {', '.join(sorted(seams))} while {len(groups[majority])} other "
                    f"example test(s) patch {majority_text}. AAASM-6156's defect was one stale "
                    "mock copied into 16 directories; a seam updated in some examples and not "
                    "others is the same failure mid-flight. Move every example to the same seam.",
                )
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check example SDK mock contracts.")
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    targets = discover_test_files(root)
    if not targets:
        print("::error::Found zero Python example test files.")
        print(
            "::error::This gate measures "
            + ", ".join(TEST_GLOBS)
            + ". Zero matches means the layout moved and nothing was checked, "
            "which is not the same as a clean tree."
        )
        return 1

    findings: list[Finding] = []
    sites: list[PatchSite] = []
    for rel in targets:
        try:
            source = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"::error::Could not read {rel}: {exc}")
            return 1
        try:
            file_findings, file_sites = scan_text(rel, source)
        except SyntaxError as exc:
            print(f"::error::Could not parse {rel}: {exc}")
            print("::error::Refusing to report a clean result for a file this gate did not read.")
            return 1
        findings.extend(file_findings)
        sites.extend(file_sites)

    findings.extend(check_consistency(sites))

    print(f"Scanned {len(targets)} Python example test file(s).")
    resolved = [s for s in sites if s.target is not None]
    if resolved:
        inventory: dict[str, int] = {}
        for site in resolved:
            inventory[str(site.target)] = inventory.get(str(site.target), 0) + 1
        for target, count in sorted(inventory.items()):
            print(f"  {count:>3} site(s)  {target}")
    else:
        print("  no example test patches anything under agent_assembly.")

    if not findings:
        print(f"OK: {len(targets)} file(s) scanned, zero private-seam patches, one seam in use.")
        return 0

    for finding in sorted(findings, key=lambda f: (f.path, f.line, f.rule_id)):
        print(f"::error file={finding.path},line={finding.line}::{finding.rule_id}: {finding.message}")
    print(f"\ncheck_example_sdk_mocks: {len(findings)} blocking finding(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
