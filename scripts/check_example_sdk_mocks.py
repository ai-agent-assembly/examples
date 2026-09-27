#!/usr/bin/env python3
"""Assert no Python example test patches a *private* part of the SDK, that the
examples all patch the same seam, and that a test claiming to need no gateway
makes that true rather than assuming it. AAASM-6156, AAASM-6196.

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

AAASM-6196 added a second, related failure mode: the same 16 tests asserted that
``mode="sdk-only"`` needs no gateway while doing nothing to make one unreachable.
On a machine running the product they registered against a real gateway and
passed regardless of the SDK — measured, they passed against ``0.0.1rc7``, which
breaks that contract, and failed on the same machine once the endpoint was
pinned. ``gateway_url`` cannot fix it: the resolver keeps only that URL's host
and substitutes the fixed gRPC port 50051, so every loopback value lands on the
one port a local gateway occupies. Hence:

* ``EX-MOCK-05`` — a test that calls ``init_assembly`` must pin
  ``AA_GATEWAY_ENDPOINT`` (the one lever honoured verbatim) in the same
  function, so the gateway's reachability is a fact of the test rather than a
  property of the machine.
* ``EX-MOCK-06`` — and that pin may not name port 50051, which would restore
  the ambient dependency while looking like a fix, nor be a value this gate
  cannot read, which would hide either outcome.

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

# The SDK entry point whose gateway reachability the tests depend on, the one
# environment variable that steers it, and the port a pin must not name.
INIT_ENTRY_POINT = f"{SDK_ROOT}.init_assembly"
GATEWAY_ENDPOINT_ENV = "AA_GATEWAY_ENDPOINT"
DEFAULT_GRPC_PORT = "50051"

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


def _resolve(dotted: str, bindings: dict[str, str]) -> str | None:
    """A dotted call target rewritten through the file's SDK imports.

    Handles both ``init_assembly(...)`` after a ``from agent_assembly import``
    and ``agent_assembly.init_assembly(...)`` after a plain ``import``.
    """
    if dotted in bindings:
        return bindings[dotted]
    head, _, tail = dotted.partition(".")
    if tail and head in bindings:
        return f"{bindings[head]}.{tail}"
    return None


def _env_pins(node: ast.AST) -> list[tuple[int, str | None]]:
    """Every place in ``node``'s subtree that sets ``AA_GATEWAY_ENDPOINT``, as
    ``(line, value)``; ``value`` is None when it is not a string literal.

    Three mechanisms are accepted deliberately — this gate is about the endpoint
    being pinned, not about which tool does the pinning: ``monkeypatch.setenv``,
    ``patch.dict(os.environ, {...})`` and a direct ``os.environ[...] =``.
    """
    pins: list[tuple[int, str | None]] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            callee = _dotted(child.func) or ""
            if callee.rsplit(".", 1)[-1] == "setenv" and len(child.args) >= 2:
                if _string_value(child.args[0]) == GATEWAY_ENDPOINT_ENV:
                    pins.append((child.lineno, _string_value(child.args[1])))
            for argument in child.args + [kw.value for kw in child.keywords]:
                if not isinstance(argument, ast.Dict):
                    continue
                for key, value in zip(argument.keys, argument.values):
                    if key is not None and _string_value(key) == GATEWAY_ENDPOINT_ENV:
                        pins.append((child.lineno, _string_value(value)))
        elif isinstance(child, ast.Assign):
            for target in child.targets:
                if not isinstance(target, ast.Subscript):
                    continue
                if _string_value(target.slice) == GATEWAY_ENDPOINT_ENV:
                    pins.append((child.lineno, _string_value(child.value)))
    return pins


def _init_sites(
    tree: ast.AST, bindings: dict[str, str]
) -> list[tuple[ast.AST, ast.Call]]:
    """Every ``init_assembly`` call, paired with the innermost function enclosing
    it — the scope a pin has to appear in, so a pin in a sibling test does not
    vouch for this one. A call outside any function is scoped to the module.
    """
    enclosing: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            enclosing[child] = parent

    def innermost_scope(node: ast.AST) -> ast.AST:
        current: ast.AST | None = enclosing.get(node)
        while current is not None:
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return current
            current = enclosing.get(current)
        return tree

    sites: list[tuple[ast.AST, ast.Call]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = _dotted(node.func)
        if callee is None or _resolve(callee, bindings) != INIT_ENTRY_POINT:
            continue
        sites.append((innermost_scope(node), node))
    return sites


def gateway_coverage(source: str) -> tuple[int, int]:
    """``(init_assembly call sites, of those with the endpoint pinned)``.

    Reported by ``main`` so the EX-MOCK-05 rule cannot pass by measuring nothing:
    a parser that stops recognising these calls shows 0 sites, not a clean tree.
    """
    tree = ast.parse(source)
    bindings = _sdk_bindings(tree)
    total = 0
    pinned = 0
    for scope, _node in _init_sites(tree, bindings):
        total += 1
        if _env_pins(scope):
            pinned += 1
    return total, pinned


def _gateway_findings(path: str, tree: ast.AST, bindings: dict[str, str]) -> list[Finding]:
    """EX-MOCK-05 / EX-MOCK-06: AAASM-6196."""
    findings: list[Finding] = []
    for scope, node in _init_sites(tree, bindings):
        pins = _env_pins(scope)
        if not pins:
            findings.append(
                Finding(
                    path,
                    node.lineno,
                    "EX-MOCK-05",
                    f"calls init_assembly without pinning {GATEWAY_ENDPOINT_ENV}, so whether a "
                    "gateway answers is a property of the machine, not of the test. AAASM-6196: "
                    "with a gateway listening on :50051 these tests passed against SDK 0.0.1rc7, "
                    "which breaks the no-gateway contract they claim to assert. Passing a "
                    f"different gateway_url does not help — the resolver keeps only its host and "
                    f"substitutes port {DEFAULT_GRPC_PORT}. Set {GATEWAY_ENDPOINT_ENV} in this "
                    "test, e.g. monkeypatch.setenv(..., 'http://127.0.0.1:1').",
                )
            )
            continue

        for line, value in pins:
            if value is None:
                findings.append(
                    Finding(
                        path,
                        line,
                        "EX-MOCK-06",
                        f"sets {GATEWAY_ENDPOINT_ENV} to a value this gate cannot read, so it "
                        "cannot tell whether the endpoint ends up unreachable or pointed at a "
                        f"live gateway on :{DEFAULT_GRPC_PORT}. Pass a string literal.",
                    )
                )
            elif f":{DEFAULT_GRPC_PORT}" in value:
                findings.append(
                    Finding(
                        path,
                        line,
                        "EX-MOCK-06",
                        f"pins {GATEWAY_ENDPOINT_ENV} to {value!r}, which names the default gRPC "
                        f"port {DEFAULT_GRPC_PORT} — the one port a locally running gateway "
                        "occupies. That reinstates the ambient dependency AAASM-6196 removed "
                        "while looking like a pin. Name a port nothing can serve on.",
                    )
                )
    return findings


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

    findings.extend(_gateway_findings(path, tree, bindings))

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
    init_sites = 0
    pinned_sites = 0
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
        file_init, file_pinned = gateway_coverage(source)
        init_sites += file_init
        pinned_sites += file_pinned

    findings.extend(check_consistency(sites))

    print(f"Scanned {len(targets)} Python example test file(s).")
    print(f"  {pinned_sites:>3} of {init_sites} init_assembly site(s) pin {GATEWAY_ENDPOINT_ENV}")
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
        print(
            f"OK: {len(targets)} file(s) scanned, zero private-seam patches, one seam in use, "
            f"{pinned_sites}/{init_sites} init_assembly site(s) pinned to a fixed endpoint."
        )
        return 0

    for finding in sorted(findings, key=lambda f: (f.path, f.line, f.rule_id)):
        print(f"::error file={finding.path},line={finding.line}::{finding.rule_id}: {finding.message}")
    print(f"\ncheck_example_sdk_mocks: {len(findings)} blocking finding(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
