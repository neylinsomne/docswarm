-- =============================================================================
-- R__ · Vistas (migración repetible; se re-aplica al cambiar su checksum)
-- -----------------------------------------------------------------------------
-- Vistas de lectura para el tablero de la feature central y para búsquedas.
-- =============================================================================

-- Resumen por cambio maestro: cuántos documentos afectó y cuántos ya firmaron.
CREATE OR REPLACE VIEW vw_cambios_resumen AS
SELECT
    cm.id                          AS cambio_id,
    cm.tipo_objeto,
    cm.accion,
    cm.descripcion,
    cm.version_anterior,
    cm.version_nueva,
    cm.created_at,
    coalesce(cl.codigo, pr.codigo)  AS objeto_codigo,
    coalesce(cl.titulo, pr.producto) AS objeto_titulo,
    count(cda.id)                                              AS docs_afectados,
    count(cda.id) FILTER (WHERE cda.firmado_proveedor)        AS docs_firmados,
    count(cda.id) FILTER (WHERE NOT cda.firmado_proveedor)    AS docs_pendientes
FROM cambios_maestros cm
LEFT JOIN clausulas_maestras cl ON cl.id = cm.clausula_maestra_id
LEFT JOIN precios_maestros   pr ON pr.id = cm.precio_maestro_id
LEFT JOIN cambios_documentos_afectados cda ON cda.cambio_id = cm.id
GROUP BY cm.id, cl.codigo, pr.codigo, cl.titulo, pr.producto;

-- Detalle de documentos afectados por un cambio (para drill-down).
CREATE OR REPLACE VIEW vw_cambios_afectados_detalle AS
SELECT
    cda.cambio_id,
    cda.id                AS afectado_id,
    c.id                  AS contrato_id,
    c.numero              AS contrato_numero,
    c.titulo              AS contrato_titulo,
    e.id                  AS empresa_proveedor_id,
    e.nombre              AS empresa_proveedor,
    cda.estado_propagacion,
    cda.firmado_proveedor,
    cda.fecha_firma,
    cda.notificado_at,
    cda.raw_document_id
FROM cambios_documentos_afectados cda
JOIN contratos c ON c.id = cda.contrato_id
JOIN empresas  e ON e.id = cda.empresa_proveedor_id;
