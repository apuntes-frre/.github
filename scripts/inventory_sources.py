# /// script
# requires-python = ">=3.12"
# dependencies = ["jinja2>=3.0.0"]
# ///
"""Inventario de metadatos de OneDrive; no descarga masivamente ni afirma cobertura."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import unicodedata

from common import ROOT, load_manifests, parse_repo_name

DOCUMENTS = {".pdf", ".doc", ".docx", ".odt", ".rtf", ".ppt", ".pptx", ".xls", ".xlsx", ".ods", ".html", ".epub", ".txt", ".md"}
ASSETS = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".circ"}
EXAMPLES = {".sql", ".py", ".csv", ".c", ".cpp", ".java", ".zip", ".mwb", ".dm1"}
SOFTWARE_PARTS = {"programas", "packages", "node_modules", ".venv", "venv", "bin", "obj", ".vs", ".git", "__pycache__"}


def normalized(name: str) -> str:
    return unicodedata.normalize("NFC", name)


def inventory(folder: Path) -> dict:
    counts = Counter()
    files = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(folder)
        parts = [normalized(p).casefold() for p in relative.parts]
        if path.name == ".DS_Store" or path.name.startswith("._"):
            counts["system"] += 1
            continue
        if SOFTWARE_PARTS.intersection(parts[:-1]):
            counts["software_or_build"] += 1
            continue
        suffix = path.suffix.lower()
        category = "document" if suffix in DOCUMENTS else "asset" if suffix in ASSETS else "example_or_archive" if suffix in EXAMPLES else "other"
        counts[category] += 1
        if category == "other":
            continue
        name = normalized(str(relative))
        year = next((p for p in relative.parts if re.fullmatch(r"20\d{2}", p)), None)
        unit = re.search(r"(?:unidad|ut)[ _-]*([ivx]+|\d+)\b", name, re.IGNORECASE)
        practice = re.search(r"pr[aá]ctic|\btp\b|gu[ií]a|preguntas|cuestionario", name, re.IGNORECASE)
        stat = path.stat()
        files.append({"path": name, "category": category, "year_hint": year,
                      "unit_hint": unit.group(1).upper() if unit else None,
                      "practice_hint": bool(practice), "bytes_metadata": stat.st_size,
                      "cloud_only": bool(getattr(stat, "st_flags", 0) & 0x40000000),
                      "pages": None, "sha256": None, "review": "metadata-only; pendiente verificar materia y versión"})
    return {"counts": dict(counts), "files": files}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path.home() / "Library/CloudStorage/OneDrive-FacultadRegionalResistencia/Facultad/Materias ISI")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=ROOT.parent)
    args = parser.parse_args()
    mapping = json.loads((ROOT / "transcription/sources.json").read_text())
    manifests = load_manifests()
    folders = {normalized(p.name): p for p in args.source_root.iterdir() if p.is_dir()}
    subjects = {}
    used = set()
    for repo, folder_name in mapping["subjects"].items():
        career, plan, slug = parse_repo_name(repo)
        if slug not in manifests[career]["planes"][plan]["materias"]:
            raise ValueError(f"Mapeo sin materia declarada: {repo}")
        if folder_name is None:
            subjects[repo] = {"folder": None, "status": "pending-source-mapping"}
        elif folder_name not in folders:
            subjects[repo] = {"folder": folder_name, "status": "missing-source-folder"}
        else:
            used.add(folder_name)
            subjects[repo] = {"folder": folder_name, "status": "inventory-pending-content-review", **inventory(folders[folder_name])}
        clone = args.repo_root / repo
        origin = subprocess.run(["git", "-C", str(clone), "remote", "get-url", "origin"], text=True, capture_output=True)
        verified_clone = origin.returncode == 0 and re.search(rf"github\.com[:/]apuntes-frre/{re.escape(repo)}(?:\.git)?\s*$", origin.stdout) is not None
        subjects[repo]["local_clone_verified"] = verified_clone
        subjects[repo]["existing_notes"] = [str(p.relative_to(clone)) for p in sorted(clone.rglob("*.md")) if p.parts[len(clone.parts)] in {"notes", "study-guides"}] if verified_clone else []
    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "source_root": str(args.source_root),
              "scope": "Metadatos; nombres y existencia no prueban pertenencia, legibilidad ni transcripción completa.",
              "subjects": subjects, "unassigned_folders": sorted(set(folders) - used)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ {len(subjects)} materias inventariadas; {len(used)} carpetas vinculadas; {len(folders)-len(used)} sin asignar: {args.output}")


if __name__ == "__main__":
    main()
