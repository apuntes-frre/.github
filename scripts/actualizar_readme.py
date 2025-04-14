#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "PyGithub>=2.1.0",
#   "jinja2>=3.0.0"
# ]
# ///

"""
Script para actualizar automáticamente el README del perfil de la organización
utilizando información de los repositorios y una plantilla Jinja2.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

from github import Github
from github.Organization import Organization
from jinja2 import Environment, FileSystemLoader


def obtener_info_repos() -> Dict[str, Any]:
    """Obtiene información de todos los repositorios de la organización."""
    g = Github(os.getenv("GITHUB_TOKEN"))
    org: Organization = g.get_organization("apuntes-frre")

    materias: List[Dict[str, str]] = []
    años: Set[str] = set()
    materias_por_año: Dict[str, List[Dict[str, Any]]] = {}
    actualizaciones_recientes: List[Dict[str, str]] = []

    for repo in org.get_repos():
        if not repo.name.startswith("isi-"):
            continue

        # Información básica del repositorio
        materia_name = (
            repo.name[4:].replace("-", " ").title()
        )  # Remover 'isi-' y formatear
        info_materia = {
            "name": materia_name,
            "code": repo.name,  # Usar el nombre completo como código
            "repo_url": repo.html_url,
            "description": repo.description or "",
            "last_update": repo.updated_at.strftime("%Y-%m-%d"),
        }
        materias.append(info_materia)

        # Procesar años disponibles
        try:
            contents = repo.get_contents("notes")
            for content in contents:
                if content.type == "dir" and content.name.isdigit():
                    año = content.name
                    años.add(año)
                    if año not in materias_por_año:
                        materias_por_año[año] = []

                    # Obtener temas del año
                    temas: List[str] = []
                    try:
                        contenido_año = repo.get_contents(f"notes/{año}")
                        temas = [
                            c.name
                            for c in contenido_año
                            if c.type == "dir" and not c.name == "recursos"
                        ]
                    except Exception as e:
                        print(f"Error al obtener temas del año {año}: {e}")

                    materias_por_año[año].append({
                        "code": info_materia["code"],
                        "year_url": f"{repo.html_url}/tree/main/notes/{año}",
                        "latest_topics": temas[:3],  # Solo los primeros 3 temas
                    })
        except Exception as e:
            print(f"Error al procesar el repositorio {repo.name}: {e}")
            continue

        # Obtener actualizaciones recientes
        for commit in repo.get_commits(since=datetime.now().replace(day=1))[:3]:
            actualizaciones_recientes.append({
                "date": commit.commit.author.date.strftime("%Y-%m-%d"),
                "subject": info_materia["code"],
                "description": commit.commit.message.split("\n")[0],
            })

    # Obtener recursos comunes
    recursos_comunes: List[Dict[str, str]] = []
    try:
        common_repo = org.get_repo("apuntes-frre")
        if common_repo:
            contents = common_repo.get_contents("resources/common")
            recursos_comunes = [
                {
                    "name": c.name,
                    "url": c.html_url,
                    "description": "Recurso compartido entre materias",
                }
                for c in contents
                if c.type == "file"
            ]
    except Exception as e:
        print(f"Error al obtener recursos comunes: {e}")

    return {
        "subjects": sorted(materias, key=lambda x: x["code"]),
        "years": sorted(años, reverse=True),
        "year_subjects": materias_por_año,
        "recent_updates": sorted(
            actualizaciones_recientes, key=lambda x: x["date"], reverse=True
        )[:10],
        "active_subjects": len(materias),
        "current_year": datetime.now().year,
        "current_date": datetime.now().strftime("%Y-%m-%d"),
        "common_resources": recursos_comunes,
        "progress_chart": generar_grafico_progreso(materias),
    }


def generar_grafico_progreso(materias: List[Dict[str, str]]) -> str:
    """Genera una representación visual del progreso."""
    total = len(materias)
    actualizadas = sum(
        1
        for m in materias
        if datetime.strptime(m["last_update"], "%Y-%m-%d").month == datetime.now().month
    )
    porcentaje = (actualizadas / total) * 100 if total > 0 else 0
    bloques = int(porcentaje / 10)
    return "█" * bloques + "░" * (10 - bloques) + f" {porcentaje:.1f}%"


def main() -> None:
    # Configurar Jinja2
    env = Environment(loader=FileSystemLoader(Path(__file__).parent.parent / "profile"))
    template = env.get_template("README.md.jinja2")

    # Obtener datos
    datos = obtener_info_repos()

    # Generar README
    contenido_readme = template.render(**datos)

    # Guardar README
    readme_path = Path(__file__).parent.parent / "profile" / "README.md"
    readme_path.write_text(contenido_readme, encoding="utf-8")


if __name__ == "__main__":
    main()
