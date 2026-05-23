#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "jinja2>=3.0.0",
#   "pyyaml>=6.0",
#   "rich>=13.0.0",
# ]
# ///

"""Regenera docs/README.md a partir del estado real del repo de control `.github`.

Recorre el árbol del repo (scripts, workflows, data, templates, docs) y rinde un
inventario. Es idempotente: compara con el archivo en disco y solo escribe si hay
diferencias. Así, leer docs/README.md siempre refleja qué hay en el repo.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

import yaml  # ty: ignore
from jinja2 import Environment, FileSystemLoader  # ty: ignore
from rich.console import Console  # ty: ignore

ROOT = Path(__file__).parent.parent
console = Console()


def _script_purpose(path: Path) -> str:
    """Primera línea del docstring del módulo."""
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))
    except (SyntaxError, ValueError):
        doc = None
    return doc.strip().splitlines()[0] if doc else "—"


def _workflow_info(path: Path) -> dict[str, Any]:
    """Nombre y triggers de un workflow de GitHub Actions."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    # PyYAML interpreta el `on:` sin comillas como el booleano True.
    on = data.get("on", data.get(True, {}))
    if isinstance(on, str):
        triggers = [on]
    elif isinstance(on, list):
        triggers = list(on)
    elif isinstance(on, dict):
        triggers = list(on.keys())
    else:
        triggers = []
    return {
        "file": path.name,
        "name": data.get("name", path.stem),
        "triggers": ", ".join(triggers) or "—",
    }


def collect_state() -> dict[str, Any]:
    scripts = [
        {"name": p.name, "purpose": _script_purpose(p)}
        for p in sorted((ROOT / "scripts").glob("*.py"))
    ]
    workflows = [
        _workflow_info(p) for p in sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    ]
    data_files = [p.name for p in sorted((ROOT / "data").glob("*.toml"))]
    templates = [p.name for p in sorted((ROOT / "templates").glob("*.j2"))]
    docs = [
        p.name for p in sorted((ROOT / "docs").glob("*.md")) if p.name != "README.md"
    ]
    return {
        "scripts": scripts,
        "workflows": workflows,
        "data_files": data_files,
        "templates": templates,
        "docs": docs,
    }


def render(data: dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    return env.get_template("repo_readme.md.j2").render(**data)


def main() -> int:
    rendered = render(collect_state())
    target = ROOT / "docs" / "README.md"
    current = target.read_text(encoding="utf-8") if target.exists() else ""

    if rendered == current:
        console.print("[yellow]≡ docs/README.md sin cambios. No se escribe.[/]")
        return 0

    target.write_text(rendered, encoding="utf-8")
    console.print(f"[bold green]✅ docs/README.md regenerado: {target}[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
