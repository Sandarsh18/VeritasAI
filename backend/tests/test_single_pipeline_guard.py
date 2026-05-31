"""Guard test: main.py must route all retrieval through rag/retriever.py only.

Property 9 (single-pipeline invariant): no import of retrieval.py /
legacy.retrieval anywhere in main.py.
"""

import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
MAIN_PY = BACKEND_DIR / "main.py"


def test_main_does_not_import_legacy_retrieval():
    source = MAIN_PY.read_text(encoding="utf-8")
    # No top-level `from retrieval import` or `import retrieval`
    assert not re.search(r"^\s*from\s+retrieval\s+import", source, re.MULTILINE), \
        "main.py still imports from the retired retrieval.py shim"
    assert not re.search(r"^\s*import\s+retrieval\b", source, re.MULTILINE), \
        "main.py still imports the retired retrieval module"
    assert "legacy.retrieval" not in source, "main.py references legacy.retrieval"


def test_retrieval_shim_is_removed():
    assert not (BACKEND_DIR / "retrieval.py").exists(), \
        "retrieval.py shim should be deleted (retired)"


def test_unified_retriever_is_used():
    source = MAIN_PY.read_text(encoding="utf-8")
    assert "from rag.retriever import retrieve_evidence" in source, \
        "main.py should call the unified rag.retriever.retrieve_evidence"
