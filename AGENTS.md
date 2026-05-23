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
  ([`templates/subject_readme.md.j2`](templates/subject_readme.md.j2)). No editarlos a mano: CI los
  sobrescribe.

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

## Tooling

Scripts en [`scripts/`](scripts/), PEP 723, ejecutados con `uv run`:

- `sync_repos.py` — operaciones org-wide (manifest, sync de repos, READMEs).
- `sync_readme.py` — regenera el README público del perfil.
- `gen_repo_readme.py` — regenera `docs/README.md` (inventario de este repo).
- `init_repo.py` — scaffolding de estructura por repo.

Los que escriben en la org soportan dry-run; agregar `--apply` para ejecutar.
