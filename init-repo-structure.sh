#!/bin/bash
# Script para inicializar la estructura base de un repositorio de apuntes

CURRENT_YEAR="2025"

# Crear estructura base
mkdir -p notes/$CURRENT_YEAR/{tema1,tema2,recursos}
mkdir -p examples/$CURRENT_YEAR
mkdir -p study-guides/$CURRENT_YEAR
mkdir -p resources/{common,$CURRENT_YEAR}

# Crear README base
cat > README.md << 'END'
# 📚 [Nombre de la Materia]

## 📝 Descripción
[Descripción de la materia]

## 📂 Estructura del Repositorio

- 📁 **notes/**: Apuntes de clase organizados por año y tema
- 📁 **examples/**: Ejemplos prácticos y código
- �� **study-guides/**: Guías de estudio y material de práctica
- 📁 **resources/**: Recursos adicionales y material de referencia

## 🗓️ Contenido Actual (2025)

### 📚 Temas
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

## 📝 Temas Actuales

### 📂 Tema 1
- [Pendiente]

### �� Tema 2
- [Pendiente]

### 📚 Recursos
- [Por agregar]

## 📅 Cronograma
- [ ] Tema 1
- [ ] Tema 2

## 📌 Notas Importantes
- [Por agregar]
END

git add .
git commit -m "chore: inicializar estructura base del repositorio"
git push
