# Ojo de Dios: vigilancia forestal con dron e IA

MVP de una plataforma B2B que detecta cambios en la cobertura forestal comparando imágenes aéreas de una misma concesión en dos fechas, y avisa al concesionario con alertas georreferenciadas sobre un mapa.

Piloto: concesiones de ecoturismo en la zona de amortiguamiento de la Reserva Nacional Tambopata (Madre de Dios, Perú).
Curso: Formulación y Evaluación de Proyectos de TI (UNAMAD, 2026).

## Qué hace (flujo del caso de uso CU-01)

```
Técnico                     Sistema                              Analista                  Concesionario
  │ registra vuelo + imagen   │                                     │                          │
  ├──────────────────────────►│ valida georreferenciación           │                          │
  │                           │ compara con el vuelo anterior (ExG) │                          │
  │                           │ crea alertas "pendientes"  ────────►│ revisa evidencia         │
  │                           │                                     ├─ confirma ──────────────►│ ve la alerta en su mapa
  │                           │                                     └─ descarta (no notifica)  │ + historial / CSV
```

| Módulo | Qué incluye |
|---|---|
| Acceso | Login y 3 roles: técnico, analista y concesionario. Cada cliente solo ve los datos de sus concesiones |
| Concesiones | Registro de concesionarias (RUC, plan SaaS) y concesiones con el polígono dibujado en el mapa; el área se calcula sola |
| Vuelos | Registro del vuelo y de su imagen georreferenciada (JPG/PNG con límites, o GeoTIFF que se lee automáticamente) |
| Análisis | Comparación entre dos fechas: índice de verdor ExG, pérdida de vegetación, zonas, área, tipo de cambio y gravedad |
| Alertas | Revisión del analista (confirmar/descartar), mapa por gravedad, historial filtrable y exportación a CSV como evidencia |

### Cómo funciona el análisis (`analisis/detector.py`)

1. Recorta las dos imágenes a la zona geográfica que comparten.
2. Calcula el índice **ExG = 2g − r − b** (con valores normalizados), alto para la vegetación y bajo para el suelo desnudo.
3. Marca como **pérdida** los píxeles que tenían vegetación antes y ya no la tienen.
4. Limpia el ruido (morfología) y agrupa la pérdida en zonas.
5. A cada zona le asigna coordenadas, área en m², tipo (*claro*, *posible trocha*, *pérdida extensa*) y gravedad (baja, media o alta).

Es procesamiento de imagen real, no simulado. El modelo de IA entrenado (segmentación) queda para la fase 2 y se comparará contra esta línea base.

## Tecnología

- **Backend:** Python 3.12+ y Django 5.2
- **Base de datos:** PostgreSQL 16 (7 tablas, ver [docs/base-de-datos.md](docs/base-de-datos.md))
- **Análisis de imagen:** OpenCV y NumPy
- **Interfaz:** plantillas Django, Bootstrap 5 y Leaflet. Las librerías van incluidas en `static/vendor`, así que la app funciona sin internet; solo el mapa base satelital necesita conexión.

### Relación con la arquitectura cloud (Guía N° 4)

El MVP corre como una sola aplicación, pero respeta los tres servicios que propone la arquitectura en AWS. Cada uno puede separarse después sin rediseñar:

| MVP (local) | Producción (AWS, Guía 4) |
|---|---|
| app `vuelos` y carpeta `media/` | API Gateway, URL firmada y S3 |
| app `analisis` (`detector.py`) | SQS, Lambda y SageMaker |
| app `alertas` | DynamoDB y notificaciones |
| app `cuentas` (roles) | Cognito e IAM |
| PostgreSQL | RDS PostgreSQL |

## Instalación en Windows

1. Instala **Python 3.12 o superior** (marca *Add python.exe to PATH*) y **PostgreSQL 16**. Anota la contraseña del usuario `postgres`.
2. Clona el repositorio en una ruta corta para evitar el error de rutas largas, por ejemplo `C:\dev`:
   ```powershell
   cd C:\dev
   git clone <url-del-repo> ojo-de-dios
   cd ojo-de-dios
   ```
3. Crea el entorno virtual e instala las dependencias:
   ```powershell
   py -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Crea la base de datos (o hazlo desde pgAdmin):
   ```powershell
   psql -U postgres -c "CREATE DATABASE ojodedios;"
   ```
5. Copia `.env.example` como `.env` y escribe tu contraseña en `DB_PASSWORD`.
6. Crea las tablas y carga los datos de demostración:
   ```powershell
   python manage.py migrate
   python manage.py cargar_demo
   python manage.py runserver
   ```
7. Abre http://127.0.0.1:8000.

| Usuario | Rol | Contraseña |
|---|---|---|
| `tecnico` | Operador de dron | `demo1234` |
| `analista` | Analista forestal | `demo1234` |
| `cliente` | Concesionario | `demo1234` |
| `admin` | Administrador (incluye `/admin`) | `demo1234` |

`cargar_demo` crea una concesión con dos vuelos (agosto y octubre). Con `python manage.py cargar_demo --analizar` además ejecuta el análisis.

## Pruebas

```powershell
python manage.py test
```

Las pruebas cubren el detector (detecta claros y trocha, no da falsos positivos sin cambios, coordenadas válidas), la carga de GeoTIFF, el aislamiento por cliente y el flujo de revisión del analista.

## Estructura

```
config/        configuración de Django
cuentas/       usuario con rol, permisos y mapa general
concesiones/   concesionarias, concesiones, cálculos geográficos y comando cargar_demo
vuelos/        vuelos e imágenes georreferenciadas (incluye lectura de GeoTIFF)
analisis/      detector de cambios (OpenCV) y servicio que crea las alertas
alertas/       revisión, historial, exportación CSV
templates/     pantallas
static/        CSS, JS del mapa y librerías locales
docs/          base de datos, guion de la demo, cómo obtener imágenes reales
```

## Siguientes pasos (fuera del MVP)

- Sincronización offline desde el campamento (cola local y envío por lotes)
- Notificación por correo/SMS al confirmar una alerta
- Reporte PDF por rango de fechas (RF-005)
- Zonas de aprovechamiento y reforestación dentro de la concesión (RF-004)
- Modelo de segmentación entrenado con imágenes etiquetadas de la zona
