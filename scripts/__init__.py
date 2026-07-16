"""Repo tooling package.

Exists so the metadata generator's unit tests are importable as
``scripts.test_generate_example_metadata`` (``python -m unittest``). The
generator and snippet extractors are also runnable directly by path, which does
not depend on this marker.
"""
