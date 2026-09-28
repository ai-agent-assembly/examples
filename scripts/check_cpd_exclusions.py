#!/usr/bin/env python3
"""Assert the SonarCloud copy-paste exclusion list covers every generated snippet.

WHY THIS EXISTS
---------------
AAASM-6206. ``.sonarcloud.properties`` is the only config file SonarCloud's
Automatic Analysis honours, and it forbids wildcard patterns. So
``sonar.cpd.exclusions`` cannot say ``snippets/**``; every generated snippet has
to be named individually. The list was originally seeded from the duplication
report of one particular day, 2026-07-23, which means it recorded the pairs that
happened to exceed Sonar's minimum block size *that day* rather than the pairs
that are duplicated *by construction*.

Those are different sets, and the difference bites. Every
``snippets/<sdk>/<framework>.<ext>`` is a verbatim extraction of the
``region: quickstart`` slice of its example entrypoint (``extract_snippets.py``,
drift-gated by ``example-metadata-check.yml``), so all of them duplicate their
source by design. They merely become *visible* to the detector once the region
grows past its minimum block size. AAASM-6204 added one argument plus a two-line
comment to all 16 Python quickstart regions; that pushed
``llamaindex-tool-policy`` over the boundary and failed the new-code duplication
gate on a pair that was already byte-identical on main.

Left alone, the next region to cross that boundary fails the same way, on a
change that introduced no duplication at all. This gate closes that by deriving
the required set from ``snippets/manifest.json`` instead of from a report
snapshot, so a snippet cannot reach main without its exclusion.

THE CONTRACT
------------
A1  Every ``snippet_path`` in ``snippets/manifest.json`` appears verbatim in
    ``sonar.cpd.exclusions``.
A2  The list is sorted and duplicate-free, so appends stay reviewable and the
    diff of adding one entry stays one entry wide.
A3  Every path in the list exists on disk. A stale entry protects nothing and
    silently survives a rename.
A4  The scan is non-vacuous: the manifest yielded at least one snippet and the
    property was actually found. A gate that checks an empty set passes
    everything.
A5  No entry contains a wildcard character. The property does not support them,
    so a well-meant ``snippets/**`` would silently match nothing and look like
    a fix while protecting no file at all. This is the exact trap A1 exists to
    make unnecessary.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It does not require ``source_example`` to be excluded. Excluding the generated
side is enough to retire a pair, and leaving the hand-written side under full
duplication analysis is the stronger posture. Several source files *are* in the
list, but for a different reason the file's own comment records: the
per-framework ``main.py`` / ``index.ts`` / ``policy.*`` templates duplicate each
*other*, independently of any snippet. This gate does not touch those.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROPERTIES = REPO_ROOT / ".sonarcloud.properties"
MANIFEST = REPO_ROOT / "snippets" / "manifest.json"
PROPERTY_KEY = "sonar.cpd.exclusions"

# Characters SonarCloud's wildcard syntax would use. `.sonarcloud.properties`
# does not support any of them, which is the whole reason this gate is needed.
WILDCARD_CHARS = "*?"


class ContractError(Exception):
    """A contract assertion failed."""


def read_exclusions(text: str) -> list[str]:
    """Return the ``sonar.cpd.exclusions`` entries, in file order."""
    match = re.search(rf"^{re.escape(PROPERTY_KEY)}=(.*)$", text, re.MULTILINE)
    if match is None:
        raise ContractError(
            f"A4: {PROPERTY_KEY} not found in .sonarcloud.properties. "
            "Without it every snippet is under copy-paste detection and this "
            "gate would otherwise pass over an empty set."
        )
    return [entry for entry in match.group(1).split(",") if entry]


def read_snippet_paths(manifest: dict) -> list[str]:
    """Return every declared snippet path from the generator's manifest."""
    paths = []
    for entries in manifest.get("sdks", {}).values():
        for entry in entries:
            paths.append(entry["snippet_path"])
    return paths


def check(
    text: str,
    manifest: dict,
    *,
    path_exists=None,
    verbose: bool = False,
) -> None:
    """Raise ``ContractError`` on the first violated assertion."""
    if path_exists is None:
        path_exists = lambda rel: (REPO_ROOT / rel).exists()  # noqa: E731

    exclusions = read_exclusions(text)
    snippets = read_snippet_paths(manifest)

    # A4 — non-vacuity, checked before anything that could pass over an empty set.
    if not snippets:
        raise ContractError(
            "A4: snippets/manifest.json declared no snippets. Either the "
            "manifest is broken or this gate is checking nothing."
        )
    if not exclusions:
        raise ContractError(f"A4: {PROPERTY_KEY} is present but empty.")

    # A5 — wildcards are silently inert here, so they must never appear.
    inert = [e for e in exclusions if any(c in e for c in WILDCARD_CHARS)]
    if inert:
        raise ContractError(
            "A5: wildcard pattern(s) in "
            f"{PROPERTY_KEY}: {', '.join(inert)}. "
            ".sonarcloud.properties does not support wildcards, so these match "
            "no file and protect nothing. List the exact paths instead."
        )

    # A2 — sorted and duplicate-free.
    duplicates = sorted({e for e in exclusions if exclusions.count(e) > 1})
    if duplicates:
        raise ContractError(f"A2: duplicate entries: {', '.join(duplicates)}")
    if exclusions != sorted(exclusions):
        first = next(
            (b for a, b in zip(exclusions, exclusions[1:]) if b < a),
            "?",
        )
        raise ContractError(
            f"A2: list is not sorted; {first!r} appears after a later-sorting "
            "entry. Keep it sorted so adding one path is a one-entry diff."
        )

    # A1 — completeness against the manifest, the whole point of the gate.
    missing = sorted(set(snippets) - set(exclusions))
    if missing:
        raise ContractError(
            "A1: generated snippet(s) absent from "
            f"{PROPERTY_KEY}:\n"
            + "".join(f"    {m}\n" for m in missing)
            + "  Each snippet is a verbatim extraction of its example "
            "entrypoint, so it duplicates that source by construction and will "
            "fail the duplication gate as soon as the region crosses Sonar's "
            "minimum block size. Add it now, keeping the list sorted."
        )

    # A3 — no stale entries.
    stale = sorted(e for e in exclusions if not path_exists(e))
    if stale:
        raise ContractError(
            "A3: exclusion(s) name a path that does not exist:\n"
            + "".join(f"    {s}\n" for s in stale)
            + "  A stale entry protects nothing. Remove it, or fix the path if "
            "the file was renamed."
        )

    if verbose:
        print(f"  {PROPERTY_KEY}: {len(exclusions)} entries, sorted, all present on disk")
        print(f"  manifest snippets: {len(snippets)}, all excluded from copy-paste detection")
        sources = len(exclusions) - len(snippets)
        print(f"  non-snippet entries: {sources} (per-framework templates that duplicate each other)")


