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

Audit mode (``--check``): instead of rewriting, scan the same bounded set of
human-authored surfaces (manifest pins under ``python/ node/ go/ scenarios/``
and SDK-version prose in READMEs / ``docs/*.md`` — never lockfiles or vendored
trees) and exit non-zero, naming each ``file:line``, if any SDK-version literal
has drifted from the SoT. This is the anti-recurrence invariant: a newly added
stale surface fails CI. Legitimate historical/provenance text is exempted per
line by the inline marker ``sdk-version-exempt``; such a line is never rewritten
and never audited.
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
        # Normalize the operator to exact ``==``. The core SDK pin must never be a
        # floor/open range (AAASM-4704 and the repo's "never a bare >=" rule),
        # so a bump self-heals a drifted operator; the --check audit enforces the
        # same invariant. The regex still captures ``op`` so a non-``==`` pin is
        # matched and rewritten.
        indent = match.group("indent")
        tail = match.group("tail")
        return f'{indent}"{sdk.package}=={sdk.version}"{tail}'

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
# Dockerfile pin rewrites
# ---------------------------------------------------------------------------
#
# A handful of scenario Dockerfiles ``pip install`` the published Python SDK by
# an exact ``agent-assembly==<version>`` pin (the live-core-enforcement
# python-agent image). Left to hand-maintenance these drift on every SDK bump —
# AAASM-4702 had to hand-correct one. The generator now owns that pin too so
# future bumps (and the --check audit) cover it. The negative lookbehind anchors
# the match to the standalone ``agent-assembly`` project name so it can never
# fire on ``@agent-assembly/sdk`` or ``github.com/ai-agent-assembly/...``.
_DOCKERFILE_PIN_RE = re.compile(
    r'(?<![\w/@.-])(?P<pre>agent-assembly==)(?P<ver>[^"\s]+)'
)


def rewrite_dockerfile(path: Path, sdk: PythonSdk) -> bool:
    text = path.read_text(encoding="utf-8")

    def _sub(match: re.Match[str]) -> str:
        return f"{match.group('pre')}{sdk.version}"

    new_text = _DOCKERFILE_PIN_RE.sub(_sub, text)
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


# Some landing-page READMEs state the same requirement as a Markdown *bullet*
# instead of a table row — ``go/README.md`` carries ``- Agent Assembly Go SDK
# <version>`` under ``## Prerequisites`` (AAASM-4717). The bullet is anchored to
# a list marker (``-``/``*``), so it can never collide with the table row (which
# starts with ``|``) nor with the generated sdk-install block. Only the first
# version token in the value is rewritten, so a trailing note is preserved
# verbatim, exactly like the table-row pass.
def _prereq_bullet_re(label: str) -> re.Pattern[str]:
    return re.compile(
        r"^(?P<pre>[ \t]*[-*][ \t]+Agent Assembly "
        + re.escape(label)
        + r" SDK[ \t]+)(?P<val>.*)$",
        re.MULTILINE,
    )


def rewrite_prereq_bullet(path: Path, label: str, version: str) -> bool:
    """Align a bullet-form ``- Agent Assembly <label> SDK <version>`` line.

    The list-item sibling of ``rewrite_prereq_row``. A no-op for READMEs that
    state the requirement as a table row or omit it entirely; when the bullet is
    present only its first version token is aligned with the SoT.
    """

    text = path.read_text(encoding="utf-8")
    bullet_re = _prereq_bullet_re(label)

    def _sub(match: re.Match[str]) -> str:
        new_val = _VERSION_TOKEN_RE.sub(version, match.group("val"), count=1)
        return f"{match.group('pre')}{new_val}"

    new_text = bullet_re.sub(_sub, text)
    return _write_if_changed(path, new_text)


# Some scenario READMEs label the same requirement row not with the prose
# ``Agent Assembly <Lang> SDK`` name but with the bare backtick *package* name —
# ``| `agent-assembly` SDK | ≥ 0.0.1rc5 |`` (python), ``| `@agent-assembly/sdk`
# | ... |`` (node), ``| `github.com/ai-agent-assembly/go-sdk` | ... |`` (go).
# Left to hand-maintenance these drift from the SoT (AAASM-4722: they still said
# rc.3 while the scenario's own manifest was rc.5). The generator now owns that
# version literal too. The first cell is anchored to *start* with the backticked
# package name (``| `pkg```), which is exactly what separates this hand-written
# row from the generated block's row (``| Agent Assembly <Lang> SDK (`pkg`) |
# ...``, whose first cell starts with prose) and from the plain ``Agent Assembly
# <Lang> SDK`` prereq rows — so this pass can never touch either of those.
def _prereq_backtick_row_re(package: str) -> re.Pattern[str]:
    return re.compile(
        r"^(?P<pre>\|[ \t]*`"
        + re.escape(package)
        + r"`[^|]*\|[ \t]*)(?P<val>[^|]*?)(?P<post>[ \t]*\|[ \t]*)$",
        re.MULTILINE,
    )


def rewrite_prereq_backtick_row(path: Path, package: str, version: str) -> bool:
    """Align a backtick-``package``-labelled Prerequisites row with the SoT.

    Rewrites only the first version token in the row's value cell; the comparison
    operator (``≥``/``>=``) and any trailing note are left untouched, exactly like
    ``rewrite_prereq_row``. A no-op for READMEs that do not carry the row.
    """

    text = path.read_text(encoding="utf-8")
    row_re = _prereq_backtick_row_re(package)

    def _sub(match: re.Match[str]) -> str:
        new_val = _VERSION_TOKEN_RE.sub(version, match.group("val"), count=1)
        return f"{match.group('pre')}{new_val}{match.group('post')}"

    new_text = row_re.sub(_sub, text)
    return _write_if_changed(path, new_text)


# ---------------------------------------------------------------------------
# README install-hint prose
# ---------------------------------------------------------------------------
#
# A README may show a raw SDK install/pin *hint* in its running prose (outside
# the generated sdk-install block) — ``pip install "agent-assembly==<ver>"``
# (python) or ``... @agent-assembly/sdk@<ver>`` (node). These drift on every bump
# (AAASM-4722: a live-core-enforcement "run outside Docker" hint still pinned
# rc.3 while the scenario's Dockerfile was rc.5). The generator now owns them.
#
# Scoping is deliberately narrow:
#   * The python id reuses ``_DOCKERFILE_PIN_RE``: the negative lookbehind anchors
#     to the standalone project name, so it never fires on ``@agent-assembly/sdk``
#     or ``github.com/ai-agent-assembly/...``. A README install hint legitimately
#     shows ``==<version>`` (unlike a floor pin), so the ``==`` is preserved and
#     only the version token is aligned.
#   * The node id requires the exact ``@agent-assembly/sdk@`` install form, so a
#     ``@agent-assembly/runtime-*`` subpackage or a bare ``@agent-assembly/sdk``
#     mention (no trailing ``@<ver>``) can never false-match.
#   * The substitution is applied only to the regions *outside* the generated
#     sdk-install block, so the block (which legitimately carries ``uv add
#     agent-assembly==<ver>`` etc.) is never disturbed by this pass.
_README_NODE_INSTALL_RE = re.compile(
    r"(?P<pre>@agent-assembly/sdk@)(?P<ver>[^\"'\s,)]+)"
)


def _sub_outside_block(
    text: str, pattern: re.Pattern[str], repl
) -> str:
    """Apply ``pattern.sub(repl, ...)`` only to text outside the generated block.

    The generated sdk-install block is copied through verbatim; every span
    between (and around) blocks has the substitution applied. Keeps the prose
    install-hint pass from fighting the generator-owned block.
    """

    out: list[str] = []
    last = 0
    for block in _BLOCK_RE.finditer(text):
        out.append(pattern.sub(repl, text[last : block.start()]))
        out.append(block.group(0))
        last = block.end()
    out.append(pattern.sub(repl, text[last:]))
    return "".join(out)


def rewrite_readme_install_hints(path: Path, versions: SdkVersions) -> bool:
    """Align raw ``agent-assembly==`` / ``@agent-assembly/sdk@`` README hints.

    Rewrites only the version token of an install hint that sits in README prose
    outside the generated sdk-install block. A no-op for READMEs that carry no
    such hint.
    """

    text = path.read_text(encoding="utf-8")

    def _py(match: re.Match[str]) -> str:
        return f"{match.group('pre')}{versions.python.version}"

    def _node(match: re.Match[str]) -> str:
        return f"{match.group('pre')}{versions.node.version}"

    new_text = _sub_outside_block(text, _DOCKERFILE_PIN_RE, _py)
    new_text = _sub_outside_block(new_text, _README_NODE_INSTALL_RE, _node)
    return _write_if_changed(path, new_text)


# ---------------------------------------------------------------------------
# Directory walkers
# ---------------------------------------------------------------------------


_PYPROJECT_TOML = "pyproject.toml"
_README = "README.md"


def _globbed(repo_root: Path, patterns: tuple[str, ...]) -> list[Path]:
    """Return the de-duplicated files matched by a set of bounded globs.

    The patterns are explicit (no ``**`` recursion) so vendored trees
    (``node_modules``, ``.venv``, ``dist``, build contexts) can never leak into
    the generator's or the audit's scope.
    """

    seen: set[Path] = set()
    out: list[Path] = []
    for pattern in patterns:
        for path in sorted(repo_root.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                out.append(path)
    return out


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


# Bounded, non-recursive walk over the scenario Dockerfiles: a scenario may keep
# its Dockerfile at ``scenarios/<scenario>/Dockerfile`` or one level deeper at
# ``scenarios/<scenario>/<component>/Dockerfile`` (e.g. the python-agent image).
_DOCKERFILE_GLOBS = ("scenarios/*/Dockerfile", "scenarios/*/*/Dockerfile")


def _dockerfiles(repo_root: Path) -> list[Path]:
    """Return every in-scope scenario Dockerfile."""

    return _globbed(repo_root, _DOCKERFILE_GLOBS)


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


def process_dockerfiles(repo_root: Path, versions: SdkVersions) -> list[Path]:
    """Align the ``agent-assembly==`` pin in every in-scope Dockerfile.

    Returns the list of files that were rewritten.
    """

    changed: list[Path] = []
    for dockerfile in _dockerfiles(repo_root):
        if rewrite_dockerfile(dockerfile, versions.python):
            changed.append(dockerfile)
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
    # The backtick-package-name variant is keyed on the package/module id, not
    # the prose language label, since that is what its label cell carries.
    backtick_packages = (
        (versions.python.package, versions.python.version),
        (versions.node.package, versions.node.version),
        (versions.go.module, versions.go.version),
    )
    changed: list[Path] = []
    for readme in _prereq_readmes(repo_root):
        touched = False
        for label, version in labels:
            if rewrite_prereq_row(readme, label, version):
                touched = True
            if rewrite_prereq_bullet(readme, label, version):
                touched = True
        for package, version in backtick_packages:
            if rewrite_prereq_backtick_row(readme, package, version):
                touched = True
        if touched:
            changed.append(readme)
    return changed


def process_readme_install_hints(
    repo_root: Path, versions: SdkVersions
) -> list[Path]:
    """Align every raw SDK install hint in README prose with the SoT.

    Walks the same bounded README set as the Prerequisites rows and rewrites the
    version token of any ``agent-assembly==`` / ``@agent-assembly/sdk@`` install
    hint that sits outside the generated sdk-install block. Returns the list of
    files rewritten.
    """

    changed: list[Path] = []
    for readme in _prereq_readmes(repo_root):
        if rewrite_readme_install_hints(readme, versions):
            changed.append(readme)
    return changed


# ---------------------------------------------------------------------------
# Orphan-version-literal audit (--check)
# ---------------------------------------------------------------------------
#
# The rewriters above make the generator the single *writer* of every SDK-version
# literal it knows about; this audit is the matching *reader* that fails CI when
# a new human-authored surface introduces a literal the generator does not yet
# own, or when someone hand-edits an owned literal out of sync. It scans a
# bounded set of human-authored surfaces — never lockfiles (``go.sum``,
# ``pnpm-lock.yaml``), vendored trees, or build output — and reports each
# ``file:line`` whose SDK-version literal differs from the SoT.
#
# Exemption: any line containing the inline marker ``sdk-version-exempt`` is
# skipped, for legitimate historical / provenance text (e.g. a release note or
# a "written against 0.0.1-rc.3" verification report).

EXEMPT_MARKER = "sdk-version-exempt"

# Which SDK a prose line refers to, so its version token can be compared against
# the right SoT entry.
_PROSE_LABEL_RE = re.compile(r"Agent Assembly (Python|Node\.js|Go) SDK")

# Precise main-SDK pin matchers for the manifest audit. Each captures the pinned
# version in group ``ver``. The identifiers are anchored so a subpackage
# (``@agent-assembly/runtime-*``) or a non-``go-sdk`` org path
# (``github.com/ai-agent-assembly/...``) can never false-match: the python id is
# ``agent-assembly`` immediately followed by a PEP 440 operator; the node id is
# exactly ``@agent-assembly/sdk``; the go id is exactly
# ``github.com/ai-agent-assembly/go-sdk`` followed by whitespace.
_PY_PIN_AUDIT_RE = re.compile(
    r"(?<![\w/@.-])agent-assembly(?P<op>==|>=|~=|<=|!=|<|>)(?P<ver>[^\"'\s,]+)"
)
_NODE_PIN_AUDIT_RE = re.compile(r'"@agent-assembly/sdk"\s*:\s*"(?P<ver>[^"]+)"')
_GO_PIN_AUDIT_RE = re.compile(
    r"github\.com/ai-agent-assembly/go-sdk(?=\s)\s+(?P<ver>\S+)"
)

# Bounded globs for the pin audit — every manifest that carries a main-SDK pin
# under python/, node/, go/, and scenarios/. Lockfiles and go.sum are excluded
# by construction (never globbed).
_PY_PIN_GLOBS = (
    "python/*/pyproject.toml",
    "scenarios/*/pyproject.toml",
    "scenarios/*/*/pyproject.toml",
)
_NODE_PIN_GLOBS = (
    "node/*/package.json",
    "scenarios/*/package.json",
    "scenarios/*/*/package.json",
)
_GO_PIN_GLOBS = (
    "go/*/go.mod",
    "scenarios/*/go.mod",
    "scenarios/*/*/go.mod",
)


def _audit_lines(path: Path):
    """Yield ``(lineno, line)`` pairs for a text file, 1-based."""

    for lineno, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        yield lineno, line


def _audit_pins(repo_root: Path, versions: SdkVersions) -> list[str]:
    """Report every manifest/Dockerfile pin whose version drifts from the SoT."""

    checks = (
        (_PY_PIN_GLOBS, _PY_PIN_AUDIT_RE, versions.python.version),
        (_NODE_PIN_GLOBS, _NODE_PIN_AUDIT_RE, versions.node.version),
        (_GO_PIN_GLOBS, _GO_PIN_AUDIT_RE, versions.go.version),
        (_DOCKERFILE_GLOBS, _DOCKERFILE_PIN_RE, versions.python.version),
    )
    problems: list[str] = []
    for globs, pin_re, expected in checks:
        for path in _globbed(repo_root, globs):
            for lineno, line in _audit_lines(path):
                if EXEMPT_MARKER in line:
                    continue
                match = pin_re.search(line)
                if match and match.group("ver") != expected:
                    rel = path.relative_to(repo_root)
                    problems.append(
                        f"{rel}:{lineno}: pins {match.group('ver')!r}, "
                        f"expected {expected!r}"
                    )
    return problems


# The core SDK pin must be exact (``==``): a floor (``>=``) or open range lets a
# resolver pull a future major and silently break an example (AAASM-4704, and the
# repo's own "never a bare >=" rule). The version-drift audit above only checks
# the version token, so this pass enforces the operator separately. Python
# manifests are the only core-SDK pins that carry an operator — node pins are a
# bare ``"<version>"`` string and go pins are a bare ``go.mod`` version.
def _audit_py_operator(repo_root: Path, versions: SdkVersions) -> list[str]:
    """Report every python core-SDK pin whose operator is not exact (``==``)."""

    problems: list[str] = []
    for path in _globbed(repo_root, _PY_PIN_GLOBS):
        for lineno, line in _audit_lines(path):
            if EXEMPT_MARKER in line:
                continue
            match = _PY_PIN_AUDIT_RE.search(line)
            if match and match.group("op") != "==":
                rel = path.relative_to(repo_root)
                problems.append(
                    f"{rel}:{lineno}: uses {match.group('op')!r} operator on the "
                    f"core SDK pin, expected '=='"
                )
    return problems


def _audit_prose(repo_root: Path, versions: SdkVersions) -> list[str]:
    """Report every README/doc prose line whose SDK version drifts from the SoT.

    Covers the three human-authored prose surfaces the generator owns:
    ``Agent Assembly <Lang> SDK`` rows/bullets, backtick-``package``-labelled
    prereq rows, and raw ``agent-assembly==`` / ``@agent-assembly/sdk@`` install
    hints. Each token is compared the same way the matching rewriter aligns it,
    so a generator-produced tree always audits clean. Install-hint lines inside
    the generated sdk-install block are skipped — that block is generator-owned
    and the prose install-hint pass deliberately excludes it.
    """

    expected_by_label = {
        "Python": versions.python.version,
        "Node.js": versions.node.version,
        "Go": versions.go.version,
    }
    # Backtick-labelled prereq rows, keyed by package/module id -> SoT version.
    backtick_checks = tuple(
        (_prereq_backtick_row_re(package), version)
        for package, version in (
            (versions.python.package, versions.python.version),
            (versions.node.package, versions.node.version),
            (versions.go.module, versions.go.version),
        )
    )
    # Raw install-hint literals, checked only outside the generated block.
    install_checks = (
        (_DOCKERFILE_PIN_RE, versions.python.version),
        (_README_NODE_INSTALL_RE, versions.node.version),
    )
    problems: list[str] = []
    for path in _globbed(repo_root, _README_GLOBS + ("docs/*.md",)):
        rel = path.relative_to(repo_root)
        in_block = False
        for lineno, line in _audit_lines(path):
            if SDK_BLOCK_BEGIN in line:
                in_block = True
            elif SDK_BLOCK_END in line:
                in_block = False
                continue
            if EXEMPT_MARKER in line:
                continue

            label_match = _PROSE_LABEL_RE.search(line)
            if label_match:
                token_match = _VERSION_TOKEN_RE.search(line)
                if token_match is not None:
                    expected = expected_by_label[label_match.group(1)]
                    if token_match.group(0) != expected:
                        problems.append(
                            f"{rel}:{lineno}: states {token_match.group(0)!r}, "
                            f"expected {expected!r}"
                        )

            for row_re, expected in backtick_checks:
                row_match = row_re.search(line)
                if row_match is None:
                    continue
                token_match = _VERSION_TOKEN_RE.search(row_match.group("val"))
                if token_match is not None and token_match.group(0) != expected:
                    problems.append(
                        f"{rel}:{lineno}: states {token_match.group(0)!r}, "
                        f"expected {expected!r}"
                    )

            if in_block:
                continue
            for hint_re, expected in install_checks:
                hint_match = hint_re.search(line)
                if hint_match and hint_match.group("ver") != expected:
                    problems.append(
                        f"{rel}:{lineno}: install hint pins "
                        f"{hint_match.group('ver')!r}, expected {expected!r}"
                    )
    return problems


def audit(repo_root: Path, versions: SdkVersions) -> list[str]:
    """Return every drifted SDK-version literal as a sorted ``file:line`` list."""

    return sorted(
        _audit_pins(repo_root, versions)
        + _audit_py_operator(repo_root, versions)
        + _audit_prose(repo_root, versions)
    )


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
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Audit mode: do not rewrite. Scan the bounded human-authored "
            "surfaces and exit non-zero, naming each file:line, if any "
            "SDK-version literal has drifted from the SoT."
        ),
    )
    args = parser.parse_args(argv)

    versions = load_sdk_versions(args.repo_root)

    if args.check:
        problems = audit(args.repo_root, versions)
        if problems:
            print("SDK-version literals out of sync with the SoT:")
            for problem in problems:
                print(f"  {problem}")
            print(
                "\nAlign metadata/sdk-versions.yaml + re-run the generator, or "
                f"mark legitimate historical text with '{EXEMPT_MARKER}'."
            )
            return 1
        print("--check: every audited surface matches the SoT.")
        return 0

    changed: list[Path] = []
    changed.extend(process_python(args.repo_root, versions))
    changed.extend(process_node(args.repo_root, versions))
    changed.extend(process_go(args.repo_root, versions))
    changed.extend(process_dockerfiles(args.repo_root, versions))
    changed.extend(process_prereq_rows(args.repo_root, versions))
    changed.extend(process_readme_install_hints(args.repo_root, versions))

    if changed:
        print(f"Rewrote {len(changed)} file(s):")
        for path in changed:
            print(f"  {path.relative_to(args.repo_root)}")
    else:
        print("No changes — every example is already in sync with the SoT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
