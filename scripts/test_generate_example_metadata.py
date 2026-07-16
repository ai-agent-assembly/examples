"""Unit tests for the SDK-version metadata generator and its --check audit.

These exercise the capabilities added for AAASM-4719/AAASM-4717 in isolation,
against synthetic trees built in a tmp dir — they never depend on the live repo
layout, so they stay valid as examples are added or renamed. Run with:

    python -m unittest scripts.test_generate_example_metadata
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import generate_example_metadata as gen

# A self-contained SoT mirroring metadata/sdk-versions.yaml, so load_sdk_versions
# resolves the same version literals the real generator aligns to.
_SOT_YAML = """\
python:
  package: "agent-assembly"
  version: "0.0.1rc5"
  install_pip: "pip install agent-assembly=={{version}}"
  install_uv: "uv add agent-assembly=={{version}}"

node:
  package: "@agent-assembly/sdk"
  version: "0.0.1-rc.5"
  install_pnpm: "pnpm add @agent-assembly/sdk@{{version}}"
  install_npm: "npm install @agent-assembly/sdk@{{version}}"
  install_yarn: "yarn add @agent-assembly/sdk@{{version}}"

go:
  module: "github.com/ai-agent-assembly/go-sdk"
  version: "v0.0.1-rc.5"
  install: "go get github.com/ai-agent-assembly/go-sdk@{{version}}"
