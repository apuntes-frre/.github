# /// script
# requires-python = ">=3.12"
# dependencies = ["mdformat==1.0.0", "mdformat-gfm==1.0.0", "mdformat-myst==0.3.0"]
# ///
"""Valida Markdown modificado; la fidelidad se comprueba contra los originales."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

import mdformat
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

PARSER = MarkdownIt("commonmark").enable("table").use(dollarmath_plugin)
FORMAT_OPTIONS = {"wrap": 80, "compact_tables": True}
CONTENT_DIRS = {"notes", "resources", "study-guides"}
BAD_TEXT = re.compile(r"\ufffd|\(cid:\d+\)|[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd]")


def formatted(text: str) -> str:
    return mdformat.text(text, extensions={"gfm", "myst"}, options=FORMAT_OPTIONS)


def math_expressions(text: str) -> list[tuple[str, bool]]:
    expressions = []
    for token in PARSER.parse(text):
        if token.type.startswith("math_block"):
            expressions.append((token.content.strip(), True))
        for child in token.children or []:
            if child.type == "math_inline":
                expressions.append((child.content, False))
    return expressions


class HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value and (tag, key) in {("a", "href"), ("img", "src")}:
                self.links.append(value)


def links(text: str) -> list[str]:
    found = []
    for token in PARSER.parse(text):
        for child in token.children or []:
            if child.type in {"link_open", "image"}:
                found.append(child.attrGet("href" if child.type == "link_open" else "src"))
            elif child.type == "html_inline":
                html = HTMLLinks()
                html.feed(child.content)
                found.extend(html.links)
        if token.type == "html_block":
            html = HTMLLinks()
            html.feed(token.content)
            found.extend(html.links)
    return found


def anchors(text: str) -> set[str]:
    counts = {}
    result = set()
    tokens = PARSER.parse(text)
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        title = "".join(t.content for t in tokens[index + 1].children or [] if t.type != "html_inline")
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        number = counts.get(slug, 0)
        result.add(f"{slug}-{number}" if number else slug)
        counts[slug] = number + 1
    result.update(re.findall(r'\bid=["\']([^"\']+)["\']', text))
    return result


def local_target(root: Path, source: Path, url: str) -> Path | None:
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    return ((root / path.lstrip("/")) if path.startswith("/") else (source.parent / path)).resolve()


def link_errors(root: Path, source: Path, text: str) -> list[str]:
    errors = []
    for url in links(text):
        if url.startswith("data:"):
            errors.append("medio base64: extraerlo como archivo")
            continue
        target = local_target(root, source, url)
        if target is None:
            continue
        if not target.is_relative_to(root.resolve()) or not target.exists():
            errors.append(f"enlace local ausente o fuera del repo: {url}")
            continue
        fragment = unquote(urlsplit(url).fragment)
        if fragment and target.is_file() and target.suffix.lower() == ".md":
            if fragment not in anchors(target.read_text(encoding="utf-8")):
                errors.append(f"ancla local ausente: {url}")
    return errors


def check_text(root: Path, path: Path, text: str) -> list[str]:
    errors = link_errors(root, path, text)
    if not text.strip():
        errors.append("Markdown vacío")
    # Los ejemplos de código pueden documentar marcadores defectuosos literalmente.
    for token in PARSER.parse(text):
        if token.type == "inline":
            for child in token.children or []:
                if child.type in {"text", "math_inline"} and BAD_TEXT.search(child.content):
                    errors.append("carácter perdido, privado o marcador cid: revisar el original")
        elif token.type.startswith("math_block") or token.type == "html_block":
            if BAD_TEXT.search(token.content):
                errors.append("carácter perdido, privado o marcador cid: revisar el original")
    output = formatted(text)
    equations = math_expressions(text)
    if equations != math_expressions(output):
        errors.append("el formato altera LaTeX; no aplicar esa salida")
    if output != text:
        errors.append("formato pendiente: mdformat --extensions gfm --extensions myst --wrap 80 --compact-tables")
    # GitHub requiere delimitadores de bloque en líneas separadas.
    display_lines = sum(
        line.strip() == "$$"
        for token in PARSER.parse(text) if token.type != "fence"
        for line in token.content.splitlines()
    )
    if display_lines:
        errors.append("delimitador $$ sin bloque matemático reconocido")
    for expression, display in equations:
        command = ["katex"] + (["--display-mode"] if display else [])
        result = subprocess.run(command, input=expression, text=True, capture_output=True)
        if result.returncode:
            errors.append(f"LaTeX inválido: {expression}\n{result.stderr.strip()}")
    return errors


def git(root: Path, *args: str) -> list[str]:
    result = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return [p for p in result.stdout.decode().split("\0") if p]


def changed_paths(root: Path, base: str) -> tuple[list[Path], list[Path]]:
    changed = set(git(root, "diff", "--name-only", "--no-renames", "--diff-filter=ACMR", "-z", base, "--"))
    changed.update(git(root, "ls-files", "--others", "--exclude-standard", "-z"))
    removed = [root / p for p in git(root, "diff", "--name-only", "--no-renames", "--diff-filter=D", "-z", base, "--")]
    notes = [root / p for p in sorted(changed) if Path(p).parts[0] in CONTENT_DIRS and p.lower().endswith(".md")]
    return notes, removed


def removed_link_errors(root: Path, removed: list[Path], changed: list[Path]) -> list[str]:
    """Detecta referencias afectadas por borrar/renombrar medios, sin formatear notas antiguas."""
    errors = []
    removed_paths = {p.resolve() for p in removed}
    if not removed_paths:
        return errors
    for name in git(root, "ls-files", "-z"):
        path = root / name
        if path in changed or not path.is_file() or path.suffix.lower() != ".md":
            continue
        for url in links(path.read_text(encoding="utf-8")):
            target = local_target(root, path, url)
            if target in removed_paths and not target.exists():
                errors.append(f"{name}: medio/enlace eliminado aún referenciado: {url}")
    return errors


def self_test() -> None:
    fixture = r"""# Prueba

