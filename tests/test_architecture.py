import ast
from pathlib import Path


def test_core_imports_only_point_inward():
    root = Path(__file__).parents[1] / "src" / "sharp"
    for name in ["contracts", "career", "selection", "layout", "workflow"]:
        tree = ast.parse((root / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = [node.module or ""] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            for imported in names:
                assert not imported.startswith(("sharp.adapters", "app", "resume2", "reportlab", "pypdf", "extism", "pptx", "docx", "mcp", "acp", "litellm")), (name, imported)
