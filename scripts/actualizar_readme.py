#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "PyGithub>=2.1.0",
#   "jinja2>=3.0.0",
#   "python-dotenv>=1.0.0",
#   "rich>=13.0.0"
# ]
# ///

"""
Script para actualizar automáticamente el README del perfil de la organización y mantener
la estructura de los repositorios de apuntes.
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, TypeAlias

from github import Github, Repository
from github.Organization import Organization
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.progress import track

# Definición de tipos específicos
RepoInfo: TypeAlias = dict[str, str]
YearSubjects: TypeAlias = dict[str, list[dict[str, Any]]]
UpdateInfo: TypeAlias = dict[str, str]
CommonResource: TypeAlias = dict[str, str]

console = Console()


def load_github_token() -> str:
    """Carga el token de GitHub desde las variables de entorno de GitHub Actions."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError(
            "No se encontró el token de GitHub (GITHUB_TOKEN) en las variables de entorno"
        )
    return token


def init_repo_structure(repo: Repository) -> None:
    """Inicializa la estructura base de un repositorio."""
    current_year = str(datetime.now().year)

    # Clonar o actualizar el repositorio localmente
    repo_path = Path.home() / "_Repos" / repo.name
    if not repo_path.exists():
        subprocess.run(["git", "clone", repo.clone_url, str(repo_path)], check=True)

    # Crear estructura de directorios
    dirs_to_create = (
        [
            f"notes/{current_year}/{tipo}/{subtipo}"
            for tipo in ["teoria", "practica"]
            for subtipo in ["tema1", "tema2", "recursos"]
        ]
        + [
            f"{category}/{current_year}/{tipo}"
            for category in ["examples", "study-guides"]
            for tipo in ["teoria", "practica"]
        ]
        + [
            f"resources/{subfolder}/{tipo}"
            for subfolder in ["common", current_year]
            for tipo in ["teoria", "practica"]
        ]
    )

    for dir_path in dirs_to_create:
        (repo_path / dir_path).mkdir(parents=True, exist_ok=True)
        (repo_path / dir_path / ".gitkeep").touch()

    # Actualizar README si no existe
    readme_path = repo_path / "README.md"
    if not readme_path.exists():
        materia_name = repo.name[4:].replace("-", " ").title()
        create_readme(readme_path, materia_name, repo.description or "")

    # Commit y push de los cambios
    if has_changes(repo_path):
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "chore: actualizar estructura del repositorio"],
            cwd=repo_path,
            check=True,
        )
        subprocess.run(["git", "push"], cwd=repo_path, check=True)


def create_readme(path: Path, name: str, description: str) -> None:
    """Crea el README.md base para un repositorio."""
    current_year = datetime.now().year
    template = """# 📚 {name}

## 📝 Descripción
{description}

## 📂 Estructura del Repositorio

- 📁 **notes/**: Apuntes de clase organizados por año
  - 📚 **teoria/**: Contenido teórico por temas
  - 💻 **practica/**: Ejercicios y trabajos prácticos
- 📁 **examples/**: Ejemplos prácticos y código
  - 📚 **teoria/**: Ejemplos de conceptos teóricos
  - 💻 **practica/**: Ejemplos de implementación práctica
- 📖 **study-guides/**: Guías de estudio y material de práctica
  - 📚 **teoria/**: Guías de estudio teóricas
  - 💻 **practica/**: Guías de ejercicios prácticos
- 📁 **resources/**: Recursos adicionales y material de referencia
  - 📚 **teoria/**: Recursos para contenido teórico
  - 💻 **practica/**: Recursos para trabajos prácticos

## 🗓️ Contenido Actual ({year})

### 📚 Temas Teóricos
- [Por definir]

### 💻 Temas Prácticos
- [Por definir]

### 📖 Guías de Estudio
- [Por agregar]

### 💻 Ejemplos
- [Por agregar]

## 🤝 Contribuir
¡Las contribuciones son bienvenidas! Por favor, lee nuestras guías de contribución.

## 📜 Licencia
Este repositorio está bajo la Licencia MIT.
"""
    path.write_text(
        template.format(name=name, description=description, year=current_year),
        encoding="utf-8",
    )


