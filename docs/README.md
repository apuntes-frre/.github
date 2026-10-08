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
├── templates/              # plantillas de READMEs y .gitignore
├── tests/                  # regresiones sin llamadas a GitHub
└── .github/workflows/      # CI/CD del repo de control
```

## 🐍 Scripts y módulos (`scripts/`)

Ejecutar los scripts con `uv run scripts/<nombre>` (dependencias inline, PEP 723).
`common.py` es un módulo compartido; no se ejecuta directamente.
Las regresiones se verifican con `uv run tests/test_scripts.py`.

| Script | Propósito |
| ------ | --------- |
| `common.py` | Manifest curricular, nombres de repos y plantillas compartidos. |
| `gen_repo_readme.py` | Regenera docs/README.md a partir del estado real del repo de control `.github`. |
| `sync_readme.py` | Regenera profile/README.md a partir del estado vivo de la organización. |
| `sync_repos.py` | Audita y sincroniza repos de materia desde el manifest curricular. |

## ⚙️ Workflows (`.github/workflows/`)

| Workflow | Triggers |
| -------- | -------- |
| `check.yml` — Check Scripts | pull_request, push |
| `link-check.yml` — Link Check | schedule, workflow_dispatch, pull_request |
| `repo-readme.yml` — Update READMEs | push, schedule, workflow_dispatch, repository_dispatch |
| `repo-sync.yml` — Repository Audit | schedule, workflow_dispatch |

## 📊 Manifests (`data/`)

- `isi.toml`

## 🧩 Plantillas (`templates/`)

- `profile_readme.md.j2`
- `repo_readme.md.j2`
- `subject.gitignore`
- `subject_readme.md.j2`

## 📚 Documentación (`docs/`)

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`ROADMAP.md`](ROADMAP.md)
