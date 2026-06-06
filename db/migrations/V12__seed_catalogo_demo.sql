-- =============================================================================
-- V12 · Semilla ampliada para demo del front (catálogo + empresas + contratos)
-- -----------------------------------------------------------------------------
-- Amplía la semilla mínima de V10 con el dataset que muestra el front (ver
-- docs/mocks/). Ids deterministas (OVERRIDING SYSTEM VALUE) para que casen con
-- los mocks. Todos los proveedores quedan con un contrato que incluye la
-- cláusula maestra de CALIDAD (id 1), de modo que un cambio en esa cláusula
-- dispara la alarma de notificaciones a TODOS.
-- Credenciales demo (todas): Demo1234*
-- =============================================================================

-- --- Empresas 4..9 (Bayern=1, AgroSemillas=2, Alimentos=3 vienen de V10) -------
INSERT INTO empresas (id, tipo, nombre, nit, sector, nicho, ciudad, metadata, activo)
OVERRIDING SYSTEM VALUE VALUES
 (4,'PROVEEDOR','Fertilizantes Andinos','900333333-3','agro','fertilizantes','Bucaramanga',
    '{"capacidad_ton":5400,"empleados":210,"telefono":"+57 607 5553333","certificaciones":["ISO14001","ICA"]}',TRUE),
 (5,'PROVEEDOR','Maquinaria Agrícola Coltrac','900444444-4','agro','maquinaria','Bogotá',
    '{"empleados":60,"telefono":"+57 601 5554444","certificaciones":["ISO9001"]}',TRUE),
 (6,'PROVEEDOR','Logística FríoSeguro','900555555-5','logistica','cadena_frio','Barranquilla',
    '{"flota":45,"empleados":320,"telefono":"+57 605 5555555","certificaciones":["ISO9001","BASC"]}',TRUE),
 (7,'PROVEEDOR','Empaques VerdePack','900666666-6','agro','empaques','Cali',
    '{"capacidad_ton":900,"empleados":70,"telefono":"+57 602 5556666","certificaciones":["FSC","ISO9001"]}',TRUE),
 (8,'PROVEEDOR','AgroQuímicos Tropical','900777777-7','agro','agroquimicos','Villavicencio',
    '{"capacidad_ton":2100,"empleados":95,"telefono":"+57 608 5557777","certificaciones":["ICA","ISO45001"]}',TRUE),
 (9,'PROVEEDOR','Riego Tecnificado del Norte','900888888-8','agro','riego','Valledupar',
    '{"empleados":40,"telefono":"+57 605 5558888","certificaciones":["ISO9001"]}',TRUE);
SELECT setval(pg_get_serial_sequence('empresas','id'), (SELECT max(id) FROM empresas));

INSERT INTO empresa_caracteristicas (empresa_id, clave, valor, valor_num) VALUES
 (4,'certificacion','ISO14001',NULL),(4,'capacidad_ton','5400',5400),
 (5,'certificacion','ISO9001',NULL),(5,'garantia_meses','24',24),
 (6,'certificacion','BASC',NULL),(6,'flota_vehiculos','45',45),
 (7,'certificacion','FSC',NULL),(7,'biodegradable','si',NULL),
 (8,'certificacion','ISO45001',NULL),(8,'capacidad_ton','2100',2100),
 (9,'certificacion','ISO9001',NULL),(9,'tecnologia','goteo',NULL);

-- --- Usuarios (login) por empresa proveedora --------------------------------
INSERT INTO usuarios (empresa_id, email, password_hash, nombre, rol) VALUES
 (4,'fertilizantes.demo@docswarm.local', crypt('Demo1234*', gen_salt('bf',12)),'Gestor Fertilizantes Andinos','GESTOR'),
 (5,'maquinaria.demo@docswarm.local',    crypt('Demo1234*', gen_salt('bf',12)),'Gestor Maquinaria Coltrac','GESTOR'),
 (6,'logistica.demo@docswarm.local',     crypt('Demo1234*', gen_salt('bf',12)),'Gestor Logística FríoSeguro','GESTOR'),
 (7,'empaques.demo@docswarm.local',      crypt('Demo1234*', gen_salt('bf',12)),'Gestor Empaques VerdePack','GESTOR'),
 (8,'agroquimicos.demo@docswarm.local',  crypt('Demo1234*', gen_salt('bf',12)),'Gestor AgroQuímicos Tropical','GESTOR'),
 (9,'riego.demo@docswarm.local',         crypt('Demo1234*', gen_salt('bf',12)),'Gestor Riego del Norte','GESTOR');

