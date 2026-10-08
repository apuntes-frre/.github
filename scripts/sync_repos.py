#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "PyGithub>=2.1.0",
#   "jinja2>=3.0.0",
#   "rich>=13.0.0",
#   "typer>=0.12.0",
# ]
# ///

"""Audita y sincroniza repos de materia desde el manifest curricular.

`inspect` y `manifest list/validate/diff` solo leen. `manifest sync`, `readmes`,
`contributing` y `gitignore` muestran cambios pendientes; `--apply` los publica.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated, Any

import typer  # ty: ignore
from github import Auth, Github, GithubException  # ty: ignore
from github.Repository import Repository  # ty: ignore
from jinja2 import Template  # ty: ignore
from rich.console import Console  # ty: ignore
from rich.table import Table  # ty: ignore

if __package__:
    from .common import (
        DEFAULT_PLAN, ORG_NAME, ROOT, get_plan, load_manifest,
        load_manifests, parse_repo_name, template_environment,
    )
else:
    from common import (
        DEFAULT_PLAN, ORG_NAME, ROOT, get_plan, load_manifest,
        load_manifests, parse_repo_name, template_environment,
    )

console = Console()
app = typer.Typer(add_completion=False, no_args_is_help=True)


def _client() -> Github:
    token = os.getenv("ORG_ADMIN_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Falta ORG_ADMIN_TOKEN o GITHUB_TOKEN")
    return Github(auth=Auth.Token(token))


def _load_manifest(carrera: str) -> dict[str, Any]:
    try:
        return load_manifest(carrera)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _plan_data(manifest: dict[str, Any], plan: str) -> dict[str, Any]:
    try:
        data = get_plan(manifest, plan)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if data.get("correlativas-estado") == "pendientes":
        console.print(f"[yellow]⚠ Plan {plan}: correlativas pendientes de definición FRRE.[/]")
    return data


def _expected_repo_names(manifest: dict[str, Any], plan: str) -> list[str]:
    carrera = manifest["carrera"]["codigo"]
    materias = _plan_data(manifest, plan)["materias"]
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

    for repo in sorted(org.get_repos(), key=lambda repo: repo.name):
        parsed = parse_repo_name(repo.name)
        if parsed is None:
            table.add_row(repo.name, "-", "-", "-", "[dim]ignorado[/]")
            continue
        carrera, plan, slug = parsed
        table.add_row(repo.name, carrera, plan, slug, "[green]actual[/]")
    console.print(table)


@manifest_app.command("list")
def manifest_list(
    carrera: Annotated[str, typer.Argument(help="Código de carrera (ej. isi)")] = "isi",
    plan: Annotated[str, typer.Option(help="Plan a listar")] = DEFAULT_PLAN,
) -> None:
    """Lista las materias declaradas en data/<carrera>.toml para un plan."""
    manifest = _load_manifest(carrera)
    table = Table(title=f"{manifest['carrera']['nombre']} — Plan {plan}")
    table.add_column("#", justify="right")
    table.add_column("Repo esperado", style="cyan")
    table.add_column("Nivel", justify="right")
    table.add_column("Hs/sem", justify="right")
    table.add_column("Bloque")
    table.add_column("Área")

    materias = _plan_data(manifest, plan)["materias"]
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
    """Valida tipos, orden, referencias y ciclos de todos los planes."""
    manifest = _load_manifest(carrera)
    for plan in manifest["planes"]:
        _plan_data(manifest, plan)
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
    repos = _carrera_repos_by_name(org, carrera, plan)
    actual = set(repos)
    subjects = manifest["planes"][plan]["materias"]
    descriptions = {f"{carrera}-{plan}-{slug}": subject["nombre"] for slug, subject in subjects.items()}
    drift = sorted(name for name in expected & actual if (repos[name].description or "") != descriptions[name])

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
    if drift:
        console.print("[cyan]Descripciones diferentes del manifest:[/]")
        for name in drift:
            console.print(f"  ~ {name} → {descriptions[name]}")
    if missing or extra or drift:
        raise typer.Exit(1)
    console.print("[green]✓ Org y manifest coinciden.[/]")


def _carrera_repos_by_name(org, carrera: str, plan: str) -> dict[str, Repository]:
    """Repos activos de la carrera y el plan seleccionados."""
    return {
        repo.name: repo
        for repo in org.get_repos()
        if not repo.archived
        and (parsed := parse_repo_name(repo.name)) is not None
        and parsed[:2] == (carrera, plan)
    }


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
    materias = _plan_data(manifest, plan)["materias"]
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

    if not (missing or drift or extra):
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


def _render_subject_readme(
    manifest: dict[str, Any], plan: str, slug: str, template: Template
) -> str:
    """Renderiza el README de una materia desde el manifest."""
    materia = manifest["planes"][plan]["materias"][slug]
    names = {s: m["nombre"] for s, m in manifest["planes"][plan]["materias"].items()}
    resolve = lambda keys: [names[s] for s in keys]  # noqa: E731

    return template.render(
        prerequisites_pending=manifest["planes"][plan].get("correlativas-estado") == "pendientes",
        carrera=manifest["carrera"]["codigo"],
        carrera_nombre=manifest["carrera"]["nombre"],
        plan=plan,
        nombre=materia["nombre"],
        nivel=materia["nivel"],
        area=materia.get("area", "—"),
        bloque=materia.get("bloque", "—"),
        hs=materia.get("hs-semanales", "—"),
        integradora=materia.get("integradora", False),
        cursar_cursadas=resolve(materia.get("correlativas-cursar-cursadas", [])),
        cursar_aprobadas=resolve(materia.get("correlativas-cursar-aprobadas", [])),
        rendir_aprobadas=resolve(materia.get("correlativas-rendir-aprobadas", [])),
        rendir_todas=materia.get("correlativas-rendir-todas", False),
    )


@app.command()
def readmes(
    carrera: Annotated[str, typer.Argument()] = "isi",
    plan: Annotated[str, typer.Option(help="Plan a publicar")] = DEFAULT_PLAN,
    apply: Annotated[bool, typer.Option("--apply", help="Publica los READMEs")] = False,
) -> None:
    """Genera el README de cada repo de materia desde el manifest y lo publica.

    Idempotente: solo escribe en los repos donde el contenido difiere. El manifest
    es la única fuente de verdad; cualquier edición manual del README se sobrescribe.
    """
    manifest = _load_manifest(carrera)
    materias = _plan_data(manifest, plan)["materias"]

    org = _client().get_organization(ORG_NAME)
    repos = _carrera_repos_by_name(org, carrera, plan)

    template = template_environment().get_template("subject_readme.md.j2")
    changed = 0
    for slug in materias:
        name = f"{carrera}-{plan}-{slug}"
        repo = repos.get(name)
        if repo is None:
            console.print(f"[yellow]⚠ {name}: repo ausente, omitido[/]")
            continue

        rendered = _render_subject_readme(manifest, plan, slug, template)
        changed += _publish_file(repo, "README.md", rendered, "docs: sincronizar README desde manifest", apply)

    if not changed:
        console.print("[green]✓ Todos los READMEs ya están sincronizados.[/]")
    elif not apply:
        console.print(
            f"[yellow]DRY-RUN: {changed} README(s) a actualizar. "
            f"Repetí con --apply para publicarlos.[/]"
        )
    else:
        console.print(f"[green]✓ {changed} README(s) publicados.[/]")


def _publish_file(repo: Repository, path: str, content: str, message: str, apply: bool) -> bool:
    """Compara un archivo y lo publica solo si difiere; solo 404 significa ausencia."""
    try:
        current = repo.get_contents(path)
    except GithubException as exc:
        if exc.status != 404:
            raise
        current = None
    if current is not None and current.decoded_content.decode("utf-8") == content:
        return False
    console.print(f"  ~ {repo.name}/{path}")
    if apply:
        if current is None:
            repo.create_file(path, message, content)
        else:
            repo.update_file(path, message, content, current.sha)
    return True


def _publish_shared_file(source: Path, path: str, message: str, apply: bool) -> None:
    content = source.read_text(encoding="utf-8")
    manifests = load_manifests()
    org = _client().get_organization(ORG_NAME)
    changed = 0
    for repo in sorted(org.get_repos(), key=lambda repo: repo.name):
        parsed = parse_repo_name(repo.name)
        if repo.archived or parsed is None:
            continue
        career, plan, slug = parsed
        manifest = manifests.get(career)
        if manifest is None or plan not in manifest["planes"] or slug not in manifest["planes"][plan]["materias"]:
            continue
        changed += _publish_file(repo, path, content, message, apply)
    if not changed:
        console.print(f"[green]✓ {path} ya está sincronizado en todos los repos.[/]")
    elif not apply:
        console.print(f"[yellow]DRY-RUN: {changed} repo(s) a actualizar. Repetí con --apply para publicar {path}.[/]")
    else:
        console.print(f"[green]✓ {path} publicado en {changed} repo(s).[/]")


@app.command()
def contributing(
    apply: Annotated[bool, typer.Option("--apply", help="Publica el CONTRIBUTING.md")] = False,
) -> None:
    """Publica CONTRIBUTING.md en los repos de materia declarados en el manifest."""
    _publish_shared_file(ROOT / "CONTRIBUTING.md", "CONTRIBUTING.md", "docs: sincronizar CONTRIBUTING", apply)


@app.command()
def gitignore(
    apply: Annotated[bool, typer.Option("--apply", help="Publica el .gitignore")] = False,
) -> None:
    """Publica templates/subject.gitignore en los repos declarados en el manifest."""
    _publish_shared_file(ROOT / "templates" / "subject.gitignore", ".gitignore", "chore: sincronizar .gitignore", apply)


if __name__ == "__main__":
    try:
        app()
    except (GithubException, OSError, ValueError) as exc:
        console.print(f"✗ {exc}", markup=False)
        sys.exit(1)
