#!/usr/bin/env python3
"""Tests for ``scripts/check_pnpm_build_decision_parity.py``.

Each test pairs a file the checker must accept with the specific edit that
reproduces the AAASM-6243 defect and must turn it red. The two shapes that
actually occurred in this repo are covered explicitly: a directory declaring
``onlyBuiltDependencies`` with no ``allowBuilds`` (``node/mastra``,
``scenarios/approval-gates/node``, ``scenarios/policy-enforcement/node`` — all
three failed pnpm 11 while looking correctly configured), and a directory
declaring neither, which must stay silent.
"""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_pnpm_build_decision_parity import _parse_list_block, check

BOTH_KEYS = textwrap.dedent(
    """\
    onlyBuiltDependencies:
      - '@agent-assembly/sdk'
      - esbuild

    allowBuilds:
      '@agent-assembly/sdk': true
      esbuild: true
    """
)

ONLY_PNPM10_KEY = textwrap.dedent(
    """\
    onlyBuiltDependencies:
      - '@agent-assembly/sdk'
      - esbuild
    """
)


class _Tree:
    """A throwaway repo root holding one pnpm-workspace.yaml per directory."""

    def __init__(self, tmp: str) -> None:
        self.root = Path(tmp)

    def add(self, rel: str, body: str) -> None:
        d = self.root / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "pnpm-workspace.yaml").write_text(body, encoding="utf-8")


class ParseListBlockTests(unittest.TestCase):
    def test_absent_header_is_none_not_empty(self) -> None:
        # The distinction is load-bearing: None means "declares nothing", while
        # [] would mean "declares an empty allow-list", which is a real and
        # different statement.
        self.assertIsNone(_parse_list_block(["allowBuilds:", "  esbuild: true"], "onlyBuiltDependencies"))

    def test_quoted_and_bare_items_both_parse(self) -> None:
        lines = ONLY_PNPM10_KEY.splitlines()
        self.assertEqual(_parse_list_block(lines, "onlyBuiltDependencies"), ["@agent-assembly/sdk", "esbuild"])

    def test_interleaved_comment_does_not_end_the_block(self) -> None:
        lines = textwrap.dedent(
            """\
            onlyBuiltDependencies:
              - esbuild
              # why protobufjs needs its postinstall
              - protobufjs
            """
        ).splitlines()
        self.assertEqual(_parse_list_block(lines, "onlyBuiltDependencies"), ["esbuild", "protobufjs"])

    def test_dedent_ends_the_block(self) -> None:
        lines = textwrap.dedent(
            """\
            onlyBuiltDependencies:
              - esbuild
            overrides:
              - not-a-build-dep
            """
        ).splitlines()
        self.assertEqual(_parse_list_block(lines, "onlyBuiltDependencies"), ["esbuild"])


class CheckTests(unittest.TestCase):
    def test_both_keys_in_agreement_passes(self) -> None:
        with TemporaryDirectory() as tmp:
            t = _Tree(tmp)
            t.add("node/sample", BOTH_KEYS)
            problems, declaring = check(t.root)
            self.assertEqual(problems, [])
            self.assertEqual(declaring, 1)

    def test_only_pnpm10_key_is_the_real_defect_and_fails(self) -> None:
        # The exact shape of node/mastra before AAASM-6243: a complete-looking
        # onlyBuiltDependencies list, and pnpm 11 refusing the directory anyway.
        with TemporaryDirectory() as tmp:
            t = _Tree(tmp)
            t.add("node/mastra", ONLY_PNPM10_KEY)
            problems, declaring = check(t.root)
            self.assertEqual(declaring, 1)
            self.assertEqual(len(problems), 1)
            self.assertIn("no allowBuilds", problems[0])
            self.assertIn("ERR_PNPM_IGNORED_BUILDS", problems[0])

    def test_only_pnpm11_key_fails_because_pnpm10_would_skip_builds(self) -> None:
        with TemporaryDirectory() as tmp:
            t = _Tree(tmp)
            t.add("node/sample", "allowBuilds:\n  esbuild: true\n")
            problems, _ = check(t.root)
            self.assertEqual(len(problems), 1)
            self.assertIn("no onlyBuiltDependencies", problems[0])

    def test_package_missing_from_allowbuilds_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            t = _Tree(tmp)
            t.add("node/sample", BOTH_KEYS.replace("  esbuild: true\n", ""))
            problems, _ = check(t.root)
            self.assertEqual(len(problems), 1)
            self.assertIn("not allowed by allowBuilds", problems[0])
            self.assertIn("esbuild", problems[0])

    def test_explicit_false_counts_as_denial_not_as_agreement(self) -> None:
        # `esbuild: false` is a deliberate *denial*, so it must not satisfy a
        # listing in onlyBuiltDependencies. Treating any present key as allowed
        # would let the two majors disagree about whether a build runs.
        with TemporaryDirectory() as tmp:
            t = _Tree(tmp)
            t.add("node/sample", BOTH_KEYS.replace("esbuild: true", "esbuild: false"))
            problems, _ = check(t.root)
            self.assertEqual(len(problems), 1)
            self.assertIn("not allowed by allowBuilds", problems[0])

    def test_allowbuilds_superset_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            t = _Tree(tmp)
            t.add("node/sample", BOTH_KEYS.replace("  esbuild: true\n", "  esbuild: true\n  protobufjs: true\n"))
            problems, _ = check(t.root)
            self.assertEqual(len(problems), 1)
            self.assertIn("not in onlyBuiltDependencies", problems[0])
            self.assertIn("protobufjs", problems[0])

    def test_directory_declaring_neither_key_is_silent(self) -> None:
        # scenarios/audit-trace/node and two siblings legitimately declare
        # nothing because they pull no build-script dependency at all. They must
        # not be reported, and must not count towards the declaring total.
        with TemporaryDirectory() as tmp:
            t = _Tree(tmp)
            t.add("scenarios/audit-trace/node", "overrides:\n  js-yaml: ^4.3.2\n")
            problems, declaring = check(t.root)
            self.assertEqual(problems, [])
            self.assertEqual(declaring, 0)

    def test_node_modules_is_not_walked(self) -> None:
        with TemporaryDirectory() as tmp:
            t = _Tree(tmp)
            t.add("node/sample/node_modules/dep", ONLY_PNPM10_KEY)
            problems, declaring = check(t.root)
            self.assertEqual(problems, [])
            self.assertEqual(declaring, 0)

    def test_every_divergent_directory_is_reported_not_just_the_first(self) -> None:
        with TemporaryDirectory() as tmp:
            t = _Tree(tmp)
            t.add("node/a", ONLY_PNPM10_KEY)
            t.add("node/b", ONLY_PNPM10_KEY)
            t.add("node/c", BOTH_KEYS)
            problems, declaring = check(t.root)
            self.assertEqual(declaring, 3)
            self.assertEqual(len(problems), 2)


if __name__ == "__main__":
    unittest.main()
