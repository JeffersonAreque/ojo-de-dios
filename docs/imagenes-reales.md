# Cómo usar imágenes satelitales reales en la demo

La demo trae un par de imágenes sintéticas. Para que sea más convincente, conviene cargar dos imágenes reales de **la misma zona en fechas distintas**, donde se vea pérdida de bosque.

## Opción recomendada: Copernicus Browser (Sentinel-2, gratis)

1. Crea una cuenta en https://browser.dataspace.copernicus.eu
2. Ubica una zona de la carretera Interoceánica o del entorno de la RN Tambopata donde se vea deforestación reciente.
3. Elige **Sentinel-2 L2A**, la visualización **True color** y una fecha con poca nubosidad (filtro de nubes < 10 %).
4. Dibuja un rectángulo (área de interés) de 2 a 5 km de lado.
5. Usa **Download image → Analytical**, con estas opciones:
   - Formato: **TIFF (8-bit)**
   - Sistema de coordenadas: **WGS 84 (EPSG:4326)**
   - Capa: True color
6. Repite el paso 5 con **el mismo rectángulo** para una fecha posterior (por ejemplo, 6 a 12 meses después).
7. En la app, registra la concesión que cubra esa zona y luego un vuelo por cada fecha. Elige *Imagen satelital* como fuente. Al subir el GeoTIFF, los límites se leen solos y la imagen se convierte a PNG.

> Si el GeoTIFF llega en otra proyección (UTM, en metros), la app no podrá leer los límites. En ese caso, escríbelos a mano con las coordenadas del rectángulo.

Sentinel-2 tiene una resolución de 10 m por píxel, así que solo detecta claros de al menos 300 m² (el área mínima por defecto). Con un ortomosaico de dron (3 a 5 cm por píxel) se ven también claros pequeños y trochas angostas.

## Imágenes JPG o PNG sin georreferencia

También se pueden usar. En el formulario hay que escribir los límites norte, sur, este y oeste en grados decimales; el botón *Usar los límites de la concesión* los completa con la caja de la concesión.
