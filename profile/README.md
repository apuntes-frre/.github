# 📚 Apuntes FRRE - Universidad Tecnológica Nacional

¡Bienvenidos al repositorio central de apuntes y recursos educativos de la UTN-FRRE! Este es un espacio colaborativo para compartir y mantener material de estudio actualizado.

## 📊 Estado General del Repositorio

- 📅 **Última actualización**: {{ current_date }}
- 📚 **Materias activas**: {{ active_subjects }}
- 📆 **Año académico**: {{ current_year }}
- 📈 **Progreso general**: {{ progress_chart }}

## 🎯 Objetivos del Repositorio

- 📝 Mantener material de estudio actualizado y organizado
- 🤝 Fomentar la colaboración entre estudiantes
- 📚 Centralizar recursos educativos de calidad
- 🔄 Facilitar el acceso a material histórico

## 📝 Repositorios de Materias

{% for subject in subjects %}
### {{ subject.name }}
- 📁 [{{ subject.code }} - {{ subject.name }}]({{ subject.repo_url }})
- {{ subject.description }}
- **Último material**: {{ subject.last_update }}
{% endfor %}

## 🗂 Material por Año

{% for year in years %}
### {{ year }}
{% for subject in year_subjects[year] %}
- [{{ subject.code }}]({{ subject.year_url }}) - {{ subject.latest_topics|join(', ') }}
{% endfor %}
{% endfor %}

## 📌 Recursos Comunes

Recursos compartidos entre todas las materias:
{% for resource in common_resources %}
- [{{ resource.name }}]({{ resource.url }}) - {{ resource.description }}
{% endfor %}

## 🔄 Actualizaciones Recientes

{% for update in recent_updates %}
- {{ update.date }} - {{ update.subject }}: {{ update.description }}
{% endfor %}

## 📊 Progreso General

```
{{ progress_chart }}
```

## 🤝 Contribuir

Valoramos las contribuciones de la comunidad estudiantil. Para participar:

1. Revisa nuestras [guías de contribución](./docs/CONTRIBUTING.md)
2. Mantén el formato establecido
3. Asegúrate de que el contenido sea educativo y relevante

## 🔗 Enlaces Útiles

- [Guía de Contribución](./docs/CONTRIBUTING.md)
- [Código de Conducta](./docs/CODE_OF_CONDUCT.md)
- [Template de Repositorio](./docs/TEMPLATE.md)

---

💡 ¿Tienes preguntas? ¡Abre un issue en el repositorio correspondiente!

> Este README se actualiza automáticamente cada día usando GitHub Actions.
> Última actualización: {{ current_date }}
