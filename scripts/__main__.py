"""Índice de los scripts de automatización.

    uv run python -m scripts

Lista cada módulo de `scripts/` con la primera línea de su docstring. Lee el
código fuente sin importarlo, así que no dispara las dependencias PEP 723 de
cada script.
"""

from __future__ import annotations

import ast
from pathlib import Path

HERE = Path(__file__).parent
SKIP = {"__init__.py", "__main__.py"}


def _summary(path: Path) -> str:
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))
    except (SyntaxError, ValueError):
        doc = None
    return doc.strip().splitlines()[0] if doc else "—"


def main() -> None:
    print("Scripts de automatización (uv run scripts/<nombre>.py):\n")
    for path in sorted(HERE.glob("*.py")):
        if path.name in SKIP:
            continue
        print(f"  {path.name}")
        print(f"      {_summary(path)}\n")


if __name__ == "__main__":
    main()