def has_changes(repo_path: Path) -> bool:
    """Verifica si hay cambios en el repositorio."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(result.stdout.strip())


def obtener_info_repos() -> dict[str, Any]:
    """Obtiene información de todos los repositorios de la organización."""
    g = Github(os.getenv("GITHUB_TOKEN"))
    org: Organization = g.get_organization("apuntes-frre")

    materias: list[dict[str, str]] = []
    años: set[str] = set()
    materias_por_año: dict[str, list[dict[str, Any]]] = {}
    actualizaciones_recientes: list[dict[str, str]] = []

    for repo in org.get_repos():
        if not repo.name.startswith("isi-"):
            continue

        # Información básica del repositorio
        materia_name = repo.name[4:].replace("-", " ").title()
        info_materia = {
            "name": materia_name,
            "code": repo.name,
            "repo_url": repo.html_url,
            "description": repo.description or "",
            "last_update": repo.updated_at.strftime("%Y-%m-%d"),
        }
        materias.append(info_materia)

        # Procesar años disponibles
        try:
            contents = repo.get_contents("notes")
            for content in contents:
                match content:
                    case _ if content.type == "dir" and content.name.isdigit():
                        año = content.name
                        años.add(año)
                        if año not in materias_por_año:
                            materias_por_año[año] = []

                        try:
                            contenido_año = repo.get_contents(f"notes/{año}")
                            temas = []
                            for item in contenido_año:
                                match item:
                                    case _ if (
                                        item.type == "dir" and item.name != "recursos"
                                    ):
                                        temas.append(item.name)
                                    case _:
                                        continue

                            materias_por_año[año].append({
                                "code": info_materia["code"],
                                "year_url": f"{repo.html_url}/tree/main/notes/{año}",
                                "latest_topics": temas[:3] if len(temas) > 3 else temas,
                            })
                        except Exception as e:
                            print(f"Error al obtener temas del año {año}: {e}")
                    case _:
                        continue
        except Exception as e:
            print(f"Error al procesar el repositorio {repo.name}: {e}")
            continue

        # Obtener actualizaciones recientes
        # Obtener los últimos 3 commits
        recent_commits = list(repo.get_commits()[:3])
        if recent_commits:
            for commit in recent_commits:
            actualizaciones_recientes.append({
                "date": commit.commit.author.date.strftime("%Y-%m-%d"),
                "subject": info_materia["code"],
                "description": commit.commit.message.split("\n")[0],
            })
        else:
            console.print(
            f"No hay commits para {info_materia['code']}."
            )
            console.print("Por favor, verifica el repositorio para más detalles.")
    # Obtener recursos comunes
    recursos_comunes: list[dict[str, str]] = []
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


def generar_grafico_progreso(materias: list[dict[str, str]]) -> str:
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
    try:
        # Configurar GitHub
        token = load_github_token()
        g = Github(token)
        org: Organization = g.get_organization("apuntes-frre")

        console.print("[bold green]🚀 Iniciando actualización de repositorios...[/]")

        # Inicializar estructura en cada repositorio
        repos = list(org.get_repos())
        for repo in track(repos, description="Inicializando repositorios"):
            if repo.name.startswith("isi-"):
                try:
                    init_repo_structure(repo)
                    console.print(f"✅ Repositorio {repo.name} actualizado")
                except Exception as e:
                    console.print(
                        f"❌ Error en {repo.name}: {str(e)}", style="bold red"
                    )

        # Obtener datos y actualizar README
        console.print("\n[bold blue]📝 Actualizando README principal...[/]")
        datos = obtener_info_repos()

        # Configurar Jinja2 y generar README
        env = Environment(
            loader=FileSystemLoader(Path(__file__).parent.parent / "profile")
        )
        template = env.get_template("README.md.jinja2")
        contenido_readme = template.render(**datos)

        # Guardar README
        readme_path = Path(__file__).parent.parent / "profile" / "README.md"
        readme_path.write_text(contenido_readme, encoding="utf-8")
        console.print("[bold green]✅ README actualizado exitosamente![/]")

    except Exception as e:
        console.print(f"[bold red]❌ Error: {str(e)}[/]")
        raise


if __name__ == "__main__":
    main()
