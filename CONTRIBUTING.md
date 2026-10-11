# Cómo contribuir apuntes

Esta guía se aplica a los repositorios de materias de
[apuntes-frre](https://github.com/apuntes-frre) (UTN-FRRE). Explica cómo aportar
material nuevo de forma consistente.

Para modificar scripts, manifests o plantillas del repo de control `.github`,
consultá [su arquitectura](https://github.com/apuntes-frre/.github/blob/main/docs/ARCHITECTURE.md)
y abrí un PR con los cambios y su validación.

> ⚠️ El `README.md` de cada repo de materia es **autogenerado** desde el manifest curricular
> (ver [`.github/data`](https://github.com/apuntes-frre/.github/tree/main/data)).
> **No lo edites a mano**: se sobrescribe en la próxima sincronización.

## 📍 Dónde va cada cosa

```text
<repo-de-la-materia>/
├── notes/<año>/teoria/<tema>.md      # apuntes teóricos
├── notes/<año>/practica/<tema>.md    # ejercicios, TPs
├── study-guides/guia-estudio-<tema>.md
└── resources/
    ├── common/                       # bibliografía/links compartidos entre años
    └── <año>/                        # material (imágenes, PDFs) de un año puntual
```

- Nombres en **kebab-case, español, ASCII**: `tabla-hash.md`, no `Tabla Hash.md`.
- Las carpetas se crean **cuando hay contenido** (no usamos `.gitkeep`).
- Las imágenes van a `resources/` y se referencian; no se pegan como base64.

## 🛠️ Herramientas de conversión

Cada repo de materia recibe un `AGENTS.md` con las instrucciones completas
para Codex: fuente canónica en OneDrive, herramientas, LaTeX y verificación.
La plantilla común está en `templates/subject_agents.md` del repo de control.
Las herramientas se seleccionan por formato y se comparan contra la fuente.

| Fuente | Ruta inicial |
| --- | --- |
| DOCX, ODT, HTML, EPUB | Pandoc → GFM |
| XLS/XLSX, PPTX | MarkItDown |
| PDF con texto | PyMuPDF4LLM; comparar con Docling si pierde contenido |
| PDF científico complejo | Docling, revisando fórmulas y tablas |
| PDF escaneado o mixto | OCRmyPDF → PyMuPDF4LLM o Docling OCR |
| DOC, RTF, PPT, ODS | LibreOffice → DOCX/PPTX/XLSX; luego convertir |

En la laptop del propietario, usar las instalaciones de mise con
`mise exec -- <herramienta> <argumentos>`. `mise run documents:check` verifica
la base del toolchain; comprobar también Docling, mdformat y markdownlint-cli2.
En otros hosts, verificar disponibilidad e instalar las herramientas necesarias.
[`uv`](https://docs.astral.sh/uv/) permite ejecutar herramientas Python con
`uvx` cuando no hay una instalación administrada disponible.

## 🔁 Flujo

1. `gh repo clone apuntes-frre/<repo-de-la-materia>`
2. Leé `AGENTS.md` e inventariá originales y material existente.
3. Convertí en un directorio temporal nuevo; preservá la fuente y sus figuras.
4. Ubicá el `.md` en `notes/<año>/{teoria|practica}/` y verificá su contenido.
5. Entregá los cambios en una rama de revisión; publicá según la autorización.

Los manuscritos, diagramas y fórmulas requieren comparación visual. La salida
de OCR o de un modelo es una propuesta de transcripción; señalá lo ilegible.

## Convertir según el formato de origen

### Documentos estructurados → Pandoc; planillas y slides → MarkItDown

```sh
mise exec -- pandoc apunte.docx --to gfm --wrap none \
  --extract-media apunte.assets --output apunte.md
mise exec -- markitdown planilla.xlsx --output planilla.md
mise exec -- markitdown presentacion.pptx --output presentacion.md
```

Conservá los medios de Pandoc y verificá todas las hojas o diapositivas
relevantes. Las fórmulas de planillas pueden depender de valores almacenados.

### PDF → PyMuPDF4LLM o Docling

Para PDF con texto, conservando figuras, encabezados y pies:

```sh
mise exec -- pymupdf4llm apunte.pdf --out salida-pdf --backend md \
  --workers 1 --ocr-mode never --write-images --header --footer
```

Para layout o fórmulas difíciles, compará con Docling y conservá su JSON:

```sh
mise exec -- docling convert apunte.pdf --to md --to json \
  --image-export-mode referenced --output salida-docling
```

Evaluá `--enrich-formula` si hace falta y verificá cada expresión contra la
fuente. Compará con `pdftotext -layout` y páginas renderizadas con `pdftoppm`.

### Imágenes / PDF escaneado (capturas, pizarras, fórmulas)

Usá OCRmyPDF sobre una copia y luego la ruta PDF. Verificá antes que Tesseract
tenga el idioma del original; para español, `spa`:

```sh
mise exec -- tesseract --list-langs
mise exec -- ocrmypdf --skip-text --output-type pdf -l spa \
  escaneado.pdf buscable.pdf
```

Las capas textuales corruptas y las imágenes en páginas con texto requieren
inspección adicional. Transcribí las fórmulas a Markdown/LaTeX, preservando
negaciones y subíndices. La imagen original, si aporta, va a `resources/<año>/`:

```markdown
![Diagrama entidad-relación](../../../resources/2026/der-ventas.png)
```

### Google Docs

Descargá el documento como **Markdown (.md)** (*Archivo → Descargar → Markdown*) o
como `.docx` y pasalo por Pandoc.

### URL (artículos, apuntes web) → `trafilatura`

```sh
uvx trafilatura -u "https://…" --markdown -o notes/2026/teoria/<tema>.md
```

Para **links de referencia** (no para copiar el contenido), no transcribas:
agregalos a `resources/common/` o a una sección "Recursos" del `.md`. Respetá los
derechos de autor: resumí y citá, no copies material protegido completo.

## 🧱 Qué versionar y qué no

- **Sí:** los `.md` transcritos, imágenes propias livianas, diagramas.
- **Con criterio:** PDFs/planillas originales en `resources/` solo si son chicos y
  aportan. Git no es para binarios pesados.
- **No:** material con copyright que no puedas redistribuir; dejá el link.

## ✅ Checklist por nota

- [ ] Ubicada en `notes/<año>/{teoria|practica}/` con nombre kebab-case.
- [ ] Títulos como `#`/`##`, no texto en mayúsculas.
- [ ] Imágenes en `resources/` y referenciadas (no base64).
- [ ] Páginas, ejercicios, tablas, figuras y anexos comparados con la fuente.
- [ ] Procedencia y SHA-256 registrados en `resources/<año>/fuentes.md`.
- [ ] Enlaces y LaTeX revisados; formato y lint comprobados.
- [ ] Rama de revisión lista para publicar según la autorización.

---

> Convenciones generales de la organización:
> [apuntes-frre/.github](https://github.com/apuntes-frre/.github).
