"""Single cached access point for the fictional datasets."""
from __future__ import annotations

from functools import lru_cache

from . import generator as gen


@lru_cache(maxsize=1)
def data() -> gen.Datasets:
    """Datasets are regenerated deterministically in memory, so the app never
    depends on CSV files the user might have edited. The CSVs in datasets/
    are byte-for-byte what this returns (checked by the test-suite)."""
    return gen.build()
