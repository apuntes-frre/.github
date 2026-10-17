# /// script
# requires-python = ">=3.12"
# dependencies = ["mdformat==1.0.0", "mdformat-gfm==1.0.0", "mdformat-myst==0.3.0"]
# ///
"""Regresiones de pérdidas reales: fórmulas, enlaces y selección de cambios."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import check_transcription as check, transcription_preflight as preflight


class TranscriptionTests(unittest.TestCase):
    def test_formatter_preserves_math_and_gfm(self):
        source = r"""# Álgebra

$F = \overline{A}B + A\overline{B}$, $\frac{a_1}{2^n}$ y $\alpha$.

$$
\begin{bmatrix}
a & b \\
c & d
\end{bmatrix}
$$

| A | B |
| - | - |
| 1 | 2 |

- [x] ~~Hecho~~

```text
$esto no es una ecuación$
```
"""
        output = check.formatted(source)
        self.assertEqual(check.math_expressions(source), check.math_expressions(output))
        self.assertEqual(len(check.math_expressions(output)), 4)
        self.assertIn(r"a & b \\" + "\n", output)
        self.assertIn("- [x] ~~Hecho~~", output)
        self.assertEqual(check.formatted(output), output)

    def test_links_support_reference_images_html_and_encoded_filenames(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "imagen uno.png"
            image.write_bytes(b"image")
            note = root / "nota.md"
            note.write_text("# Sección\n\n## Sección\n")
            source = '[Ver](nota.md#sección-1)\n\n![Figura][fig]\n\n[fig]: imagen%20uno.png\n\n<img src="imagen%20uno.png">\n'
            self.assertEqual(check.link_errors(root, note, source), [])
            image.unlink()
            self.assertEqual(len(check.link_errors(root, note, source)), 2)
            self.assertTrue(check.link_errors(root, note, "[Fuera](../fuera.md)"))
            self.assertTrue(check.link_errors(root, note, "[Ancla](nota.md#no-existe)"))

    def test_invalid_latex_and_extraction_artifacts_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text = check.formatted("# Nota\n\n$\\comandoInexistente{x}$\n\nTexto � (cid:123) \ue123.\n")
            errors = check.check_text(root, root / "nota.md", text)
            self.assertTrue(any("LaTeX inválido" in error for error in errors))
            self.assertTrue(any("carácter perdido" in error for error in errors))
            good = check.formatted("# Nota\n\n`(cid:123)` es un ejemplo.\n")
            self.assertEqual(check.check_text(root, root / "nota.md", good), [])

    def test_changed_scope_skips_legacy_but_checks_deleted_asset_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
            git("init")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.com")
            (root / "notes").mkdir()
            (root / "resources").mkdir()
            (root / "resources/figura.png").write_bytes(b"figure")
            (root / "notes/legacy.md").write_text("# Legacy\n![Figura](../resources/figura.png)\n")
            (root / "README.md").write_text("root")
            git("add", ".")
            git("commit", "-m", "baseline")
            (root / "README.md").write_text("changed generated README")
            (root / "notes/new.md").write_text("# Nueva\n")
            paths, removed = check.changed_paths(root, "HEAD")
            self.assertEqual(paths, [root / "notes/new.md"])
            self.assertEqual(removed, [])
            (root / "resources/figura.png").unlink()
            paths, removed = check.changed_paths(root, "HEAD")
            errors = check.removed_link_errors(root, removed, paths)
            self.assertEqual(len(errors), 1)
            self.assertIn("legacy.md", errors[0])

    def test_github_rendering_failures_are_rejected(self):
        cases = [
            (r"$\operatorname{sen}x$", "operatorname"),
            ("```math\n\\operatorname{sen}x\n```", "operatorname"),
            (r"$x\,dx$", "escapes Markdown"),
            ("```math\nf(x)=\\begin{cases}x&0<x<1\\end{cases}\n```", "comparaciones como HTML"),
            ("1. Ejercicio\n\n   ```math\n   x+1\n   ```", "bloque matemático anidado"),
            ("1. Ejercicio\n\n   $$\n   x+1\n   $$", "bloque matemático anidado"),
            ("```math\n\\begin{aligned}x&=1\\tag{1}\\end{aligned}\n```", "tag dentro de aligned"),
            (r"*La misma forma que $`g(x)`$*", "cursivas"),
            ("Texto[^nota].\n\n[^nota]: $`y'=u`$", "nota al pie"),
            ("Texto[^nota].\n\n[^nota]: Texto.\n\n    ```math\n    x+1\n    ```", "nota al pie"),
            (r"$`x^{`}`$", "acento grave"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source, message in cases:
                with self.subTest(source=source):
                    errors = check.check_text(root, root / "nota.md", check.formatted(source))
                    self.assertTrue(any(message in error for error in errors), errors)

    def test_github_safe_forms_preserve_math_and_pass(self):
        source = r"""# Formas comprobadas

