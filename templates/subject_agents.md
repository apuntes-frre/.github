# AGENTS.md

<!-- Sincronizado desde apuntes-frre/.github/templates/subject_agents.md.
     Cambiar las reglas comunes en esa plantilla; las reglas específicas
     pueden ir en AGENTS.md dentro de las subcarpetas de la materia. -->

## Fuente y alcance

- OneDrive es la fuente canónica indicada por el propietario. Localizar la
  carpeta de esta materia y comprobar que los archivos estén descargados y
  legibles antes de convertirlos. En esta laptop, buscar bajo
  `~/Library/CloudStorage/OneDrive-*/Facultad/Materias ISI/`. Si el mapeo está
  pendiente o no aparece la materia, buscar también en el resto de `Facultad/`,
  incluida `Materias Homogeneas/`, y verificar la pertenencia en los documentos.
- Consultar el mapeo `transcription/sources.json` del repo de control
  `apuntes-frre/.github` (con `gh api` o su clone local). Un valor `null`
  requiere identificar la fuente; no asignar por semejanza curricular. Los
  nombres de archivos son pistas: verificar la materia en el documento. Separar
  versiones, anexos, ejemplos y software del material docente.
- Inventariar originales y apuntes existentes por año, UT, práctica, páginas,
  anexos y versiones. No declarar una materia completa solo por sus carpetas.
- Transcribir el contenido completo: idioma, numeración, ejercicios, tablas,
  figuras y notas. No resumir, resolver ejercicios vacíos ni inventar texto
  ilegible. Identificar pérdidas y conservar las erratas del original; cualquier
  corrección debe quedar separada y explicada.
- Preservar los originales y convertir en un directorio temporal nuevo.
  Registrar archivo de origen, SHA-256, páginas, autor/año cuando consten,
  herramienta y comprobaciones realizadas en `resources/<año>/fuentes.md`.

## Herramientas de conversión

Antes de convertir, leer la skill `document-to-markdown` si está disponible en
`~/.codex/skills/document-to-markdown/SKILL.md`. Estas instrucciones también
definen el flujo cuando esa skill no está instalada.

Usar `mise exec -- <herramienta> <argumentos>` para resolver instalaciones
administradas por mise en shells no interactivos. Comprobar `mise ls` y
`mise exec -- which <herramienta>`; evitar instalaciones duplicadas por pip/npm.
En la laptop del propietario, mise está en `~/.local/bin/mise`; usar su ruta
absoluta si falta en el PATH. Si existe la tarea, ejecutar
`mise run documents:check`. Verificar además Docling, mdformat y markdownlint.
Las instalaciones de esta laptop no se heredan en agentes remotos: verificar
herramientas y acceso a OneDrive en el host que ejecuta el trabajo. Las
herramientas Python de conversión usan un intérprete estable 3.14.8 en mise; no
enlazar sus entornos a `python/latest`, que puede cambiar de ABI.

Antes de transcribir, comprobar una conversión real y materializar únicamente
las fuentes asignadas en un directorio nuevo fuera del repo:

```sh
mise exec -- uv run .github/transcription/preflight.py \
  --engine pymupdf4llm --work-dir /ruta/temporal/nueva /ruta/canonica/fuente.pdf
```

El preflight comprueba el motor, copia archivos legibles, verifica SHA-256 y
registra páginas PDF. No declara cobertura ni fidelidad. Para Docling,
`--engine docling --download-models` prepara los modelos estándar; una
conversión real verifica que carguen. Modelos opcionales de fórmulas requieren
además probar `--enrich-formula` sobre una muestra antes del lote.

| Fuente | Ruta inicial | Si pierde contenido |
| -- | -- | -- |
| DOCX, ODT, HTML, EPUB | Pandoc → GFM | Docling o MarkItDown |
| XLS/XLSX, PPTX | MarkItDown | Inspección nativa |
| PDF con texto | PyMuPDF4LLM | Docling |
| PDF escaneado o mixto | OCRmyPDF → PyMuPDF4LLM | Docling OCR |
| PDF científico complejo | Docling | Comparación visual y reparación |
| DOC, RTF, PPT, ODS | LibreOffice → DOCX/PPTX/XLSX | Ruta normalizada |

