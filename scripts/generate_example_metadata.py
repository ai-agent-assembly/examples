#!/usr/bin/env python3
"""Regenerate example SDK-version pins and bounded README blocks from the SoT.

The single source of truth is ``metadata/sdk-versions.yaml`` at the repo root.
Running this script rewrites the SDK pin in every in-scope example manifest
(``python/*/pyproject.toml``, ``scenarios/*/python/pyproject.toml``) and
regenerates the bounded ``<!-- BEGIN GENERATED: sdk-install --> ... <!-- END
GENERATED: sdk-install -->`` block in each README that currently advertises
an SDK version literal.

Design constraints:

* Standard library only. YAML is parsed with a tiny hand-rolled loader that
  understands the flat structure of ``metadata/sdk-versions.yaml``; no PyYAML
  dependency is required, keeping the CI drift check dependency-free.
* Line-level regex substitutions on manifests — never a full-file rewrite —
  so unrelated dependencies and formatting are preserved verbatim.
* Idempotent: running twice produces no diff. This is a hard requirement and
  is enforced by the CI drift check.
* Content-neutral for pins: the SoT captures the currently-pinned versions.
  This script never bumps versions; it aligns drift.

Historical release notes and example-provenance content (e.g. "written
against 0.0.1-rc.3") are out of scope and must not be touched.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# SoT loader (minimal YAML subset — stdlib only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PythonSdk:
    package: str
    version: str
    install_pip: str
    install_uv: str


@dataclass(frozen=True)
class NodeSdk:
    package: str
    version: str
    install_pnpm: str
    install_npm: str
    install_yarn: str


@dataclass(frozen=True)
class GoSdk:
    module: str
    version: str
    install: str


@dataclass(frozen=True)
class SdkVersions:
    python: PythonSdk
    node: NodeSdk
    go: GoSdk


def _parse_top_level(
    line: str, raw_line: str, out: dict[str, dict[str, str]]
) -> str:
    """Register a top-level key and return it as the new current section."""

    key, sep, _ = line.partition(":")
    if not sep:
        raise ValueError(f"Malformed top-level line: {raw_line!r}")
    current = key.strip()
    out[current] = {}
    return current


def _parse_child(
    line: str, raw_line: str, current: str | None, out: dict[str, dict[str, str]]
) -> None:
    """Store an indented ``key: "value"`` pair under the current section."""

    if current is None:
        raise ValueError(f"Indented line before any top-level key: {raw_line!r}")
    key, sep, value = line.strip().partition(":")
    if not sep:
        raise ValueError(f"Malformed indented line: {raw_line!r}")
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    out[current][key.strip()] = value


def _parse_flat_yaml(text: str) -> dict[str, dict[str, str]]:
    """Parse the narrow YAML dialect used by ``metadata/sdk-versions.yaml``.

    Supports top-level keys with two-space-indented ``key: "value"`` children.
    Ignores blank lines and ``#`` comments. Strings may be quoted with ``"``.
    """

    out: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            current = _parse_top_level(line, raw_line, out)
        else:
            _parse_child(line, raw_line, current, out)
    return out


def _render_install(template: str, version: str) -> str:
    return template.replace("{{version}}", version)


def load_sdk_versions(repo_root: Path) -> SdkVersions:
    path = repo_root / "metadata" / "sdk-versions.yaml"
    data = _parse_flat_yaml(path.read_text(encoding="utf-8"))
    py = data["python"]
    nd = data["node"]
    go = data["go"]
    return SdkVersions(
        python=PythonSdk(
            package=py["package"],
            version=py["version"],
            install_pip=_render_install(py["install_pip"], py["version"]),
            install_uv=_render_install(py["install_uv"], py["version"]),
        ),
        node=NodeSdk(
            package=nd["package"],
            version=nd["version"],
            install_pnpm=_render_install(nd["install_pnpm"], nd["version"]),
            install_npm=_render_install(nd["install_npm"], nd["version"]),
            install_yarn=_render_install(nd["install_yarn"], nd["version"]),
        ),
        go=GoSdk(
            module=go["module"],
            version=go["version"],
            install=_render_install(go["install"], go["version"]),
        ),
    )


# ---------------------------------------------------------------------------
# File rewrite helpers
# ---------------------------------------------------------------------------


def _write_if_changed(path: Path, new_text: str) -> bool:
    """Write ``new_text`` to ``path`` iff it differs from the current contents.

    Returns True if the file was rewritten. Keeps the trailing-newline shape of
    the original file.
    """

    current = path.read_text(encoding="utf-8")
    if current == new_text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Python manifest rewrites
# ---------------------------------------------------------------------------


_PY_PIN_RE = re.compile(
    r'''^(?P<indent>\s*)"agent-assembly(?P<op>==|>=|~=|<=|<|>)[^"]*"(?P<tail>,?\s*)$''',
    re.MULTILINE,
)


def rewrite_python_manifest(path: Path, sdk: PythonSdk) -> bool:
    text = path.read_text(encoding="utf-8")

    def _sub(match: re.Match[str]) -> str:
        indent = match.group("indent")
        op = match.group("op")
        tail = match.group("tail")
        return f'{indent}"{sdk.package}{op}{sdk.version}"{tail}'

    new_text = _PY_PIN_RE.sub(_sub, text)
    return _write_if_changed(path, new_text)


# ---------------------------------------------------------------------------
# Node manifest rewrites
# ---------------------------------------------------------------------------


# Match a "@agent-assembly/sdk": "<version>" line in package.json. Preserves
# leading indent and the optional trailing comma so we never disturb the
# surrounding key order or JSON validity.
_NODE_PIN_RE = re.compile(
    r'''^(?P<indent>\s*)"@agent-assembly/sdk"\s*:\s*"[^"]*"(?P<tail>,?\s*)$''',
    re.MULTILINE,
)


def rewrite_node_manifest(path: Path, sdk: NodeSdk) -> bool:
    text = path.read_text(encoding="utf-8")

    def _sub(match: re.Match[str]) -> str:
        indent = match.group("indent")
        tail = match.group("tail")
        return f'{indent}"{sdk.package}": "{sdk.version}"{tail}'

    new_text = _NODE_PIN_RE.sub(_sub, text)
    return _write_if_changed(path, new_text)


# ---------------------------------------------------------------------------
# Go manifest rewrites
# ---------------------------------------------------------------------------


# Match a go.mod line of the form:
#   require github.com/ai-agent-assembly/go-sdk v0.0.1-rc.3
# or, inside a require ( ... ) block:
#   \tgithub.com/ai-agent-assembly/go-sdk v0.0.1-rc.3
# The regex captures the prefix (indent + optional "require ") so we preserve
# whichever form the surrounding file uses. The tail requires whitespace before a
# ``// comment`` so the version token ``\S+`` has an unambiguous, non-whitespace
# boundary — otherwise the engine could backtrack ``\S+`` into the ``//``,
# non-linear behavior static analysis flags as a ReDoS risk.
_GO_PIN_RE = re.compile(
    r'''^(?P<prefix>\s*(?:require\s+)?)github\.com/ai-agent-assembly/go-sdk\s+\S+(?P<tail>(?:\s+//.*)?\s*)$''',
    re.MULTILINE,
)


def rewrite_go_manifest(path: Path, sdk: GoSdk) -> bool:
    text = path.read_text(encoding="utf-8")

    def _sub(match: re.Match[str]) -> str:
        prefix = match.group("prefix")
        tail = match.group("tail")
        return f"{prefix}{sdk.module} {sdk.version}{tail}"

    new_text = _GO_PIN_RE.sub(_sub, text)
    return _write_if_changed(path, new_text)


# ---------------------------------------------------------------------------
# README bounded-block rewrites
# ---------------------------------------------------------------------------


SDK_BLOCK_BEGIN = "<!-- BEGIN GENERATED: sdk-install -->"
SDK_BLOCK_END = "<!-- END GENERATED: sdk-install -->"

_BLOCK_RE = re.compile(
    re.escape(SDK_BLOCK_BEGIN) + r".*?" + re.escape(SDK_BLOCK_END),
    re.DOTALL,
)


def _python_sdk_block(sdk: PythonSdk) -> str:
    return (
        f"{SDK_BLOCK_BEGIN}\n"
        f"<!-- This block is generated by scripts/generate_example_metadata.py. -->\n"
        f"<!-- Edit metadata/sdk-versions.yaml and re-run the generator. -->\n"
        f"| Requirement | Version |\n"
        f"|---|---|\n"
        f"| Agent Assembly Python SDK ({sdk.package}) | >= {sdk.version} |\n"
        f"\n"
        f"Install:\n"
        f"\n"
        f"```bash\n"
        f"{sdk.install_uv}\n"
        f"# or\n"
        f"{sdk.install_pip}\n"
        f"```\n"
        f"{SDK_BLOCK_END}"
    )


def _node_sdk_block(sdk: NodeSdk) -> str:
    return (
        f"{SDK_BLOCK_BEGIN}\n"
        f"<!-- This block is generated by scripts/generate_example_metadata.py. -->\n"
        f"<!-- Edit metadata/sdk-versions.yaml and re-run the generator. -->\n"
        f"| Requirement | Version |\n"
        f"|---|---|\n"
        f"| Agent Assembly Node.js SDK (`{sdk.package}`) | {sdk.version} |\n"
        f"\n"
        f"Install:\n"
        f"\n"
        f"```bash\n"
        f"{sdk.install_pnpm}\n"
        f"# or\n"
        f"{sdk.install_npm}\n"
        f"# or\n"
        f"{sdk.install_yarn}\n"
        f"```\n"
        f"{SDK_BLOCK_END}"
    )


def _go_sdk_block(sdk: GoSdk) -> str:
    return (
        f"{SDK_BLOCK_BEGIN}\n"
        f"<!-- This block is generated by scripts/generate_example_metadata.py. -->\n"
        f"<!-- Edit metadata/sdk-versions.yaml and re-run the generator. -->\n"
        f"| Requirement | Version |\n"
        f"|---|---|\n"
        f"| Agent Assembly Go SDK (`{sdk.module}`) | {sdk.version} |\n"
        f"\n"
        f"Install:\n"
        f"\n"
        f"```bash\n"
        f"{sdk.install}\n"
        f"```\n"
        f"{SDK_BLOCK_END}"
    )


def _apply_or_insert_block(text: str, block: str) -> str:
    """Replace an existing sdk-install block, or insert one just after the H1.

    Insertion is bounded and idempotent: subsequent runs replace the same
    block in-place.
    """

    if _BLOCK_RE.search(text):
        return _BLOCK_RE.sub(lambda _m: block, text)

    lines = text.splitlines(keepends=True)
    insert_at = 0
    for idx, line in enumerate(lines):
        if line.startswith("# "):  # H1
            insert_at = idx + 1
            break
    # Skip a single blank line after the H1 if present, so the block sits
    # cleanly under the title with one blank line above and below it.
    insertion = f"\n{block}\n"
    return "".join(lines[:insert_at]) + insertion + "".join(lines[insert_at:])


def rewrite_python_readme(path: Path, sdk: PythonSdk) -> bool:
    text = path.read_text(encoding="utf-8")
    new_text = _apply_or_insert_block(text, _python_sdk_block(sdk))
    return _write_if_changed(path, new_text)


def rewrite_node_readme(path: Path, sdk: NodeSdk) -> bool:
    text = path.read_text(encoding="utf-8")
    new_text = _apply_or_insert_block(text, _node_sdk_block(sdk))
    return _write_if_changed(path, new_text)


def rewrite_go_readme(path: Path, sdk: GoSdk) -> bool:
    text = path.read_text(encoding="utf-8")
    new_text = _apply_or_insert_block(text, _go_sdk_block(sdk))
    return _write_if_changed(path, new_text)


# ---------------------------------------------------------------------------
# Hand-written "Prerequisites" table row
# ---------------------------------------------------------------------------
#
# Many READMEs carry, in their prose ``## Prerequisites`` table, a row of the
# form ``| Agent Assembly <Lang> SDK | <version> |`` that sits *outside* the
# generated sdk-install block. Left to hand-maintenance it drifts from the SoT
# (AAASM-4703): the generated block advertised rc.5 while these rows still said
# rc.3 / an old beta. The generator now owns the version literal in that row too
# so the two can never disagree again.
#
# The label cell is matched *exactly* (``Agent Assembly <Lang> SDK`` with no
# trailing parenthetical), which is precisely what distinguishes this prose row
# from the generated block's row (``... SDK (<package>) | ...``) — so this pass
# never touches the generated block.


# A PEP 440 / SemVer-ish pre-release version literal, covering the shapes used
# across these examples: ``0.0.1rc5`` (python), ``v0.0.1-rc.5`` (go), and any
# alpha/beta/rc pre-release suffix. Only the version token is rewritten, so an
# operator prefix (``>= ``) and any trailing note (``(with the LlamaIndex
# adapter)``) are preserved verbatim.
_VERSION_TOKEN_RE = re.compile(
    r"v?\d+\.\d+\.\d+(?:[-.]?(?:rc|beta|alpha|b|a)\.?\d+)?"
)


def _prereq_row_re(label: str) -> re.Pattern[str]:
    return re.compile(
        r"^(?P<pre>\|[ \t]*Agent Assembly "
        + re.escape(label)
        + r" SDK[ \t]*\|[ \t]*)(?P<val>[^|]*?)(?P<post>[ \t]*\|[ \t]*)$",
        re.MULTILINE,
    )


def rewrite_prereq_row(path: Path, label: str, version: str) -> bool:
    """Align the ``Agent Assembly <label> SDK`` Prerequisites row with the SoT.

    Rewrites only the version token inside the row's value cell; the comparison
    operator and any trailing note are left untouched. A no-op for READMEs that
    do not carry the row.
    """

    text = path.read_text(encoding="utf-8")
    row_re = _prereq_row_re(label)

    def _sub(match: re.Match[str]) -> str:
        new_val = _VERSION_TOKEN_RE.sub(version, match.group("val"), count=1)
        return f"{match.group('pre')}{new_val}{match.group('post')}"

    new_text = row_re.sub(_sub, text)
    return _write_if_changed(path, new_text)


# ---------------------------------------------------------------------------
# Directory walkers
# ---------------------------------------------------------------------------


_PYPROJECT_TOML = "pyproject.toml"
_README = "README.md"


def _python_subprojects(repo_root: Path) -> list[Path]:
    """Return every directory that holds a python `pyproject.toml` in scope."""

    out: list[Path] = []
    py_dir = repo_root / "python"
    if py_dir.is_dir():
        for sub in sorted(py_dir.iterdir()):
            if (sub / _PYPROJECT_TOML).is_file():
                out.append(sub)
    scenarios_dir = repo_root / "scenarios"
    if scenarios_dir.is_dir():
        for scen in sorted(scenarios_dir.iterdir()):
            inner = scen / "python"
            if (inner / _PYPROJECT_TOML).is_file():
                out.append(inner)
    return out


def _node_subprojects(repo_root: Path) -> list[Path]:
    """Return every directory that holds a node `package.json` that pins the SDK.

    Covers both the top-level ``node/*`` examples and the scenario
    real-transport drivers at ``scenarios/*/node-agent`` — the latter pin the
    SDK too but sit outside ``node/``, so they were previously invisible to the
    generator and drifted (AAASM-4702). Scenario node packages that do not
    depend on ``@agent-assembly/sdk`` are still excluded: they have no manifest
    line to rewrite and no SDK version literal to advertise in their README.
    """

    candidates: list[Path] = []
    node_dir = repo_root / "node"
    if node_dir.is_dir():
        candidates.extend(sorted(node_dir.iterdir()))
    candidates.extend(sorted(repo_root.glob("scenarios/*/node-agent")))

    out: list[Path] = []
    for sub in candidates:
        manifest = sub / "package.json"
        if manifest.is_file() and "@agent-assembly/sdk" in manifest.read_text(
            encoding="utf-8"
        ):
            out.append(sub)
    return out


def _go_subprojects(repo_root: Path) -> list[Path]:
    """Return every directory that holds a Go module pinning the go-sdk.

    Covers both the top-level ``go/*`` examples and the scenario
    real-transport drivers at ``scenarios/*/go-agent`` — the latter pin the
    go-sdk too but sit outside ``go/``, so they were previously invisible to
    the generator and drifted (AAASM-4702).
    """

    candidates: list[Path] = []
    go_dir = repo_root / "go"
    if go_dir.is_dir():
        candidates.extend(sorted(go_dir.iterdir()))
    candidates.extend(sorted(repo_root.glob("scenarios/*/go-agent")))

    out: list[Path] = []
    for sub in candidates:
        manifest = sub / "go.mod"
        if manifest.is_file() and "github.com/ai-agent-assembly/go-sdk" in (
            manifest.read_text(encoding="utf-8")
        ):
            out.append(sub)
    return out


def process_python(repo_root: Path, versions: SdkVersions) -> list[Path]:
    """Rewrite all in-scope python manifests and READMEs.

    Returns the list of files that were rewritten.
    """

    changed: list[Path] = []
    for subproject in _python_subprojects(repo_root):
        manifest = subproject / _PYPROJECT_TOML
        if rewrite_python_manifest(manifest, versions.python):
            changed.append(manifest)
        readme = subproject / _README
        if readme.is_file() and rewrite_python_readme(readme, versions.python):
            changed.append(readme)
    return changed


def process_node(repo_root: Path, versions: SdkVersions) -> list[Path]:
    """Rewrite all in-scope node manifests and READMEs.

    Returns the list of files that were rewritten.
    """

    changed: list[Path] = []
    for subproject in _node_subprojects(repo_root):
        manifest = subproject / "package.json"
        if rewrite_node_manifest(manifest, versions.node):
            changed.append(manifest)
        readme = subproject / _README
        if readme.is_file() and rewrite_node_readme(readme, versions.node):
            changed.append(readme)
    return changed


def process_go(repo_root: Path, versions: SdkVersions) -> list[Path]:
    """Rewrite all in-scope go manifests and READMEs.

    Returns the list of files that were rewritten. Also rewrites the
    aggregate ``go/README.md`` if it exists, so the top-level Go landing
    page advertises the same SDK version as the per-example READMEs.
    """

    changed: list[Path] = []
    for subproject in _go_subprojects(repo_root):
        manifest = subproject / "go.mod"
        if rewrite_go_manifest(manifest, versions.go):
            changed.append(manifest)
        readme = subproject / _README
        if readme.is_file() and rewrite_go_readme(readme, versions.go):
            changed.append(readme)
    top_level_readme = repo_root / "go" / _README
    if top_level_readme.is_file() and rewrite_go_readme(
        top_level_readme, versions.go
    ):
        changed.append(top_level_readme)
    return changed


# Bounded set of README locations that may carry a prose ``## Prerequisites``
# table: the per-example READMEs, the language landing pages, and the scenario
# READMEs (both scenario-level and per-agent). Kept as explicit globs rather
# than a recursive ``**/README.md`` walk so a local ``node_modules`` / build
# tree can never leak into the generator's scope.
_README_GLOBS = (
    "README.md",
    "python/README.md",
    "node/README.md",
    "go/README.md",
    "python/*/README.md",
    "node/*/README.md",
    "go/*/README.md",
    "scenarios/*/README.md",
    "scenarios/*/*/README.md",
)


def _prereq_readmes(repo_root: Path) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for pattern in _README_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                out.append(path)
    return out


def process_prereq_rows(repo_root: Path, versions: SdkVersions) -> list[Path]:
    """Align every hand-written ``Agent Assembly <Lang> SDK`` prereq row.

    Label-driven (not directory-driven): a README's row is rewritten for
    whichever language label it carries, so the version can never disagree with
    the generated sdk-install block. Returns the list of files rewritten.
    """

    labels = (
        ("Python", versions.python.version),
        ("Node.js", versions.node.version),
        ("Go", versions.go.version),
    )
    changed: list[Path] = []
    for readme in _prereq_readmes(repo_root):
        touched = False
        for label, version in labels:
            if rewrite_prereq_row(readme, label, version):
                touched = True
        if touched:
            changed.append(readme)
    return changed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _repo_root_from_script() -> Path:
    # This file lives at <repo>/scripts/generate_example_metadata.py.
    return Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_repo_root_from_script(),
        help="Path to the repository root (defaults to the script's parent).",
    )
    args = parser.parse_args(argv)

    versions = load_sdk_versions(args.repo_root)
    changed: list[Path] = []
    changed.extend(process_python(args.repo_root, versions))
    changed.extend(process_node(args.repo_root, versions))
    changed.extend(process_go(args.repo_root, versions))
    changed.extend(process_prereq_rows(args.repo_root, versions))

    if changed:
        print(f"Rewrote {len(changed)} file(s):")
        for path in changed:
            print(f"  {path.relative_to(args.repo_root)}")
    else:
        print("No changes — every example is already in sync with the SoT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
