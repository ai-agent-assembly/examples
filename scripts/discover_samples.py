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
_PYPROJECT_TOML = "pyproject.toml"
_GO_MOD = "go.mod"
_PACKAGE_JSON = "package.json"
_AGENT_PY = "agent.py"
_AGENT_JS = "agent.js"
_MARKERS = (_PYPROJECT_TOML, _GO_MOD, _PACKAGE_JSON, _AGENT_PY, _AGENT_JS)

# Build manifests own their whole subtree (see ``_manifest_roots``).
_MANIFEST_MARKERS = (_PYPROJECT_TOML, _GO_MOD, _PACKAGE_JSON)


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

    if (directory / _PYPROJECT_TOML).is_file():
        if (directory / "tests").is_dir():
            return ("python", "uv-pytest", "")
        return ("python", "uv-main", "src/main.py")
    if (directory / _GO_MOD).is_file():
        return ("go", "go-test", "")
    if (directory / _PACKAGE_JSON).is_file():
        scripts = _load_scripts(directory / _PACKAGE_JSON)
        if "test" in scripts:
            return ("node", "pnpm-test", "")
        if (directory / _AGENT_JS).is_file():
            return ("node", "node-script", _AGENT_JS)
        return None
    if (directory / _AGENT_PY).is_file():
        return ("python", "py-script", _AGENT_PY)
    if (directory / _AGENT_JS).is_file():
        return ("node", "node-script", _AGENT_JS)
    return None


def _gather_candidate_roots(repo_root: Path) -> set[Path]:
    """Directories holding a marker file, minus vendored/build/cache subtrees."""

    candidates: set[Path] = set()
    for marker in _MARKERS:
        for found in repo_root.rglob(marker):
            parent = found.parent
            rel_parts = parent.relative_to(repo_root).parts
            if any(part in _SKIP_PARTS for part in rel_parts):
                continue
            candidates.add(parent)
    return candidates


def _manifest_roots(candidates: set[Path]) -> set[Path]:
    """Candidates rooted by a build manifest.

    Such a directory owns its whole subtree, so a candidate nested under one is
    dropped later — an example's internal module (e.g.
    ``python/pydantic-ai/src/agent.py``) is never mistaken for its own sample.
    """

    return {
        directory
        for directory in candidates
        if any((directory / m).is_file() for m in _MANIFEST_MARKERS)
    }


def _matrix_entry(
    directory: Path, repo_root: Path, manifest_roots: set[Path]
) -> tuple[str, dict[str, str]] | None:
    """Return ``(lang, matrix_entry)`` for a sample dir, or ``None`` to skip it."""

    rel = directory.relative_to(repo_root).as_posix()
    if rel == ".":
        return None
    if any(rel == p or rel.startswith(p + "/") for p in _EXCLUDE_PREFIXES):
        return None
    if any(root in directory.parents for root in manifest_roots):
        return None
    result = classify(directory)
    if result is None:
        return None
    lang, runner, entry = result
    return lang, {"name": rel, "path": rel, "runner": runner, "entry": entry}


def discover(repo_root: Path) -> dict[str, list[dict[str, str]]]:
    candidates = _gather_candidate_roots(repo_root)
    manifest_roots = _manifest_roots(candidates)

    buckets: dict[str, list[dict[str, str]]] = {"python": [], "node": [], "go": []}
    for directory in sorted(candidates):
        entry = _matrix_entry(directory, repo_root, manifest_roots)
        if entry is None:
            continue
        lang, matrix_entry = entry
        buckets[lang].append(matrix_entry)
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
