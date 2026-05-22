# 🏛️ Arquitectura — Apuntes FRRE

## 📌 Resumen

La organización `apuntes-frre` se compone de **un repo de control** (este,
`.github`) y **N repos de materia**. El repo de control define convenciones,
plantillas y workflows; los repos de materia contienen únicamente apuntes,
ejemplos, guías y recursos.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                       Organización: apuntes-frre                         │
│                                                                          │
│   ┌──────────────────────┐         ┌──────────────────────────────────┐  │
│   │   .github (control)  │ ──────▶ │  isi-2008-base-datos             │  │
│   │                      │         │  isi-2008-redes-datos            │  │
│   │  • docs/             │         │  isi-2008-analisis-matematico-i  │  │
│   │  • profile/          │         │  isi-2008-…                      │  │
│   │  • scripts/*.py      │         │                                  │  │
│   │  • .github/workflows │         │  Cada uno: notes/ examples/      │  │
│   └──────────────────────┘         │  study-guides/ resources/        │  │
│             │                      └──────────────────────────────────┘  │
│             │ workflows usan PyGithub                                    │
│             ▼                                                            │
│   ┌──────────────────────┐                                               │
│   │  GitHub API          │                                               │
│   │  (lectura org-wide,  │                                               │
│   │   sync de estructura)│                                               │
│   └──────────────────────┘                                               │
└──────────────────────────────────────────────────────────────────────────┘
```

## 🧱 Componentes

### 1. Repo de control `.github`

| Path                                 | Propósito                                                 |
| ------------------------------------ | --------------------------------------------------------- |
| `profile/README.md`                  | Vista pública de la organización (auto-generada).         |
| `profile/README.md.jinja2`           | Plantilla de la vista pública.                            |
| `docs/`                              | Documentación: roadmap, arquitectura, plan de refactor.   |
| `data/<carrera>.toml`                | Manifest curricular (single source of truth).             |
| `data/sources/`                      | PDFs originales del diseño curricular.                    |
| `scripts/*.py`                       | Automatización (PEP 723, ejecutado con `uv run`).         |
| `.github/workflows/*.yml`            | CI/CD del repo de control.                                |
| `.github/copilot-instructions.md`    | Guías de IA para colaboradores.                           |

### 1.1 Manifest curricular `data/<carrera>.toml`

Es la **única fuente de verdad** para el diseño curricular de cada carrera.
Las herramientas (`init_repo.py`, `sync_repos.py`, `actualizar_readme.py`)
leen este archivo en lugar de inferir desde nombres de repos o descripciones.

Cada manifest contiene:

- Datos generales de la carrera (`[carrera]`).
- Uno o más planes de estudios (`[planes.<año>]`) con su ordenanza y estado.
- Cada plan declara sus materias bajo `[planes.<año>.materias.<slug>]` con
  metadatos: `orden`, `nivel`, `hs-semanales`, `area`, `bloque`, `integradora`.
- Las correlativas se referencian por **slug** (no por número de orden), para
  que el grafo sobreviva renumeraciones entre planes:
  - `correlativas-cursar-cursadas`
  - `correlativas-cursar-aprobadas`
  - `correlativas-rendir-aprobadas`
  - `correlativas-rendir-todas` (booleano, para Proyecto Final)

Operaciones disponibles:

```sh
uv run scripts/sync_repos.py manifest list isi --plan 2008
uv run scripts/sync_repos.py manifest validate isi
uv run scripts/sync_repos.py manifest diff isi --plan 2008
```

### 2. Repos de materia `<carrera>-<plan>-<slug>`

Cada repo es **autocontenido**. La estructura objetivo es:

```text
isi-2008-base-datos/
├── README.md                ← generado por scripts/init_repo.py
├── notes/
│   └── <año-calendario>/
│       ├── teoria/          ← .md por tema, sin placeholders
│       └── practica/
├── examples/                ← solo si hay contenido real
├── study-guides/            ← guías de estudio para finales
└── resources/
    ├── common/              ← bibliografía, papers, links
    └── <año-calendario>/
```

> Diferencia clave con la estructura previa: **no se crean carpetas vacías**
> con `.gitkeep`. Las carpetas aparecen cuando hay material.

## 🏷️ Convención de nombres

```text
<carrera>-<plan>-<slug>
```

| Segmento  | Valores                          | Ejemplo                 |
| --------- | -------------------------------- | ----------------------- |
| `carrera` | `isi`, `lic`, `tec`, …           | `isi`                   |
| `plan`    | Año del plan de estudios UTN     | `2008`, `2023`          |
| `slug`    | Nombre de la materia, kebab-case | `analisis-matematico-i` |

**Reglas del slug:**

- Todo en minúsculas, ASCII (sin tildes ni `ñ`).
- Numerales romanos en minúsculas (`-i`, `-ii`, `-iii`).
- Conservar palabras significativas; omitir artículos (`-de-`, `-y-` opcional
  según legibilidad).

**Ejemplos:**

| Materia                              | Repo                                       |
| ------------------------------------ | ------------------------------------------ |
| Análisis Matemático I                | `isi-2008-analisis-matematico-i`           |
| Base de Datos                        | `isi-2008-base-de-datos`                   |
| Algoritmos y Estructuras de Datos    | `isi-2008-algoritmos-y-estructuras-datos`  |
| Sistemas Operativos                  | `isi-2008-sistemas-operativos`             |

## 🔁 Pipeline de automatización

| Workflow                      | Trigger                          | Acción                                                   |
| ----------------------------- | -------------------------------- | -------------------------------------------------------- |
| `update-profile-readme.yml`   | `cron` semanal + `dispatch`      | Regenera `profile/README.md`. Commit solo si hay diff.   |
| `repo-sync.yml`               | `dispatch` + `cron` mensual      | Aplica `init_repo.py` a todos los repos de materia.      |
| `markdown-lint.yml`           | `pull_request` + `push` a `main` | Lint de markdown en docs/ y profile/.                    |
| `link-check.yml`              | `cron` semanal + `dispatch`      | Verifica enlaces rotos en docs.                          |
| `stale.yml`                   | `cron` diario                    | Marca y cierra issues/PRs sin actividad.                 |

## 🛠️ Tooling

### Scripts en Python

Todos los scripts ejecutables viven en `scripts/` y siguen este contrato:

- **Cabecera PEP 723** declara dependencias inline.
- Se ejecutan con `uv run scripts/<nombre>.py [args]`.
- Soportan `--dry-run` cuando producen efectos sobre repos remotos.
- Logs vía `rich` con códigos de salida convencionales (0 OK, 1 error).

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "PyGithub>=2.1",
#   "rich>=13.0",
# ]
# ///
```

### Sin requirements.txt, sin Poetry

Las dependencias declaradas en cada script son **autosuficientes**. `uv`
resuelve y cachea por script. CI usa `astral-sh/setup-uv@v5`.

## 👥 Roles

| Rol             | Permisos GitHub        | Responsabilidades                                  |
| --------------- | ---------------------- | -------------------------------------------------- |
| Admin org       | Owner                  | Renombres, creación de repos, secrets de CI.       |
| Mantenedor      | Maintain en `.github`  | Reviewer de PRs en `.github`, mergea workflows.    |
| Contribuidor    | Triage o externo       | Abre PRs con apuntes en repos de materia.          |

## 🔒 Seguridad

- `GITHUB_TOKEN` con permisos mínimos por workflow (`contents: write` solo
  donde se necesita).
- Para acciones org-wide (sync de estructura) se requiere un PAT de admin
  almacenado como secret `ORG_ADMIN_TOKEN` y solo accesible al workflow
  `repo-sync.yml`.
- Sin secrets en código. Validación con `gitleaks` opcional en CI.

## 🚪 Puntos de extensión

- **Nueva carrera:** agregar prefijo a la lista en `scripts/sync_repos.py` y
  documentarlo en este archivo.
- **Nuevo plan de estudios:** ya soportado por la convención. Solo crear los
  repos `<carrera>-<plan-nuevo>-<slug>`.
- **Nuevo tipo de contenido por repo:** agregarlo a `init_repo.py` con su
  README de sección.