Comparar páginas representativas antes de seleccionar un motor para un lote.
Conservar figuras referenciadas y el JSON de Docling para revisar estructura.

```sh
# Desde un directorio de salida nuevo.
mise exec -- pandoc /ruta/fuente.docx --to gfm --wrap none \
  --extract-media fuente.assets --output fuente.md
mise exec -- markitdown /ruta/fuente.xlsx --output /ruta/temporal/fuente.md
mise exec -- pymupdf4llm /ruta/fuente.pdf --out /ruta/temporal/salida \
  --backend md --workers 1 --ocr-mode never --write-images --header --footer
mise exec -- docling convert /ruta/fuente.pdf --to md --to json \
  --image-export-mode referenced --output /ruta/temporal/salida
```

Para escaneos, verificar el idioma con `mise exec -- tesseract --list-langs`.
Para español, comprobar `spa` antes de usarlo. En macOS, el paquete mise
`brew:tesseract-lang` proporciona los idiomas adicionales.

```sh
mise exec -- ocrmypdf --skip-text --output-type pdf -l spa \
  /ruta/original.pdf /ruta/temporal/buscable.pdf
```

`--skip-text` no repara capas textuales corruptas ni asegura OCR de imágenes
dentro de páginas con texto. Inspeccionar esos casos sobre una copia. Para
fórmulas difíciles, evaluar `--enrich-formula` de Docling y verificar cada
expresión contra la página original. Puede requerir modelos locales. Usar
LibreOffice con un perfil temporal aislado para formatos antiguos y comprobar
que su salida existe y no está vacía. En Codex, localizar utilidades faltantes
del runtime con `load_workspace_dependencies`.

## Notación y organización

- Escribir fórmulas en LaTeX: `$...$` en línea y bloques `$$` en líneas
  separadas. Preservar subíndices, exponentes, fracciones, letras griegas y
  barras de negación; comparar con el original y verificar su renderizado.
- Guardar apuntes en `notes/<año>/{teoria,practica}/`, guías en `study-guides/`
  y medios en `resources/<año>/`. Usar nombres en español, ASCII kebab-case. No
  crear carpetas vacías ni `.gitkeep`.
- Mantener imágenes originales como PNG/SVG/JPEG con enlaces relativos; extraer
  o convertir objetos incrustados y revisar etiquetas y conexiones. No incluir
  base64 ni reemplazar por capturas fórmulas que puedan transcribirse.
- Escribir los textos editoriales en español y conservar el idioma de la fuente.
  No editar el README raíz autogenerado de esta materia.

## Verificación y entrega

1. Comparar texto PDF con `mise exec -- pdftotext -layout` y páginas
   renderizadas con `mise exec -- pdftoppm`. Revisar todas las páginas antes de
   declarar una transcripción completa; contar ejercicios, tablas, figuras y
   anexos.

1. Detectar pérdidas, orden alterado, caracteres `�`, `(cid:...)` y símbolos de
   fuentes privadas. Reparar con evidencia visual. Revisar todas las hojas y
   diapositivas relevantes; las fórmulas de Excel pueden tener cachés obsoletos.

1. Comprobar enlaces, figuras, números, tablas y LaTeX. No confundir una
   conversión exitosa o una fórmula que renderiza con fidelidad o corrección.

1. Formatear solo archivos modificados con GFM **y MyST**: GFM solo altera
   comandos LaTeX y matrices. Revisar el diff y conservar las expresiones. El
   validador comprueba formato, lint, enlaces/imágenes, artefactos y KaTeX:

   ```sh
   mise exec -- mdformat --extensions gfm --extensions myst --wrap 80 \
     --compact-tables /ruta/nota.md
   mise -C .github/transcription exec -- uv run check.py --self-test
   mise -C .github/transcription exec -- uv run check.py --base origin/main
   ```

   CI revisa las notas modificadas y referencias a medios eliminados. No exige
   reformatear contenido anterior. KaTeX válido y CI verde no reemplazan la
   comparación completa con originales.

1. Trabajar en una rama de revisión, preservar cambios existentes y entregar el
   material con su procedencia, comprobaciones y pérdidas pendientes. Publicar o
   fusionar según la autorización del usuario para esta tarea.
