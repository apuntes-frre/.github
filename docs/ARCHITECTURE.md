# 🏛️ Arquitectura — Apuntes FRRE

## Modelo

La organización `apuntes-frre` tiene un repo de control (`.github`) y repos de
materia. El control mantiene manifests, plantillas, scripts y workflows;
los repos de materia contienen apuntes, ejemplos, guías y recursos.

`data/<carrera>.toml` es la única fuente de verdad curricular. La lista de
GitHub indica qué repos están publicados; las descripciones no definen el
nombre ni los requisitos de una materia.

## Convención y contenido

Los repos de materia se nombran `<carrera>-<plan>-<slug>`:
`isi-2008-analisis-matematico-i`. El slug conserva el nombre en español,
en kebab-case ASCII; los numerales romanos van en minúscula.
No se aceptan nombres legacy sin plan.

```text
isi-2008-<slug>/
├── README.md                 # generado desde el manifest
├── CONTRIBUTING.md           # copia de la guía del control
├── .gitignore                # copia de templates/subject.gitignore
├── notes/<año>/teoria/
├── notes/<año>/practica/
├── examples/
├── study-guides/
└── resources/common/
```

Las carpetas aparecen cuando hay contenido; no se crean carpetas vacías
ni `.gitkeep`. La guía de colaboración describe cómo cargar material.

## Manifest curricular

Cada manifest declara `[carrera]` y uno o más `[planes.<año>]`, con materias
bajo `[planes.<año>.materias.<slug>]`. Se validan nombres, slugs, campos,
tipos, orden único y niveles. Las correlativas referencian slugs existentes
y su grafo debe ser acíclico.

`correlativas-estado` distingue `completas` de `pendientes`. El plan 2023
está pendiente de definición de correlativas por FRRE: la ausencia de datos
no significa ausencia de requisitos. Sus READMEs muestran esa advertencia.
Los PDFs de `data/sources/` preservan la procedencia curricular y se conservan.

## Scripts

| Archivo | Responsabilidad |
| --- | --- |
| `scripts/common.py` | Lectura y validación del manifest, nombres de repos y entorno Jinja estricto. Módulo compartido, no ejecutable. |
| `scripts/sync_repos.py` | Auditar repos, sincronizar metadatos y publicar archivos de materia. |
| `scripts/sync_readme.py` | Generar el perfil con nombres del manifest y estado público de GitHub. |
| `scripts/gen_repo_readme.py` | Generar el inventario del árbol local en `docs/README.md`. |
| `scripts/__main__.py` | Índice local de scripts y módulos, sin importar sus dependencias. |

Los ejecutables usan PEP 723 y `uv run`; no requieren un proyecto Python
instalable ni `requirements.txt`. Python mínimo: 3.12.

```sh
uv run python -m scripts
uv run scripts/sync_repos.py manifest list isi --plan 2008
uv run scripts/sync_repos.py manifest validate isi
uv run scripts/sync_repos.py manifest diff isi --plan 2008
uv run scripts/sync_repos.py manifest sync isi --plan 2008
uv run scripts/sync_repos.py readmes isi --plan 2008
uv run scripts/sync_repos.py contributing
uv run scripts/sync_repos.py gitignore
```

El índice y los comandos `manifest list`, `validate` y `diff` solo leen. `manifest diff` sale con código 1
ante repos faltantes, sobrantes o descripciones diferentes.
`manifest sync`, `readmes`, `contributing` y `gitignore` son dry-run por
defecto; agregar `--apply` para publicar. `manifest sync --archive --apply`
solo puede archivar sobrantes de la carrera y el plan seleccionados.

La publicación de archivos usa una sola implementación: leer, comparar y
crear o actualizar solo si difiere. Solo una respuesta HTTP 404 se interpreta
como archivo ausente; errores de permisos, servidor o transporte se propagan.
El README autogenerado reemplaza las ediciones manuales en la próxima
sincronización manual; no existe CI que lo publique en repos de materia.

El perfil solo incluye repos públicos activos declarados en el manifest.
Obtiene hasta tres nombres de notas Markdown del último año con contenido
mediante un árbol de Git por repo. Busca el último commit de contenido entre
los diez más recientes, excluyendo commits generados de mantenimiento.
El orden es estable y la fecha cambia con la actividad de contenido.

## Workflows

| Workflow | Disparadores | Resultado |
| --- | --- | --- |
| `check.yml` | PR y push a main de scripts, tests, manifests, templates o workflows | Regresiones sin llamadas a GitHub y validación de workflows. |
| `repo-readme.yml` | Cambios de fuentes en main, semanal, dispatch y `subject-repo-updated` | Regenera perfil e inventario; publica ambos en un solo commit cuando hay diferencias. |
| `repo-sync.yml` | Mensual y dispatch | Valida todos los planes y compara el plan publicado 2008 con GitHub. Solo lectura, sin clones. |
| `link-check.yml` | PR de Markdown, semanal y dispatch | Falla ante enlaces rotos; en ejecuciones programadas crea o actualiza un único issue abierto. |
| `dependabot.yml` | Semanal | Propone actualizaciones agrupadas de GitHub Actions. |

Un solo workflow publica los dos READMEs y serializa sus ejecuciones por ref.
Antes de hacer push incorpora los cambios recientes de main con rebase;
si hay conflicto, falla para revisión. Un dispatch desde otra rama no hace push.

El token de CI tiene `contents: read` en auditoría y checks; el generador
necesita `contents: write` en el control. El chequeo de enlaces necesita
`issues: write` para reportes programados. Las operaciones manuales sobre
repos de materia requieren `ORG_ADMIN_TOKEN` o `GITHUB_TOKEN` con los permisos
correspondientes. No se almacena ningún token en archivos del repositorio.

GitHub puede deshabilitar workflows programados por inactividad. Verificar
su estado con `gh workflow list --all --repo apuntes-frre/.github`.
Si corresponde reactivar uno, después de aprobar y mergear sus cambios:
`gh workflow enable link-check.yml --repo apuntes-frre/.github`.

## Verificación y extensiones

```sh
uv run tests/test_scripts.py
```

Las pruebas cubren aislamiento de planes, errores de publicación, dry-run,
idempotencia, validación curricular, renderizado de las 71 materias,
actividad del perfil y actualización del issue de enlaces con un CLI simulado.
CI también valida los workflows con actionlint.

Para agregar una carrera, incorporar `data/<carrera>.toml`; no hay una lista
paralela de prefijos. Para publicar otro plan, crearlo manualmente con
`manifest sync --plan <año> --apply` y agregarlo explícitamente a la auditoría
solo cuando deba existir en GitHub. El plan 2023 aún no se publica automáticamente.
