# Guion de la demo (examen parcial, aprox. 8 min)

**Antes de exponer:** ejecuta `python manage.py cargar_demo` sobre una base limpia y deja abiertas tres ventanas del navegador, una por usuario, en modo incógnito para que no se mezclen las sesiones.

| # | Quién | Acción | Qué decir |
|---|---|---|---|
| 1 | — | Pantalla de login | "Plataforma B2B; tres roles, como en el SRS." |
| 2 | analista | Concesiones → abrir la concesión | "La concesión se registra con su polígono; el área se calcula sola." (Opcional: *Nueva concesión* y dibujar un polígono.) |
| 3 | tecnico | Vuelos → ver los dos vuelos (14/08 y 12/10) | "El técnico sube el ortomosaico georreferenciado de cada vuelo. Si no tiene coordenadas, el sistema lo rechaza (RF-001)." |
| 4 | tecnico | Análisis → Nuevo → elegir concesión → Ejecutar | "Comparamos las dos fechas: índice de verdor, pérdida de vegetación, zonas, área y gravedad." |
| 5 | tecnico | Resultado del análisis | Mostrar antes/después/cambios y el mapa: "Detectó dos claros y una posible trocha. Todo queda *pendiente de revisión*: la IA no acusa sola." |
| 6 | cliente | Mapa general | "El concesionario **todavía no ve nada**: falta que el analista confirme." |
| 7 | analista | Alertas → abrir la primera → Confirmar; descartar otra | "El analista valida con la evidencia. Si es sombra o nube, se descarta (flujo alternativo del CU-01)." |
| 8 | cliente | Recargar el mapa general → abrir la alerta | "Ahora la ve: ubicación exacta, área, fecha y quién la validó." |
| 9 | cliente | Alertas → Exportar CSV | "Historial exportable como sustento ante ARFFS/SERFOR." |
| 10 | — | (Opcional) `/admin` o pgAdmin | Mostrar las 7 tablas con los datos reales del flujo. |

## Preguntas probables

- **¿Es IA?** "La versión 1 usa visión por computadora clásica (índice ExG y morfología): es explicable y no necesita datos etiquetados. Es la línea base. En la fase 2 se entrena un modelo de segmentación con imágenes de la zona y se compara contra esta línea."
- **¿Y el offline-first?** "La app no depende de internet: las librerías van incluidas y el análisis corre en la misma máquina, lo que en campo sería el edge. La sincronización con la nube por lotes es la siguiente fase, tal como está en la Guía 4."
- **¿Por qué no está en AWS?** "Es el piloto local de la misma arquitectura: cada app de Django corresponde a uno de los servicios de la Guía 4 (vuelos, análisis y alertas). Pasar a AWS es despliegue, no rediseño."
- **¿Qué pasa si las fechas tienen distinta luz o nubes?** "Por eso existe la revisión humana, y el umbral del índice se calcula automáticamente para cada par de imágenes (Otsu)."
