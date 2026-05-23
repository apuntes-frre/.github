# 🗺️ Roadmap — Apuntes FRRE

> Documento vivo. Define la dirección de la organización `apuntes-frre`, lleva
> el registro de lo ya refactorado (ver **Milestones**) y el orden de lo que
> sigue. Para el detalle técnico ver [`ARCHITECTURE.md`](./ARCHITECTURE.md).

## 🎯 Visión

Una organización ordenada y de bajo mantenimiento donde cualquier estudiante de la
**UTN-FRRE** pueda:

- Encontrar el material de cualquier materia en menos de tres clics.
- Saber, sin ambigüedad, a qué **carrera**, **plan de estudios** y **año de cursada**
  pertenece cada repositorio.
- Contribuir apuntes nuevos siguiendo una estructura predecible.
- Confiar en que la automatización (READMEs, sincronización de estructura) corre
  sola y sin generar ruido.

## 🧭 Principios

1. **Convención sobre configuración.** Una sola forma de nombrar repos, una sola
   estructura interna. Las excepciones se documentan, no se normalizan.
2. **Manifest como única fuente de verdad.** `data/<carrera>.toml` define el plan
   curricular; las herramientas leen de ahí, no infieren desde nombres de repos.
3. **Automatización idempotente.** Los workflows nunca commitean si no hay un
   cambio real de contenido.
4. **Español primero.** Todo el contenido público se escribe en español; el
   código y los identificadores, en inglés.
5. **Tooling moderno.** Scripts en `scripts/*.py` con cabecera **PEP 723**,
   ejecutados con `uv run`. Sin `requirements.txt`, sin `poetry`, sin bash para
   lógica no trivial.
6. **Reversible por default.** Las operaciones sobre la org corren en dry-run y
   requieren `--apply` para ejecutarse.

## ✅ Milestones — lo refactorado hasta ahora

### M0 · Cimientos

- Documentación de visión y arquitectura (`docs/`).
- Reemplazo del bash `init-repo-structure.sh` por `scripts/init_repo.py` (PEP 723,
  con `init` y `migrate`).
- `scripts/sync_readme.py`: regenera el README del perfil en memoria y escribe
  solo si difiere (sin commits vacíos por fecha).
- `update-profile-readme.yml` pasa a cron semanal con guard `git diff --quiet`.
- Workflows transversales: `link-check`, `stale`, `repo-sync`.
  (Se probó `markdown-lint` y se retiró: la estructura está en alpha y los
  formatos van a cambiar.)

### M1 · Manifest curricular

- `data/isi.toml` como única fuente de verdad, con los planes **2008** y **2023**
  completos (materias, niveles, horas, correlativas por slug).
- Comandos `manifest list` / `validate` / `diff` / `sync` en `scripts/sync_repos.py`.

### M2 · Convención de nombres y poblado de la org

- Adoptado `<carrera>-<plan>-<slug>` (ej. `isi-2008-analisis-matematico-i`).
- **35 repos del plan 2008 creados** desde el manifest vía `manifest sync --apply`.
- Los **15 repos legacy** (nombres viejos, plantillas vacías) fueron **eliminados**
  — no renombrados — porque su contenido era descartable. La org coincide hoy con
  el manifest 2008 (`manifest diff` → ✓).

### M3 · READMEs autogenerados desde el manifest

- `templates/profile_readme.md.j2` (vista pública) y
  `templates/subject_readme.md.j2` (por materia).
- Comando `sync_repos.py readmes`: renderiza y publica el README de cada repo de
  materia; idempotente, sobrescribe ediciones manuales.
- Sin CI para los repos de materia: se sincronizan **a mano** tras editar el
  manifest (evita gestionar un token de org). Ver el docstring de
  `scripts/sync_readme.py` para el detalle de cada tipo de README.

### M4 · Guías de colaboración

- `AGENTS.md` + `CLAUDE.md` reemplazan a `copilot-instructions.md` (que describía
  la estructura vieja).
- Plantillas consolidadas en `templates/`.

## 📅 Próximas fases

### Plan de estudios 2023

El manifest ya tiene el plan 2023 cargado. Falta crear los repos:
`uv run scripts/sync_repos.py manifest sync isi --plan 2023 --apply`.
Los del 2008 se preservan como histórico.

### Scaffolding y contenido de los repos

- Los 35 repos tienen README autogenerado pero estructura vacía. Pendiente:
  hacer que `init-all` (o un modo `--push`) deje el layout `notes/<año>/…` en
  cada repo, y empezar a cargar apuntes.

### Otras carreras

Habilitar prefijos `lic-`, `tec-`, etc.: agregar `data/<carrera>.toml` y el
prefijo a `KNOWN_CARRERAS`. La convención y los workflows ya lo soportan.

## 📊 Indicadores de éxito

| Indicador                                       | Meta             | Estado    |
| ----------------------------------------------- | ---------------- | --------- |
| Repos siguiendo `<carrera>-<plan>-<slug>`       | 100%             | ✅ (2008) |
| Commits automáticos vacíos por mes              | 0                | ✅        |
| READMEs de materia generados desde el manifest  | 100%             | ✅ (2008) |
| Cobertura de `study-guides/` por materia activa | ≥ 1 por cuatri.  | ⏳        |
| Workflows fallando en `main`                    | 0                | ✅        |

## 🚫 No-objetivos

- **No** somos un sistema de gestión de cursada: no tracking de notas, ni
  calendarios académicos.
- **No** es un Wiki: el contenido vive en archivos versionados.
- **No** sustituimos al campus virtual de la UTN.

## 🔗 Referencias

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — diseño técnico.
- [`../AGENTS.md`](../AGENTS.md) — convenciones para colaboradores y agentes.
- [`../profile/README.md`](../profile/README.md) — vista pública de la organización.
