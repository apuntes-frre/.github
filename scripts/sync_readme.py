#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "PyGithub>=2.1.0",
#   "jinja2>=3.0.0",
#   "rich>=13.0.0",
# ]
# ///

"""Regenera profile/README.md a partir del estado vivo de la organización.

El script es idempotente: vuelve a renderizar la plantilla en memoria, compara
con el archivo en disco y solo escribe (y por lo tanto, solo permite commit) si
hay diferencias reales de contenido. Esto evita los commits diarios vacíos que
se producían cuando la plantilla incluía la fecha actual.

Sincronización de READMEs
------------------------
repo-readme.yml regenera el perfil y el inventario en un solo commit.
Los archivos de los repos de materia se publican manualmente con --apply.

Token (solo para los que tocan la org): tu cuenta ya tiene acceso, así que

    export GITHUB_TOKEN="$(gh auth token)"

1. README del PERFIL de la org  ->  profile/README.md
   Fuente: estado vivo de la org (lista de repos). Requiere token.

       uv run scripts/sync_readme.py

2. README de CADA REPO DE MATERIA  ->  <repo>/README.md
   Fuente: data/<carrera>.toml. Requiere token con acceso de escritura a la org.
   Correrlo solo tras editar el manifest o templates/subject_readme.md.j2.

       uv run scripts/sync_repos.py readmes isi --plan 2008            # dry-run
       uv run scripts/sync_repos.py readmes isi --plan 2008 --apply    # publica

3. INVENTARIO del repo de control  ->  docs/README.md
   Fuente: el árbol local de este repo. No requiere token.

       uv run scripts/gen_repo_readme.py

4. CONTRIBUTING de cada repo de materia  ->  <repo>/CONTRIBUTING.md
   Fuente: CONTRIBUTING.md (raíz de este repo). Requiere token de escritura.
   Correrlo tras editar el CONTRIBUTING.md de la raíz.

       uv run scripts/sync_repos.py contributing            # dry-run
       uv run scripts/sync_repos.py contributing --apply    # publica

5. .gitignore de cada repo de materia  ->  <repo>/.gitignore
   Fuente: templates/subject.gitignore. Requiere token de escritura.

       uv run scripts/sync_repos.py gitignore            # dry-run
       uv run scripts/sync_repos.py gitignore --apply    # publica
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from github import Auth, Github, GithubException  # ty: ignore
from github.Organization import Organization  # ty: ignore
from github.Repository import Repository  # ty: ignore
from rich.console import Console  # ty: ignore
from rich.progress import track  # ty: ignore

if __package__:
    from .common import ORG_NAME, ROOT, load_manifests, parse_repo_name, template_environment
else:
    from common import ORG_NAME, ROOT, load_manifests, parse_repo_name, template_environment

# Mensajes de commit que no representan contenido de estudio.
SCAFFOLD_MARKERS = (
    "[skip ci]",
    "sincronizar README",
    "actualizar README",
    "README autogenerado desde manifest",
    "agregar CONTRIBUTING",
    "sincronizar CONTRIBUTING",
    "agregar .gitignore",
)
SCAFFOLD_PREFIXES = ("chore", "ci", "build")

console = Console()


def is_scaffold(msg: str) -> bool:
    """True si el commit es andamiaje (no contenido de estudio)."""
    if msg.strip() == "Initial commit":
        return True
    if any(m in msg for m in SCAFFOLD_MARKERS):
        return True
    prefix = msg.split(":", 1)[0].split("(", 1)[0].strip().lower()
    return prefix in SCAFFOLD_PREFIXES


def load_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN no está definido en el entorno")
    return token


def latest_year_topics(repo: Repository) -> list[str]:
    """Hasta tres nombres de notas reales del último año con contenido."""
    try:
        tree = repo.get_git_tree(repo.default_branch, recursive=True)
    except GithubException as exc:
        if exc.status == 409:  # Repositorio todavía vacío.
            return []
        raise
    if tree.truncated:
        raise ValueError(f"{repo.name}: árbol de archivos incompleto")
    notes: dict[str, list[str]] = defaultdict(list)
    for item in tree.tree:
        if item.type == "blob" and Path(item.path).stem.lower() != "readme" and (match := re.fullmatch(r"notes/(\d{4})/(.+)\.md", item.path)):
            notes[match[1]].append(item.path)
    if not notes:
        return []
    paths = sorted(notes[max(notes)])
    names = (Path(path).stem.replace("-", " ").replace("_", " ").capitalize() for path in paths)
    return list(dict.fromkeys(names))[:3]


def collect_org_state(org: Organization) -> dict[str, Any]:
    subjects_by_carrera: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    recent: list[dict[str, str]] = []
    carreras: set[str] = set()
    planes: set[str] = set()
    materias: list[dict[str, Any]] = []

    manifests = load_manifests()
    repos = sorted(org.get_repos(), key=lambda repo: repo.name)
    for repo in track(repos, description="Inspeccionando repos"):
        if repo.archived or repo.private:
            continue
        parsed = parse_repo_name(repo.name)
        if parsed is None:
            continue
        carrera, plan, slug = parsed
        manifest = manifests.get(carrera)
        if manifest is None or plan not in manifest["planes"] or slug not in manifest["planes"][plan]["materias"]:
            console.print(f"[yellow]⚠ {repo.name}: no está declarado en el manifest; omitido.[/]")
            continue
        carreras.add(carrera)
        planes.add(plan)

        info = {
            "code": repo.name,
            "display_name": manifest["planes"][plan]["materias"][slug]["nombre"],
            "repo_url": repo.html_url,
            "latest_topics": latest_year_topics(repo),
        }
        materias.append(info)
        subjects_by_carrera[carrera][plan].append(info)

        try:
            for commit in list(repo.get_commits()[:10]):
                msg = commit.commit.message.split("\n", 1)[0]
                if is_scaffold(msg):
                    continue
                recent.append({
                    "date": commit.commit.author.date.strftime("%Y-%m-%d"),
                    "timestamp": commit.commit.author.date.isoformat(),
                    "subject": repo.name,
                    "description": msg,
                })
                break  # solo el commit de contenido más reciente por repo
        except GithubException as exc:
            if exc.status != 409:
                raise

    recent_updates = sorted(recent, key=lambda x: (x["timestamp"], x["subject"]), reverse=True)[:5]
    # Idempotente: la fecha solo cambia cuando cambia el contenido real.
    last_updated = recent_updates[0]["date"] if recent_updates else "—"

    return {
        "subjects_by_carrera": {
            c: dict(planes_dict) for c, planes_dict in subjects_by_carrera.items()
        },
        "recent_updates": recent_updates,
        "active_subjects": len(materias),
        "carreras": sorted(carreras),
        "carrera_nombres": {c: manifests[c]["carrera"]["nombre"] for c in sorted(carreras)},
        "planes": sorted(planes),
        "last_updated": last_updated,
    }


def render(data: dict[str, Any]) -> str:
    return template_environment().get_template("profile_readme.md.j2").render(**data)


def main() -> int:
    g = Github(auth=Auth.Token(load_token()))
    org = g.get_organization(ORG_NAME)

    console.print(f"[bold blue]📥 Recolectando estado de {ORG_NAME}…[/]")
    data = collect_org_state(org)

    rendered = render(data)
    target = ROOT / "profile" / "README.md"
    current = target.read_text(encoding="utf-8") if target.exists() else ""

    if rendered == current:
        console.print("[yellow]≡ README sin cambios. No se escribe.[/]")
        return 0

    target.write_text(rendered, encoding="utf-8")
    console.print(f"[bold green]✅ README actualizado: {target}[/]")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (GithubException, OSError, ValueError) as exc:
        console.print(f"✗ {exc}", markup=False)
        sys.exit(1)
