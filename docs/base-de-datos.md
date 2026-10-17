# Base de datos

PostgreSQL, 7 tablas del dominio. Django crea además sus tablas internas: sesiones, permisos y migraciones.

```mermaid
erDiagram
    CONCESIONARIA ||--o{ USUARIO : "tiene (rol concesionario)"
    CONCESIONARIA ||--o{ CONCESION : "es titular de"
    CONCESION ||--o{ VUELO : "se monitorea con"
    USUARIO ||--o{ VUELO : "opera"
    VUELO ||--o{ IMAGEN : "produce"
    CONCESION ||--o{ ANALISIS : "se analiza en"
    IMAGEN ||--o{ ANALISIS : "antes / después"
    USUARIO ||--o{ ANALISIS : "ejecuta"
    ANALISIS ||--o{ ALERTA : "genera"
    CONCESION ||--o{ ALERTA : "recibe"
    USUARIO ||--o{ ALERTA : "revisa"

    USUARIO {
        bigint id PK
        varchar username UK
        varchar rol "tecnico | analista | concesionario"
        bigint concesionaria_id FK "solo concesionario"
        varchar telefono
    }
    CONCESIONARIA {
        bigint id PK
        varchar razon_social
        varchar ruc UK "11 dígitos"
        varchar plan "basico | pro | enterprise"
        boolean activa
    }
    CONCESION {
        bigint id PK
        bigint concesionaria_id FK
        varchar nombre
        varchar codigo_contrato UK
        varchar tipo "ecoturismo | conservacion | maderable"
        jsonb limite "polígono [[lon,lat],...]"
        numeric area_ha "calculada"
    }
    VUELO {
        bigint id PK
        bigint concesion_id FK
        bigint operador_id FK
        date fecha_vuelo
        varchar dron
        int altitud_m
    }
    IMAGEN {
        bigint id PK
        bigint vuelo_id FK
        varchar archivo
        varchar fuente "dron | satelite"
        float norte
        float sur
        float este
        float oeste
        int ancho_px
        int alto_px
    }
    ANALISIS {
        bigint id PK
        bigint concesion_id FK
        bigint imagen_antes_id FK
        bigint imagen_despues_id FK
        bigint ejecutado_por_id FK
        varchar estado "completado | error"
        float cobertura_antes_pct
        float cobertura_despues_pct
        float area_perdida_m2
        varchar imagen_resultado
    }
    ALERTA {
        bigint id PK
        bigint analisis_id FK
        bigint concesion_id FK
        float latitud
        float longitud
        jsonb poligono
        float area_m2
        varchar tipo_cambio "claro | trocha | perdida"
        varchar gravedad "baja | media | alta"
        boolean dentro_concesion
        varchar estado "pendiente | confirmada | descartada"
        bigint revisado_por_id FK
        timestamp fecha_revision
    }
```

## Decisiones de diseño

- **Revisión dentro de la alerta.** No se creó una tabla aparte para la revisión: la alerta guarda su `estado` (pendiente, confirmada o descartada), quién la revisó y cuándo. Así se cumplen el RF-002 y el RF-003, y la Guía 4 ("pendiente de revisión hasta ser verificada") sin agregar una octava tabla.
- **Geometría en JSON, no en PostGIS.** Los polígonos se guardan como JSON `[[lon, lat], …]` y los cálculos (área, punto dentro del polígono) se hacen en `concesiones/geo.py`. Esto evita instalar PostGIS/GDAL en Windows. Si el proyecto crece, se migra a PostGIS sin cambiar las pantallas.
- **Integridad.** Casi todas las relaciones usan `PROTECT`: no se puede borrar una concesión con vuelos, ni una imagen usada en un análisis. Así se conserva la trazabilidad de la evidencia (RNF-003).
- **Aislamiento por cliente.** El usuario con rol concesionario está ligado a su `concesionaria`, y todas las consultas filtran por ella (`cuentas/permisos.py`).
- **`alerta.concesion_id` está duplicado a propósito** (también se puede llegar a él por `analisis`) para filtrar el historial y el mapa rápido.