-- --- Cláusulas maestras 3..12 (1,2 vienen de V10) ---------------------------
INSERT INTO clausulas_maestras (id, codigo, tipo, titulo, contenido_actual, sector, nicho, version)
OVERRIDING SYSTEM VALUE VALUES
 (3,'CL-PAGO-001','PAGO','Condiciones de pago',
    'Pago mediante transferencia bancaria a 30 días calendario desde la radicación de la factura.',NULL,NULL,1),
 (4,'CL-PAGO-002','PAGO','Anticipo y amortización',
    'Anticipo del 20% del valor del contrato, amortizable proporcionalmente en cada entrega.',NULL,NULL,1),
 (5,'CL-PENAL-001','PENALIZACION','Penalización por mora en la entrega',
    'Por cada día hábil de retraso se aplicará una multa del 0,5% del valor de la entrega afectada, hasta 10%.',NULL,NULL,1),
 (6,'CL-PENAL-002','PENALIZACION','Rechazo por incumplimiento de calidad',
    'El comprador podrá rechazar lotes que no cumplan el estándar de calidad, con reposición a cargo del proveedor.','agro',NULL,1),
 (7,'CL-CONF-001','CONFIDENCIALIDAD','Confidencialidad de la información comercial',
    'Las partes mantendrán reserva sobre precios, volúmenes y condiciones durante la vigencia y 2 años posteriores.',NULL,NULL,1),
 (8,'CL-CALIDAD-002','CALIDAD','Certificación fitosanitaria',
    'Cada lote debe adjuntar certificado fitosanitario ICA vigente y trazabilidad de origen.','agro','semillas',1),
 (9,'CL-ENTREGA-002','ENTREGA','Cadena de frío en transporte',
    'El transporte de perecederos se realizará en cadena de frío entre 2°C y 6°C con registro de temperatura.','logistica','cadena_frio',1),
 (10,'CL-GEN-001','GENERAL','Vigencia y renovación',
    'El contrato tiene vigencia de un año, renovable automáticamente salvo aviso con 30 días de antelación.',NULL,NULL,1),
 (11,'CL-GEN-002','GENERAL','Resolución de controversias',
    'Las controversias se resolverán mediante conciliación; en su defecto, tribunal de arbitramento de la Cámara de Comercio.',NULL,NULL,1),
 (12,'CL-CALIDAD-003','CALIDAD','Empaque y rotulado',
    'El producto debe empacarse en material biodegradable rotulado con lote, peso y fecha de producción.','agro','empaques',2);
SELECT setval(pg_get_serial_sequence('clausulas_maestras','id'), (SELECT max(id) FROM clausulas_maestras));

-- --- Precios maestros 3..10 (1,2 vienen de V10) -----------------------------
INSERT INTO precios_maestros (id, codigo, producto, categoria, precio, moneda, unidad, sector, nicho, vigente)
OVERRIDING SYSTEM VALUE VALUES
 (3,'PR-ARROZ-PADDY','Arroz paddy','cereales',1750000,'COP','ton','agro',NULL,TRUE),
 (4,'PR-UREA-46','Urea 46%','fertilizantes',2300000,'COP','ton','agro','fertilizantes',TRUE),
 (5,'PR-DAP','Fosfato diamónico (DAP)','fertilizantes',2850000,'COP','ton','agro','fertilizantes',TRUE),
 (6,'PR-GLIFOSATO','Glifosato 48%','agroquimicos',18500,'COP','litro','agro','agroquimicos',TRUE),
 (7,'PR-EMPAQUE-50KG','Saco biodegradable 50kg','empaques',1800,'COP','unidad','agro','empaques',TRUE),
 (8,'PR-FLETE-TON-KM','Flete refrigerado','logistica',1200,'COP','ton-km','logistica','cadena_frio',TRUE),
 (9,'PR-CAFE-PERGAMINO','Café pergamino','cereales',11200000,'COP','ton','agro',NULL,FALSE),
 (10,'PR-RIEGO-GOTEO-HA','Sistema riego por goteo','riego',6500000,'COP','hectarea','agro','riego',TRUE);
SELECT setval(pg_get_serial_sequence('precios_maestros','id'), (SELECT max(id) FROM precios_maestros));

-- --- Contratos demo para 4..9 (ids 3.. por identity normal) ------------------
INSERT INTO contratos (empresa_proveedor_id, empresa_compradora_id, numero, titulo, objeto,
                       sector, estado, valor, moneda, fecha_inicio, fecha_fin,
                       firmado_proveedor, fecha_firma)
VALUES
 (4,1,'CTR-2026-003','Suministro de urea y DAP 2026','Fertilizantes nitrogenados y fosfatados',
    'agro','VIGENTE',1540000000,'COP','2026-01-01','2026-12-31',FALSE,NULL),
 (6,1,'CTR-2026-004','Transporte refrigerado regional 2026','Logística en cadena de frío',
    'logistica','BORRADOR',320000000,'COP','2026-01-01','2026-12-31',FALSE,NULL),
 (7,1,'CTR-2026-005','Empaques biodegradables 2026','Sacos y empaques biodegradables',
    'agro','VIGENTE',180000000,'COP','2026-01-01','2026-12-31',TRUE,now()),
 (8,1,'CTR-2026-006','Agroquímicos campaña 2026','Suministro de agroquímicos',
    'agro','SUSPENDIDO',410000000,'COP','2026-01-01','2026-12-31',FALSE,NULL),
 (5,1,'CTR-2026-007','Maquinaria agrícola 2026','Tractores y cosechadoras',
    'agro','VIGENTE',780000000,'COP','2026-01-01','2026-12-31',FALSE,NULL),
 (9,1,'CTR-2026-008','Riego tecnificado 2026','Sistemas de riego por goteo',
    'agro','BORRADOR',650000000,'COP','2026-01-01','2026-12-31',FALSE,NULL);

-- Cada contrato nuevo lleva la cláusula maestra de CALIDAD (id 1) → un cambio a
-- esa cláusula afecta (y notifica) a TODOS los proveedores.
INSERT INTO contrato_clausulas (contrato_id, tipo, titulo, contenido, orden, clausula_maestra_id)
SELECT c.id, 'CALIDAD', cm.titulo, cm.contenido_actual, 1, cm.id
FROM contratos c CROSS JOIN clausulas_maestras cm
WHERE cm.id = 1
  AND c.numero IN ('CTR-2026-003','CTR-2026-004','CTR-2026-005',
                   'CTR-2026-006','CTR-2026-007','CTR-2026-008');
