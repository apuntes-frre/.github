<!-- AUTOGENERADO por scripts/gen_repo_readme.py desde el estado del repo.
     No editar a mano: se sobrescribe en el próximo run de CI. -->
# .github — repo de control de apuntes-frre

Repositorio central de configuración y automatización de la organización de
apuntes de la **UTN-FRRE**. Define convenciones, plantillas, scripts y workflows
para todos los repos de materia. Detalle en
[`ROADMAP.md`](ROADMAP.md) y [`ARCHITECTURE.md`](ARCHITECTURE.md).

> Este inventario se regenera automáticamente: refleja exactamente qué hay hoy
> en el repo.

## 🗂️ Estructura

```text
.github/
├── AGENTS.md / CLAUDE.md   # guías para colaboradores y agentes
├── data/                   # manifests curriculares (fuente de verdad)
├── docs/                   # documentación de la organización
├── profile/                # README público de la organización (autogenerado)
├── scripts/                # automatización (PEP 723, `uv run`)
├── templates/              # plantillas Jinja de los READMEs
└── .github/workflows/      # CI/CD del repo de control
```

## 🐍 Scripts (`scripts/`)

Ejecutar con `uv run scripts/<nombre>` (dependencias inline, PEP 723).

| Script | Propósito |
| ------ | --------- |
| `gen_repo_readme.py` | Regenera docs/README.md a partir del estado real del repo de control `.github`. |
| `init_repo.py` | Inicializa o migra la estructura interna de un repositorio de materia. |
| `sync_readme.py` | Regenera profile/README.md a partir del estado vivo de la organización. |
| `sync_repos.py` | Operaciones org-wide sobre apuntes-frre. |

## ⚙️ Workflows (`.github/workflows/`)

| Workflow | Triggers |
| -------- | -------- |
| `link-check.yml` — Link Check | schedule, workflow_dispatch, pull_request |
| `repo-readme.yml` — Repo README | push, workflow_dispatch |
| `repo-sync.yml` — Repo Structure Sync | schedule, workflow_dispatch |
| `stale.yml` — Stale Issues & PRs | schedule, workflow_dispatch |
| `update-profile-readme.yml` — Update Profile README | schedule, workflow_dispatch, repository_dispatch |

## 📊 Manifests (`data/`)

- `isi.toml`

## 🧩 Plantillas (`templates/`)

- `profile_readme.md.j2`
- `repo_readme.md.j2`
- `subject_readme.md.j2`

## 📚 Documentación (`docs/`)

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`ROADMAP.md`](ROADMAP.md)
