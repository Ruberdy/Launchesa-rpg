# Revisión rápida de la base de código: problemas detectados y tareas propuestas

## 1) Tarea: corregir error tipográfico (ruta/nombre de archivo)
- **Problema detectado**: el repositorio contiene `assets/Logo.png` (L mayúscula), pero la configuración usa `assets/logo.png` (l minúscula). En Linux esto rompe la carga del icono por sensibilidad a mayúsculas/minúsculas.
- **Impacto**: launcher sin icono y potencial inconsistencia visual.
- **Tarea propuesta**:
  1. Normalizar el nombre del archivo y su referencia (`assets/Logo.png` vs `assets/logo.png`).
  2. Elegir una convención única (`snake_case` en minúsculas recomendado) y aplicar en `launcher.json` y recursos.
  3. Verificar que `os.path.exists(LOGO_IMAGE_PATH)` sea `True` al iniciar.

## 2) Tarea: solucionar un fallo funcional
- **Problema detectado**: `NewsCard.open_news_detail()` crea una ventana secundaria en una variable local (`news_window`) y no guarda referencia persistente.
- **Impacto**: la ventana puede cerrarse de forma inesperada por garbage collection o comportamiento errático al abrir noticias.
- **Tarea propuesta**:
  1. Guardar la referencia como atributo (`self.news_window` o en el padre).
  2. Reutilizar instancia existente si ya está abierta.
  3. Añadir prueba/manual check para abrir varias noticias consecutivas sin cierre inesperado.

## 3) Tarea: corregir comentario/discrepancia de documentación
- **Problema detectado**: en `launchers1.py`, el fallback de `read_config()` documenta por código un `LOGO_IMAGE_PATH` por defecto de `logo.png`, que no coincide con la estructura real del proyecto (activo en `assets/`).
- **Impacto**: en ausencia de `launcher.json`, la “documentación viva” del fallback lleva a una ruta inválida.
- **Tarea propuesta**:
  1. Actualizar valor por defecto a la ruta real del recurso.
  2. Añadir una nota breve en comentarios o README sobre rutas esperadas de assets.
  3. Validar fallback arrancando la app sin `launcher.json` en entorno local.

## 4) Tarea: mejorar una prueba
- **Problema detectado**: no hay pruebas automatizadas que cubran configuración/fallback ni errores comunes de UI.
- **Impacto**: regresiones silenciosas en rutas y flujo de interacción.
- **Tarea propuesta**:
  1. Crear tests unitarios para `read_config()` (archivo presente/ausente, JSON inválido, defaults).
  2. Añadir test para validar que `LOGO_IMAGE_PATH` apunte a un recurso existente del repo.
  3. Añadir test de comportamiento para `NewsCard.open_news_detail()` verificando persistencia de referencia.
  4. Incluir estos tests en CI con ejecución mínima (por ejemplo `pytest -q`).
