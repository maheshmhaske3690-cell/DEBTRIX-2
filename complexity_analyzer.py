"""
Static complexity analysis.

- Python files: use `radon` (cyclomatic complexity + maintainability index)
- All other supported languages: use `lizard` (cross-language complexity)

We only extract NUMBERS (complexity scores, line counts) — the
analyzers read the file content in-memory but nothing here persists
or logs the actual source text.
"""
import os

import lizard
from radon.complexity import cc_visit
from radon.metrics import mi_visit

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb",
    ".php", ".c", ".cpp", ".cs", ".swift", ".kt",
}


def _analyze_python_file(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    try:
        blocks = cc_visit(source)
        avg_complexity = sum(b.complexity for b in blocks) / len(blocks) if blocks else 1.0
        maintainability = mi_visit(source, multi=True)
    except Exception:
        avg_complexity = 1.0
        maintainability = 100.0

    return {
        "language": "python",
        "cyclomatic_complexity": round(avg_complexity, 2),
        "maintainability_index": round(maintainability, 2),
        "lines_of_code": len(source.splitlines()),
    }


def _analyze_generic_file(file_path: str) -> dict:
    result = lizard.analyze_file(file_path)
    avg_complexity = (
        sum(f.cyclomatic_complexity for f in result.function_list) / len(result.function_list)
        if result.function_list else 1.0
    )
    return {
        "language": os.path.splitext(file_path)[1].lstrip("."),
        "cyclomatic_complexity": round(avg_complexity, 2),
        "maintainability_index": None,  # lizard doesn't compute this directly
        "lines_of_code": result.nloc,
    }


def analyze_repository(repo_path: str) -> dict[str, dict]:
    """
    Walks the cloned repo and returns { relative_file_path: metrics_dict }
    for every supported source file. Skips hidden dirs, node_modules,
    venv, etc.
    """
    ignored_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}
    results: dict[str, dict] = {}

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]

        for filename in files:
            ext = os.path.splitext(filename)[1]
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, repo_path)

            try:
                if ext == ".py":
                    metrics = _analyze_python_file(full_path)
                else:
                    metrics = _analyze_generic_file(full_path)
                results[relative_path] = metrics
            except Exception:
                # Skip unreadable/binary-ish files rather than failing the whole scan
                continue

    return results
