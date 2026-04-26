# 🗺️ Roadmap — Apuntes FRRE

> Documento vivo. Define la dirección de la organización `apuntes-frre` y el orden
> en que se aborda cada cambio. Para detalles arquitectónicos ver
> [`ARCHITECTURE.md`](./ARCHITECTURE.md); para el plan concreto de migración ver
> [`REFACTOR.md`](./REFACTOR.md).

## 🎯 Visión

Una organización ordenada y de bajo mantenimiento donde cualquier estudiante de la
**UTN-FRRE** pueda:

- Encontrar el material de cualquier materia en menos de tres clics.
- Saber, sin ambigüedad, a qué **carrera**, **plan de estudios** y **año de cursada**
  pertenece cada repositorio.
- Contribuir apuntes nuevos siguiendo una estructura predecible.
- Confiar en que la automatización (READMEs, sincronización de estructura, calidad
  de markdown) corre sola y sin generar ruido.

## 🧭 Principios

1. **Convención sobre configuración.** Una sola forma de nombrar repos, una sola
   estructura interna. Las excepciones se documentan, no se normalizan.
2. **Automatización idempotente.** Los workflows nunca commitean si no hay un
   cambio real de contenido.
3. **Español primero.** Todo el contenido público (READMEs, issues, PRs, docs)
   se escribe en español. Términos técnicos en inglés se mantienen pero se
   explican.
4. **Tooling moderno.** Scripts en `scripts/*.py` con cabecera **PEP 723** y
   ejecutados con `uv run`. Sin `requirements.txt`, sin `poetry`, sin bash para
   lógica no trivial.
5. **Reversible por default.** Renombres y migraciones masivas se hacen detrás
   de un script con `--dry-run` y se versionan en este repo antes de aplicarse.

## 📅 Fases

### Fase 0 — Cimientos (este PR)

- Documentación de visión, arquitectura y plan de refactor.
- Refactor del workflow de README para ejecutarse semanalmente y solo commitear
  ante cambios reales.
- Reemplazo del bash `init-repo-structure.sh` por `scripts/init_repo.py` con
  PEP 723.
- Workflows transversales: `markdown-lint`, `link-check`, `stale`, `repo-sync`.

### Fase 1 — Adopción de la convención de nombres

- Adoptar `<carrera>-<plan>-<slug>` (ej. `isi-2008-analisis-matematico-i`).
- Renombrar los 15 repos `isi-*` existentes según el plan 2008.
- GitHub redirige automáticamente el nombre viejo al nuevo, pero igualmente:
  - Anunciar en el README de la organización.
  - Actualizar enlaces internos vía `scripts/sync_repos.py --update-links`.

### Fase 2 — Aplanado de estructura interna

- Migrar repos al layout flat: `notes/<año>/{teoria,practica}/`, sin
  `tema1/tema2` placeholders.
- Mantener `examples/`, `study-guides/`, `resources/` solo si tienen contenido
  real (no `.gitkeep`).
- Script: `scripts/init_repo.py --migrate <repo>`.

### Fase 3 — Plan de estudios 2023

Cuando UTN publique materias del plan 2023, crear repos paralelos
`isi-2023-<slug>`. Los del 2008 se preservan como histórico.

### Fase 4 — Otras carreras

Habilitar prefijos adicionales (`lic-`, `tec-`, etc.) reutilizando la misma
infraestructura. Sin cambios en scripts ni workflows: la convención lo soporta
de raíz.

## 📊 Indicadores de éxito

| Indicador                                       | Meta             |
| ----------------------------------------------- | ---------------- |
| Repos siguiendo `<carrera>-<plan>-<slug>`       | 100% (Fase 1)    |
| Commits automáticos vacíos por mes              | 0                |
| Tiempo medio de un PR de apuntes hasta merge    | < 7 días         |
| Cobertura de `study-guides/` por materia activa | ≥ 1 por cuatri.  |
| Workflows fallando en `main`                    | 0                |

## 🚫 No-objetivos

- **No** somos un sistema de gestión de cursada: no tracking de notas, ni
  calendarios académicos.
- **No** es un Wiki: el contenido vive en archivos versionados, no en
  GitHub Wikis.
- **No** sustituimos al campus virtual de la UTN.

## 🔗 Referencias

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — diseño técnico.
- [`REFACTOR.md`](./REFACTOR.md) — pasos concretos de migración.
- [`../profile/README.md`](../profile/README.md) — vista pública de la
  organización.
