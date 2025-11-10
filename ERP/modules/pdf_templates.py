# modules/pdf_templates.py
# =========================================================
# 📄 Plantillas PDF profesionales para Presupuestos / Pedidos
# =========================================================
import base64
from io import BytesIO
from datetime import datetime, date
import streamlit as st

# ---------------------------------------------------------
# Dependencias reportlab (seguras)
# ---------------------------------------------------------
_REPORTLAB_OK = True
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))  # soporte UTF-8
except Exception as _err:
    _REPORTLAB_OK = False
    _REPORTLAB_ERROR = _err


# ---------------------------------------------------------
# Utilidades
# ---------------------------------------------------------
def _ensure_reportlab():
    if _REPORTLAB_OK:
        return True
    st.error(f"❌ Falta 'reportlab'. Instálalo con `pip install reportlab pillow`\n\n{_REPORTLAB_ERROR}")
    return False

def _fmt_money(v):
    try:
        return f"{float(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "-"

def _fmt_date(d):
    if not d:
        return "-"
    if isinstance(d, (datetime, date)):
        return d.strftime("%d/%m/%Y")
    try:
        return datetime.fromisoformat(str(d)).strftime("%d/%m/%Y")
    except Exception:
        return str(d)

def _maybe(val, default="-"):
    return val if val not in (None, "", "null") else default


# =========================================================
# 🧱 ESTILOS Y MOTOR BASE
# =========================================================
def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H1", fontSize=16, fontName="Helvetica-Bold", spaceAfter=8))
    styles.add(ParagraphStyle(name="H2", fontSize=12.5, fontName="Helvetica-Bold", spaceAfter=6))
    styles.add(ParagraphStyle(name="Body", fontSize=9.8, fontName="Helvetica"))
    styles.add(ParagraphStyle(name="Tiny", fontSize=8, fontName="Helvetica-Oblique", textColor=colors.grey))
    return styles


def _header_footer(canvas, doc, empresa):
    """Cabecera y pie de página uniformes."""
    canvas.saveState()
    top = A4[1] - 15 * mm
    bottom = 12 * mm

    # Línea superior
    canvas.setStrokeColorRGB(0.85, 0.87, 0.92)
    canvas.setLineWidth(0.6)
    canvas.line(15 * mm, top, A4[0] - 15 * mm, top)

    # Logo / nombre
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(15 * mm, top - 9 * mm, _maybe(empresa.get("nombre"), "EnteNova S.L."))

    # Datos empresa (derecha)
    canvas.setFont("Helvetica", 8.5)
    right_x = A4[0] - 15 * mm
    lines = [
        _maybe(empresa.get("cif"), ""),
        _maybe(empresa.get("direccion"), ""),
        f"{_maybe(empresa.get('cp'), '')} {_maybe(empresa.get('ciudad'), '')}",
        _maybe(empresa.get("web"), ""),
    ]
    dy = 0
    for ln in lines:
        if ln:
            canvas.drawRightString(right_x, top - 9 * mm - dy, ln)
            dy += 4 * mm

    # Línea inferior + pie
    canvas.setStrokeColorRGB(0.85, 0.87, 0.92)
    canvas.line(15 * mm, bottom, A4[0] - 15 * mm, bottom)
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColorRGB(0.45, 0.47, 0.52)
    canvas.drawString(15 * mm, bottom - 4.5 * mm, _maybe(empresa.get("pie"), "Documento generado automáticamente"))
    canvas.drawRightString(A4[0] - 15 * mm, bottom - 4.5 * mm, f"Página {doc.page}")
    canvas.restoreState()


