# Estrategias para cargar apuntes en los repos de materia

Guía práctica para convertir material de origen (PDF, DOCX, Google Docs,
imágenes, planillas, links) en notas Markdown dentro de cada repo
`isi-2008-<slug>`. El objetivo es **cargar rápido** y de forma consistente.

> Esta guía es sobre el **contenido de los repos de materia**. El plan
> curricular vive en [`isi.toml`](isi.toml); las convenciones generales en
> [`../AGENTS.md`](../AGENTS.md).

## 📍 Dónde va cada cosa (recordatorio)

```text
isi-2008-<slug>/
├── notes/<año>/teoria/<tema>.md      # apuntes teóricos
├── notes/<año>/practica/<tema>.md    # ejercicios, TPs
├── study-guides/guia-estudio-<tema>.md
└── resources/
    ├── common/                       # bibliografía/links compartidos entre años
    └── <año>/                        # material de un año puntual
```

- Archivos en **kebab-case, español, ASCII**: `tabla-hash.md`, no `Tabla Hash.md`.
- Las carpetas se crean **cuando hay contenido** (sin `.gitkeep`).

## 🔁 Flujo general (3 pasos)

1. **Clonar** el repo de la materia: `gh repo clone apuntes-frre/isi-2008-<slug>`.
2. **Convertir** la fuente a Markdown (ver sección por formato).
3. **Ubicar** el `.md` en `notes/<año>/…`, revisar, `commit` + `push`.

> ⚡ **El camino más rápido (Claude Code):** en vez de pelear con herramientas,
> arrastrá la fuente al repo (o pegá el texto) y pedile a Claude que la
> transcriba a Markdown siguiendo la convención de carpetas/nombres. Funciona
> especialmente bien con capturas, PDFs escaneados y material desordenado, donde
> los conversores automáticos fallan. Siempre revisá el resultado.

## 🛠️ Herramientas (instalar lo que falte)

```sh
brew install pandoc poppler tesseract ocrmypdf
# pandoc → DOCX/HTML/MD ; poppler → pdftotext ; tesseract → OCR ; ocrmypdf → OCR sobre PDF
```

Para conversiones puntuales sin instalar nada global, también sirve `uvx`
(ej. `uvx markitdown <archivo>`).

---

## Por formato de origen

### 📄 PDF con texto (no escaneado)

`pandoc` no lee PDF como entrada; usar **poppler**:

```sh
pdftotext -layout entrada.pdf - | tee notes/2026/teoria/<tema>.md
```

- `-layout` preserva columnas/tablas razonablemente.
- Limpiar a mano encabezados/pies repetidos y rehacer títulos como `#`/`##`.
- Si el PDF tiene estructura (índice, secciones), conviene que Claude lo lea
  directo y lo reescriba como Markdown limpio.

### 🖼️ PDF escaneado o capturas (PNG/JPG)

Es imagen: necesita **OCR** o transcripción por visión.

```sh
ocrmypdf entrada.pdf salida.pdf && pdftotext -layout salida.pdf -   # PDF escaneado
tesseract captura.png - -l spa                                      # imagen suelta (idioma español)
```

- El OCR de fórmulas/diagramas es flojo. Para pizarras, diagramas o mate,
  **transcribir con Claude (visión)** suele dar mejor Markdown/LaTeX.
- La imagen original, si aporta, va a `resources/<año>/` y se referencia desde
  el `.md` con `![desc](../../resources/<año>/<archivo>.png)`.

### 📝 DOCX

```sh
pandoc entrada.docx -o notes/2026/teoria/<tema>.md \
  --wrap=none --extract-media=resources/2026
```

- `--wrap=none` evita saltos de línea artificiales.
- `--extract-media` saca las imágenes embebidas a `resources/2026/` y las
  enlaza solo.

### 📑 Google Docs

Dos opciones:

1. **Exportar directo a Markdown:** en el Doc, _Archivo → Descargar → Markdown
   (.md)_. Listo para ubicar y revisar.
2. **Vía DOCX:** _Descargar → Word (.docx)_ y luego el comando `pandoc` de arriba
   (útil si querés extraer las imágenes embebidas).

### 📊 XLSX / CSV (planillas, tablas de datos)

`pandoc` no abre XLSX. Convertir a CSV y de ahí a tabla Markdown:

```sh
uvx xlsx2csv planilla.xlsx datos.csv          # XLSX → CSV
pandoc datos.csv -f csv -t gfm                 # CSV → tabla Markdown (GitHub)
```

- Para planillas grandes, conviene dejar el `.csv` en `resources/<año>/` y en el
  `.md` poner solo la tabla relevante.
- Si la planilla tiene varias hojas, exportá la que importa o pedile a Claude que
  arme la tabla.

### 🔗 URL (artículos, apuntes web)

Extraer el contenido legible, no el HTML crudo:

```sh
uvx trafilatura -u "https://…" --markdown            # artículo → Markdown
# o, rápido y sucio:
pandoc -f html -t gfm "https://…" -o notes/2026/teoria/<tema>.md
```

- Para **links de referencia** (no para copiar el contenido), no transcribas:
  agregalos a `resources/common/` o a una sección "Recursos" del `.md`.
- Respetá derechos de autor: resumí/citá, no copies material protegido completo.

---

## 🧱 Qué versionar y qué no

- **Sí:** los `.md` transcritos, imágenes propias livianas, diagramas.
- **Con criterio:** PDFs/planillas originales en `resources/` solo si son chicos
  y aportan. Git no es para binarios pesados.
- **No:** material con copyright que no puedas redistribuir; dejá el link.

## ✅ Checklist por nota

- [ ] Ubicada en `notes/<año>/{teoria|practica}/` con nombre kebab-case.
- [ ] Títulos como `#`/`##`, no texto en mayúsculas.
- [ ] Imágenes en `resources/` y referenciadas, no embebidas como base64.
- [ ] Revisada (el OCR y los conversores meten ruido).
- [ ] `commit` + `push`.
