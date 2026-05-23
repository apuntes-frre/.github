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
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from github import Github  # ty: ignore
from github.Organization import Organization  # ty: ignore
from github.Repository import Repository  # ty: ignore
from jinja2 import Environment, FileSystemLoader  # ty: ignore
from rich.console import Console  # ty: ignore
from rich.progress import track  # ty: ignore

ORG_NAME = "apuntes-frre"
REPO_NAME_RE = re.compile(r"^(?P<carrera>[a-z]+)-(?P<plan>\d{4})-(?P<slug>[a-z0-9-]+)$")
LEGACY_RE = re.compile(r"^(?P<carrera>[a-z]+)-(?P<slug>[a-z0-9-]+)$")
DEFAULT_PLAN = "2008"

console = Console()


def load_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN no está definido en el entorno")
    return token


def parse_repo_name(name: str) -> tuple[str, str, str] | None:
    """Devuelve (carrera, plan, slug) o None si no es un repo de materia."""
    if m := REPO_NAME_RE.match(name):
        return m["carrera"], m["plan"], m["slug"]
    if m := LEGACY_RE.match(name):
        carrera, slug = m["carrera"], m["slug"]
        if carrera in {"isi", "lic", "tec"}:
            return carrera, DEFAULT_PLAN, slug
    return None


def humanize_slug(slug: str) -> str:
    return slug.replace("-", " ").title()


def list_year_topics(repo: Repository, year: str) -> list[str]:
    try:
        contenido = repo.get_contents(f"notes/{year}")
    except Exception:
        return []
    temas: list[str] = []
    for item in contenido:
        if item.type == "dir" and item.name not in {"recursos", "resources"}:
            temas.append(item.name)
    return sorted(temas)[:3]


def collect_org_state(org: Organization) -> dict[str, Any]:
    subjects_by_carrera: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    year_subjects: dict[str, list[dict[str, Any]]] = defaultdict(list)
    recent: list[dict[str, str]] = []
    carreras: set[str] = set()
    planes: set[str] = set()
    materias: list[dict[str, str]] = []

    repos = list(org.get_repos())
    for repo in track(repos, description="Inspeccionando repos"):
        if repo.archived:
            continue
        parsed = parse_repo_name(repo.name)
        if parsed is None:
            continue
        carrera, plan, slug = parsed
        carreras.add(carrera)
        planes.add(plan)

        info = {
            "code": repo.name,
            "name": humanize_slug(slug),
            "repo_url": repo.html_url,
            "description": (repo.description or "").strip(),
            "carrera": carrera,
            "plan": plan,
        }
        materias.append(info)
        subjects_by_carrera[carrera][plan].append(info)

        try:
            for content in repo.get_contents("notes"):
                if content.type == "dir" and content.name.isdigit():
                    año = content.name
                    year_subjects[año].append({
                        "code": repo.name,
                        "year_url": f"{repo.html_url}/tree/main/notes/{año}",
                        "latest_topics": list_year_topics(repo, año),
                    })
        except Exception:
            pass

        try:
            for commit in list(repo.get_commits()[:2]):
                msg = commit.commit.message.split("\n", 1)[0]
                if "[skip ci]" in msg or msg.startswith("docs: actualizar README"):
                    continue
                recent.append({
                    "date": commit.commit.author.date.strftime("%Y-%m-%d"),
                    "subject": repo.name,
                    "description": msg,
                })
        except Exception:
            pass

    return {
        "subjects_by_carrera": {
            c: dict(planes_dict) for c, planes_dict in subjects_by_carrera.items()
        },
        "years": sorted(year_subjects.keys(), reverse=True),
        "year_subjects": dict(year_subjects),
        "recent_updates": sorted(recent, key=lambda x: x["date"], reverse=True)[:10],
        "active_subjects": len(materias),
        "carreras": sorted(carreras),
        "planes": sorted(planes),
        "common_resources": [],
        "progress_chart": progress_bar(materias),
    }


def progress_bar(materias: list[dict[str, str]]) -> str:
    """Porcentaje de materias con commits del mes en curso."""
    if not materias:
        return "░░░░░░░░░░ 0.0%"
    now = datetime.now()
    actualizadas = sum(
        1
        for m in materias
        if (last := m.get("last_update"))
        and (d := _try_parse(last))
        and d.year == now.year
        and d.month == now.month
    )
    pct = actualizadas / len(materias) * 100
    blocks = int(pct / 10)
    return "█" * blocks + "░" * (10 - blocks) + f" {pct:.1f}%"


def _try_parse(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None


def render(data: dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent.parent / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    return env.get_template("profile_readme.md.j2").render(**data)


def main() -> int:
    g = Github(load_token())
    org = g.get_organization(ORG_NAME)

    console.print(f"[bold blue]📥 Recolectando estado de {ORG_NAME}…[/]")
    data = collect_org_state(org)

    rendered = render(data)
    target = Path(__file__).parent.parent / "profile" / "README.md"
    current = target.read_text(encoding="utf-8") if target.exists() else ""

    if rendered == current:
        console.print("[yellow]≡ README sin cambios. No se escribe.[/]")
        return 0

    target.write_text(rendered, encoding="utf-8")
    console.print(f"[bold green]✅ README actualizado: {target}[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