# =========================================================
# 🧾 GENERADOR DE PRESUPUESTOS
# =========================================================
def build_presupuesto_pdf(data: dict) -> bytes:
    styles = _build_styles()
    empresa = data.get("empresa", {})
    cliente = data.get("cliente", {})
    pres = data.get("presupuesto", {})
    lineas = data.get("lineas", [])
    tot = data.get("totales", {})

    # Cuerpo
    cuerpo = []
    cuerpo.append(Paragraph("🧾 PRESUPUESTO", styles["H1"]))
    cuerpo.append(Spacer(1, 6))

    # Info básica
    info = f"""
    <b>Nº:</b> {_maybe(pres.get('numero'))} &nbsp;&nbsp;
    <b>Fecha:</b> {_fmt_date(pres.get('fecha'))}<br/>
    <b>Cliente:</b> {_maybe(cliente.get('nombre'))}<br/>
    {_maybe(cliente.get('direccion'))}, {_maybe(cliente.get('cp'))} {_maybe(cliente.get('ciudad'))}
    """
    cuerpo.append(Paragraph(info, styles["Body"]))
    cuerpo.append(Spacer(1, 8))

    # Tabla líneas
    headers = ["Concepto", "Ud.", "P.Unit", "Dto", "IVA", "Importe"]
    rows = [headers]
    for ln in lineas:
        ud = float(ln.get("unidades") or 0)
        pu = float(ln.get("precio") or 0)
        dto = float(ln.get("dto") or 0)
        iva = float(ln.get("iva") or 21)
        importe = ud * pu * (1 - dto / 100)
        rows.append([
            _maybe(ln.get("concepto")),
            f"{ud:.2f}", _fmt_money(pu), f"{dto:.0f}%", f"{iva:.0f}%", _fmt_money(importe)
        ])

    table = Table(rows, colWidths=[None, 22 * mm, 25 * mm, 18 * mm, 18 * mm, 28 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))
    cuerpo += [table, Spacer(1, 8)]

    # Totales
    tot_rows = [
        ["Base imponible", _fmt_money(tot.get("base"))],
        ["IVA", _fmt_money(tot.get("iva"))],
        ["<b>Total</b>", f"<b>{_fmt_money(tot.get('total'))}</b>"],
    ]
    ttot = Table(tot_rows, colWidths=[40 * mm, 30 * mm], hAlign="RIGHT")
    ttot.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 2), (-1, 2), 11),
        ("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor("#111827")),
    ]))
    cuerpo += [ttot, Spacer(1, 6)]

    # Notas
    if pres.get("notas"):
        cuerpo += [Paragraph("<b>Notas</b>", styles["H2"]), Paragraph(pres["notas"], styles["Body"])]

    # Render PDF
    buff = BytesIO()
    doc = SimpleDocTemplate(
        buff, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=30 * mm, bottomMargin=20 * mm
    )
    doc.build(cuerpo,
              onFirstPage=lambda c, d: _header_footer(c, d, empresa),
              onLaterPages=lambda c, d: _header_footer(c, d, empresa))
    return buff.getvalue()

import io
import base64
import streamlit as st
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet


