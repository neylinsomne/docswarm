"""Lógica de negocio del dominio B2B (auth, companies, contracts, changes, search).

Cada subpaquete expone `schemas` (Pydantic, contrato de la API) y `service`
(operaciones contra la BD). Los routers de `app/api` solo orquestan estos
servicios; no contienen SQL.
"""
