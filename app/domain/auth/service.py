"""Autenticación y alta de usuarios."""

from __future__ import annotations

from typing import Optional

from psycopg.rows import dict_row

from app.db import db_conn
from app.security import create_access_token, hash_password, verify_password
from app.domain.auth import schemas


def login(email: str, password: str) -> Optional[schemas.TokenResponse]:
    """Valida credenciales y emite un JWT. Devuelve None si fallan."""
    # tenant=None: el login corre en contexto admin (aún no hay token).
    with db_conn(empresa_id=None) as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            SELECT u.id, u.password_hash, u.rol, u.activo,
                   e.id AS empresa_id, e.tipo AS tipo_empresa, e.activo AS emp_activa
            FROM usuarios u
            JOIN empresas e ON e.id = u.empresa_id
            WHERE u.email = %s
            """,
            (email,),
        ).fetchone()

        if not row or not row["activo"] or not row["emp_activa"]:
            return None
        if not verify_password(password, row["password_hash"]):
            return None

        conn.execute("UPDATE usuarios SET ultimo_login = now() WHERE id = %s", (row["id"],))

    token = create_access_token(
        usuario_id=row["id"], empresa_id=row["empresa_id"],
        tipo_empresa=row["tipo_empresa"], rol=row["rol"],
    )
    return schemas.TokenResponse(
        access_token=token, empresa_id=row["empresa_id"],
        tipo_empresa=row["tipo_empresa"], rol=row["rol"],
    )


def register_usuario(data: schemas.RegisterUsuario) -> int:
    """Crea un usuario para una empresa. Devuelve el id creado."""
    with db_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO usuarios (empresa_id, email, password_hash, nombre, rol)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (data.empresa_id, data.email, hash_password(data.password),
             data.nombre, data.rol),
        ).fetchone()
    return row["id"]
