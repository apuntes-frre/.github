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
import string
import subprocess
from urllib.parse import unquote, urlsplit

import mdformat
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.footnote import footnote_plugin

PARSER = MarkdownIt("commonmark").enable("table").use(dollarmath_plugin).use(footnote_plugin)
FORMAT_OPTIONS = {"wrap": 80, "compact_tables": True}
CONTENT_DIRS = {"notes", "resources", "study-guides"}
BAD_TEXT = re.compile(r"\ufffd|\(cid:\d+\)|[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd]")
MARKDOWN_ESCAPE = re.compile(r"\\[" + re.escape(string.punctuation) + "]")


def formatted(text: str) -> str:
    return mdformat.text(text, extensions={"gfm", "myst"}, options=FORMAT_OPTIONS)


def math_expressions(text: str) -> list[tuple[str, bool]]:
    expressions = []
    for token in PARSER.parse(text):
        if token.type.startswith("math_block") or (token.type == "fence" and token.info.strip() == "math"):
            expressions.append((token.content.strip(), True))
        for child in token.children or []:
            if child.type == "math_inline":
                content = child.content
                ticks = len(content) - len(content.lstrip("`"))
                if ticks and content.endswith("`" * ticks):
                    content = content[ticks:-ticks]
                expressions.append((content, False))
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


def published_path_errors(root: Path, path: Path) -> list[str]:
    """Exige nombres públicos por tema; no modifica nombres canónicos externos."""
    relative = path.resolve().relative_to(root.resolve())
    if not relative.parts or relative.parts[0] not in CONTENT_DIRS:
        return []
    errors = []
    for index, part in enumerate(relative.parts[1:], 1):
        stem = Path(part).stem if index == len(relative.parts) - 1 and path.suffix else part
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", stem) or part != part.lower():
            errors.append(f"nombre publicado debe ser ASCII kebab-case: {part}")
        if re.match(r"^(?:office|pdf[0-9]{4}|resume)(?:-|$)", stem) or re.search(r"-[0-9a-f]{8,64}$", stem):
            errors.append(f"nombre publicado contiene prefijo de lote o hash; usar tema/autor/fecha/versión: {part}")
    return errors


def check_text(root: Path, path: Path, text: str) -> list[str]:
    errors = published_path_errors(root, path) + link_errors(root, path, text)
    if not text.strip():
        errors.append("Markdown vacío")
    # Los ejemplos de código pueden documentar marcadores defectuosos literalmente.
    footnote_depth = 0
    for token in PARSER.parse(text):
        if token.type == "footnote_open":
            footnote_depth += 1
        elif token.type == "footnote_close":
            footnote_depth -= 1
        if footnote_depth and (token.type.startswith("math_block") or
                               (token.type == "fence" and token.info.strip() == "math")):
            errors.append("GitHub deja matemática sin renderizar en una nota al pie; moverla a una nota enlazada")
        if token.type == "inline":
            emphasis_depth = 0
            children = token.children or []
            for child_index, child in enumerate(children):
                if child.type == "em_open":
                    emphasis_depth += 1
                elif child.type == "em_close":
                    emphasis_depth -= 1
                if child.type == "math_inline":
                    if emphasis_depth and child_index + 1 < len(children) and children[child_index + 1].type == "em_close":
                        errors.append("GitHub deja matemática sin renderizar al final de cursivas; sacar la fórmula del cierre de énfasis")
                    if footnote_depth:
                        errors.append("GitHub deja matemática sin renderizar en una nota al pie; moverla a una nota enlazada")
                    raw = child.content
                    ticks = len(raw) - len(raw.lstrip("`"))
                    if ticks and raw.endswith("`" * ticks):
                        if re.search(r"(?<!`)`{" + str(ticks) + r"}(?!`)", raw[ticks:-ticks]):
                            errors.append("el acento grave corta el delimitador; usar más backticks exteriores")
                if child.type in {"text", "math_inline"} and BAD_TEXT.search(child.content):
                    errors.append("carácter perdido, privado o marcador cid: revisar el original")
                if child.type == "math_inline" and MARKDOWN_ESCAPE.search(child.content):
                    if not (child.content.startswith("`") and child.content.endswith("`")):
                        errors.append("GitHub altera escapes Markdown en LaTeX en línea; usar $`...`$")
        elif token.type.startswith("math_block") or token.type == "html_block" or (token.type == "fence" and token.info.strip() == "math"):
            if BAD_TEXT.search(token.content):
                errors.append("carácter perdido, privado o marcador cid: revisar el original")
            if token.type.startswith("math_block") and (MARKDOWN_ESCAPE.search(token.content) or re.search(r"[*<>]", token.content)):
                errors.append("GitHub puede alterar metacaracteres Markdown en el bloque; usar un bloque ```math")
            if (token.type.startswith("math_block") or (token.type == "fence" and token.info.strip() == "math")) and text.splitlines()[token.map[0]].startswith(" "):
                errors.append("GitHub puede dejar sin renderizar el bloque matemático anidado; usar $`\\displaystyle ...`$")
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
        if re.search(r"\\begin\{aligned\}[\s\S]*?\\tag\{[\s\S]*?\\end\{aligned\}", expression):
            errors.append("GitHub rechaza \\tag dentro de aligned; mover la etiqueta después de \\end{aligned}")
            continue
        if "<" in expression or ">" in expression:
            errors.append("GitHub puede interpretar comparaciones como HTML; usar \\lt y \\gt")
            continue
        if re.search(r"\\operatorname\b", expression):
            errors.append("GitHub rechaza \\operatorname; usar \\mathop{\\mathrm{nombre}}\\nolimits")
            continue
        command = ["katex"] + (["--display-mode"] if display else [])
        result = subprocess.run(command, input=expression, text=True, capture_output=True)
        if result.returncode:
            errors.append(f"LaTeX inválido: {expression}\n{result.stderr.strip()}")
    return errors


