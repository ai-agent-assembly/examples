#!/usr/bin/env python3
"""Tests for ``scripts/check_example_sdk_mocks.py``.

These exist to keep the gate falsifiable. The AAASM-6156 defect is "an example
pinned a private helper's return shape, and the shape moved", so each test pairs
the fixed mock with the exact pre-fix text that reproduces the defect and must
turn the gate red. A checker that reported clean on both would deliver the same
false confidence the original code had.

The fixtures below are the real shapes: ``BEFORE`` is what all 16 Python
examples contained before AAASM-6156 (including the aliased-``patch`` and
combined-``with`` variants that a text-level check would have missed), and
``AFTER`` is the replacement.
"""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_example_sdk_mocks import (
    PatchSite,
    check_consistency,
    discover_test_files,
    main,
    scan_text,
)

BEFORE = textwrap.dedent(
    """\
    def test_init_assembly_sdk_only_requires_no_gateway() -> None:
        from unittest.mock import patch

        from agent_assembly import init_assembly
        from agent_assembly.core import assembly as _core

        with patch.object(_core, "_register_adapters", return_value=[]):
            with patch.object(
                _core, "_start_network_layer", return_value=("sdk-only", lambda: None)
            ):
                ctx = init_assembly(
                    gateway_url="http://localhost:8080",
                    agent_id="test-crew",
                    mode="sdk-only",
                )
                try:
                    assert ctx.client.agent_id == "test-crew"
                finally:
                    ctx.shutdown()
    """
)

AFTER = textwrap.dedent(
    """\
    def test_init_assembly_sdk_only_requires_no_gateway() -> None:
        from unittest.mock import patch

        from agent_assembly import init_assembly
        from agent_assembly.adapters.registry import AdapterRegistry

        with patch.object(AdapterRegistry, "get_available_adapters_by_priority", return_value=[]):
            ctx = init_assembly(
                gateway_url="http://localhost:8080",
                agent_id="test-crew",
                mode="sdk-only",
            )
            try:
                assert ctx.client.agent_id == "test-crew"
            finally:
                ctx.shutdown()
    """
)


def _rules(source: str) -> list[str]:
    findings, _ = scan_text("python/example/tests/test_smoke.py", source)
    return sorted(f.rule_id for f in findings)


class TestPrivateSeamDetection(unittest.TestCase):
    def test_reproduces_aaasm_6156_private_helper_patch(self) -> None:
        # The real defect, verbatim. Two private patches, so two findings.
        findings, sites = scan_text("python/crewai-research-crew/tests/test_smoke.py", BEFORE)
        self.assertEqual([f.rule_id for f in findings], ["EX-MOCK-01", "EX-MOCK-01"])
        self.assertEqual(len(sites), 2)
        names = sorted(str(s.target).rsplit(".", 1)[-1] for s in sites)
        self.assertEqual(names, ["_register_adapters", "_start_network_layer"])

    def test_the_fix_is_clean(self) -> None:
        findings, sites = scan_text("python/crewai-research-crew/tests/test_smoke.py", AFTER)
        self.assertEqual(findings, [])
        self.assertEqual(
            [s.target for s in sites],
            ["agent_assembly.adapters.registry.AdapterRegistry.get_available_adapters_by_priority"],
        )

    def test_aliased_patch_import_is_still_seen(self) -> None:
        # haystack-tool-policy imported it as `mock_patch`. A checker keyed on
        # the literal name `patch.object` would have passed this file.
        source = BEFORE.replace("import patch", "import patch as mock_patch").replace(
            "patch.object", "mock_patch.object"
        )
        self.assertEqual(_rules(source), ["EX-MOCK-01", "EX-MOCK-01"])

    def test_combined_with_statement_is_still_seen(self) -> None:
        # Several examples used a single parenthesised `with (a, b):` instead of
        # nesting. The AST sees a Call either way; a line-oriented check does not.
        source = textwrap.dedent(
            """\
            def test_x() -> None:
                from unittest.mock import patch

                from agent_assembly.core import assembly as _core

                with (
                    patch.object(_core, "_register_adapters", return_value=[]),
                    patch.object(_core, "_start_network_layer", return_value=("sdk-only", None)),
                ):
                    pass
            """
        )
        self.assertEqual(_rules(source), ["EX-MOCK-01", "EX-MOCK-01"])

    def test_string_target_form_is_seen(self) -> None:
        source = textwrap.dedent(
            """\
            from unittest.mock import patch


            def test_x() -> None:
                with patch("agent_assembly.core.assembly._register_adapters", return_value=[]):
                    pass
            """
        )
        self.assertEqual(_rules(source), ["EX-MOCK-01"])

    def test_private_module_in_the_path_is_seen_separately(self) -> None:
        # A public attribute reached through a private module is the same class
        # of coupling, and gets its own rule so the message can say why.
        source = textwrap.dedent(
            """\
            from unittest.mock import patch


            def test_x() -> None:
                with patch("agent_assembly._internal.registry.lookup", return_value=[]):
                    pass
            """
        )
        self.assertEqual(_rules(source), ["EX-MOCK-02"])

    def test_dunder_is_not_treated_as_private(self) -> None:
        source = textwrap.dedent(
            """\
            from unittest.mock import patch

            import agent_assembly


            def test_x() -> None:
                with patch.object(agent_assembly, "__version__", "0.0.0"):
                    pass
            """
        )
        self.assertEqual(_rules(source), [])

    def test_patching_a_non_sdk_private_attribute_is_not_this_gates_business(self) -> None:
        # Examples legitimately patch their own helpers and third-party
        # libraries. Flagging those would make the gate noise and get it waived.
        source = textwrap.dedent(
            """\
            from unittest.mock import patch

            from mypackage import helpers


            def test_x() -> None:
                with patch.object(helpers, "_local_thing", return_value=[]):
                    pass
                with patch("openai._client.OpenAI", return_value=None):
                    pass
            """
        )
        self.assertEqual(_rules(source), [])

    def test_computed_attribute_name_is_reported_not_silently_skipped(self) -> None:
        source = textwrap.dedent(
            """\
            from unittest.mock import patch

            from agent_assembly.core import assembly as _core

            NAME = "_register_adapters"


            def test_x() -> None:
                with patch.object(_core, NAME, return_value=[]):
                    pass
            """
        )
        self.assertEqual(_rules(source), ["EX-MOCK-04"])


