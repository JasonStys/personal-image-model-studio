"""AST-derived Python declaration/variable inventory; read source only and emit JSON for the code-map builder."""

# Index: declarations module.inventory@L10, inventory.scope@L17; variables path@L10, source@L12, tree@L13, declarations@L14, variables@L14, child@L15, parent@L15, parents@L15, node@L17, names@L19, node@L21, node@L26, description@L28, parent@L46, value@L61, value@L62. Purposes/parameters: docs/code-map.json.
import ast
import json
import sys
from pathlib import Path


def inventory(path: Path) -> dict:
    """Extract real declaration/argument/assignment locations and source-derived purposes without execution."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    declarations, variables = [], []
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}

    def scope(node):
        """Qualify nested names so repeated locals in different functions remain distinguishable."""
        names = []
        while node in parents:
            node = parents[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.append(node.name)
        return ".".join(reversed(names)) or "module"

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            description = ast.get_docstring(node)
            if not description:
                raise SystemExit(
                    f"Missing declaration documentation: {path}:{node.lineno} {node.name}"
                )
            declarations.append(
                {
                    "name": scope(node) + "." + node.name,
                    "line": node.lineno,
                    "kind": type(node).__name__,
                    "purpose": description,
                }
            )
        if (
            isinstance(node, ast.arg)
            or isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Store)
        ):
            parent = parents.get(node)
            variables.append(
                {
                    "name": node.arg if isinstance(node, ast.arg) else node.id,
                    "scope": scope(node),
                    "line": node.lineno,
                    "purpose": (
                        "Function parameter"
                        if isinstance(node, ast.arg)
                        else ast.unparse(parent)[:180]
                    ),
                }
            )
    return {
        "purpose": ast.get_docstring(tree) or "",
        "declarations": sorted(declarations, key=lambda value: (value["line"], value["name"])),
        "variables": sorted(variables, key=lambda value: (value["line"], value["name"])),
    }


if __name__ == "__main__":
    print(json.dumps(inventory(Path(sys.argv[1])), ensure_ascii=False))