"""


def _write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class _RepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _write(self.root, "metadata/sdk-versions.yaml", _SOT_YAML)
        self.versions = gen.load_sdk_versions(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class BulletRewriteTests(_RepoTestCase):
    def test_rewrites_stale_bullet_to_sot(self) -> None:
        path = _write(
            self.root,
            "go/README.md",
            "## Prerequisites\n\n- Go >= 1.26\n- Agent Assembly Go SDK v0.0.1-rc.3\n",
        )
        changed = gen.rewrite_prereq_bullet(path, "Go", self.versions.go.version)
        self.assertTrue(changed)
        self.assertIn("- Agent Assembly Go SDK v0.0.1-rc.5", path.read_text())

    def test_preserves_trailing_note(self) -> None:
        path = _write(
            self.root,
            "go/README.md",
            "- Agent Assembly Go SDK v0.0.1-rc.3 (server component only)\n",
        )
        gen.rewrite_prereq_bullet(path, "Go", self.versions.go.version)
        self.assertEqual(
            path.read_text(),
            "- Agent Assembly Go SDK v0.0.1-rc.5 (server component only)\n",
        )

    def test_does_not_touch_table_row(self) -> None:
        table = "| Agent Assembly Go SDK | v0.0.1-rc.3 |\n"
        path = _write(self.root, "go/README.md", table)
        changed = gen.rewrite_prereq_bullet(path, "Go", self.versions.go.version)
        self.assertFalse(changed)
        self.assertEqual(path.read_text(), table)

    def test_does_not_touch_generated_block(self) -> None:
        block = (
            f"{gen.SDK_BLOCK_BEGIN}\n"
            "| Agent Assembly Go SDK (`github.com/ai-agent-assembly/go-sdk`) "
            "| v0.0.1-rc.3 |\n"
            f"{gen.SDK_BLOCK_END}\n"
        )
        path = _write(self.root, "go/README.md", block)
        changed = gen.rewrite_prereq_bullet(path, "Go", self.versions.go.version)
        self.assertFalse(changed)
        self.assertEqual(path.read_text(), block)


class DockerfileRewriteTests(_RepoTestCase):
    def test_rewrites_stale_pin(self) -> None:
        path = _write(
            self.root,
            "scenarios/live/python-agent/Dockerfile",
            'RUN pip install --no-cache-dir maturin "agent-assembly==0.0.1rc3"\n',
        )
        changed = gen.rewrite_dockerfile(path, self.versions.python)
        self.assertTrue(changed)
        self.assertIn('"agent-assembly==0.0.1rc5"', path.read_text())

    def test_ignores_node_and_go_identifiers(self) -> None:
        content = (
            '"@agent-assembly/sdk": "0.0.1-rc.5"\n'
            "github.com/ai-agent-assembly/go-sdk v0.0.1-rc.5\n"
        )
        path = _write(self.root, "scenarios/live/x/Dockerfile", content)
        changed = gen.rewrite_dockerfile(path, self.versions.python)
        self.assertFalse(changed)
        self.assertEqual(path.read_text(), content)

    def test_walker_is_bounded_to_two_levels(self) -> None:
        _write(self.root, "scenarios/a/Dockerfile", "x")
        _write(self.root, "scenarios/a/b/Dockerfile", "x")
        _write(self.root, "scenarios/a/b/c/Dockerfile", "x")  # too deep, ignored
        found = {p.relative_to(self.root).as_posix() for p in gen._dockerfiles(self.root)}
        self.assertEqual(found, {"scenarios/a/Dockerfile", "scenarios/a/b/Dockerfile"})


def _in_sync_tree(root: Path) -> None:
    """Populate a tmp repo whose every audited surface matches the SoT."""

    _write(
        root,
        "python/ex/pyproject.toml",
        'dependencies = [\n    "agent-assembly==0.0.1rc5",\n]\n',
    )
    _write(
        root,
        "node/ex/package.json",
        '{\n  "dependencies": {\n    "@agent-assembly/sdk": "0.0.1-rc.5"\n  }\n}\n',
    )
    _write(
        root,
        "go/ex/go.mod",
        "require github.com/ai-agent-assembly/go-sdk v0.0.1-rc.5\n",
    )
    _write(
        root,
        "scenarios/live/python-agent/Dockerfile",
        'RUN pip install "agent-assembly==0.0.1rc5"\n',
    )
    _write(
        root,
        "go/README.md",
        "- Agent Assembly Go SDK v0.0.1-rc.5\n",
    )


class AuditTests(_RepoTestCase):
    def test_passes_on_in_sync_tree(self) -> None:
        _in_sync_tree(self.root)
        self.assertEqual(gen.audit(self.root, self.versions), [])

    def test_detects_stale_manifest_pin(self) -> None:
        _in_sync_tree(self.root)
        _write(
            self.root,
            "go/ex/go.mod",
            "require github.com/ai-agent-assembly/go-sdk v0.0.1-rc.3\n",
        )
        problems = gen.audit(self.root, self.versions)
        self.assertEqual(len(problems), 1)
        self.assertIn("go/ex/go.mod:1", problems[0])
        self.assertIn("v0.0.1-rc.3", problems[0])

    def test_detects_stale_dockerfile_pin(self) -> None:
        _in_sync_tree(self.root)
        _write(
            self.root,
            "scenarios/live/python-agent/Dockerfile",
            'RUN pip install "agent-assembly==0.0.1rc4"\n',
        )
        problems = gen.audit(self.root, self.versions)
        self.assertTrue(
            any("scenarios/live/python-agent/Dockerfile:1" in p for p in problems)
        )

    def test_detects_stale_prose(self) -> None:
        _in_sync_tree(self.root)
        _write(self.root, "go/README.md", "- Agent Assembly Go SDK v0.0.1-rc.3\n")
        problems = gen.audit(self.root, self.versions)
        self.assertEqual(len(problems), 1)
        self.assertIn("go/README.md:1", problems[0])

    def test_exemption_marker_is_honored(self) -> None:
        _in_sync_tree(self.root)
        _write(
            self.root,
            "go/ex/go.mod",
            "require github.com/ai-agent-assembly/go-sdk v0.0.1-rc.3 "
            "// sdk-version-exempt\n",
        )
        self.assertEqual(gen.audit(self.root, self.versions), [])

    def test_ignores_runtime_subpackage_and_org_path(self) -> None:
        # A node runtime subpackage and the go org path are not the main SDK id;
        # a stale-looking version on those lines must not trip the audit.
        _in_sync_tree(self.root)
        _write(
            self.root,
            "node/ex/package.json",
            '{\n  "dependencies": {\n'
            '    "@agent-assembly/sdk": "0.0.1-rc.5",\n'
            '    "@agent-assembly/runtime-linux-x64": "0.0.1-rc.3"\n'
            "  }\n}\n",
        )
        self.assertEqual(gen.audit(self.root, self.versions), [])


if __name__ == "__main__":
    unittest.main()
