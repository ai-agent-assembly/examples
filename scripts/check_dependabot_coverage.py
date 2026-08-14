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
    :class:`DependabotConfigError`. Split into three stages — isolate the
    ``updates:`` block, cut it into per-entry chunks, read each chunk — because
    a parser whose correctness is load-bearing should be reviewable in pieces.
    """
    block = _updates_block(text.splitlines())
    chunks = _split_entries(block)
    return [_parse_entry(chunk) for chunk in chunks]


def _updates_block(lines: list[str]) -> list[tuple[int, str]]:
    """Return the ``(line number, text)`` pairs sitting under ``updates:``.

    Blank lines and comments are dropped; the block ends at the next key in
    column 0.
    """
    block: list[tuple[int, str]] = []
    inside = False

    for number, raw in enumerate(lines, start=1):
        if not inside:
            inside = raw.rstrip() == "updates:"
            continue
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue
        if _indent_of(stripped) == 0:
            break
        block.append((number, stripped))

    if not inside:
        raise DependabotConfigError("no top-level 'updates:' key found")
    return block


def _split_entries(block: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Cut the ``updates:`` block into one chunk per ``- `` item."""
    chunks: list[list[tuple[int, str]]] = []
    entry_indent: int | None = None

    for number, line in block:
        indent = _indent_of(line)
        content = line.strip()
        # A `- ` deeper than the entry indent is a list item belonging to the
        # current entry (a `directories:` path, an `ignore:` rule), so only the
        # ones at the entry indent open a new chunk.
        if content.startswith("- "):
            if entry_indent is None:
                entry_indent = indent
            if indent == entry_indent:
                chunks.append([])

        if not chunks:
            raise DependabotConfigError(
                f"line {number}: expected an update entry, found {content!r}"
            )
        chunks[-1].append((number, line))

    if not chunks:
        raise DependabotConfigError("'updates:' contains zero entries")
    return chunks


def _parse_entry(chunk: list[tuple[int, str]]) -> UpdateEntry:
    """Read one update entry's ecosystem and directories."""
    first_number, first_line = chunk[0]
    entry_indent = _indent_of(first_line)
    key_indent = entry_indent + 2

    ecosystem: str | None = None
    directories: list[str] = []
    collecting = False

    for number, line in chunk:
        indent = _indent_of(line)
        content = line.strip()

        # `  - package-ecosystem: "npm"` carries its first key inline.
        if indent == entry_indent and content.startswith("- "):
            content = content[2:].strip()
            indent = key_indent
            if not content:
                continue

        # A `directories:` list item sits deeper than the entry's own keys.
        if collecting and indent > key_indent and content.startswith("- "):
            directories.append(_normalise_directory(_unquote(content[2:])))
            continue

        # Deeper than an entry key -> schedule/ignore/labels internals.
        if indent != key_indent:
            continue

        collecting = False
        key, value = _split_key(number, content)
        if key == "package-ecosystem":
            ecosystem = _unquote(value)
        elif key == "directory":
            directories.append(_normalise_directory(_unquote(value)))
        elif key == "directories":
            if value:
                raise DependabotConfigError(
                    f"line {number}: inline 'directories' lists are not supported"
                )
            collecting = True

    return _validated_entry(ecosystem, directories, first_number)


def _split_key(number: int, content: str) -> tuple[str, str]:
    key, sep, value = content.partition(":")
    if not sep:
        raise DependabotConfigError(f"line {number}: expected 'key: value', found {content!r}")
    return key.strip(), value.strip()


def _validated_entry(
    ecosystem: str | None, directories: list[str], line: int
) -> UpdateEntry:
    if ecosystem is None:
        raise DependabotConfigError(f"update entry at line {line} has no 'package-ecosystem'")
    if not directories:
        raise DependabotConfigError(
            f"update entry '{ecosystem}' at line {line} declares neither "
            "'directory' nor 'directories'"
        )
    return UpdateEntry(ecosystem, directories, line)


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
