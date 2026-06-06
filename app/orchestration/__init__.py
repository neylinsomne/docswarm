"""Orquestación: swarm de agentes (engine docswarm) + worker de cola durable."""

from app.orchestration.supervisor import build_runner, generar_documento

__all__ = ["build_runner", "generar_documento"]