class TestConsistency(unittest.TestCase):
    def _site(self, path: str, target: str | None):
        findings, sites = scan_text(path, AFTER if target else BEFORE)
        del findings
        return sites

    def test_all_examples_on_one_seam_is_clean(self) -> None:
        sites = []
        for name in ("langgraph", "pydantic-ai", "google-adk"):
            sites.extend(self._site(f"python/{name}/tests/test_smoke.py", "after"))
        self.assertEqual(len(sites), 3)
        self.assertEqual(check_consistency(sites), [])

    def test_one_example_left_behind_is_reported_by_name(self) -> None:
        # The drift AAASM-6156 asks to prevent: 15 directories updated, 1 missed.
        sites = []
        for name in ("langgraph", "pydantic-ai"):
            sites.extend(self._site(f"python/{name}/tests/test_smoke.py", "after"))
        stale = self._site("python/google-adk/tests/test_smoke.py", None)
        sites.extend(stale)
        findings = check_consistency(sites)
        self.assertTrue(findings)
        self.assertEqual({f.rule_id for f in findings}, {"EX-MOCK-03"})
        self.assertEqual({f.path for f in findings}, {"python/google-adk/tests/test_smoke.py"})

    def test_a_single_patch_site_cannot_disagree_with_itself(self) -> None:
        sites = self._site("python/langgraph/tests/test_smoke.py", "after")
        self.assertEqual(check_consistency(sites), [])

    def test_one_example_patching_two_public_seams_is_not_drift(self) -> None:
        # The rule's subject is disagreement *between* examples. An example that
        # needs two seams is doing something legitimate, and flagging it would
        # make the gate noise — which is how gates get waived.
        two_seams = AFTER.replace(
            "        ctx = init_assembly(",
            '        with patch.object(AdapterRegistry, "discover", return_value=[]):\n'
            "            ctx = init_assembly(",
        )
        findings, sites = scan_text("python/langgraph/tests/test_smoke.py", two_seams)
        self.assertEqual(findings, [])
        self.assertEqual(len(sites), 2)
        sibling = [
            PatchSite("python/pydantic-ai/tests/test_smoke.py", s.line, s.target) for s in sites
        ]
        self.assertEqual(check_consistency(sites + sibling), [])

    def test_the_pre_fix_tree_agreed_with_itself_so_only_ex_mock_01_fires(self) -> None:
        # All 16 examples carried the *same* stale mock, so the drift rule
        # correctly says nothing about the original defect — EX-MOCK-01 is what
        # catches it. Asserted so a future reader does not mistake EX-MOCK-03 for
        # the rule that would have prevented AAASM-6156.
        sites = []
        for name in ("langgraph", "pydantic-ai", "google-adk"):
            sites.extend(self._site(f"python/{name}/tests/test_smoke.py", None))
        self.assertEqual(check_consistency(sites), [])


class TestDiscoveryAndExit(unittest.TestCase):
    def _tree(self, root: Path, rel: str, source: str) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")

    def test_discovers_both_example_layouts(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._tree(root, "python/langgraph/tests/test_smoke.py", AFTER)
            self._tree(root, "scenarios/approval-gates/python/tests/test_smoke.py", AFTER)
            self._tree(root, "node/langgraph/tests/smoke.test.ts", "// not python")
            self._tree(root, "scripts/test_check_example_sdk_mocks.py", BEFORE)
            found = discover_test_files(root)
            self.assertEqual(
                found,
                [
                    "python/langgraph/tests/test_smoke.py",
                    "scenarios/approval-gates/python/tests/test_smoke.py",
                ],
            )

    def test_exit_zero_on_a_fixed_tree_and_one_on_the_pre_fix_tree(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._tree(root, "python/langgraph/tests/test_smoke.py", AFTER)
            self._tree(root, "python/pydantic-ai/tests/test_smoke.py", AFTER)
            self.assertEqual(main(["--root", str(root)]), 0)

            self._tree(root, "python/pydantic-ai/tests/test_smoke.py", BEFORE)
            self.assertEqual(main(["--root", str(root)]), 1)

    def test_empty_tree_fails_rather_than_reporting_clean(self) -> None:
        # A layout change that matches zero files must not read as success.
        with TemporaryDirectory() as tmp:
            self.assertEqual(main(["--root", tmp]), 1)

    def test_unparseable_file_fails_rather_than_reporting_clean(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._tree(root, "python/langgraph/tests/test_smoke.py", "def broken(:\n")
            self.assertEqual(main(["--root", str(root)]), 1)


if __name__ == "__main__":
    unittest.main()
