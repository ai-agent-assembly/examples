#!/usr/bin/env python3
"""Discover every runnable sample in the repo for the scheduled sweep lane.

WHY THIS EXISTS
---------------
The per-PR ``verify-python``/``verify-node``/``verify-go`` lanes enumerate their
examples with a **hardcoded job list**. That is how AAASM-4458 stayed open after
the framework examples were added: a stale or freshly-added sample that nobody
remembered to wire into the hardcoded list would never be executed, so a
langchain-class API-drift break in it would ship undetected. This script removes
the hardcoded list from the equation — it walks the tree and finds every sample
by its manifest/entry file, so a new example directory is covered the moment it
lands, with no workflow edit required. ``verify-all-samples.yml`` consumes its
output as three dynamic job matrices.

CONTRACT
--------
Emits three JSON arrays (``python``, ``node``, ``go``); each element is
``{"name", "path", "runner", "entry"}`` and drives one matrix job:

* ``uv-pytest``  — ``pyproject.toml`` + ``tests/``: ``uv sync --extra dev`` then
  ``uv run pytest tests/`` (the offline ``--mock`` path this repo's CI verifies).
* ``uv-main``    — ``pyproject.toml``, no ``tests/``: ``uv run python <entry> --mock``.
* ``py-script``  — bare ``agent.py`` (scenario smoke run): ``python <entry>``.
* ``go-test``    — ``go.mod``: ``go test ./...``.
* ``pnpm-test``  — ``package.json`` with a ``test`` script: ``pnpm install`` +
  ``pnpm test`` (and ``pnpm typecheck`` when that script exists).
* ``node-script``— ``package.json``/``agent.js`` with no ``test`` script: ``node <entry>``.

Standard library only — no PyYAML/tomllib-version constraint, so it runs on any
CI Python without an install step, matching ``generate_example_metadata.py``.

The sweep is deliberately **mock/offline only**: it never installs the ``live``
extra and excludes ``scenarios/live-core-enforcement`` — that scenario needs a
real gateway and is owned by the scheduled ``verify-live.yml`` lane (AAASM-4475),
which this must not duplicate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Directories that are never a sample root: vendored deps, build output, VCS,
# and tooling caches. Any candidate whose path crosses one of these is dropped.
_SKIP_PARTS = frozenset(
    {
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        ".git",
        ".github",
        "target",
        ".pytest_cache",
        "__pycache__",
        ".mypy_cache",
        ".idea",
    }
)

# Scenario roots the sweep must NOT run: they require a real gateway/native
# transport and are covered by the scheduled verify-live.yml lane instead.
_EXCLUDE_PREFIXES = ("scenarios/live-core-enforcement",)

# Marker files that identify a sample root, in classification precedence order.
_MARKERS = ("pyproject.toml", "go.mod", "package.json", "agent.py", "agent.js")


def _load_scripts(package_json: Path) -> dict[str, str]:
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    scripts = data.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def classify(directory: Path) -> tuple[str, str, str] | None:
    """Return ``(lang, runner, entry)`` for a sample root, or ``None``.

    ``entry`` is the run target relative to ``directory`` (empty when the runner
    does not need one). Precedence follows ``_MARKERS``.
    """

    if (directory / "pyproject.toml").is_file():
        if (directory / "tests").is_dir():
            return ("python", "uv-pytest", "")
        return ("python", "uv-main", "src/main.py")
    if (directory / "go.mod").is_file():
        return ("go", "go-test", "")
    if (directory / "package.json").is_file():
        scripts = _load_scripts(directory / "package.json")
        if "test" in scripts:
            return ("node", "pnpm-test", "")
        if (directory / "agent.js").is_file():
            return ("node", "node-script", "agent.js")
        return None
    if (directory / "agent.py").is_file():
        return ("python", "py-script", "agent.py")
    if (directory / "agent.js").is_file():
        return ("node", "node-script", "agent.js")
    return None


def discover(repo_root: Path) -> dict[str, list[dict[str, str]]]:
    candidates: set[Path] = set()
    for marker in _MARKERS:
        for found in repo_root.rglob(marker):
            parent = found.parent
            rel_parts = parent.relative_to(repo_root).parts
            if any(part in _SKIP_PARTS for part in rel_parts):
                continue
            candidates.add(parent)

    # A sample rooted by a build manifest owns its whole subtree. Drop any
    # candidate nested under one so an example's internal module (e.g.
    # ``python/pydantic-ai/src/agent.py``) is never mistaken for its own sample.
    manifest_roots = {
        directory
        for directory in candidates
        if any(
            (directory / m).is_file()
            for m in ("pyproject.toml", "go.mod", "package.json")
        )
    }

    buckets: dict[str, list[dict[str, str]]] = {"python": [], "node": [], "go": []}
    for directory in sorted(candidates):
        rel = directory.relative_to(repo_root).as_posix()
        if rel == ".":
            continue
        if any(rel == p or rel.startswith(p + "/") for p in _EXCLUDE_PREFIXES):
            continue
        if any(root in directory.parents for root in manifest_roots):
            continue
        result = classify(directory)
        if result is None:
            continue
        lang, runner, entry = result
        buckets[lang].append(
            {"name": rel, "path": rel, "runner": runner, "entry": entry}
        )
    return buckets


def _repo_root_from_script() -> Path:
    # This file lives at <repo>/scripts/discover_samples.py.
    return Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_repo_root_from_script(),
        help="Path to the repository root (defaults to the script's parent).",
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="Append python/node/go matrix arrays to $GITHUB_OUTPUT.",
    )
    args = parser.parse_args(argv)

    buckets = discover(args.repo_root)

    if args.github_output:
        output = os.environ.get("GITHUB_OUTPUT")
        if not output:
            print("GITHUB_OUTPUT is not set", file=sys.stderr)
            return 1
        with open(output, "a", encoding="utf-8") as handle:
            for lang in ("python", "node", "go"):
                handle.write(f"{lang}={json.dumps(buckets[lang])}\n")

    for lang in ("python", "node", "go"):
        entries = buckets[lang]
        print(f"{lang}: {len(entries)} sample(s)")
        for entry in entries:
            print(f"  [{entry['runner']}] {entry['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