# ======================================================
# 📄 Render PDF de presupuesto con vista previa y subida a Supabase
# ======================================================
def render_presupuesto_pdf_panel(data_real: dict, supabase=None, bucket="presupuestos", height_preview=720):
    """
    Genera y muestra el PDF del presupuesto.
    - data_real: estructura unificada (empresa, cliente, presupuesto, lineas, totales)
    - supabase: cliente de conexión Supabase (para subir PDF)
    - bucket: nombre del bucket destino
    - height_preview: alto de la vista previa en px
    """

    try:
        # -------------------------------------------------
        # 1️⃣ Crear PDF en memoria
        # -------------------------------------------------
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        elements = []

        emp = data_real.get("empresa", {})
        cli = data_real.get("cliente", {})
        pre = data_real.get("presupuesto", {})
        lineas = data_real.get("lineas", [])
        tot = data_real.get("totales", {})

        # -------------------------------------------------
        # 2️⃣ Encabezado
        # -------------------------------------------------
        elements.append(Paragraph(f"<b>{emp.get('nombre','')}</b>", styles["Title"]))
        elements.append(Paragraph(f"{emp.get('direccion','')} — {emp.get('cp','')} {emp.get('ciudad','')}", styles["Normal"]))
        elements.append(Paragraph(f"CIF: {emp.get('cif','-')} · Web: {emp.get('web','')}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        elements.append(Paragraph(f"<b>PRESUPUESTO Nº {pre.get('numero','')}</b>", styles["Heading2"]))
        elements.append(Paragraph(f"Fecha: {pre.get('fecha','-')}", styles["Normal"]))
        elements.append(Spacer(1, 6))

        elements.append(Paragraph("<b>Cliente:</b>", styles["Heading3"]))
        elements.append(Paragraph(f"{cli.get('nombre','-')} ({cli.get('identificador','-')})", styles["Normal"]))
        elements.append(Paragraph(f"{cli.get('direccion','-')} · {cli.get('cp','-')} {cli.get('ciudad','-')} ({cli.get('provincia','-')})", styles["Normal"]))
        elements.append(Paragraph(f"Región: {cli.get('region','-')}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        # -------------------------------------------------
        # 3️⃣ Tabla de líneas
        # -------------------------------------------------
        data_table = [["Descripción", "Cant.", "Precio", "DTO", "IVA", "Base", "Total"]]
        for l in lineas:
            data_table.append([
                l.get("concepto", "-"),
                str(l.get("unidades", "")),
                f"{float(l.get('precio') or 0):.2f} €",
                f"{float(l.get('dto') or 0):.1f}%",
                f"{float(l.get('iva') or 0):.1f}%",
                f"{float(l.get('base') or 0):.2f} €",
                f"{float(l.get('total') or 0):.2f} €",
            ])

        table = Table(data_table, colWidths=[70*mm, 15*mm, 20*mm, 15*mm, 15*mm, 25*mm, 25*mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

        # -------------------------------------------------
        # 4️⃣ Totales
        # -------------------------------------------------
        total_data = [
            ["Base imponible", f"{float(tot.get('base') or 0):,.2f} €"],
            ["IVA/IGIC", f"{float(tot.get('iva') or 0):,.2f} €"],
            ["TOTAL PRESUPUESTO", f"{float(tot.get('total') or 0):,.2f} €"],
        ]
        total_table = Table(total_data, colWidths=[120*mm, 50*mm])
        total_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ]))
        elements.append(total_table)
        elements.append(Spacer(1, 12))

        # -------------------------------------------------
        # 5️⃣ Notas
        # -------------------------------------------------
        elements.append(Paragraph("<b>Notas:</b>", styles["Heading3"]))
        elements.append(Paragraph(pre.get("notas", "-"), styles["Normal"]))
        elements.append(Spacer(1, 18))

        elements.append(Paragraph(emp.get("pie", ""), styles["Normal"]))

        doc.build(elements)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        # -------------------------------------------------
        # 6️⃣ Subida a Supabase Storage
        # -------------------------------------------------
        file_name = f"presupuesto_{pre.get('numero','sin_numero')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        public_url = None

        if supabase and bucket:
            try:
                # subir al bucket docs/
                supabase.storage.from_(bucket or "presupuestos").upload(file_name, pdf_bytes, {"content-type": "application/pdf"})
                
                res = supabase.storage.from_(bucket).get_public_url(file_name)
                if res:
                    public_url = res
                    st.success("📤 PDF guardado correctamente en Supabase Storage.")
            except Exception as e:
                st.warning(f"⚠️ No se pudo subir el PDF a Supabase: {e}")

        # -------------------------------------------------
        # 7️⃣ Vista previa embebida
        # -------------------------------------------------
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_display = f'<iframe src="data:application/pdf;base64,{pdf_b64}" width="100%" height="{height_preview}px"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)

        # -------------------------------------------------
        # 8️⃣ Enlace de descarga / acceso público
        # -------------------------------------------------
        st.download_button(
            "⬇️ Descargar PDF",
            pdf_bytes,
            file_name=file_name,
            mime="application/pdf",
            use_container_width=True,
        )

        if public_url:
            st.markdown(f"🔗 [Abrir en Supabase Storage]({public_url})")

    except Exception as e:
        st.error(f"❌ Error generando PDF: {e}")
