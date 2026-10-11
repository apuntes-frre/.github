# Delegar transcripciones

El flujo se valida primero en esta laptop, que tiene OneDrive y herramientas
mise. Un agente remoto necesita acceso propio a los originales y su toolchain.
Una sesión nueva debe comenzar dentro del clone/worktree de la materia para leer
su `AGENTS.md`.

## Preparación de la organización

```sh
uv run scripts/sync_repos.py auth
uv run scripts/sync_repos.py bootstrap
uv run scripts/sync_repos.py bootstrap --apply
uv run scripts/sync_repos.py bootstrap --apply
```

La segunda aplicación debe informar cero escrituras. Se distribuyen AGENTS,
CONTRIBUTING, preflight, validador, configuración mise/lint y el workflow
`Validate Transcription`. `manifest sync --apply` instala los mismos archivos al
crear una materia; bootstrap repara instalaciones parciales.

### Credencial para Actions

La sesión autenticada de `gh` y el secreto de Actions son credenciales
distintas. `PAT_TOKEN` vencido produce HTTP 401 aunque `gh auth status`
funcione. El workflow comprueba el secreto antes de publicar; todavía requiere
permisos de escritura.

Crear un token fine-grained dedicado con propietario `apuntes-frre`, acceso a
**All repositories** para cubrir futuras materias, **Contents: Read and write**,
**Workflows: Read and write** y Metadata de lectura. No necesita permisos de
administración o borrado: el workflow sincroniza archivos, no crea repos. Los
permisos están documentados en la
[API Contents de GitHub](https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents).

GitHub permite
[prellenar el formulario](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#pre-filling-fine-grained-personal-access-token-details-using-url-parameters),
pero la creación se realiza en ajustes de la cuenta. No guardar el token OAuth
amplio de la CLI como sustituto permanente del token dedicado.

Tras generar el token, ingresarlo en el prompt oculto de:

```sh
gh secret set PAT_TOKEN --repo apuntes-frre/.github
gh workflow run subject-agents.yml --repo apuntes-frre/.github --ref main
gh run list --repo apuntes-frre/.github --workflow subject-agents.yml --limit 1
```

No pegar credenciales en chats, argumentos de comandos o archivos versionados.
Revisar logs y repetir el workflow para probar idempotencia. Renovar el token
antes de su expiración; `gh` puede almacenar el secreto, pero no crear un token
fine-grained mediante una operación CLI.

## Inventario y asignación

[sources.json](../transcription/sources.json) vincula nombres reales de carpetas
con repos. Sus `null` requieren identificar la fuente; electivas como BDA o
Taller Álgebra no se asignan automáticamente a una materia/plan.

```sh
uv run scripts/inventory_sources.py --output /ruta/temporal/source-inventory.json
```

El informe incluye años/UT/prácticas como pistas de nombres, originales,
material previo en clones con origin verificado, estado cloud-only y paquetes de
software/build separados. No descarga los 75 mil archivos del árbol. Páginas y
hashes permanecen pendientes hasta leer fuentes concretas. La pertenencia a una
materia y las versiones se comprueban dentro del documento.

Cada asignación incluye repo, año de archivo y año impreso, UT/práctica,
originales exactos, material previo, rama/base y alcance de publicación. Usar un
worktree por materia y conservar cambios locales previos. Inventariar
suplementos y duplicados por hash/contenido. No resolver ejercicios vacíos.

## Inicio y verificación en una materia

```sh
mise run documents:check
mise exec -- uv run .github/transcription/preflight.py --engine pymupdf4llm \
  --work-dir /ruta/temporal/nueva /ruta/OneDrive/fuente.pdf
```

El preflight prueba el arranque de herramientas, materializa fuentes
seleccionadas, verifica SHA-256 y cuenta páginas PDF. Para Docling, agregar
`--download-models` y comprobar una conversión real; modelos opcionales como
fórmulas requieren su prueba específica. En OCR, se comprueba el idioma
solicitado, por defecto español. Mantener Python estable para los entornos:
`python/latest` puede cambiar de ABI y dejar los paquetes invisibles.

Seguir las rutas por formato en AGENTS/CONTRIBUTING. Comparar todas las páginas,
hojas o diapositivas; contrastar texto PDF con `pdftotext -layout` y vistas de
`pdftoppm`. Registrar originales, SHA-256, motores, conteos, páginas revisadas y
pérdidas en `resources/<año>/fuentes.md`. Una extracción exitosa no demuestra
fidelidad. Registrar medios enlazados ausentes, sin inventarlos.

```sh
mise exec -- mdformat --extensions gfm --extensions myst --wrap 80 \
  --compact-tables notes/2026/teoria/tema.md
mise -C .github/transcription exec -- uv run check.py --self-test
mise -C .github/transcription exec -- uv run check.py --base origin/main
```

MyST agrega parsing de matemática con delimitadores GitHub. Las regresiones
comprueban negación, fracciones, subíndices, matrices, tablas GFM y listas de
tareas. El validador exige preservación del formato, enlaces relativos/anclas,
imágenes, ausencia de marcadores defectuosos y KaTeX sin errores. Al eliminar
medios se detectan referencias afectadas sin formatear notas antiguas.

CI usa los mismos scripts y versiones fijadas con el base SHA del PR o el commit
anterior al push. La validación no exige reformatear toda la materia ni
determina si una fórmula coincide con el original. La revisión documental
completa sigue siendo condición de entrega.
