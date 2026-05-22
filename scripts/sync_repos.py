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

- `inspect`         → lista los repos detectados y los clasifica por convención.
- `init-all`        → ejecuta init_repo.py contra cada repo (clona temporalmente).
- `rename`          → propone (o aplica) renombres al formato
                      <carrera>-<plan>-<slug>.
- `manifest list`   → lista materias declaradas en data/<carrera>.toml.
- `manifest validate` → verifica que el DAG de correlativas no tenga huérfanas.
- `manifest diff`   → diff entre repos expected (según manifest) y la org.
- `manifest sync`   → crea faltantes, actualiza descripciones y reporta/archiva
                      sobrantes. El manifest es la única fuente de verdad.

Todos los subcomandos sobre la org soportan `--dry-run`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Annotated, Any

import typer
from github import Github
from github.Repository import Repository
from rich.console import Console
from rich.table import Table

ORG_NAME = "apuntes-frre"
DEFAULT_PLAN = "2008"
DATA_DIR = Path(__file__).parent.parent / "data"
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


def _load_manifest(carrera: str) -> dict[str, Any]:
    path = DATA_DIR / f"{carrera}.toml"
    if not path.exists():
        raise typer.BadParameter(f"No existe manifest para carrera '{carrera}': {path}")
    with path.open("rb") as f:
        return tomllib.load(f)


def _expected_repo_names(manifest: dict[str, Any], plan: str) -> list[str]:
    carrera = manifest["carrera"]["codigo"]
    materias = manifest["planes"][plan]["materias"]
    return [f"{carrera}-{plan}-{slug}" for slug in materias]


manifest_app = typer.Typer(add_completion=False, no_args_is_help=True, help="Operaciones sobre el manifest TOML.")
app.add_typer(manifest_app, name="manifest")


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


@manifest_app.command("list")
def manifest_list(
    carrera: Annotated[str, typer.Argument(help="Código de carrera (ej. isi)")] = "isi",
    plan: Annotated[str, typer.Option(help="Plan a listar")] = DEFAULT_PLAN,
) -> None:
    """Lista las materias declaradas en data/<carrera>.toml para un plan."""
    manifest = _load_manifest(carrera)
    if plan not in manifest["planes"]:
        raise typer.BadParameter(
            f"Plan '{plan}' no existe. Disponibles: {sorted(manifest['planes'])}"
        )
    table = Table(title=f"{manifest['carrera']['nombre']} — Plan {plan}")
    table.add_column("#", justify="right")
    table.add_column("Repo esperado", style="cyan")
    table.add_column("Nivel", justify="right")
    table.add_column("Hs/sem", justify="right")
    table.add_column("Bloque")
    table.add_column("Área")

    materias = manifest["planes"][plan]["materias"]
    rows = sorted(materias.items(), key=lambda kv: kv[1]["orden"])
    for slug, m in rows:
        table.add_row(
            str(m["orden"]),
            f"{carrera}-{plan}-{slug}",
            str(m["nivel"]),
            str(m.get("hs-semanales", "-")),
            m.get("bloque", "-"),
            m.get("area", "-"),
        )
    console.print(table)


@manifest_app.command("validate")
def manifest_validate(
    carrera: Annotated[str, typer.Argument()] = "isi",
) -> None:
    """Verifica que el DAG de correlativas referencia solo slugs existentes."""
    manifest = _load_manifest(carrera)
    errors: list[str] = []

    for plan, plan_data in manifest["planes"].items():
        materias = plan_data.get("materias", {})
        slugs = set(materias)
        for slug, m in materias.items():
            for key in ("correlativas-cursar-cursadas", "correlativas-cursar-aprobadas", "correlativas-rendir-aprobadas"):
                for ref in m.get(key, []):
                    if ref not in slugs:
                        errors.append(f"plan {plan} · {slug}.{key} → '{ref}' no existe")

    if errors:
        for e in errors:
            console.print(f"[red]✗ {e}[/]")
        raise typer.Exit(1)
    console.print("[green]✓ Manifest válido.[/]")


