# AGENTS.md

Guía para agentes de IA y colaboradores de la organización **apuntes-frre** (UTN-FRRE). Define
convenciones e idioma. Para el detalle arquitectónico ver
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Idioma

- El contenido (apuntes, READMEs, docs) se escribe en **español**.
- El **código** y los identificadores de programación van en **inglés** (nombres de
  scripts, variables, funciones).
- Los **slugs de repos** derivan del nombre **en español** de la materia,
  normalizado a ASCII (ej. `fisica-i`, `analisis-matematico-ii`). No se traducen.
- Términos técnicos pueden quedar en inglés; explicarlos en español si hace falta.

## Fuente de verdad

- [`data/<carrera>.toml`](data/) es la **única fuente de verdad** del plan curricular (materias,
  niveles, correlativas). No inferir datos desde nombres de repos ni descripciones: leer el
  manifest.
- Los READMEs de los repos de materia son **autogenerados** desde el manifest
  ([`templates/subject_readme.md.j2`](templates/subject_readme.md.j2)). No editarlos a mano:
  la sincronización manual los sobrescribe.

## Convención de nombres de repos

```text
<carrera>-<plan>-<slug>
```

- `carrera`: `isi`, `lic`, `tec`, … · `plan`: año del plan UTN (`2008`, `2023`).
- `slug`: kebab-case, ASCII (sin tildes ni `ñ`), romanos en minúscula (`-i`, `-ii`).
- Ejemplo: `isi-2008-analisis-matematico-i`.

## Estructura de un repo de materia

Layout flat, **sin carpetas vacías** ni `.gitkeep`: las carpetas aparecen cuando hay material.

```text
isi-2008-<slug>/
├── README.md                ← autogenerado desde el manifest
├── notes/<año>/teoria/
├── notes/<año>/practica/
├── examples/                ← solo si hay contenido
├── study-guides/
└── resources/common/
```

Convención de archivos: `nombre-tema.md`, `guia-estudio-tema.md`, imágenes
`nombre-tema-descripcion.png`.

Cómo cargar apuntes (conversión por formato, herramientas vía mise,
flujo de trabajo): ver [`CONTRIBUTING.md`](CONTRIBUTING.md). Se publica en cada
repo de materia con `uv run scripts/sync_repos.py contributing --apply`.

Las instrucciones Codex de las materias provienen de
[`templates/subject_agents.md`](templates/subject_agents.md). `manifest sync
--apply` instala el bootstrap al crear cada repo; `uv run scripts/sync_repos.py
agents --apply` sincroniza solo esa plantilla. `bootstrap --apply` sincroniza
AGENTS, CONTRIBUTING, preflight, validador, configuración y CI. La creación
instala el bootstrap completo; repetirlo repara una creación parcial.
Ejecutar localmente `uv run scripts/sync_repos.py` después de cambiar esas fuentes
o crear una materia fuera del script. Sin argumentos, usa la sesión autenticada
de `gh`, valida los manifests y publica el bootstrap y los READMEs en las materias
existentes declaradas. No requiere secretos de Actions ni variables de entorno.
Seguir [el flujo](docs/TRANSCRIPTION.md).

Corregir la validación en `scripts/check_transcription.py` y sus regresiones en
`tests/test_transcription.py`, no solo en la copia de una materia: una posterior
sincronización del bootstrap sobrescribe las copias distribuidas. Verificar los
casos que fallaban y las formas válidas antes de sincronizar.

## Tooling

Scripts en [`scripts/`](scripts/), PEP 723, ejecutados con `uv run`:

- `sync_repos.py` — operaciones org-wide (manifest, sync de repos, READMEs).
- `sync_readme.py` — regenera el README público del perfil.
- `gen_repo_readme.py` — regenera `docs/README.md` (inventario de este repo).
- `common.py` — módulo compartido de manifests y plantillas; no es un ejecutable.
- `inventory_sources.py` — metadatos OneDrive y notas existentes; no descarga
  todo el árbol ni interpreta nombres como prueba de cobertura.
- `transcription_preflight.py` y `check_transcription.py` — se distribuyen en
  `.github/transcription/` de las materias; usan GFM + MyST para fórmulas.

`transcription/sources.json` contiene el mapeo de fuentes, separado de
`data/*.toml` para no mezclarlo con el schema curricular. Los valores `null`
son pendientes explícitos. No inferir equivalencias entre planes 2008/2023.

`manifest validate` verifica campos, referencias y ciclos. `manifest diff`
compara solo la carrera y el plan seleccionados; sale con código 1 ante
repos faltantes, sobrantes o descripciones diferentes.
Las correlativas del plan 2023 están pendientes: no inferir que no hay requisitos.

Para verificar cambios sin acceder a GitHub: `uv run tests/test_scripts.py`.

Los subcomandos de publicación soportan dry-run; agregar `--apply` para ejecutar.
El comando sin argumentos publica directamente el bootstrap y los READMEs;
no crea ni archiva repos y conserva las personalizaciones de `.gitignore`.