Negación: $F = \overline{A}B + A\overline{B}$; fracción: $\frac{a_1}{2^n}$.

$$
\begin{bmatrix}
a & b \\
c & d
\end{bmatrix}
$$

- [x] GFM

| A | B |
| -- | -- |
| 1 | 2 |
"""
    output = formatted(fixture)
    if math_expressions(output) != math_expressions(fixture) or formatted(output) != output:
        raise ValueError("El formatter instalado no preserva las ecuaciones/matrices")
    for expression, display in math_expressions(output):
        subprocess.run(["katex"] + (["--display-mode"] if display else []), input=expression,
                       text=True, check=True, stdout=subprocess.DEVNULL)
    print("✓ GFM + LaTeX: preservación, idempotencia y renderizado comprobados")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    if args.files:
        paths, removed = [p.resolve() for p in args.files], []
    else:
        paths, removed = changed_paths(root, args.base)
    errors = removed_link_errors(root, removed, paths)
    for path in paths:
        errors.extend(f"{path.relative_to(root)}: {error}" for error in check_text(root, path, path.read_text(encoding="utf-8")))
    if paths:
        config = Path(__file__).with_name("markdownlint.jsonc")
        if not config.exists():
            config = Path(__file__).resolve().parents[1] / "templates/transcription/markdownlint.jsonc"
        lint = subprocess.run(["markdownlint-cli2", "--config", str(config), *map(str, paths)])
        if lint.returncode:
            errors.append("markdownlint falló; ver líneas anteriores")
    for error in errors:
        print(f"✗ {error}")
    if not errors:
        print(f"✓ {len(paths)} archivo(s) Markdown modificados verificados; fidelidad documental requiere revisión de las fuentes")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
