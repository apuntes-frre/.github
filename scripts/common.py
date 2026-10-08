"""Manifest curricular, nombres de repos y plantillas compartidos."""

from __future__ import annotations

from graphlib import CycleError, TopologicalSorter
from pathlib import Path
import re
import tomllib
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parent.parent
ORG_NAME = "apuntes-frre"
DEFAULT_PLAN = "2008"
REPO_NAME_RE = re.compile(r"^([a-z]+)-(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
PREREQUISITE_KEYS = (
    "correlativas-cursar-cursadas",
    "correlativas-cursar-aprobadas",
    "correlativas-rendir-aprobadas",
)


def parse_repo_name(name: str) -> tuple[str, str, str] | None:
    match = REPO_NAME_RE.fullmatch(name)
    return match.groups() if match else None


def validate_manifest(manifest: dict[str, Any]) -> None:
    """Rechaza datos incompletos, referencias inválidas y ciclos."""
    career = manifest.get("carrera", {})
    if not isinstance(career, dict) or not re.fullmatch(
        r"[a-z]+", str(career.get("codigo", ""))
    ):
        raise ValueError("carrera.codigo debe ser un código en minúsculas")
    if not isinstance(career.get("nombre"), str) or not career["nombre"].strip():
        raise ValueError("carrera.nombre debe ser un texto no vacío")
    plans = manifest.get("planes")
    if not isinstance(plans, dict) or not plans:
        raise ValueError("planes debe contener al menos un plan")
    for plan, data in plans.items():
        if not re.fullmatch(r"\d{4}", plan) or not isinstance(data, dict):
            raise ValueError(f"Plan inválido: {plan}")
        subjects = data.get("materias")
        if not isinstance(subjects, dict) or not subjects:
            raise ValueError(
                f"Plan {plan}: materias debe contener al menos una materia"
            )
        if data.get("correlativas-estado", "completas") not in (
            "completas",
            "pendientes",
        ):
            raise ValueError(f"Plan {plan}: correlativas-estado inválido")
        orders: set[int] = set()
        graph: dict[str, set[str]] = {}
        for slug, subject in subjects.items():
            label = f"plan {plan} · {slug}"
            if parse_repo_name(
                f"{career['codigo']}-{plan}-{slug}"
            ) is None or not isinstance(subject, dict):
                raise ValueError(f"{label}: slug o materia inválidos")
            for field in ("nombre", "area", "bloque"):
                if (
                    not isinstance(subject.get(field), str)
                    or not subject[field].strip()
                ):
                    raise ValueError(f"{label}.{field}: debe ser un texto no vacío")
            for field in ("orden", "nivel", "hs-semanales", "hs-totales", "rtf"):
                if field not in subject and field in {"hs-totales", "rtf"}:
                    continue
                value = subject.get(field)
                if type(value) is not int or value <= 0:
                    raise ValueError(f"{label}.{field}: debe ser un entero positivo")
            if not 1 <= subject["nivel"] <= 5:
                raise ValueError(f"{label}.nivel: debe estar entre 1 y 5")
            if subject["orden"] in orders:
                raise ValueError(f"{label}.orden: duplicado ({subject['orden']})")
            orders.add(subject["orden"])
            for field in ("integradora", "correlativas-rendir-todas"):
                if field in subject and type(subject[field]) is not bool:
                    raise ValueError(f"{label}.{field}: debe ser booleano")
            refs: set[str] = set()
            for field in PREREQUISITE_KEYS:
                values = subject.get(field, [])
                if not isinstance(values, list) or any(
                    not isinstance(v, str) for v in values
                ):
                    raise ValueError(f"{label}.{field}: debe ser una lista de slugs")
                for ref in values:
                    if ref not in subjects:
                        raise ValueError(f"{label}.{field}: '{ref}' no existe")
                refs.update(values)
            graph[slug] = refs
        try:
            TopologicalSorter(graph).prepare()
        except CycleError as exc:
            raise ValueError(
                f"Plan {plan}: ciclo de correlativas: {' → '.join(exc.args[1])}"
            ) from exc


def load_manifest(career: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z]+", career):
        raise ValueError(f"Código de carrera inválido: {career}")
    path = ROOT / "data" / f"{career}.toml"
    if not path.exists():
        raise ValueError(f"No existe manifest para carrera '{career}': {path}")
    with path.open("rb") as source:
        manifest = tomllib.load(source)
    validate_manifest(manifest)
    if manifest["carrera"]["codigo"] != career:
        raise ValueError(
            f"{path.name}: carrera.codigo no coincide con el nombre del archivo"
        )
    return manifest


def load_manifests() -> dict[str, dict[str, Any]]:
    return {
        path.stem: load_manifest(path.stem)
        for path in sorted((ROOT / "data").glob("*.toml"))
    }


def get_plan(manifest: dict[str, Any], plan: str) -> dict[str, Any]:
    if plan not in manifest["planes"]:
        raise ValueError(
            f"Plan '{plan}' no existe. Disponibles: {sorted(manifest['planes'])}"
        )
    return manifest["planes"][plan]


def template_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
