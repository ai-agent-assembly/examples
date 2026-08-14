#!/usr/bin/env python3
"""Assert each dependency manifest in this repo is reachable by Dependabot.

WHY THIS EXISTS
---------------
AAASM-5675 was filed after a Dependabot *security* job failed for weeks against
a directory that ``.github/dependabot.yml`` did not list. Security updates are
advisory-driven: GitHub runs them against a manifest whether or not that
manifest has a scheduled-update entry. So an unlisted directory does not go
quiet — it gets a job whose configuration cannot satisfy it, the job errors, and
the vulnerable dependency stays put. The failure is real, and invisible: it lands
on a check run nobody is required to read.

Two distinct defects produce that outcome, and this script asserts against both:

1. **An uncovered manifest.** A directory holding ``pnpm-lock.yaml`` /
   ``go.mod`` / ``uv.lock`` that matches zero entries for its ecosystem. It gets
   no scheduled maintenance, and its security jobs run unconfigured.

2. **A dead directory pattern.** An entry in ``.github/dependabot.yml`` whose
   ``directory``/``directories`` value matches zero manifests. A mistyped path
   is silently inert — the config *looks* like coverage while delivering zero,
   which is indistinguishable from the bug in (1) without a check like this one.

Defect 2 is the one that hides. A reviewer reading ``dependabot.yml`` sees a
plausible path and moves on; only expansion against the real tree separates a
working entry from a typo.

CONTRACT
--------
Exit 0 when each discovered manifest directory maps to at least one entry of its
ecosystem, and each configured directory pattern expands to at least one
manifest. Exit 1 otherwise, listing both populations.

This is a *coverage* check, not a vulnerability scanner. It asserts that
Dependabot can reach the manifest; it says nothing about what Dependabot finds
there. Advisory state is Dependabot's job — this guards its reachability.

DIRECTORY PATTERN MATCHING
--------------------------
Dependabot expands globs in ``directories``. This script implements the two
forms this repo uses, matched segment-wise against POSIX-style paths rooted at
``/``:

* ``*``  — matches exactly one path segment (``/node/*`` covers ``/node/mastra``
  but not ``/node/a/b``).
* ``**`` — matches zero or more path segments.

A pattern with neither wildcard is compared literally. Trailing slashes are
normalised away, and ``/`` denotes the repository root.

Stdlib only, matching ``scripts/generate_example_metadata.py`` — CI runs it
straight after ``actions/setup-python`` with zero installs, so a parse failure
here cannot be caused by a missing third-party package.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

# Manifest filename -> the Dependabot ecosystem responsible for it.
#
# `uv.lock` maps to `pip`: this repo's Python examples pair a `uv.lock` with a
# `pyproject.toml`, and Dependabot's pip ecosystem demonstrably raises PRs that
# rewrite those lockfiles (see the "Bump cryptography in /python/..." commits).
MANIFEST_ECOSYSTEMS: dict[str, str] = {
    "pnpm-lock.yaml": "npm",
    "go.mod": "gomod",
    "uv.lock": "pip",
}

# `github-actions` does not follow the one-manifest-per-directory shape of the
# others: Dependabot scans `.github/workflows/` and expects the entry to be
# pinned at the repository root. It is discovered separately, as `/`, whenever
# this repo holds at least one workflow file.
GITHUB_ACTIONS_ECOSYSTEM = "github-actions"
WORKFLOW_DIRECTORY = Path(".github") / "workflows"

# Directories that hold vendored or generated dependency trees. A `go.mod` or a
# lockfile inside one of these is not a manifest this repo maintains, and
# Dependabot does not update it either, so counting them would produce false
# "uncovered" findings.
SKIP_DIRECTORY_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
        "vendor",
        "venv",
    }
)


class DependabotConfigError(RuntimeError):
    """Raised when ``.github/dependabot.yml`` cannot be read with confidence.

    Deliberately fatal rather than skipped. A coverage gate that silently
    tolerates a config it failed to understand reports success while measuring
    zero, which is the exact failure mode this script was written to catch.
    """


class UpdateEntry:
    """One item under ``updates:`` in ``.github/dependabot.yml``."""

    def __init__(self, ecosystem: str, directories: list[str], line: int) -> None:
        self.ecosystem = ecosystem
        self.directories = directories
        self.line = line

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"UpdateEntry({self.ecosystem!r}, {self.directories!r}, line={self.line})"


def _strip_comment(value: str) -> str:
    """Drop a trailing ``#`` comment that sits outside a quoted string."""
    in_single = False
    in_double = False
    for index, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            # A `#` only opens a comment when preceded by whitespace or at the
            # start of the value, matching YAML's own rule.
            if index == 0 or value[index - 1].isspace():
                return value[:index]
    return value


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def parse_dependabot_config(text: str) -> list[UpdateEntry]:
    """Parse the narrow YAML dialect used by ``.github/dependabot.yml``.

    Only the fields this gate needs are extracted — ``package-ecosystem``,
    ``directory`` and ``directories``. Keys nested deeper than an entry's own
    level (``schedule``, ``ignore``, ``labels`` and friends) are skipped by
    indentation, so a ``dependency-name`` under ``ignore`` cannot be mistaken
    for an entry key.

    Fails loudly on a structure it does not recognise, per
    :class:`DependabotConfigError`.
    """
    lines = text.splitlines()

    updates_index: int | None = None
    for index, raw in enumerate(lines):
        if raw.rstrip() == "updates:":
            updates_index = index
            break
    if updates_index is None:
        raise DependabotConfigError("no top-level 'updates:' key found")

    entries: list[UpdateEntry] = []
    current_ecosystem: str | None = None
    current_directories: list[str] = []
    current_line = 0
    entry_indent: int | None = None
    collecting_directories = False

    def flush() -> None:
        nonlocal current_ecosystem, current_directories, collecting_directories
        if current_ecosystem is None and not current_directories:
            return
        if current_ecosystem is None:
            raise DependabotConfigError(
                f"update entry at line {current_line} has no 'package-ecosystem'"
            )
        if not current_directories:
            raise DependabotConfigError(
                f"update entry '{current_ecosystem}' at line {current_line} "
                "declares neither 'directory' nor 'directories'"
            )
        entries.append(UpdateEntry(current_ecosystem, current_directories, current_line))
        current_ecosystem = None
        current_directories = []
        collecting_directories = False

    for offset, raw in enumerate(lines[updates_index + 1 :], start=updates_index + 2):
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue

        indent = _indent_of(stripped)
        content = stripped.strip()

        # A new top-level key ends the `updates:` block.
        if indent == 0:
            break

        # Start of a new update entry: `  - package-ecosystem: "npm"`.
        if content.startswith("- ") and (entry_indent is None or indent == entry_indent):
            if entry_indent is None:
                entry_indent = indent
            flush()
            current_line = offset
            inner = content[2:].strip()
            if inner:
                key, sep, value = inner.partition(":")
                if not sep:
                    raise DependabotConfigError(
                        f"line {offset}: expected 'key: value', found {inner!r}"
                    )
                key = key.strip()
                if key == "package-ecosystem":
                    current_ecosystem = _unquote(value)
                elif key == "directory":
                    current_directories.append(_normalise_directory(_unquote(value)))
                elif key == "directories":
                    collecting_directories = True
                    continue
            collecting_directories = False
            continue

        if entry_indent is None:
            # Content under `updates:` that is not an entry — unrecognised.
            raise DependabotConfigError(
                f"line {offset}: expected an update entry, found {content!r}"
            )

        key_indent = entry_indent + 2

        # A `directories:` list item: `      - "/node/*"`.
        if collecting_directories and indent > key_indent and content.startswith("- "):
            current_directories.append(_normalise_directory(_unquote(content[2:])))
            continue

        if indent == key_indent:
            collecting_directories = False
            key, sep, value = content.partition(":")
            if not sep:
                raise DependabotConfigError(f"line {offset}: expected 'key: value', found {content!r}")
            key = key.strip()
            value = value.strip()
            if key == "package-ecosystem":
                current_ecosystem = _unquote(value)
            elif key == "directory":
                current_directories.append(_normalise_directory(_unquote(value)))
            elif key == "directories":
                if value:
                    raise DependabotConfigError(
                        f"line {offset}: inline 'directories' lists are not supported"
                    )
                collecting_directories = True
            # Other entry keys (schedule, labels, ignore, ...) are not this
            # gate's concern and are skipped by indentation below.
            continue

        # Deeper than an entry key -> belongs to schedule/ignore/labels/etc.
        if indent > key_indent:
            continue

        raise DependabotConfigError(f"line {offset}: unexpected indentation in {content!r}")

    flush()

    if not entries:
        raise DependabotConfigError("'updates:' contains zero entries")
    return entries


