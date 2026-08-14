#!/usr/bin/env python3
"""Tests for ``scripts/check_dependabot_coverage.py``.

These exist to keep the gate falsifiable. A coverage checker that returns 0 on
a tree it failed to parse is worse than no checker, because it converts an
unmeasured state into a reported-healthy one. Each test below therefore pairs a
green case with the specific edit that should turn it red.
"""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_dependabot_coverage import (
    DependabotConfigError,
    directory_matches,
    discover_manifest_directories,
    evaluate,
    main,
    parse_dependabot_config,
)

SAMPLE_CONFIG = textwrap.dedent(
    """\
    version: 2
    updates:
      - package-ecosystem: "gomod"
        directories:
          - "/go/*"
          - "/scenarios/live-core-enforcement/go-agent"
        schedule:
          interval: "daily"
        labels:
          - "dependencies"

      - package-ecosystem: "npm"
        directories:
          - "/node/*"
          - "/scenarios/*/node"
        schedule:
          interval: "daily"
        ignore:
          # A comment that mentions directories: and package-ecosystem: to be safe.
          - dependency-name: "typescript"
            update-types: ["version-update:semver-major"]

      - package-ecosystem: "github-actions"
        directory: "/"
        schedule:
          interval: "daily"
    """
)


class ParseConfigTests(unittest.TestCase):
    def test_extracts_ecosystems_and_directories(self) -> None:
        entries = parse_dependabot_config(SAMPLE_CONFIG)
        self.assertEqual([entry.ecosystem for entry in entries], ["gomod", "npm", "github-actions"])
        self.assertEqual(entries[0].directories, ["/go/*", "/scenarios/live-core-enforcement/go-agent"])
        self.assertEqual(entries[1].directories, ["/node/*", "/scenarios/*/node"])
        self.assertEqual(entries[2].directories, ["/"])

    def test_nested_ignore_keys_are_not_mistaken_for_entry_keys(self) -> None:
        """`dependency-name` sits under `ignore:` and must not start an entry."""
        entries = parse_dependabot_config(SAMPLE_CONFIG)
        self.assertEqual(len(entries), 3)

    def test_missing_updates_block_is_fatal(self) -> None:
        with self.assertRaises(DependabotConfigError):
            parse_dependabot_config("version: 2\n")

    def test_entry_without_directory_is_fatal(self) -> None:
        broken = textwrap.dedent(
            """\
            version: 2
            updates:
              - package-ecosystem: "npm"
                schedule:
                  interval: "daily"
            """
        )
        with self.assertRaises(DependabotConfigError):
            parse_dependabot_config(broken)

    def test_entry_without_ecosystem_is_fatal(self) -> None:
        broken = textwrap.dedent(
            """\
            version: 2
            updates:
              - directory: "/"
                schedule:
                  interval: "daily"
            """
        )
        with self.assertRaises(DependabotConfigError):
            parse_dependabot_config(broken)


class DirectoryMatchTests(unittest.TestCase):
    def test_single_star_spans_exactly_one_segment(self) -> None:
        self.assertTrue(directory_matches("/node/*", "/node/mastra"))
        self.assertFalse(directory_matches("/node/*", "/node/mastra/nested"))
        self.assertFalse(directory_matches("/node/*", "/node"))

    def test_double_star_spans_zero_or_more_segments(self) -> None:
        self.assertTrue(directory_matches("/scenarios/**", "/scenarios"))
        self.assertTrue(directory_matches("/scenarios/**", "/scenarios/a/b/c"))

    def test_literal_paths_compare_exactly(self) -> None:
        self.assertTrue(directory_matches("/go/basic-agent", "/go/basic-agent"))
        self.assertFalse(directory_matches("/go/basic-agent", "/go/basic-agent-2"))

    def test_middle_wildcard(self) -> None:
        self.assertTrue(directory_matches("/scenarios/*/node", "/scenarios/audit-trace/node"))
        self.assertFalse(directory_matches("/scenarios/*/node", "/scenarios/audit-trace/python"))