@manifest_app.command("diff")
def manifest_diff(
    carrera: Annotated[str, typer.Argument()] = "isi",
    plan: Annotated[str, typer.Option(help="Plan a comparar")] = DEFAULT_PLAN,
) -> None:
    """Diff entre repos esperados (manifest) y los presentes en la org."""
    manifest = _load_manifest(carrera)
    expected = set(_expected_repo_names(manifest, plan))

    org = _client().get_organization(ORG_NAME)
    actual: set[str] = set()
    for repo in org.get_repos():
        if repo.archived:
            continue
        cls = _classify(repo.name)
        if cls is None:
            continue
        c, p, slug = cls
        if c != carrera:
            continue
        # Reescribimos legacy como si ya estuviera renombrado al plan default.
        actual.add(f"{c}-{p}-{slug}" if NEW_RE.match(repo.name) else f"{c}-{plan}-{slug}")

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    if missing:
        console.print("[yellow]Faltantes (en manifest, no en org):[/]")
        for r in missing:
            console.print(f"  • {r}")
    if extra:
        console.print("[yellow]Sobrantes (en org, no en manifest):[/]")
        for r in extra:
            console.print(f"  • {r}")
    if not missing and not extra:
        console.print("[green]✓ Org y manifest coinciden.[/]")


def _carrera_repos_by_name(org, carrera: str, plan: str) -> dict[str, Repository]:
    """Repos de la carrera presentes en la org, indexados por nombre normalizado."""
    repos: dict[str, Repository] = {}
    for repo in org.get_repos():
        if repo.archived:
            continue
        cls = _classify(repo.name)
        if cls is None:
            continue
        c, p, slug = cls
        if c != carrera:
            continue
        norm = f"{c}-{p}-{slug}" if NEW_RE.match(repo.name) else f"{c}-{plan}-{slug}"
        repos[norm] = repo
    return repos


@manifest_app.command("sync")
def manifest_sync(
    carrera: Annotated[str, typer.Argument()] = "isi",
    plan: Annotated[str, typer.Option(help="Plan a sincronizar")] = DEFAULT_PLAN,
    private: Annotated[bool, typer.Option(help="Crear los repos nuevos como privados")] = False,
    archive: Annotated[bool, typer.Option("--archive", help="Archivar repos sobrantes (en vez de solo reportarlos)")] = False,
    apply: Annotated[bool, typer.Option("--apply", help="Aplica los cambios")] = False,
) -> None:
    """Sincroniza la org con el manifest: crea faltantes, actualiza descripciones
    y reporta (o archiva) repos que ya no están en el manifest.

    El manifest data/<carrera>.toml es la única fuente de verdad. Dry-run por
    defecto; agregá --apply para ejecutar.
    """
    manifest = _load_manifest(carrera)
    if plan not in manifest["planes"]:
        raise typer.BadParameter(
            f"Plan '{plan}' no existe. Disponibles: {sorted(manifest['planes'])}"
        )
    materias = manifest["planes"][plan]["materias"]
    expected = {f"{carrera}-{plan}-{slug}": m["nombre"] for slug, m in materias.items()}

    org = _client().get_organization(ORG_NAME)
    existing = _carrera_repos_by_name(org, carrera, plan)

    missing = sorted(name for name in expected if name not in existing)
    drift = sorted(
        name for name, repo in existing.items()
        if name in expected and (repo.description or "") != expected[name]
    )
    extra = sorted(name for name in existing if name not in expected)

    if missing:
        console.print("[green]Crear (en manifest, no en org):[/]")
        for name in missing:
            console.print(f"  + {name} — [dim]{expected[name]}[/]")
    if drift:
        console.print("[cyan]Actualizar descripción:[/]")
        for name in drift:
            console.print(f"  ~ {name} → [dim]{expected[name]}[/]")
    if extra:
        verb = "Archivar" if archive else "Sobrantes (no en manifest)"
        console.print(f"[yellow]{verb}:[/]")
        for name in extra:
            console.print(f"  - {existing[name].name}")

    if not (missing or drift or (extra and archive)):
        console.print("[green]✓ Org y manifest coinciden.[/]")
        return

    if not apply:
        console.print(
            f"[yellow]DRY-RUN: {len(missing)} a crear, {len(drift)} a actualizar"
            + (f", {len(extra)} a archivar" if archive else "")
            + ". Repetí con --apply para ejecutar.[/]"
        )
        return

    for name in missing:
        org.create_repo(name, description=expected[name], private=private, auto_init=True)
        console.print(f"[green]✓ creado {name}[/]")
    for name in drift:
        existing[name].edit(description=expected[name])
        console.print(f"[cyan]✓ descripción actualizada {name}[/]")
    if archive:
        for name in extra:
            existing[name].edit(archived=True)
            console.print(f"[yellow]✓ archivado {existing[name].name}[/]")


if __name__ == "__main__":
    try:
        app()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Subproceso falló: {e}[/]")
        sys.exit(e.returncode)
