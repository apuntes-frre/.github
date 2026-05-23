# Cómo contribuir apuntes

Este repo es parte de la organización
[apuntes-frre](https://github.com/apuntes-frre) (UTN-FRRE) y contiene los apuntes
de **una materia**. Acá está cómo aportar material nuevo de forma consistente.

> ⚠️ El `README.md` de este repo es **autogenerado** desde el manifest curricular
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

## 🛠️ Herramientas (Python, vía `uvx`)

No hace falta instalar nada global: [`uv`](https://docs.astral.sh/uv/) corre cada
CLI en un entorno efímero con `uvx <herramienta>`.

| Herramienta | Para qué |
| ----------- | -------- |
| `markitdown` | **Tu primera opción.** Conversor universal → Markdown: PDF, DOCX, PPTX, XLSX, HTML, imágenes. |
| `docling` | PDF con layout/tablas complejas → Markdown (más lento, mejor calidad). |
| `trafilatura` | Artículos web (URL) → Markdown limpio. |
| `xlsx2csv` | Planillas XLSX → CSV (cuando solo querés los datos). |

## 🔁 Flujo

1. `gh repo clone apuntes-frre/<repo-de-la-materia>`
2. Convertí la fuente a Markdown (ver abajo).
3. Ubicá el `.md` en `notes/<año>/{teoria|practica}/`, revisalo.
4. `commit` + `push` (o abrí un PR si no tenés acceso directo).

> ⚡ **El camino más rápido (Claude Code):** arrastrá la fuente al repo (o pegá el
> texto/imagen) y pedile a Claude que la transcriba a Markdown siguiendo esta
> convención. Imbatible con capturas, PDFs escaneados, pizarras y fórmulas, donde
> los conversores automáticos fallan. Siempre revisá el resultado.

## Convertir según el formato de origen

### Casi todo → `markitdown`

```sh
uvx markitdown apunte.pdf    -o notes/2026/teoria/<tema>.md
uvx markitdown apunte.docx   -o notes/2026/teoria/<tema>.md
uvx markitdown planilla.xlsx -o notes/2026/practica/<tema>.md
```

`markitdown` cubre PDF (con texto), DOCX, PPTX, XLSX, HTML e imágenes en un solo
comando. Empezá siempre por acá.

### PDF con tablas/columnas complejas → `docling`

Si `markitdown` desordena un PDF con layout difícil:

```sh
uvx docling apunte.pdf --to md
```

Genera Markdown (mejor reconstrucción de tablas); movés el resultado a
`notes/<año>/…`.

### Imágenes / PDF escaneado (capturas, pizarras, fórmulas)

Los conversores **no hacen buen OCR** de manuscritos ni fórmulas. Lo más rápido y
prolijo: **transcribir con Claude** (visión) a Markdown/LaTeX. La imagen original,
si aporta, va a `resources/<año>/` y se enlaza desde el `.md`:

```markdown
![Diagrama entidad-relación](../../resources/2026/der-ventas.png)
```

### Google Docs

Descargá el documento como **Markdown (.md)** (*Archivo → Descargar → Markdown*) o
como `.docx` y pasalo por `uvx markitdown`.

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
- [ ] Revisada (el OCR y los conversores meten ruido).
- [ ] `commit` + `push`.

---

> Convenciones generales de la organización:
> [apuntes-frre/.github](https://github.com/apuntes-frre/.github).
