# 🗺️ Roadmap — Apuntes FRRE

La organización busca material de estudio fácil de encontrar y mantener,
con automatización predecible. El diseño técnico está en
[ARCHITECTURE.md](ARCHITECTURE.md).

## Principios

- El manifest curricular es la única fuente de verdad.
- Contenido en español; código e identificadores en inglés.
- Las carpetas aparecen con material real, sin placeholders.
- Generar y publicar solo cuando cambie el contenido.
- Operaciones remotas en dry-run por defecto, publicación explícita con `--apply`.
- Conservar el plan 2008 al incorporar planes nuevos.

## Trabajo realizado

### M0–M4 · Organización y manifest

- Documentación de convenciones, arquitectura y contribuciones.
- Manifests de los planes 2008 y 2023, con sus PDFs de origen.
- 35 repos de materias del plan 2008 con la convención `<carrera>-<plan>-<slug>`.
- Retiro de los 15 repos legacy descartables.
- READMEs de materia desde el manifest y perfil generado desde GitHub.
- Plantillas centralizadas y publicación manual de README, CONTRIBUTING y .gitignore.
- Guías `AGENTS.md` y `CLAUDE.md`.

### M5 · Refactor de scripts y automatización

- Selección de repos limitada a la carrera y el plan solicitados, incluso al archivar.
- Validación de campos, orden único, referencias y ciclos antes de publicar.
- Correlativas pendientes del plan 2023 señaladas explícitamente.
- Una implementación de publicación idempotente; errores de API no equivalen a archivo ausente.
- Perfil con nombres del manifest y nombres de notas reales.
- Perfil e inventario publicados por un único workflow, con triggers de sus fuentes.
- Auditoría mensual de solo lectura, sin clones temporales descartables.
- Reporte recurrente de enlaces con un único issue abierto y fallos visibles en PRs.
- Regresiones y validación de workflows en CI.
- Retiro del ejemplo PAT, workflow stale y herramientas legacy de scaffolding/renombrado.
  Los 35 repos fueron comprobados sin `.gitkeep` antes de retirar la migración.

## Próximos pasos

### Publicación del plan 2023

El manifest contiene 36 materias. Sus correlativas de FRRE están pendientes;
completar y verificar la fuente antes de presentar el plan como completo.
Crear sus repos solo mediante una operación manual aprobada:

```sh
uv run scripts/sync_repos.py manifest sync isi --plan 2023
uv run scripts/sync_repos.py manifest sync isi --plan 2023 --apply
uv run scripts/sync_repos.py readmes isi --plan 2023 --apply
```

El plan 2008 se conserva. La auditoría programada compara únicamente el plan
publicado 2008 hasta que se decida incorporar el 2023.

### Contenido de estudio

Cargar apuntes en los repos existentes según CONTRIBUTING.md. Crear
`notes/<año>/`, `study-guides/` y `resources/` cuando haya archivos reales.

### Otras carreras

Agregar y validar `data/<carrera>.toml`, conservar sus fuentes y publicar
los repos de sus planes de manera explícita.

## Comprobaciones operativas

- `uv run tests/test_scripts.py`: regresiones de scripts sin llamadas a GitHub.
- `manifest validate`: integridad estructural, referencias y ciclos.
- `manifest diff`: coincidencia del plan publicado con repos y descripciones.
- Revisar Actions y reactivar los workflows retenidos que GitHub deshabilite
  por inactividad, una vez aprobados sus cambios.

El estado operativo se verifica en cada revisión; esta hoja de ruta no
asegura que todos los workflows estén activos o que no haya fallos recientes.

## Alcance

Los apuntes viven en archivos versionados. Este proyecto no administra
notas, calendarios académicos ni sustituye al campus virtual.
