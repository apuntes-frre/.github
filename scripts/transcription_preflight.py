# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Comprueba herramientas y materializa fuentes seleccionadas sin alterar originales."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ENGINES = {
    "pandoc": [["pandoc", "--version"]],
    "markitdown": [["markitdown", "--help"]],
    "pymupdf4llm": [["pymupdf4llm", "--help"]],
    "docling": [["docling", "convert", "--help"]],
    "ocr": [["ocrmypdf", "--version"], ["pymupdf4llm", "--help"]],
    "libreoffice": [["soffice", "--version"], ["pandoc", "--version"]],
}


def materialize(source: Path, destination: Path) -> dict:
    digest = hashlib.sha256()
    with source.open("rb") as original, destination.open("xb") as output:
        for chunk in iter(lambda: original.read(1024 * 1024), b""):
            digest.update(chunk)
            output.write(chunk)
    if not destination.stat().st_size:
        raise ValueError(f"Fuente vacía: {source}")
    with destination.open("rb") as copied:
        copied_hash = hashlib.file_digest(copied, "sha256").hexdigest()
    if copied_hash != digest.hexdigest():
        raise ValueError(f"La copia no coincide: {source}")
    record = {"source": str(source), "copy": str(destination), "sha256": copied_hash,
              "bytes": destination.stat().st_size, "pages": None, "review": "pendiente"}
    if destination.suffix.lower() == ".pdf":
        info = subprocess.check_output(["pdfinfo", str(destination)], text=True)
        match = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
        if not match:
            raise ValueError(f"pdfinfo no informó páginas: {source}")
        record["pages"] = int(match[1])
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--work-dir", required=True, type=Path, help="Directorio NUEVO fuera del repo")
    parser.add_argument("--engine", choices=ENGINES, required=True)
    parser.add_argument("--language", default="spa")
    parser.add_argument("--download-models", action="store_true", help="Descargar modelos estándar de Docling cuando se elige ese motor")
    args = parser.parse_args()
    tools = ENGINES[args.engine] + [["katex", "--version"], ["markdownlint-cli2", "--version"]]
    if any(p.suffix.lower() == ".pdf" for p in args.sources):
        tools += [["pdfinfo", "-v"], ["pdftotext", "-v"], ["pdftoppm", "-v"]]
    for command in tools:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if args.engine == "ocr":
        languages = subprocess.check_output(["tesseract", "--list-langs"], text=True)
        if args.language not in languages.splitlines():
            raise ValueError(f"No está instalado el idioma OCR {args.language}")
    if args.download_models:
        if args.engine != "docling":
            raise ValueError("--download-models requiere --engine docling")
        subprocess.run(["docling-tools", "models", "download"], check=True)
    args.work_dir.mkdir(parents=True, exist_ok=False)
    records = []
    for number, source in enumerate(args.sources, 1):
        source = source.expanduser().resolve(strict=True)
        records.append(materialize(source, args.work_dir / f"{number:02d}-{source.name}"))
    inventory = args.work_dir / "sources.json"
    inventory.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ {len(records)} fuente(s) legibles, copiadas y verificadas por SHA-256: {inventory}")
    print("Revisar versiones, páginas, figuras y ejercicios; la copia no prueba transcripción completa.")


if __name__ == "__main__":
    main()