def _normalise_directory(value: str) -> str:
    """Normalise a configured directory to a leading-slash, no-trailing-slash form."""
    value = value.strip()
    if not value.startswith("/"):
        value = "/" + value
    if len(value) > 1:
        value = value.rstrip("/")
    return value or "/"


def directory_matches(pattern: str, directory: str) -> bool:
    """Match a Dependabot directory pattern against a repo-relative directory.

    ``*`` spans one path segment; ``**`` spans zero or more.
    """
    if pattern == directory:
        return True

    pattern_parts = [part for part in pattern.split("/") if part]
    directory_parts = [part for part in directory.split("/") if part]

    return _match_segments(pattern_parts, directory_parts)


def _match_segments(pattern_parts: list[str], directory_parts: list[str]) -> bool:
    if not pattern_parts:
        return not directory_parts

    head, *rest = pattern_parts

    if head == "**":
        # `**` consumes zero or more segments; try each split point.
        for consumed in range(len(directory_parts) + 1):
            if _match_segments(rest, directory_parts[consumed:]):
                return True
        return False

    if not directory_parts:
        return False

    if not fnmatch.fnmatchcase(directory_parts[0], head):
        return False

    return _match_segments(rest, directory_parts[1:])


def discover_manifest_directories(repo_root: Path) -> dict[str, set[str]]:
    """Walk the tree and group manifest directories by ecosystem."""
    found: dict[str, set[str]] = {ecosystem: set() for ecosystem in MANIFEST_ECOSYSTEMS.values()}
    found[GITHUB_ACTIONS_ECOSYSTEM] = set()

    workflow_root = repo_root / WORKFLOW_DIRECTORY
    if workflow_root.is_dir() and sum(
        1 for candidate in workflow_root.iterdir() if candidate.suffix in {".yml", ".yaml"}
    ):
        found[GITHUB_ACTIONS_ECOSYSTEM].add("/")

    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        ecosystem = MANIFEST_ECOSYSTEMS.get(path.name)
        if ecosystem is None:
            continue
        relative = path.relative_to(repo_root)
        if SKIP_DIRECTORY_NAMES.intersection(relative.parts):
            continue
        directory = "/" + relative.parent.as_posix()
        if directory == "/.":
            directory = "/"
        found[ecosystem].add(directory)

    return found


