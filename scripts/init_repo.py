#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "rich>=13.0.0",
#   "typer>=0.12.0",
# ]
# ///

"""Inicializa o migra la estructura interna de un repositorio de materia.

Reemplaza al viejo `init-repo-structure.sh`. La estructura objetivo es la
descrita en docs/ARCHITECTURE.md: layout flat, sin placeholders `tema1/tema2`
ni `.gitkeep`.

Ejemplos:

    uv run scripts/init_repo.py init .                  # repo actual
    uv run scripts/init_repo.py init /ruta/al/repo --year 2026
    uv run scripts/init_repo.py migrate /ruta/al/repo --dry-run

`init` crea las carpetas mínimas y un README base si no existe. `migrate`
elimina placeholders `.gitkeep` y carpetas vacías `tema*/` heredadas del
layout antiguo.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer  # ty: ignore
from rich.console import Console  # ty: ignore

console = Console()
app = typer.Typer(add_completion=False, no_args_is_help=True)


REQUIRED_DIRS_TPL = (
    "notes/{year}/teoria",
    "notes/{year}/practica",
    "resources/common",
)

README_TEMPLATE = """\
# 📚 {name}

## 📝 Descripción
{description}

## 📂 Estructura

- `notes/<año>/teoria/` — apuntes teóricos.
- `notes/<año>/practica/` — ejercicios y trabajos prácticos.
- `examples/` — ejemplos de código (opcional, solo si hay contenido).
- `study-guides/` — guías de estudio para parciales y finales.
- `resources/common/` — bibliografía y enlaces compartidos entre años.

## 🗓️ Año en curso ({year})

- 📚 Teoría: ver [`notes/{year}/teoria/`](./notes/{year}/teoria/)
- 💻 Práctica: ver [`notes/{year}/practica/`](./notes/{year}/practica/)

## 🤝 Contribuir
Las contribuciones son bienvenidas. Convenciones generales en
[apuntes-frre/.github](https://github.com/apuntes-frre/.github).

## 📜 Licencia
MIT.
"""


@app.command()
def init(
    repo_path: Annotated[Path, typer.Argument(help="Ruta al repo local")],
    year: Annotated[int, typer.Option(help="Año académico")] = datetime.now().year,
    name: Annotated[str | None, typer.Option(help="Nombre legible de la materia")] = None,
    description: Annotated[str, typer.Option(help="Descripción corta")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Crea la estructura mínima si falta. No toca contenido existente."""
    repo_path = repo_path.resolve()
    if not repo_path.is_dir():
        raise typer.BadParameter(f"{repo_path} no es un directorio")

    materia = name or _slug_to_name(repo_path.name)
    actions: list[str] = []

    for tpl in REQUIRED_DIRS_TPL:
        target = repo_path / tpl.format(year=year)
        if not target.exists():
            actions.append(f"mkdir {target.relative_to(repo_path)}")
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)

    readme = repo_path / "README.md"
    if not readme.exists():
        actions.append("create README.md")
        if not dry_run:
            readme.write_text(
                README_TEMPLATE.format(name=materia, description=description, year=year),
                encoding="utf-8",
            )

    _report(actions, dry_run)


@app.command()
def migrate(
    repo_path: Annotated[Path, typer.Argument(help="Ruta al repo local")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Elimina .gitkeep y carpetas tema*/ vacías del layout heredado."""
    repo_path = repo_path.resolve()
    if not repo_path.is_dir():
        raise typer.BadParameter(f"{repo_path} no es un directorio")

    actions: list[str] = []

    for gitkeep in repo_path.rglob(".gitkeep"):
        if ".git" in gitkeep.parts:
            continue
        actions.append(f"rm {gitkeep.relative_to(repo_path)}")
        if not dry_run:
            gitkeep.unlink()

    for path in sorted(repo_path.rglob("tema*"), key=lambda p: -len(p.parts)):
        if ".git" in path.parts or not path.is_dir():
            continue
        if not any(path.iterdir()):
            actions.append(f"rmdir {path.relative_to(repo_path)}")
            if not dry_run:
                path.rmdir()

    for path in sorted(
        (p for p in repo_path.rglob("*") if p.is_dir() and ".git" not in p.parts),
        key=lambda p: -len(p.parts),
    ):
        if not any(path.iterdir()):
            actions.append(f"rmdir {path.relative_to(repo_path)} (vacía)")
            if not dry_run:
                path.rmdir()

    _report(actions, dry_run)


def _slug_to_name(repo_name: str) -> str:
    parts = repo_name.split("-")
    if len(parts) >= 3 and parts[1].isdigit():
        parts = parts[2:]
    return " ".join(p.capitalize() for p in parts)


def _report(actions: list[str], dry_run: bool) -> None:
    if not actions:
        console.print("[yellow]≡ Nada que hacer.[/]")
        return
    prefix = "[DRY-RUN] " if dry_run else ""
    for a in actions:
        console.print(f"{prefix}• {a}")
    verb = "se aplicarían" if dry_run else "aplicadas"
    console.print(f"[bold green]✅ {len(actions)} acciones {verb}.[/]")


if __name__ == "__main__":
    app()
