#!/usr/bin/env python3
"""Assert every pnpm-workspace.yaml "overrides" entry survives into its lockfile.

WHY THIS EXISTS
---------------
AAASM-6032: four Dependabot relocks in this repo silently dropped the
``overrides:`` block from ``pnpm-lock.yaml`` while the sibling config still
declared it, breaking every subsequent ``pnpm install --frozen-lockfile`` (the
implicit mode pnpm uses whenever ``CI=true``, which every workflow here runs
under) with ``ERR_PNPM_LOCKFILE_CONFIG_MISMATCH``. The install step already
catches this — that is how all four were found — but it reports a generic
resolver error with no directory or package name attached, so each occurrence
had to be diagnosed by hand. This script names the cause directly: which
directory, which override key, config vs. lockfile.

The overrides themselves used to live in ``package.json``'s ``pnpm.overrides``
field; AAASM-6032 also migrated them to ``pnpm-workspace.yaml``, the field
pnpm 10 and pnpm 11 both read (``pnpm.overrides`` in ``package.json`` is
no longer read as of pnpm 11 — https://pnpm.io/settings). That migration
removes the specific cross-major-version drift that caused the four relock
failures; this check is the defense-in-depth half of the fix, for whatever
future variant of "the lockfile fell out of sync with its config" turns up.

CONTRACT
--------
For every ``pnpm-workspace.yaml`` that declares an ``overrides:`` mapping,
its sibling ``pnpm-lock.yaml`` must declare the identical mapping (same keys,
same values). Exit 0 if every pair matches (or no directory declares
overrides at all). Exit 1 and list every mismatch otherwise.

This is a parity check, not a lockfile validator — it does not evaluate
whether an override's version range is itself correct, only whether the two
files agree. Actually applying the wrong version to installed packages is
``pnpm install --frozen-lockfile``'s job, and it already runs on every PR.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIR_NAMES = {"node_modules", ".git", ".venv"}


def _iter_workspace_files(root: Path) -> list[Path]:
    found = []
    for path in root.rglob("pnpm-workspace.yaml"):
        if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
            continue
        found.append(path)
    return sorted(found)


def _parse_flat_mapping(lines: list[str], header: str) -> dict[str, str] | None:
    """Extract a simple `header:\\n  key: value` block's contents as a dict.

    Handles the two shapes both files actually use: bare keys (``esbuild:``)
    and single/double-quoted keys (``'@scope/name':``). Values are taken
    verbatim (after stripping matching quotes) — good enough for a parity
    comparison, since both files are written by the same pnpm and use the
    same quoting rules for the same key.
    """
    for i, line in enumerate(lines):
        if line.rstrip() != f"{header}:":
            continue
        mapping: dict[str, str] = {}
        for follow in lines[i + 1 :]:
            if follow.strip() == "" or follow.startswith("#"):
                continue
            if not follow.startswith(("  ", "\t")):
                break  # dedented past the end of this block
            stripped = follow.strip()
            if ":" not in stripped:
                break
            key, _, value = stripped.partition(":")
            key = key.strip().strip("'\"")
            value = value.strip().strip("'\"")
            mapping[key] = value
        return mapping
    return None


def _parse_overrides(path: Path, header: str) -> dict[str, str] | None:
    lines = path.read_text(encoding="utf-8").splitlines()
    return _parse_flat_mapping(lines, header)


def main() -> int:
    mismatches: list[str] = []
    checked = 0

    for workspace_file in _iter_workspace_files(REPO_ROOT):
        config_overrides = _parse_overrides(workspace_file, "overrides")
        if not config_overrides:
            continue

        lock_file = workspace_file.parent / "pnpm-lock.yaml"
        rel = workspace_file.parent.relative_to(REPO_ROOT)
        if not lock_file.exists():
            mismatches.append(
                f"{rel}: pnpm-workspace.yaml declares overrides "
                f"{sorted(config_overrides)} but no pnpm-lock.yaml exists alongside it"
            )
            continue

        checked += 1
        lock_overrides = _parse_overrides(lock_file, "overrides") or {}

        missing = {k: v for k, v in config_overrides.items() if lock_overrides.get(k) != v}
        extra = {k: v for k, v in lock_overrides.items() if k not in config_overrides}

        if missing:
            detail = ", ".join(f"{k}={v!r} (lockfile has {lock_overrides.get(k)!r})" for k, v in sorted(missing.items()))
            mismatches.append(f"{rel}: pnpm-lock.yaml missing/mismatched overrides: {detail}")
        if extra:
            detail = ", ".join(f"{k}={v!r}" for k, v in sorted(extra.items()))
            mismatches.append(f"{rel}: pnpm-lock.yaml has overrides not in pnpm-workspace.yaml: {detail}")

    if mismatches:
        print("check_pnpm_overrides_parity: FAIL", file=sys.stderr)
        for m in mismatches:
            print(f"  {m}", file=sys.stderr)
        print(
            f"\n{len(mismatches)} mismatch(es) across {checked} overrides-carrying "
            "director(y/ies). Fix: cd <directory> && corepack pnpm@10.34.5 install "
            "--no-frozen-lockfile (matching the pnpm version CI resolves via "
            "pnpm/action-setup's `version: 10`), then re-check the diff is symmetric.",
            file=sys.stderr,
        )
        return 1

    print(f"check_pnpm_overrides_parity: OK — {checked} overrides-carrying director(y/ies) checked, 0 mismatches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
