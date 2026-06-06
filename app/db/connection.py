"""Pool de conexiones + Row-Level Security por tenant.

Patrón (igual que la arquitectura de referencia):

1. **Auth → contextvar.** Cada request fija el tenant con ``set_request_empresa``
   en un ``ContextVar``. ``None`` = admin/background (ve todo).
2. **GUC en cada préstamo.** ``db_conn()`` aplica
   ``SELECT set_config('app.current_empresa_id', <id|''>, true)`` (SET LOCAL) en la
   transacción, de modo que una conexión del pool nunca hereda el tenant del
   préstamo anterior ni "fail-opena".
3. **El rol importa.** El pool se NIEGA a arrancar si conecta con un rol que
   ignora RLS (superuser/bypassrls), salvo que ``DB_ALLOW_ADMIN_ROLE=1``.
"""

from __future__ import annotations

import contextlib
from contextvars import ContextVar
from typing import Iterator, Optional

import psycopg
from psycopg.rows import tuple_row
from psycopg_pool import ConnectionPool

from app.settings import settings

# Tenant de la request actual. None = admin / proceso de fondo.
_current_empresa_id: ContextVar[Optional[int]] = ContextVar(
    "current_empresa_id", default=None
)

_pool: Optional[ConnectionPool] = None


def set_request_empresa(empresa_id: Optional[int]) -> None:
    """Fija el tenant de la request en curso (lo lee ``db_conn``)."""
    _current_empresa_id.set(empresa_id)


def current_empresa_id() -> Optional[int]:
    return _current_empresa_id.get()


def _assert_rls_safe_role(conn: psycopg.Connection) -> None:
    """Aborta el arranque si el rol ignora RLS y no se permitió explícitamente."""
    row = conn.execute(
        """
        SELECT rolsuper, rolbypassrls
        FROM pg_roles WHERE rolname = current_user
        """
    ).fetchone()
    rolsuper, rolbypass = (row or (False, False))
    if (rolsuper or rolbypass) and not settings.db_allow_admin_role:
        raise RuntimeError(
            f"El rol de BD '{settings.db_user}' ignora RLS "
            f"(superuser={rolsuper}, bypassrls={rolbypass}). Conecta como un rol "
            "NOSUPERUSER NOBYPASSRLS (docswarm_app) o fija DB_ALLOW_ADMIN_ROLE=1 "
            "para backfills/worker admin de forma deliberada."
        )


def get_pool() -> ConnectionPool:
    """Devuelve (creando si hace falta) el pool global."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings.db_dsn,
            min_size=settings.db_pool_min,
            max_size=settings.db_pool_max,
            open=True,
            kwargs={"autocommit": False},
        )
        with _pool.connection() as conn:
            _assert_rls_safe_role(conn)
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextlib.contextmanager
def db_conn(empresa_id: Optional[int] = "__use_context__") -> Iterator[psycopg.Connection]:
    """Presta una conexión con el tenant aplicado vía SET LOCAL.

    - ``empresa_id`` por defecto toma el valor del ContextVar de la request.
    - Pasar ``None`` fuerza modo admin (ve todo); un entero fuerza ese tenant.
    Hace commit al salir sin error y rollback si hay excepción.
    """
    if empresa_id == "__use_context__":
        empresa_id = _current_empresa_id.get()

    pool = get_pool()
    with pool.connection() as conn:
        # El pool reutiliza el objeto conexión: reseteamos el row_factory a tupla
        # para que un préstamo previo (que usó dict_row) no se filtre a este.
        conn.row_factory = tuple_row
        # SET LOCAL: vive solo en esta transacción, se limpia al commit/rollback.
        conn.execute(
            "SELECT set_config('app.current_empresa_id', %s, true)",
            ("" if empresa_id is None else str(empresa_id),),
        )
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
