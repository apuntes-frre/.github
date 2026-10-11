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