def git(root: Path, *args: str) -> list[str]:
    result = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return [p for p in result.stdout.decode().split("\0") if p]


def changed_content_paths(root: Path, base: str) -> tuple[list[Path], list[Path]]:
    changed = set(git(root, "diff", "--name-only", "--no-renames", "--diff-filter=ACMR", "-z", base, "--"))
    changed.update(git(root, "ls-files", "--others", "--exclude-standard", "-z"))
    removed = [root / p for p in git(root, "diff", "--name-only", "--no-renames", "--diff-filter=D", "-z", base, "--")]
    content = [root / p for p in sorted(changed) if Path(p).parts[0] in CONTENT_DIRS]
    return content, removed


def changed_paths(root: Path, base: str) -> tuple[list[Path], list[Path]]:
    content, removed = changed_content_paths(root, base)
    return [p for p in content if p.suffix.lower() == ".md"], removed


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

Operador compatible con GitHub: $\mathop{\mathrm{sen}}\nolimits x$.

Escapes protegidos: $`\{x\in\mathbb R\mid x\gt 0\}`$ y $`x\,dx`$.

```math
\begin{bmatrix}
a & b \\
c & d
\end{bmatrix}
```

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
    for source in [r"$\operatorname{sen}x$", "$$\n\\operatorname{sen}x\n$$", "```math\n\\operatorname{sen}x\n```"]:
        errors = check_text(Path.cwd(), Path.cwd() / "self-test.md", formatted(source))
        if not any("GitHub rechaza" in error for error in errors):
            raise ValueError("No se detecta la macro que GitHub rechaza")
    if math_expressions(r"$`x\,dx`$") != [(r"x\,dx", False)]:
        raise ValueError("No se extrae la expresión protegida de GitHub")
    if math_expressions(r"$``x^{`}``$") != [(r"x^{`}", False)]:
        raise ValueError("No se conserva el acento grave dentro de la expresión protegida")
    errors = check_text(Path.cwd(), Path.cwd() / "self-test.md", formatted(r"$x\,dx$"))
    if not any("GitHub altera escapes" in error for error in errors):
        raise ValueError("No se detecta el escape Markdown sin protección")
    if math_expressions("```math\nx+1\n```") != [("x+1", True)]:
        raise ValueError("No se extrae el bloque matemático de GitHub")
    errors = check_text(Path.cwd(), Path.cwd() / "self-test.md", formatted("$$\nx^*+\\left\\{x\\right\\}\n$$"))
    if not any("GitHub puede alterar" in error for error in errors):
        raise ValueError("No se detecta el bloque con metacaracteres sin protección")
    errors = check_text(Path.cwd(), Path.cwd() / "self-test.md", formatted("```math\nf(x)=\\begin{cases}x&0<x<1\\end{cases}\n```"))
    if not any("comparaciones como HTML" in error for error in errors):
        raise ValueError("No se detecta la comparación vulnerable dentro del bloque")
    for source, message in [
        ("1. Texto\n\n   ```math\n   x+1\n   ```", "bloque matemático anidado"),
        ("1. Texto\n\n   $$\n   x+1\n   $$", "bloque matemático anidado"),
        ("```math\n\\begin{aligned}x&=1\\tag{1}\\end{aligned}\n```", "tag dentro de aligned"),
        (r"*Forma $`g(x)`$*", "cursivas"),
        ("Texto[^nota].\n\n[^nota]: $`x+1`$", "nota al pie"),
        (r"$`x^{`}`$", "acento grave"),
    ]:
        errors = check_text(Path.cwd(), Path.cwd() / "self-test.md", formatted(source))
        if not any(message in error for error in errors):
            raise ValueError("No se detecta la incompatibilidad de GitHub: " + message)
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
        content, removed = [p.resolve() for p in args.files], []
    else:
        content, removed = changed_content_paths(root, args.base)
    paths = [p for p in content if p.suffix.lower() == ".md"]
    errors = removed_link_errors(root, removed, paths)
    for path in content:
        if path not in paths:
            errors.extend(f"{path.relative_to(root)}: {error}" for error in published_path_errors(root, path))
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
