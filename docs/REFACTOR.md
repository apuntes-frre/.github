# 🛠️ Plan de Refactor — Apuntes FRRE

> Acompaña a [`ROADMAP.md`](./ROADMAP.md) y [`ARCHITECTURE.md`](./ARCHITECTURE.md).
> Este documento lista los pasos concretos para llevar la organización del
> estado actual al objetivo.

## 🔍 Estado actual (snapshot)

- **15 repositorios de materia**, todos prefijados `isi-` (inconsistente con
  `copilot-instructions.md`, que sugería `materia-codigo-nombre`).
- Estructura interna profunda con `tema1/tema2` placeholders y `.gitkeep`.
- `init-repo-structure.sh` (bash) duplica lógica de `scripts/actualizar_readme.py`
  (Python).
- Workflow `update-profile-readme.yml` corre **diariamente** y produce commits
  vacíos porque la plantilla incluye la fecha actual: cada ejecución cambia un
  byte.
- Sin lint de markdown, sin chequeo de links, sin gestión de stale issues.

## 🎯 Estado objetivo

| Aspecto              | Antes                                | Después                                              |
| -------------------- | ------------------------------------ | ---------------------------------------------------- |
| Naming               | `isi-<slug>`                         | `<carrera>-<plan>-<slug>` (ej. `isi-2008-…`)         |
| Layout               | `notes/<año>/teoria/tema1/.gitkeep`  | `notes/<año>/teoria/<archivo>.md` (sin placeholders) |
| Init                 | bash + Python (duplicado)            | un solo script `scripts/init_repo.py` (PEP 723)      |
| Sync org-wide        | manual                               | `scripts/sync_repos.py` + workflow `repo-sync.yml`   |
| README profile       | regenerado a diario, commits vacíos  | semanal, commit solo ante diff real                  |
| Calidad de docs      | sin CI                               | `markdown-lint`, `link-check`                        |

## 🚦 Fases de migración

### Fase 0 — Cimientos (este PR)

Sin cambios destructivos. Todo lo que aterriza acá es aditivo o reemplaza
infra que no afecta a los repos de materia.

- [x] `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/REFACTOR.md`.
- [x] Refactor de `profile/README.md.jinja2`: la fecha pasa al footer y se
      escribe **solo si** otro contenido cambió, evitando diffs por fecha.
- [x] Refactor de `scripts/actualizar_readme.py`: regenera el README en
      memoria, compara con el archivo, y escribe solo si difiere. La fecha
      se calcula a partir del `mtime` del archivo si nada cambió.
- [x] Reemplazo de `init-repo-structure.sh` por `scripts/init_repo.py`
      (PEP 723, soporta `--dry-run`, `--migrate`).
- [x] `scripts/sync_repos.py`: aplica `init_repo.py` a todos los repos
      `<carrera>-*` de la org.
- [x] Workflows nuevos: `markdown-lint.yml`, `link-check.yml`, `stale.yml`,
      `repo-sync.yml`.
- [x] `update-profile-readme.yml` pasa a cron **semanal** + commit con
      `git diff --quiet` como guard.

### Fase 1 — Renombre de los 15 repos existentes (PR siguiente)

Tabla de renombres propuestos (plan **2008**, salvo que UTN indique otro):

| Repo actual                            | Repo objetivo                                  |
| -------------------------------------- | ---------------------------------------------- |
| `isi-algoritmos-estructuras-datos`     | `isi-2008-algoritmos-y-estructuras-datos`      |
| `isi-analisis-matematico-ii`           | `isi-2008-analisis-matematico-ii`              |
| `isi-analisis-sistemas`                | `isi-2008-analisis-de-sistemas`                |
| `isi-arquitectura-computadoras`        | `isi-2008-arquitectura-de-computadoras`        |
| `isi-base-datos`                       | `isi-2008-base-de-datos`                       |
| `isi-diseno-sistemas`                  | `isi-2008-diseno-de-sistemas`                  |
| `isi-economia`                         | `isi-2008-economia`                            |
| `isi-fisica-ii`                        | `isi-2008-fisica-ii`                           |
| `isi-ingenieria-calidad`               | `isi-2008-ingenieria-y-calidad-de-software`    |
| `isi-investigacion-operativa`          | `isi-2008-investigacion-operativa`             |
| `isi-paradigmas-programacion`          | `isi-2008-paradigmas-de-programacion`          |
| `isi-redes-datos`                      | `isi-2008-redes-de-datos`                      |
| `isi-simulacion`                       | `isi-2008-simulacion`                          |
| `isi-sintaxis-semantica`               | `isi-2008-sintaxis-y-semantica-de-lenguajes`   |
| `isi-sistemas-operativos`              | `isi-2008-sistemas-operativos`                 |

**Procedimiento:**

1. Ejecutar `uv run scripts/sync_repos.py rename --plan 2008 --dry-run`
   para validar la tabla.
2. Aplicar con `--apply` (requiere `ORG_ADMIN_TOKEN`).
3. GitHub crea redirects automáticos del nombre viejo al nuevo: links externos
   no se rompen.
4. Regenerar `profile/README.md` (workflow se dispara por `repository_dispatch`).

**Riesgos:**

- Forks personales que tengan el remote viejo: se resuelve con
  `git remote set-url`. Se documenta en el README de la org.
- Webhooks externos hardcodeados al nombre viejo: revisar antes de aplicar.

### Fase 2 — Aplanado de estructura interna

Para cada repo:

1. `uv run scripts/init_repo.py --migrate <repo> --dry-run` lista qué se
   moverá / borrará.
2. Aplicar: elimina `.gitkeep` huérfanos, colapsa `tema1/tema2` vacíos,
   conserva archivos reales en su ubicación nueva.
3. PR automático por repo, etiquetado `chore/migration`.

### Fase 3 — Plan 2023 (cuando aplique)

Cuando UTN publique el cambio de plan:

1. Crear `isi-2023-<slug>` para cada materia nueva.
2. Marcar los `isi-2008-*` como `archived: false` pero documentar fin de
   actualización en su README.
3. Actualizar `profile/README.md.jinja2` para agrupar por plan.

## 🧪 Verificación post-cambio

Cada fase debe terminar con:

- [ ] `gh repo list apuntes-frre --limit 100 --json name | jq '.[].name'`
      coincide con la convención.
- [ ] `update-profile-readme` no genera commits vacíos durante 7 días seguidos.
- [ ] `markdown-lint` y `link-check` en verde sobre `main`.
- [ ] `profile/README.md` muestra agrupación correcta por plan / año.

## ↩️ Rollback

- **Renombres:** GitHub mantiene el nombre histórico como redirect; revertir
  es otro `rename` al nombre original.
- **Migración de layout:** cada PR de migración es independiente y se puede
  revertir con `git revert`.
- **Workflows:** versionados en este repo; revertir el commit basta.
