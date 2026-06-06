-- =============================================================================
-- V10 · Semilla de demostración (nicho agro)
-- -----------------------------------------------------------------------------
-- Crea Bayern (comprador/granbase), dos proveedores agro, sus usuarios, un
-- catálogo maestro mínimo, un contrato por proveedor con cláusulas derivadas de
-- los ítems maestros, y simula UN cambio de precio que afecta a ambos contratos
-- (uno ya firmado, otro pendiente) para poblar el tablero de la feature central.
--
-- Contraseñas hasheadas con bcrypt vía pgcrypto (compatibles con passlib bcrypt
-- en la app). Credenciales demo:  *.demo@docswarm.local  /  Demo1234*
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- --- Empresas -----------------------------------------------------------------
INSERT INTO empresas (tipo, nombre, nit, sector, nicho, ciudad, metadata) VALUES
    ('COMPRADOR', 'Bayern S.A.', '900000001-1', 'agro', 'insumos', 'Bogotá',
        '{"rol":"granbase","descripcion":"Comprador principal de insumos agro"}'),
    ('PROVEEDOR', 'AgroSemillas del Valle', '900111111-1', 'agro', 'semillas', 'Cali',
        '{"capacidad_ton":1500,"certificaciones":["ISO9001","ICA"]}'),
    ('PROVEEDOR', 'Alimentos del Campo', '900222222-2', 'agro', 'alimentos', 'Medellín',
        '{"capacidad_ton":3200,"certificaciones":["HACCP"]}');

-- --- Características facetadas --------------------------------------------------
INSERT INTO empresa_caracteristicas (empresa_id, clave, valor, valor_num)
SELECT id, 'certificacion', 'ISO9001', NULL FROM empresas WHERE nit='900111111-1'
UNION ALL
SELECT id, 'capacidad_ton', '1500', 1500 FROM empresas WHERE nit='900111111-1'
UNION ALL
SELECT id, 'certificacion', 'HACCP', NULL FROM empresas WHERE nit='900222222-2'
UNION ALL
SELECT id, 'capacidad_ton', '3200', 3200 FROM empresas WHERE nit='900222222-2';

-- --- Usuarios (uno por empresa) ----------------------------------------------
INSERT INTO usuarios (empresa_id, email, password_hash, nombre, rol)
SELECT id, 'bayern.demo@docswarm.local', crypt('Demo1234*', gen_salt('bf', 12)),
       'Admin Bayern', 'ADMIN' FROM empresas WHERE nit='900000001-1'
UNION ALL
SELECT id, 'semillas.demo@docswarm.local', crypt('Demo1234*', gen_salt('bf', 12)),
       'Gestor AgroSemillas', 'GESTOR' FROM empresas WHERE nit='900111111-1'
UNION ALL
SELECT id, 'campo.demo@docswarm.local', crypt('Demo1234*', gen_salt('bf', 12)),
       'Gestor Alimentos del Campo', 'GESTOR' FROM empresas WHERE nit='900222222-2';

-- --- Catálogo maestro de Bayern ----------------------------------------------
INSERT INTO clausulas_maestras (codigo, tipo, titulo, contenido_actual, sector, nicho) VALUES
    ('CL-CALIDAD-001', 'CALIDAD',
     'Estándar de calidad de grano',
     'El producto debe cumplir humedad <= 13% e impurezas <= 1%.', 'agro', NULL),
    ('CL-ENTREGA-001', 'ENTREGA',
     'Plazo de entrega',
     'Entrega en máximo 15 días hábiles desde la orden de compra.', 'agro', NULL);

INSERT INTO precios_maestros (codigo, producto, categoria, precio, moneda, unidad, sector, nicho) VALUES
    ('PR-MAIZ-AMARILLO', 'Maíz amarillo', 'cereales', 1200000.0000, 'COP', 'ton', 'agro', 'alimentos'),
    ('PR-SEMILLA-SOYA',  'Semilla de soya', 'semillas', 850000.0000, 'COP', 'ton', 'agro', 'semillas');

-- --- Contratos (uno por proveedor) -------------------------------------------
WITH bayern AS (SELECT id FROM empresas WHERE nit='900000001-1'),
     prov1   AS (SELECT id FROM empresas WHERE nit='900111111-1'),
     prov2   AS (SELECT id FROM empresas WHERE nit='900222222-2')
