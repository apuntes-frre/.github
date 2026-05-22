# Copilot Instructions for Study Notes Organization

You are an AI assistant helping to maintain a collection of study notes and educational resources.
Follow these guidelines when assisting with this organization.

## Language Guidelines

- Usar español como idioma principal para todo el contenido
- Proporcionar respuestas y asistencia en español
- Mantener términos técnicos en inglés cuando sea necesario, pero explicarlos en español
- En caso de recursos externos en inglés, proporcionar descripciones o resúmenes en español

## Repository Structure

- Each subject should have its own dedicated repository
- Repository names should follow the format: `materia-codigo-nombre` (e.g., `mate1-analisis`,
  `prog1-programacion`)
- Every repository must include:
  - Un README.md claro en español
  - Carpetas organizadas por temas
  - Guías de estudio en formato Markdown
  - Ejemplos de código cuando aplique

## Content Guidelines

When assisting with content:

1. Usar Markdown para la documentación
2. Incluir bloques de código con etiquetas de lenguaje apropiadas
3. Organizar el contenido jerárquicamente
4. Agregar ejemplos y explicaciones relevantes en español
5. Vincular temas relacionados entre repositorios

## Main README Structure

The organization's main README should:

- List all subject repositories
- Provide quick links to each subject
- Include a brief description for each subject
- Show current study progress

## Naming Conventions

- Archivos: `nombre-tema.md`
- Imágenes: `nombre-tema-descripcion.png`
- Archivos de código: `nombre-tema.{extension}`
- Guías de estudio: `guia-estudio-tema.md`

## Content Organization

Help maintain the following structure in each repository:

```text
subject-repository/
├── README.md
├── notes/
│   ├── 2019/
│   │   ├── teoria/
│   │   │   ├── tema1/
│   │   │   ├── tema2/
│   │   │   └── recursos/
│   │   └── practica/
│   │       ├── tema1/
│   │       ├── tema2/
│   │       └── recursos/
│   ├── 2020/
│   │   ├── teoria/
│   │   │   ├── tema1/
│   │   │   ├── tema2/
│   │   │   └── recursos/
│   │   └── practica/
│   │       ├── tema1/
│   │       ├── tema2/
│   │       └── recursos/
│   └── [año-actual]/
│       ├── teoria/
│       │   ├── tema1/
│       │   ├── tema2/
│       │   └── recursos/
│       └── practica/
│           ├── tema1/
│           ├── tema2/
│           └── recursos/
├── examples/
│   ├── 2019/
│   │   ├── teoria/
│   │   └── practica/
│   ├── 2020/
│   │   ├── teoria/
│   │   └── practica/
│   └── [año-actual]/
│       ├── teoria/
│       └── practica/
├── study-guides/
│   ├── 2019/
│   │   ├── teoria/
│   │   └── practica/
│   ├── 2020/
│   │   ├── teoria/
│   │   └── practica/
│   └── [año-actual]/
│       ├── teoria/
│       └── practica/
└── resources/
    ├── common/
    │   ├── teoria/
    │   └── practica/
    ├── 2019/
    │   ├── teoria/
    │   └── practica/
    ├── 2020/
    │   ├── teoria/
    │   └── practica/
    └── [año-actual]/
        ├── teoria/
        └── practica/
```

## Versionado Temporal

- Cada año académico debe tener su propia carpeta dentro de las secciones principales
- Dentro de cada año, el contenido se divide en:
  - `teoria/`: Material teórico, conceptos y explicaciones
  - `practica/`: Ejercicios, trabajos prácticos y aplicaciones
- La carpeta `common` en resources contiene material común a todos los años, también dividida en
  teoría y práctica
- El README principal debe incluir un índice al material más reciente
- Mantener el material histórico organizado por año para referencia
- Incluir en cada carpeta anual un README.md que describa los cambios específicos de ese año

Always ensure content is educational, clear, and well-structured.
