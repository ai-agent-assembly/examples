#!/usr/bin/env python3
"""Tests for ``scripts/check_pnpm_overrides_parity.py``.

These exist to keep the gate falsifiable — the AAASM-6032 defect this checker
guards against is exactly "the lockfile silently stopped matching the config",
so a checker that can't tell the two apart would report the same false green
the original bug produced. Each test pairs a passing pair of files with the
specific edit that reproduces the real defect and should turn it red.
"""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_pnpm_overrides_parity import _parse_flat_mapping, _parse_overrides

WORKSPACE_YAML = textwrap.dedent(
    """\
    overrides:
      js-yaml: ^4.3.1
      '@modelcontextprotocol/sdk': ^1.30.0

    onlyBuiltDependencies:
      - esbuild
    """
)

MATCHING_LOCKFILE = textwrap.dedent(
    """\
    lockfileVersion: '9.0'

    settings:
      autoInstallPeers: true

    overrides:
      js-yaml: ^4.3.1
      '@modelcontextprotocol/sdk': ^1.30.0

    importers:
      .:
        dependencies: {}
    """
)


class TestParseFlatMapping(unittest.TestCase):
    def test_parses_bare_and_quoted_keys(self) -> None:
        mapping = _parse_flat_mapping(WORKSPACE_YAML.splitlines(), "overrides")
        self.assertEqual(mapping, {"js-yaml": "^4.3.1", "@modelcontextprotocol/sdk": "^1.30.0"})

    def test_returns_none_when_header_absent(self) -> None:
        self.assertIsNone(_parse_flat_mapping(["onlyBuiltDependencies:", "  - esbuild"], "overrides"))

    def test_stops_at_dedent(self) -> None:
        # onlyBuiltDependencies must not be swallowed into the overrides mapping.
        mapping = _parse_flat_mapping(WORKSPACE_YAML.splitlines(), "overrides")
        self.assertNotIn("esbuild", mapping)


class TestParity(unittest.TestCase):
    def _write(self, dir_path: Path, workspace_text: str, lock_text: str | None) -> None:
        (dir_path / "pnpm-workspace.yaml").write_text(workspace_text, encoding="utf-8")
        if lock_text is not None:
            (dir_path / "pnpm-lock.yaml").write_text(lock_text, encoding="utf-8")

    def test_matching_files_have_no_mismatch(self) -> None:
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._write(d, WORKSPACE_YAML, MATCHING_LOCKFILE)
            config = _parse_overrides(d / "pnpm-workspace.yaml", "overrides")
            lock = _parse_overrides(d / "pnpm-lock.yaml", "overrides")
            self.assertEqual(config, lock)

    def test_reproduces_aaasm_6032_dropped_block(self) -> None:
        # The real defect: the relock's lockfile has no overrides block at all
        # while pnpm-workspace.yaml still declares one.
        dropped_lockfile = textwrap.dedent(
            """\
            lockfileVersion: '9.0'

            settings:
              autoInstallPeers: true

            importers:
              .:
                dependencies: {}
            """
        )
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._write(d, WORKSPACE_YAML, dropped_lockfile)
            config = _parse_overrides(d / "pnpm-workspace.yaml", "overrides")
            lock = _parse_overrides(d / "pnpm-lock.yaml", "overrides") or {}
            self.assertNotEqual(config, lock)
            self.assertEqual(lock, {})

    def test_detects_value_drift_not_just_key_absence(self) -> None:
        # A subtler variant: the key survives but resolves to a different
        # version than the config declares (e.g. a partial/asymmetric relock).
        drifted_lockfile = MATCHING_LOCKFILE.replace("^4.3.1", "^3.15.2")
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._write(d, WORKSPACE_YAML, drifted_lockfile)
            config = _parse_overrides(d / "pnpm-workspace.yaml", "overrides")
            lock = _parse_overrides(d / "pnpm-lock.yaml", "overrides")
            self.assertNotEqual(config["js-yaml"], lock["js-yaml"])


if __name__ == "__main__":
    unittest.main()