INSERT INTO contratos (empresa_proveedor_id, empresa_compradora_id, numero, titulo,
                       objeto, sector, estado, valor, moneda, fecha_inicio, fecha_fin,
                       firmado_proveedor, fecha_firma)
SELECT prov1.id, bayern.id, 'CTR-2026-001', 'Suministro de semilla de soya 2026',
       'Suministro anual de semilla de soya certificada', 'agro', 'VIGENTE',
       425000000.00, 'COP', DATE '2026-01-01', DATE '2026-12-31', TRUE, now()
FROM prov1, bayern
UNION ALL
SELECT prov2.id, bayern.id, 'CTR-2026-002', 'Suministro de maíz amarillo 2026',
       'Suministro anual de maíz amarillo para alimentos', 'agro', 'VIGENTE',
       960000000.00, 'COP', DATE '2026-01-01', DATE '2026-12-31', TRUE, now()
FROM prov2, bayern;

-- --- Cláusulas de contrato derivadas del catálogo maestro --------------------
INSERT INTO contrato_clausulas (contrato_id, tipo, titulo, contenido, orden, clausula_maestra_id)
SELECT c.id, 'CALIDAD', cm.titulo, cm.contenido_actual, 1, cm.id
FROM contratos c CROSS JOIN clausulas_maestras cm
WHERE cm.codigo = 'CL-CALIDAD-001';

INSERT INTO contrato_clausulas (contrato_id, tipo, titulo, contenido, orden, precio_maestro_id, valor)
SELECT c.id, 'PRECIO', 'Precio unitario ' || pm.producto,
       'Precio pactado: ' || pm.precio || ' ' || pm.moneda || '/' || pm.unidad, 2,
       pm.id, pm.precio
FROM contratos c
JOIN precios_maestros pm
  ON (c.numero = 'CTR-2026-001' AND pm.codigo = 'PR-SEMILLA-SOYA')
  OR (c.numero = 'CTR-2026-002' AND pm.codigo = 'PR-MAIZ-AMARILLO');

-- --- Simular un cambio de precio del maíz (+8%) y poblar afectados ------------
DO $$
DECLARE
    v_precio_id   BIGINT;
    v_precio_old  NUMERIC;
    v_precio_new  NUMERIC;
    v_cambio_id   BIGINT;
    v_admin_user  BIGINT;
BEGIN
    SELECT id, precio INTO v_precio_id, v_precio_old
        FROM precios_maestros WHERE codigo = 'PR-MAIZ-AMARILLO';
    v_precio_new := round(v_precio_old * 1.08, 4);
    SELECT id INTO v_admin_user FROM usuarios WHERE email='bayern.demo@docswarm.local';

    -- aplicar el cambio al ítem maestro
    UPDATE precios_maestros
       SET precio = v_precio_new, version = version + 1
     WHERE id = v_precio_id;

    -- registrar el cambio
    INSERT INTO cambios_maestros (tipo_objeto, precio_maestro_id, accion, descripcion,
                                  version_anterior, version_nueva, valor_anterior,
                                  valor_nuevo, realizado_por)
    VALUES ('PRECIO', v_precio_id, 'ACTUALIZACION',
            'Ajuste de precio de maíz amarillo (+8%)', 1, 2,
            jsonb_build_object('precio', v_precio_old),
            jsonb_build_object('precio', v_precio_new), v_admin_user)
    RETURNING id INTO v_cambio_id;

    -- documentos/contratos afectados: todo contrato con una cláusula que use ese precio
    INSERT INTO cambios_documentos_afectados (cambio_id, contrato_id, empresa_proveedor_id,
                                              clausula_contrato_id, estado_propagacion,
                                              firmado_proveedor, fecha_firma, notificado_at)
    SELECT v_cambio_id, c.id, c.empresa_proveedor_id, cc.id, 'NOTIFICADO',
           -- demo: el contrato CTR-2026-002 aún NO firma; los demás sí
           (c.numero <> 'CTR-2026-002'),
           CASE WHEN c.numero <> 'CTR-2026-002' THEN now() ELSE NULL END,
           now()
    FROM contrato_clausulas cc
    JOIN contratos c ON c.id = cc.contrato_id
    WHERE cc.precio_maestro_id = v_precio_id;
END
$$;
