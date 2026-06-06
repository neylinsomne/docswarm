"""Render de contratos y documentos generados a PDF (fpdf2, sin deps de sistema).

Las fuentes core de fpdf2 usan latin-1; se sanitiza el texto para evitar fallos
con caracteres fuera de ese rango (≤, →, comillas tipográficas, etc.). Todos los
`multi_cell` vuelven al margen izquierdo (evita el error "Not enough horizontal
space" de fpdf2 cuando la X queda a la derecha).
"""

from __future__ import annotations

import re
from typing import Any

_REEMPLAZOS = {
    "≤": "<=", "≥": ">=", "→": "->", "—": "-", "–": "-",
    "“": '"', "”": '"', "‘": "'", "’": "'", "•": "-", "…": "...", "·": "-",
}


def _latin1(texto: str) -> str:
    if texto is None:
        return ""
    texto = str(texto)
    for a, b in _REEMPLAZOS.items():
        texto = texto.replace(a, b)
    return texto.encode("latin-1", "replace").decode("latin-1")


def _mc(pdf, h: float, texto: str) -> None:
    """multi_cell de ancho completo que siempre arranca y termina en el margen izq."""
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, h, _latin1(texto), new_x="LMARGIN", new_y="NEXT")


def _money(v: Any, moneda: str = "COP") -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v):,.0f} {moneda}"
    except (TypeError, ValueError):
        return str(v)


def _strip_md(texto: str) -> str:
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = re.sub(r"`(.+?)`", r"\1", texto)
    texto = re.sub(r"\[ref:[^\]]+\]", "", texto)
    return texto


def render_contrato_pdf(contrato: dict, *, proveedor: str = "",
                        comprador: str = "Bayern S.A.") -> bytes:
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("helvetica", "B", 16)
    _mc(pdf, 9, contrato.get("titulo") or "Contrato")
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(110, 110, 110)
    num = contrato.get("numero") or f"#{contrato.get('id')}"
    _mc(pdf, 6, f"No. {num}   -   Estado: {contrato.get('estado','')}")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 11)
    _mc(pdf, 7, "Partes")
    pdf.set_font("helvetica", "", 10)
    _mc(pdf, 6, f"Comprador: {comprador}")
    _mc(pdf, 6, f"Proveedor: {proveedor or contrato.get('empresa_proveedor_id','')}")
    pdf.ln(1)

    datos = [
        ("Objeto", contrato.get("objeto") or "-"),
        ("Sector", contrato.get("sector") or "-"),
        ("Valor", _money(contrato.get("valor"), contrato.get("moneda") or "COP")),
        ("Vigencia", f"{contrato.get('fecha_inicio') or '-'}  a  {contrato.get('fecha_fin') or '-'}"),
        ("Firmado por el proveedor", "Si" if contrato.get("firmado_proveedor") else "No"),
    ]
    for k, v in datos:
        pdf.set_font("helvetica", "B", 10)
        _mc(pdf, 6, k)
        pdf.set_font("helvetica", "", 10)
        _mc(pdf, 6, str(v))
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    _mc(pdf, 8, "Clausulas")
    clausulas = sorted(contrato.get("clausulas") or [], key=lambda c: c.get("orden", 0))
    if not clausulas:
        pdf.set_font("helvetica", "I", 10)
        _mc(pdf, 6, "(Sin clausulas registradas)")
    for i, cl in enumerate(clausulas, start=1):
        pdf.set_font("helvetica", "B", 10)
        titulo = cl.get("titulo") or cl.get("tipo") or f"Clausula {i}"
        _mc(pdf, 6, f"{i}. [{cl.get('tipo','')}] {titulo}")
        pdf.set_font("helvetica", "", 10)
        _mc(pdf, 6, cl.get("contenido") or "")
        if cl.get("valor") is not None:
            pdf.set_text_color(80, 80, 80)
            _mc(pdf, 5, f"   Valor: {_money(cl.get('valor'), contrato.get('moneda') or 'COP')}")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(1)

    _bloque_firmas(pdf, proveedor=proveedor, comprador=comprador, contrato=contrato)
    return bytes(pdf.output())


def render_documento_pdf(titulo: str, markdown: str, *, proveedor: str = "",
                         comprador: str = "Bayern S.A.") -> bytes:
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("helvetica", "B", 16)
    _mc(pdf, 9, titulo or "Documento")
    pdf.ln(2)

    for raw in (markdown or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            pdf.ln(2)
            continue
        m_h = re.match(r"^(#{1,6})\s+(.*)$", line)
        bold_full = re.match(r"^\*\*(.+?)\*\*:?\s*$", line.strip())
        if m_h or bold_full:
            texto = (m_h.group(2) if m_h else bold_full.group(1)).strip()
            pdf.set_font("helvetica", "B", 12)
            _mc(pdf, 7, _strip_md(texto))
            pdf.set_font("helvetica", "", 10)
            continue
        m_li = re.match(r"^\s*[-*]\s+(.*)$", line)
        if m_li:
            pdf.set_font("helvetica", "", 10)
            _mc(pdf, 6, "  -  " + _strip_md(m_li.group(1)))
            continue
        pdf.set_font("helvetica", "", 10)
        _mc(pdf, 6, _strip_md(line))

    _bloque_firmas(pdf, proveedor=proveedor, comprador=comprador, contrato={})
    return bytes(pdf.output())


def _bloque_firmas(pdf, *, proveedor: str, comprador: str, contrato: dict) -> None:
    """Deja al final dos espacios de firma (Comprador y Proveedor)."""
    if pdf.get_y() > 215:
        pdf.add_page()
    else:
        pdf.ln(10)

    pdf.set_font("helvetica", "B", 12)
    _mc(pdf, 8, "Firmas")
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(110, 110, 110)
    _mc(pdf, 5, "En constancia de lo anterior, las partes firman el presente contrato.")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(16)

    y = pdf.get_y()
    ancho = (pdf.w - pdf.l_margin - pdf.r_margin - 16) / 2
    x1 = pdf.l_margin
    x2 = pdf.l_margin + ancho + 16

    firmado = bool(contrato.get("firmado_proveedor"))
    fecha = contrato.get("fecha_firma")
    estado_prov = ""
    if firmado:
        estado_prov = "Firmado electronicamente" + (f" - {str(fecha)[:19]}" if fecha else "")

    for x, titulo, nombre, estado in (
        (x1, "EL COMPRADOR", comprador, ""),
        (x2, "EL PROVEEDOR", proveedor or "Proveedor", estado_prov),
    ):
        pdf.line(x, y, x + ancho, y)
        pdf.set_xy(x, y + 2)
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(ancho, 5, _latin1(titulo))
        pdf.set_xy(x, y + 7)
        pdf.set_font("helvetica", "", 9)
        pdf.cell(ancho, 5, _latin1(nombre))
        if estado:
            pdf.set_xy(x, y + 12)
            pdf.set_text_color(30, 130, 70)
            pdf.set_font("helvetica", "I", 8)
            pdf.cell(ancho, 5, _latin1(estado))
            pdf.set_text_color(0, 0, 0)
        pdf.set_xy(x, y + 17)
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(ancho, 5, _latin1("Nombre / C.C. / Fecha"))
        pdf.set_text_color(0, 0, 0)
