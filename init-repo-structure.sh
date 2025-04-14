#!/bin/bash
# Script para inicializar la estructura base de un repositorio de apuntes

CURRENT_YEAR="2025"

# Crear estructura base
mkdir -p notes/$CURRENT_YEAR/{teoria,practica}/{tema1,tema2,recursos}
mkdir -p examples/$CURRENT_YEAR/{teoria,practica}
mkdir -p study-guides/$CURRENT_YEAR/{teoria,practica}
mkdir -p resources/{common,$CURRENT_YEAR/{teoria,practica}}

# Crear README base
cat > README.md << 'END'
# 📚 [Nombre de la Materia]

## 📝 Descripción
[Descripción de la materia]

## 📂 Estructura del Repositorio

- 📁 **notes/**: Apuntes de clase organizados por año
  - 📚 **teoria/**: Contenido teórico por temas
  - 💻 **practica/**: Ejercicios y trabajos prácticos
- 📁 **examples/**: Ejemplos prácticos y código
  - 📚 **teoria/**: Ejemplos de conceptos teóricos
  - 💻 **practica/**: Ejemplos de implementación práctica
- 📖 **study-guides/**: Guías de estudio y material de práctica
  - 📚 **teoria/**: Guías de estudio teóricas
  - 💻 **practica/**: Guías de ejercicios prácticos
- 📁 **resources/**: Recursos adicionales y material de referencia
  - 📚 **teoria/**: Recursos para contenido teórico
  - 💻 **practica/**: Recursos para trabajos prácticos

## 🗓️ Contenido Actual (2025)

### 📚 Temas Teóricos
- [Tema 1]
- [Tema 2]

### 💻 Temas Prácticos
- [Tema 1]
- [Tema 2]

### 📖 Guías de Estudio
- [Por agregar]

### 💻 Ejemplos
- [Por agregar]

## 🤝 Contribuir
¡Las contribuciones son bienvenidas! Por favor, lee nuestras guías de contribución.

## 📜 Licencia
Este repositorio está bajo la Licencia MIT.
END

# Crear README para el año actual
cat > notes/$CURRENT_YEAR/README.md << 'END'
# 📚 Material del Año 2025

## 📝 Contenido Actual

### 📚 Teoría
#### Tema 1
- [Pendiente]

#### Tema 2
- [Pendiente]

### 💻 Práctica
#### Tema 1
- [Pendiente]

#### Tema 2
- [Pendiente]

### 📚 Recursos
- 📖 Recursos Teóricos: [Por agregar]
- 💻 Recursos Prácticos: [Por agregar]

## 📅 Cronograma
### Teoría
- [ ] Tema 1
- [ ] Tema 2

### Práctica
- [ ] Tema 1
- [ ] Tema 2

## 📌 Notas Importantes
- [Por agregar]
END

git add .
git commit -m "chore: inicializar estructura base del repositorio"
git push