def evaluate(
    entries: list[UpdateEntry], discovered: dict[str, set[str]]
) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """Return (uncovered manifests by ecosystem, dead patterns as (ecosystem, pattern))."""
    uncovered: dict[str, list[str]] = {}
    dead_patterns: list[tuple[str, str]] = []

    patterns_by_ecosystem: dict[str, list[str]] = {}
    for entry in entries:
        patterns_by_ecosystem.setdefault(entry.ecosystem, []).extend(entry.directories)

    for ecosystem, directories in discovered.items():
        patterns = patterns_by_ecosystem.get(ecosystem, [])
        missing = sorted(
            directory
            for directory in directories
            if not _covered_by(directory, patterns)
        )
        if missing:
            uncovered[ecosystem] = missing

    for ecosystem, patterns in patterns_by_ecosystem.items():
        directories = discovered.get(ecosystem, set())
        for pattern in patterns:
            if not _matches_something(pattern, directories):
                dead_patterns.append((ecosystem, pattern))

    return uncovered, sorted(dead_patterns)


def _covered_by(directory: str, patterns: list[str]) -> bool:
    return sum(1 for pattern in patterns if directory_matches(pattern, directory)) > 0


def _matches_something(pattern: str, directories: set[str]) -> bool:
    return sum(1 for directory in directories if directory_matches(pattern, directory)) > 0


def _repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_repo_root_from_script(),
        help="repository root to scan (defaults to this script's parent repo)",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root.resolve()
    config_path = repo_root / ".github" / "dependabot.yml"
    if not config_path.is_file():
        print(f"::error::{config_path} is missing — Dependabot coverage is unmeasured.")
        return 1

    try:
        entries = parse_dependabot_config(config_path.read_text(encoding="utf-8"))
    except DependabotConfigError as exc:
        print(f"::error::Could not parse {config_path}: {exc}")
        print("::error::Refusing to report coverage from a config this gate did not understand.")
        return 1

    discovered = discover_manifest_directories(repo_root)
    uncovered, dead_patterns = evaluate(entries, discovered)

    print(f"Parsed {len(entries)} update entries from .github/dependabot.yml")
    for ecosystem in sorted(discovered):
        directories = discovered[ecosystem]
        covered = len(directories) - len(uncovered.get(ecosystem, []))
        print(f"  {ecosystem:<16} {covered}/{len(directories)} manifest directories covered")

    if not uncovered and not dead_patterns:
        total = sum(len(directories) for directories in discovered.values())
        print(f"OK: {total} manifest directories map to an entry, with zero left over.")
        return 0

    for ecosystem, directories in sorted(uncovered.items()):
        for directory in directories:
            print(
                f"::error::{directory} holds a {ecosystem} manifest that matches zero "
                f"'{ecosystem}' entries in .github/dependabot.yml. Dependabot will still "
                "run advisory-driven security jobs against it, unconfigured — which is how "
                "AAASM-5675's failing js-yaml job arose. Add the directory to the "
                f"'{ecosystem}' entry."
            )

    for ecosystem, pattern in dead_patterns:
        print(
            f"::error::'{pattern}' is configured for '{ecosystem}' but expands to zero "
            "manifest directories. A path that matches nothing looks like coverage and "
            "delivers zero. Correct or drop it."
        )

    return 1


if __name__ == "__main__":
    sys.exit(main())
