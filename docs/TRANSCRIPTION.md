# Delegar transcripciones

El flujo se valida primero en esta laptop, que tiene OneDrive y herramientas
mise. Un agente remoto necesita acceso propio a los originales y su toolchain.
Una sesión nueva debe comenzar dentro del clone/worktree de la materia para leer
su `AGENTS.md`.

## Preparación de la organización

```sh
uv run scripts/sync_repos.py
```

Es una sincronización local que usa la sesión existente de GitHub CLI (`gh`).
Valida los manifests y la credencial, y publica AGENTS, CONTRIBUTING, preflight,
validador, configuración mise/lint, el workflow `Validate Transcription` y los
READMEs generados en las materias existentes declaradas. No crea ni archiva
repos, no cambia `.gitignore` y no actualiza clones locales.

Repetir el mismo comando debe informar «sin escrituras». Los subcomandos
existentes conservan su dry-run, por ejemplo `bootstrap` y `readmes`; agregar
`--apply` para publicarlos por separado. `manifest sync --apply` instala el
bootstrap al crear una materia; el comando sin argumentos también repara
instalaciones parciales. Ejecutarlo al cambiar plantillas o agregar una materia
por otro medio.

### Credencial local

No requiere PAT ni secretos de Actions. `gh` debe estar instalado y autenticado
con acceso de escritura a las materias y permiso para publicar workflows. Si
falta la sesión, ejecutar `gh auth login --hostname github.com`; para agregar
los scopes OAuth necesarios, usar
`gh auth refresh --hostname github.com --scopes repo,workflow`.

El script obtiene la credencial con `gh auth token` y la mantiene en memoria; no
exportarla ni copiarla a archivos o secretos. La auditoría de solo lectura en
Actions conserva el `GITHUB_TOKEN` integrado de GitHub. La publicación de
archivos de materias se ejecuta desde la laptop.

## Inventario y asignación

[sources.json](../transcription/sources.json) vincula nombres reales de carpetas
con repos. Sus `null` requieren identificar la fuente; electivas como BDA o
Taller Álgebra no se asignan automáticamente a una materia/plan.

El inventario predeterminado solo busca en `Facultad/Materias ISI/` y usa los
mapeos no nulos. Si falta una fuente, buscar en el resto de `Facultad/`, incluida
`Materias Homogeneas/`, y verificar el contenido. Por ejemplo, Análisis Matemático
II está en `Facultad/Materias Homogeneas/Analisis Matemático II`; su mapeo sigue
pendiente porque el inventario actual representa carpetas de una sola raíz.
`--source-root` cambia esa raíz, pero no resuelve mapeos nulos ni combina raíces.
Registrar las fuentes identificadas fuera del mapeo en la asignación y en
`resources/<año>/fuentes.md`.

```sh
uv run scripts/inventory_sources.py --output /ruta/temporal/source-inventory.json
```

El informe incluye años/UT/prácticas como pistas de nombres, originales,
material previo en clones con origin verificado, estado cloud-only y paquetes de
software/build separados. No descarga los 75 mil archivos del árbol. Páginas y
hashes permanecen pendientes hasta leer fuentes concretas. La pertenencia a una
materia y las versiones se comprueban dentro del documento.

Cada asignación incluye repo, año de archivo y año impreso, UT/práctica,
originales exactos, material previo, rama/base y alcance de publicación. Usar un
worktree por materia y conservar cambios locales previos. Inventariar
suplementos y duplicados por hash/contenido. No resolver ejercicios vacíos.

## Inicio y verificación en una materia

```sh
mise run documents:check
mise exec -- uv run .github/transcription/preflight.py --engine pymupdf4llm \
  --work-dir /ruta/temporal/nueva /ruta/OneDrive/fuente.pdf
```

El preflight ejecuta la ayuda o versión de las herramientas, materializa fuentes
seleccionadas, verifica SHA-256 y cuenta páginas PDF. No convierte documentos:
antes de procesar un lote, comprobar por separado una conversión real sobre una
muestra representativa. Para Docling, agregar
`--download-models` y comprobar una conversión real; modelos opcionales como
fórmulas requieren su prueba específica. En OCR, se comprueba el idioma
solicitado, por defecto español. Mantener Python estable para los entornos:
`python/latest` puede cambiar de ABI y dejar los paquetes invisibles.

Seguir las rutas por formato en AGENTS/CONTRIBUTING. Comparar todas las páginas,
hojas o diapositivas; contrastar texto PDF con `pdftotext -layout` y vistas de
`pdftoppm`. Registrar originales, SHA-256, motores, conteos, páginas revisadas y
pérdidas en `resources/<año>/fuentes.md`. Una extracción exitosa no demuestra
fidelidad. Registrar medios enlazados ausentes, sin inventarlos.

```sh
mise exec -- mdformat --extensions gfm --extensions myst --wrap 80 \
  --compact-tables notes/2026/teoria/tema.md
mise -C .github/transcription exec -- uv run check.py --self-test
mise -C .github/transcription exec -- uv run check.py --base origin/main
```

MyST agrega parsing de matemática con delimitadores GitHub. Las regresiones
comprueban negación, fracciones, subíndices, matrices, tablas GFM y listas de
tareas. El validador exige preservación del formato, enlaces relativos/anclas,
imágenes, ausencia de marcadores defectuosos y KaTeX sin errores. Al eliminar
medios se detectan referencias afectadas sin formatear notas antiguas.

CI usa los mismos scripts y versiones fijadas con el base SHA del PR o el commit
anterior al push. La validación no exige reformatear toda la materia ni
determina si una fórmula coincide con el original. La revisión documental
completa sigue siendo condición de entrega.
