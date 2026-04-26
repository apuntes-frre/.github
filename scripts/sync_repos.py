#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "PyGithub>=2.1.0",
#   "rich>=13.0.0",
#   "typer>=0.12.0",
# ]
# ///

"""Operaciones org-wide sobre apuntes-frre.

Subcomandos:

- `inspect`  → lista los repos detectados y los clasifica por convención.
- `init-all` → ejecuta init_repo.py contra cada repo (clona temporalmente).
- `rename`   → propone (o aplica) renombres al formato
               <carrera>-<plan>-<slug>.

Todos los subcomandos soportan `--dry-run`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated

import typer
from github import Github
from github.Repository import Repository
from rich.console import Console
from rich.table import Table

ORG_NAME = "apuntes-frre"
DEFAULT_PLAN = "2008"
KNOWN_CARRERAS = {"isi", "lic", "tec"}

NEW_RE = re.compile(r"^(?P<carrera>[a-z]+)-(?P<plan>\d{4})-(?P<slug>[a-z0-9-]+)$")
LEGACY_RE = re.compile(r"^(?P<carrera>[a-z]+)-(?P<slug>[a-z0-9-]+)$")

console = Console()
app = typer.Typer(add_completion=False, no_args_is_help=True)


def _client() -> Github:
    token = os.getenv("ORG_ADMIN_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Falta ORG_ADMIN_TOKEN o GITHUB_TOKEN")
    return Github(token)


def _classify(name: str) -> tuple[str, str, str] | None:
    if m := NEW_RE.match(name):
        return m["carrera"], m["plan"], m["slug"]
    if m := LEGACY_RE.match(name):
        if m["carrera"] in KNOWN_CARRERAS:
            return m["carrera"], DEFAULT_PLAN, m["slug"]
    return None


@app.command()
def inspect() -> None:
    """Lista repos y muestra su clasificación según la convención."""
    org = _client().get_organization(ORG_NAME)
    table = Table(title=f"Repos en {ORG_NAME}")
    table.add_column("Repo", style="cyan")
    table.add_column("Carrera")
    table.add_column("Plan")
    table.add_column("Slug")
    table.add_column("Convención", style="bold")

    legacy = 0
    for repo in org.get_repos():
        cls = _classify(repo.name)
        if cls is None:
            table.add_row(repo.name, "-", "-", "-", "[red]ignorado[/]")
            continue
        carrera, plan, slug = cls
        is_new = NEW_RE.match(repo.name) is not None
        if not is_new:
            legacy += 1
        marker = "[green]nueva[/]" if is_new else "[yellow]legacy[/]"
        table.add_row(repo.name, carrera, plan, slug, marker)

    console.print(table)
    if legacy:
        console.print(
            f"[yellow]⚠ {legacy} repo(s) usan el formato legacy. "
            f"Ejecutá `rename --dry-run` para ver el plan de migración.[/]"
        )


@app.command()
def rename(
    plan: Annotated[str, typer.Option(help="Plan de estudios a asignar")] = DEFAULT_PLAN,
    apply: Annotated[bool, typer.Option("--apply", help="Aplica los cambios")] = False,
) -> None:
    """Renombra repos legacy <carrera>-<slug> → <carrera>-<plan>-<slug>."""
    org = _client().get_organization(ORG_NAME)
    pending: list[tuple[Repository, str]] = []

    for repo in org.get_repos():
        cls = _classify(repo.name)
        if cls is None or NEW_RE.match(repo.name):
            continue
        carrera, _, slug = cls
        new_name = f"{carrera}-{plan}-{slug}"
        pending.append((repo, new_name))

    if not pending:
        console.print("[green]Nada que renombrar.[/]")
        return

    for repo, new in pending:
        console.print(f"  • {repo.name} → [bold]{new}[/]")

    if not apply:
        console.print(
            f"[yellow]DRY-RUN: {len(pending)} renombres pendientes. "
            f"Repetí con --apply para ejecutarlos.[/]"
        )
        return

    for repo, new in pending:
        repo.edit(name=new)
        console.print(f"[green]✓ {repo.name} → {new}[/]")


@app.command("init-all")
def init_all(
    year: Annotated[int, typer.Option(help="Año académico a inicializar")] = 0,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Clona cada repo de materia y aplica scripts/init_repo.py."""
    from datetime import datetime

    año = year or datetime.now().year
    org = _client().get_organization(ORG_NAME)
    init_script = Path(__file__).with_name("init_repo.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for repo in org.get_repos():
            if _classify(repo.name) is None:
                continue
            target = tmp_path / repo.name
            console.print(f"[cyan]→ {repo.name}[/]")
            subprocess.run(
                ["git", "clone", "--depth", "1", repo.clone_url, str(target)],
                check=True,
            )
            cmd = ["uv", "run", str(init_script), "init", str(target), "--year", str(año)]
            if dry_run:
                cmd.append("--dry-run")
            subprocess.run(cmd, check=True)


if __name__ == "__main__":
    try:
        app()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Subproceso falló: {e}[/]")
        sys.exit(e.returncode)
