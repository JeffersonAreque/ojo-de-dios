-- =====================================================================
--  Ojo de Dios · Consultas SQL para la demostración
--  Base de datos: ojodedios (PostgreSQL)
--  Cómo usarlas: pgAdmin → clic derecho en "ojodedios" → Query Tool,
--  pega la consulta, selecciónala y presiona F5.
-- =====================================================================


-- 1. Las 7 tablas del sistema y cuántas filas tiene cada una
SELECT 'usuario' AS tabla, COUNT(*) AS filas FROM usuario
UNION ALL SELECT 'concesionaria', COUNT(*) FROM concesionaria
UNION ALL SELECT 'concesion',     COUNT(*) FROM concesion
UNION ALL SELECT 'vuelo',         COUNT(*) FROM vuelo
UNION ALL SELECT 'imagen',        COUNT(*) FROM imagen
UNION ALL SELECT 'analisis',      COUNT(*) FROM analisis
UNION ALL SELECT 'alerta',        COUNT(*) FROM alerta;


-- 2. Usuarios y su rol (las contraseñas se guardan cifradas, no en texto)
SELECT u.username, u.first_name, u.rol, c.razon_social AS empresa,
       LEFT(u.password, 25) || '…' AS contrasena_cifrada
FROM usuario u
LEFT JOIN concesionaria c ON c.id = u.concesionaria_id
ORDER BY u.rol, u.username;


-- 3. Empresas clientes con sus concesiones y hectáreas
SELECT ca.razon_social, ca.ruc, ca.plan, co.nombre AS concesion, co.tipo, co.area_ha
FROM concesionaria ca
JOIN concesion co ON co.concesionaria_id = ca.id
ORDER BY ca.razon_social;


-- 4. Vuelos registrados: quién voló, cuándo y qué imagen subió
SELECT v.id, co.nombre AS concesion, v.fecha_vuelo, u.username AS operador,
       i.fuente, i.ancho_px || 'x' || i.alto_px AS resolucion,
       ROUND(i.norte::numeric, 5) AS norte, ROUND(i.sur::numeric, 5) AS sur
FROM vuelo v
JOIN concesion co ON co.id = v.concesion_id
JOIN usuario u    ON u.id = v.operador_id
JOIN imagen i     ON i.vuelo_id = v.id
ORDER BY v.fecha_vuelo;


-- 5. Resultado de cada análisis (comparación entre dos fechas)
SELECT a.id, co.nombre AS concesion,
       va.fecha_vuelo AS fecha_antes, vd.fecha_vuelo AS fecha_despues,
       a.cobertura_antes_pct, a.cobertura_despues_pct,
       ROUND((a.area_perdida_m2 / 10000)::numeric, 1) AS perdida_ha,
       (SELECT COUNT(*) FROM alerta al WHERE al.analisis_id = a.id) AS alertas
FROM analisis a
JOIN concesion co ON co.id = a.concesion_id
JOIN imagen ia ON ia.id = a.imagen_antes_id   JOIN vuelo va ON va.id = ia.vuelo_id
JOIN imagen id ON id.id = a.imagen_despues_id JOIN vuelo vd ON vd.id = id.vuelo_id
ORDER BY a.id;


-- 6. Resumen de alertas por estado y gravedad
SELECT estado, gravedad, COUNT(*) AS cantidad,
       ROUND((SUM(area_m2) / 10000)::numeric, 1) AS hectareas
FROM alerta
GROUP BY estado, gravedad
ORDER BY estado, gravedad;


-- 7. Las 5 alertas más grandes confirmadas (lo más grave para el cliente)
SELECT al.id, co.nombre AS concesion, al.tipo_cambio, al.gravedad,
       ROUND((al.area_m2 / 10000)::numeric, 2) AS hectareas,
       al.latitud, al.longitud,
       CASE WHEN al.dentro_concesion THEN 'Dentro' ELSE 'Perímetro' END AS ubicacion
FROM alerta al
JOIN concesion co ON co.id = al.concesion_id
WHERE al.estado = 'confirmada'
ORDER BY al.area_m2 DESC
LIMIT 5;


-- 8. Trazabilidad: quién revisó cada alerta, cuándo y con qué comentario
SELECT al.id, al.estado, u.username AS revisado_por,
       TO_CHAR(al.fecha_revision AT TIME ZONE 'America/Lima', 'DD/MM/YYYY HH24:MI') AS fecha_revision,
       al.comentario
FROM alerta al
LEFT JOIN usuario u ON u.id = al.revisado_por_id
WHERE al.estado <> 'pendiente'
ORDER BY al.fecha_revision DESC;


-- 9. Lo que ve el cliente: solo alertas CONFIRMADAS de SU empresa
--    (cambia 'lucia' por cualquier usuario concesionario)
SELECT al.id, co.nombre AS concesion, al.tipo_cambio, al.gravedad,
       ROUND((al.area_m2 / 10000)::numeric, 2) AS hectareas
FROM alerta al
JOIN concesion co ON co.id = al.concesion_id
JOIN usuario u    ON u.concesionaria_id = co.concesionaria_id
WHERE u.username = 'lucia'
  AND al.estado = 'confirmada'
ORDER BY al.area_m2 DESC;


-- 10. Hectáreas de bosque perdidas por concesión (dentro vs. perímetro)
SELECT co.nombre AS concesion,
       ROUND((SUM(al.area_m2) FILTER (WHERE al.dentro_concesion) / 10000)::numeric, 1) AS ha_dentro,
       ROUND((SUM(al.area_m2) FILTER (WHERE NOT al.dentro_concesion) / 10000)::numeric, 1) AS ha_perimetro
FROM alerta al
JOIN concesion co ON co.id = al.concesion_id
WHERE al.estado = 'confirmada'
GROUP BY co.nombre;


-- 11. Prueba de integridad: intentar borrar una concesión que tiene vuelos
--     → PostgreSQL lo IMPIDE (error de clave foránea). Así se protege la evidencia.
--     Ejecútala solo para mostrar el error; no borra nada.
-- DELETE FROM concesion WHERE nombre = 'Concesión Lago Verde';
