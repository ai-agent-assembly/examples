#!/usr/bin/env python3
"""Assert every pnpm-workspace.yaml declares the same build decision to both pnpm majors.

WHY THIS EXISTS
---------------
AAASM-6243: nine directories here failed ``pnpm install`` outright under pnpm 11
with ``ERR_PNPM_IGNORED_BUILDS``, because pnpm 11 reads a directory's
build-script decision **only** from ``allowBuilds`` in ``pnpm-workspace.yaml``.
It does not read ``package.json``'s ``pnpm`` field (dropped in pnpm 11) and it
does not read ``onlyBuiltDependencies`` (pnpm 10's key). Two of the nine already
declared ``onlyBuiltDependencies`` in ``pnpm-workspace.yaml`` and failed anyway,
which is what makes this a parity problem rather than a migration problem: the
two keys mean the same thing to different majors and have to be kept in step.

CI pins pnpm 10 (``pnpm/action-setup`` with ``version: 10``), so pnpm 11's half
of the decision has no runtime consumer in CI today and nothing would notice it
drifting. Worse, every ``pnpm install`` in this repo's workflows passes
``--ignore-scripts``, which suppresses ``ERR_PNPM_IGNORED_BUILDS`` entirely — so
even bumping the pin to ``version: 11`` would not surface a missing
``allowBuilds``. The person who finds it is a contributor following a sample's
README on whatever pnpm they have installed. This check is the only thing in CI
that can see it.

CONTRACT
--------
For every ``pnpm-workspace.yaml`` that declares either key, both must be
declared and name the identical package set:

* ``onlyBuiltDependencies`` — a list, honoured by pnpm 10.
* ``allowBuilds`` — a mapping of package to boolean, honoured by pnpm 11.

Only packages mapped to a true value in ``allowBuilds`` count as allowed, since
``name: false`` is an explicit *denial* and is not equivalent to a listing in
``onlyBuiltDependencies``. Exit 0 if every declaring directory agrees (or none
declares anything); exit 1 and name every divergence otherwise.

WHAT THIS DOES NOT CATCH
------------------------
A directory that declares *neither* key is silent to this check, because
"does this directory have a dependency that runs a build script" is not
answerable from ``pnpm-lock.yaml`` — the lockfile records resolutions, not
whether a package ships an install hook. Three directories here legitimately
declare nothing because they pull no build-script dependency at all
(``scenarios/audit-trace/node``, ``scenarios/budget-limits/node``,
``scenarios/sidecar-runtime/examples/node-agent``), and they install cleanly on
both majors. A newly added directory that does pull one would still have to be
caught by running pnpm 11 against it, not by this script.

Run as ``python -m scripts.check_pnpm_build_decision_parity`` — it imports its
sibling checker's parsing helpers, so it needs the repo root on ``sys.path``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.check_pnpm_overrides_parity import (
    REPO_ROOT,
    _iter_workspace_files,
    _parse_flat_mapping,
)

TRUTHY = {"true", "yes", "on"}


def _parse_list_block(lines: list[str], header: str) -> list[str] | None:
    """Extract a simple ``header:\\n  - item`` block as a list of items.

    Mirrors ``_parse_flat_mapping``'s tolerances deliberately: blank lines and
    comments at any indentation are skipped rather than ending the block, since
    the files here carry justification comments between entries.
    """
    for i, line in enumerate(lines):
        if line.rstrip() != f"{header}:":
            continue
        items: list[str] = []
        for follow in lines[i + 1 :]:
            stripped = follow.strip()
            if stripped == "" or stripped.startswith("#"):
                continue
            if not follow.startswith(("  ", "\t")):
                break  # dedented past the end of this block
            if not stripped.startswith("- "):
                break
            items.append(stripped[2:].strip().strip("'\""))
        return items
    return None


def _allowed_from_mapping(mapping: dict[str, str] | None) -> set[str]:
    if mapping is None:
        return set()
    return {k for k, v in mapping.items() if v.strip().lower() in TRUTHY}


def check(root: Path) -> tuple[list[str], int]:
    """Return (problems, number of directories that declare either key)."""
    problems: list[str] = []
    declaring = 0

    for workspace_file in _iter_workspace_files(root):
        lines = workspace_file.read_text(encoding="utf-8").splitlines()
        only_built = _parse_list_block(lines, "onlyBuiltDependencies")
        allow_raw = _parse_flat_mapping(lines, "allowBuilds")
        rel = workspace_file.parent.relative_to(root)

        if only_built is None and allow_raw is None:
            continue  # declares neither; see WHAT THIS DOES NOT CATCH
        declaring += 1

        if only_built is None:
            problems.append(
                f"{rel}: declares allowBuilds but no onlyBuiltDependencies, so pnpm 10 "
                f"silently skips the build scripts for {sorted(_allowed_from_mapping(allow_raw))}"
            )
            continue
        if allow_raw is None:
            problems.append(
                f"{rel}: declares onlyBuiltDependencies but no allowBuilds, so pnpm 11 "
                f"fails this directory with ERR_PNPM_IGNORED_BUILDS "
                f"(expected allowBuilds entries for {sorted(only_built)})"
            )
            continue

        allowed = _allowed_from_mapping(allow_raw)
        listed = set(only_built)
        if missing := listed - allowed:
            problems.append(
                f"{rel}: in onlyBuiltDependencies but not allowed by allowBuilds: {sorted(missing)}"
            )
        if extra := allowed - listed:
            problems.append(
                f"{rel}: allowed by allowBuilds but not in onlyBuiltDependencies: {sorted(extra)}"
            )

    return problems, declaring


def main() -> int:
    problems, declaring = check(REPO_ROOT)

    if problems:
        print("check_pnpm_build_decision_parity: FAIL", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(
            f"\n{len(problems)} divergence(s) across {declaring} declaring director(y/ies). "
            "Fix: in that directory's pnpm-workspace.yaml, list the package under "
            "onlyBuiltDependencies (pnpm 10) and map it to true under allowBuilds (pnpm 11). "
            "Neither key alone satisfies both majors.",
            file=sys.stderr,
        )
        return 1

    print(
        f"check_pnpm_build_decision_parity: OK — {declaring} declaring "
        "director(y/ies) checked, 0 divergences"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