$`\mathop{\mathrm{sen}}\nolimits x`$, $``x^{`}``$ y *la misma forma que* $`g(x)`$.

1. Ejercicio.

   $`\displaystyle x+1`$

```math
\begin{aligned}x&=1\end{aligned}\tag{1}
```

Texto[^nota].

## Nota del original

$`y'=u`$ y $`x\lt 1`$.

[^nota]: Véase la [nota del original](#nota-del-original).

```text
$\operatorname{sen}x$ y *$`g(x)`$* son ejemplos de errores.
```
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "nota.md"
            text = check.formatted(source)
            path.write_text(text)
            self.assertEqual(check.check_text(root, path, text), [])
            self.assertEqual(check.math_expressions(text), [
                (r"\mathop{\mathrm{sen}}\nolimits x", False), ("x^{`}", False),
                ("g(x)", False), (r"\displaystyle x+1", False),
                (r"\begin{aligned}x&=1\end{aligned}\tag{1}", True),
                ("y'=u", False), (r"x\lt 1", False),
            ])

    def test_math_inside_emphasis_with_trailing_text_is_allowed(self):
        # Estas dos formas renderizan en el documento real; no prohibir todo énfasis.
        source = r"*La forma de $`y_p`$ es una combinación de $`g(x)`$.*"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(check.check_text(root, root / "nota.md", check.formatted(source)), [])

    def test_published_names_reject_internal_batches_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["notes/2022/practica/office-repaso-2e04ae39.md",
                         "notes/2020/teoria/pdf2020-gradiente.md",
                         "resources/2016/resume-misc-grafica/figura-1.png",
                         "notes/2020/teoria/repaso-2e04ae39.md",
                         "resources/2020/Taylor/image1.png"]:
                with self.subTest(name=name):
                    self.assertTrue(check.published_path_errors(root, root / name))
            for name in ["notes/2022/practica/repaso.md", "resources/2020/zill-02/figura-1.png",
                         "notes/2016/practica/examen-final-2012-07-11.md",
                         "notes/2016/practica/diferenciales-bis-version-2.md"]:
                self.assertEqual(check.published_path_errors(root, root / name), [])
            # Las rutas canónicas originales y los archivos de configuración no se renombran.
            self.assertEqual(check.published_path_errors(root, root / "originales/Taylor.docx"), [])
            self.assertEqual(check.published_path_errors(root, root / "AGENTS.md"), [])

    def test_cli_checks_unreferenced_asset_names_without_rechecking_legacy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for args in [("init",), ("config", "user.name", "Test"),
                         ("config", "user.email", "test@example.com")]:
                subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
            (root / "notes").mkdir()
            (root / "notes/legacy.md").write_text("#Legacy sin formatear\n")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "commit", "-m", "baseline"], check=True, capture_output=True)
            assets = root / "resources/2026"
            assets.mkdir(parents=True)
            bad = assets / "office-figura-1234abcd.png"
            bad.write_bytes(b"unchanged media")
            result = subprocess.run([sys.executable, check.__file__, "--base", "HEAD"],
                                    cwd=root, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("prefijo de lote o hash", result.stdout)
            bad.rename(assets / "taylor-figura-1.png")
            result = subprocess.run([sys.executable, check.__file__, "--base", "HEAD"],
                                    cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_materialization_verifies_bytes_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.docx"
            source.write_bytes(b"canonical bytes")
            record = preflight.materialize(source, root / "copy.docx")
            self.assertEqual(record["sha256"], hashlib.sha256(b"canonical bytes").hexdigest())
            self.assertEqual(source.read_bytes(), b"canonical bytes")
            self.assertEqual(record["review"], "pendiente")
            with self.assertRaises(FileExistsError):
                preflight.materialize(source, root / "copy.docx")


if __name__ == "__main__":
    unittest.main()