def _mutate_drop_snippet(text: str, manifest: dict):
    victim = read_snippet_paths(manifest)[0]
    entries = [e for e in read_exclusions(text) if e != victim]
    return _rewrite(text, entries), manifest, "A1"


def _mutate_unsort(text: str, manifest: dict):
    entries = read_exclusions(text)
    entries = [entries[-1]] + entries[:-1]
    return _rewrite(text, entries), manifest, "A2"


def _mutate_duplicate(text: str, manifest: dict):
    entries = read_exclusions(text)
    return _rewrite(text, entries + [entries[0]]), manifest, "A2"


def _mutate_wildcard(text: str, manifest: dict):
    entries = sorted(read_exclusions(text) + ["snippets/**"])
    return _rewrite(text, entries), manifest, "A5"


def _mutate_stale_path(text: str, manifest: dict):
    entries = sorted(read_exclusions(text) + ["python/deleted-example/src/main.py"])
    return _rewrite(text, entries), manifest, "A3"


def _mutate_empty_manifest(text: str, manifest: dict):
    return text, {"sdks": {}}, "A4"


def _mutate_drop_property(text: str, manifest: dict):
    stripped = re.sub(rf"^{re.escape(PROPERTY_KEY)}=.*$", "", text, flags=re.MULTILINE)
    return stripped, manifest, "A4"


def _rewrite(text: str, entries: list[str]) -> str:
    return re.sub(
        rf"^{re.escape(PROPERTY_KEY)}=.*$",
        f"{PROPERTY_KEY}=" + ",".join(entries),
        text,
        flags=re.MULTILINE,
    )


MUTATIONS = [
    ("a generated snippet dropped from the list", _mutate_drop_snippet),
    ("the list left unsorted", _mutate_unsort),
    ("a duplicated entry", _mutate_duplicate),
    ("a wildcard pattern that silently matches nothing", _mutate_wildcard),
    ("an entry naming a path that no longer exists", _mutate_stale_path),
    ("an empty manifest, so the scan covers nothing", _mutate_empty_manifest),
    ("the property removed entirely", _mutate_drop_property),
]


def selftest() -> int:
    """Require the gate to reject each way the contract can be broken.

    A gate is only worth its runtime if it can fail. Each mutation is applied to
    an in-memory copy of the real files, never to disk.
    """
    text = PROPERTIES.read_text()
    manifest = json.loads(MANIFEST.read_text())

    # The unmutated repo must pass, or every mutation below proves nothing.
    try:
        check(text, manifest, path_exists=lambda rel: True)
    except ContractError as error:
        print(f"FAIL  the real repo does not satisfy the contract: {error}")
        return 1
    print("PASS  baseline: the real repo satisfies the contract")

    failures = 0
    for label, mutate in MUTATIONS:
        mutated_text, mutated_manifest, expected = mutate(text, manifest)
        # A3 needs real existence checks; everything else must not depend on them.
        exists = (
            (lambda rel: (REPO_ROOT / rel).exists())
            if expected == "A3"
            else (lambda rel: True)
        )
        try:
            check(mutated_text, mutated_manifest, path_exists=exists)
        except ContractError as error:
            got = str(error).split(":", 1)[0]
            if got == expected:
                print(f"PASS  caught {label} ({expected})")
            else:
                print(f"FAIL  caught {label} but as {got}, expected {expected}")
                failures += 1
        else:
            print(f"FAIL  did NOT catch {label} (expected {expected})")
            failures += 1

    if failures:
        print(f"\n{failures} mutation(s) went undetected: this gate is not failing closed.")
        return 1
    print(f"\nAll {len(MUTATIONS)} mutations detected.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="prove the gate rejects each way the contract can be broken",
    )
    parser.add_argument("--verbose", action="store_true", help="print what was checked")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    try:
        check(
            PROPERTIES.read_text(),
            json.loads(MANIFEST.read_text()),
            verbose=args.verbose,
        )
    except ContractError as error:
        print(f"::error::sonar.cpd.exclusions contract violated\n{error}", file=sys.stderr)
        return 1

    if args.verbose:
        print("sonar.cpd.exclusions covers every generated snippet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