class _Tree:
    """Builds a throwaway repo tree so discovery runs against real files."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def add(self, relative: str, content: str = "") -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class DiscoveryTests(unittest.TestCase):
    def test_groups_manifests_by_ecosystem_and_skips_vendored_trees(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            tree = _Tree(root)
            tree.add("node/mastra/pnpm-lock.yaml")
            tree.add("go/basic-agent/go.mod")
            tree.add("python/langgraph/uv.lock")
            tree.add(".github/workflows/ci.yml")
            # Vendored copies that must not count as maintained manifests.
            tree.add("node/mastra/node_modules/dep/package/pnpm-lock.yaml")
            tree.add("go/basic-agent/vendor/x/go.mod")

            discovered = discover_manifest_directories(root)

            self.assertEqual(discovered["npm"], {"/node/mastra"})
            self.assertEqual(discovered["gomod"], {"/go/basic-agent"})
            self.assertEqual(discovered["pip"], {"/python/langgraph"})
            self.assertEqual(discovered["github-actions"], {"/"})


class EvaluateTests(unittest.TestCase):
    def test_clean_tree_reports_zero_findings(self) -> None:
        entries = parse_dependabot_config(SAMPLE_CONFIG)
        discovered = {
            "gomod": {"/go/basic-agent", "/scenarios/live-core-enforcement/go-agent"},
            "npm": {"/node/mastra", "/scenarios/audit-trace/node"},
            "pip": set(),
            "github-actions": {"/"},
        }
        uncovered, dead = evaluate(entries, discovered)
        self.assertEqual(uncovered, {})
        self.assertEqual(dead, [])

    def test_uncovered_manifest_is_reported(self) -> None:
        entries = parse_dependabot_config(SAMPLE_CONFIG)
        discovered = {
            "gomod": {"/go/basic-agent", "/scenarios/live-core-enforcement/go-agent"},
            # A new example added outside the configured npm patterns. The
            # other npm directories stay present so this case isolates the
            # uncovered-manifest finding from the dead-pattern one.
            "npm": {"/node/mastra", "/scenarios/audit-trace/node", "/tools/scratch-client"},
            "pip": set(),
            "github-actions": {"/"},
        }
        uncovered, dead = evaluate(entries, discovered)
        self.assertEqual(uncovered, {"npm": ["/tools/scratch-client"]})
        self.assertEqual(dead, [])

    def test_dead_pattern_is_reported(self) -> None:
        """A mistyped directory matches nothing — the defect that looks like coverage."""
        typo_config = SAMPLE_CONFIG.replace('"/node/*"', '"/nodes/*"')
        entries = parse_dependabot_config(typo_config)
        discovered = {
            "gomod": {"/go/basic-agent", "/scenarios/live-core-enforcement/go-agent"},
            "npm": {"/node/mastra", "/scenarios/audit-trace/node"},
            "pip": set(),
            "github-actions": {"/"},
        }
        uncovered, dead = evaluate(entries, discovered)
        self.assertEqual(dead, [("npm", "/nodes/*")])
        self.assertEqual(uncovered, {"npm": ["/node/mastra"]})


class MainExitCodeTests(unittest.TestCase):
    """The gate's contract is its exit code, so assert over that directly."""

    def _write_repo(self, root: Path, config: str) -> None:
        tree = _Tree(root)
        tree.add(".github/dependabot.yml", config)
        tree.add(".github/workflows/ci.yml", "name: ci\n")
        tree.add("node/mastra/pnpm-lock.yaml")
        tree.add("scenarios/audit-trace/node/pnpm-lock.yaml")
        tree.add("go/basic-agent/go.mod")
        tree.add("scenarios/live-core-enforcement/go-agent/go.mod")

    def test_exit_zero_when_each_manifest_is_covered(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            self._write_repo(root, SAMPLE_CONFIG)
            self.assertEqual(main(["--repo-root", str(root)]), 0)

    def test_exit_one_when_a_manifest_is_uncovered(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            self._write_repo(root, SAMPLE_CONFIG)
            # The exact defect AAASM-5675 describes: a lockfile lands in a
            # directory the config does not reach.
            _Tree(root).add("tools/scratch-client/pnpm-lock.yaml")
            self.assertEqual(main(["--repo-root", str(root)]), 1)

    def test_exit_one_when_config_is_unparseable(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            self._write_repo(root, "version: 2\n")
            self.assertEqual(main(["--repo-root", str(root)]), 1)

    def test_exit_one_when_config_is_absent(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            _Tree(root).add("node/mastra/pnpm-lock.yaml")
            self.assertEqual(main(["--repo-root", str(root)]), 1)


if __name__ == "__main__":
    unittest.main()
