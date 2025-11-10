# modules/presupuesto_pdf.py
import io, base64
from datetime import datetime
import streamlit as st

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

BUCKET_DEFAULT = "presupuestos"

def _money(v): 
    try: return f"{float(v):,.2f} €"
    except: return "-"

def _build_data_real(supabase, presupuestoid: int) -> dict:
    pres = supabase.table("presupuesto").select("*").eq("presupuestoid", presupuestoid).single().execute().data
    if not pres: raise RuntimeError("Presupuesto no encontrado")

    cliente = {}
    if pres.get("clienteid"):
        cliente = supabase.table("cliente").select("*").eq("clienteid", pres["clienteid"]).maybe_single().execute().data or {}

    direccion = {}
    if pres.get("direccion_envioid"):
        direccion = (supabase.table("cliente_direccion")
                     .select("direccion, cp, ciudad, provincia, region(nombre)")
                     .eq("cliente_direccionid", pres["direccion_envioid"])
                     .maybe_single().execute().data or {})

    region_nombre = "-"
    if direccion.get("region") and isinstance(direccion["region"], dict):
        region_nombre = direccion["region"].get("nombre")

    lineas = (supabase.table("presupuesto_detalle")
              .select("descripcion, cantidad, precio_unitario, descuento_pct, iva_pct, importe_base, importe_total_linea")
              .eq("presupuestoid", presupuestoid).order("presupuesto_detalleid").execute().data or [])

    total_base = sum(float(l.get("importe_base") or 0) for l in lineas)
    total_iva  = sum(float(l.get("importe_base") or 0) * float(l.get("iva_pct") or 0) / 100 for l in lineas)
    total_total = total_base + total_iva

    data_real = {
        "empresa": {
            "nombre": "EnteNova S.L.",
            "cif": "B-12345678",
            "direccion": "C/ Mayor 123",
            "cp": "28013",
            "ciudad": "Madrid",
            "web": "www.entenova.com",
            "pie": "EnteNova · Presupuestos · www.entenova.com",
        },
        "cliente": {
            "nombre": cliente.get("razon_social") or cliente.get("nombre_comercial") or "-",
            "identificador": cliente.get("cif_nif") or cliente.get("cif") or "-",
            "direccion": direccion.get("direccion") or "-",
            "cp": direccion.get("cp") or "-",
            "ciudad": direccion.get("ciudad") or "-",
            "provincia": direccion.get("provincia") or "-",
            "region": region_nombre,
        },
        "presupuesto": {
            "numero": pres.get("numero"),
            "fecha": pres.get("fecha_presupuesto"),
            "notas": pres.get("observaciones") or "Oferta válida 30 días. Portes no incluidos.",
            "total": total_total,
        },
        "lineas": [
            {
                "concepto": l["descripcion"],
                "unidades": l["cantidad"],
                "precio": l["precio_unitario"],
                "dto": l.get("descuento_pct") or 0,
                "iva": l.get("iva_pct") or 0,
                "base": l.get("importe_base"),
                "total": l.get("importe_total_linea"),
            }
            for l in lineas
        ],
        "totales": {"base": total_base, "iva": total_iva, "total": total_total},
    }
    return data_real

def build_pdf_bytes(data_real: dict) -> tuple[bytes, str]:
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)

    emp = data_real.get("empresa", {})
    cli = data_real.get("cliente", {})
    pre = data_real.get("presupuesto", {})
    lineas = data_real.get("lineas", [])
    tot = data_real.get("totales", {})

    elements = []
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

    data_table = [["Descripción", "Cant.", "Precio", "DTO", "IVA", "Base", "Total"]]
    for l in lineas:
        data_table.append([
            l.get("concepto","-"),
            str(l.get("unidades","")),
            f"{float(l.get('precio') or 0):.2f} €",
            f"{float(l.get('dto') or 0):.1f}%",
            f"{float(l.get('iva') or 0):.1f}%",
            f"{float(l.get('base') or 0):.2f} €",
            f"{float(l.get('total') or 0):.2f} €",
        ])
    table = Table(data_table, colWidths=[70*mm, 15*mm, 20*mm, 15*mm, 15*mm, 25*mm, 25*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ]))
    elements.append(table); elements.append(Spacer(1, 12))

    total_data = [["Base imponible", _money(tot.get("base"))],
                  ["IVA/IGIC", _money(tot.get("iva"))],
                  ["TOTAL PRESUPUESTO", _money(tot.get("total"))]]
    ttot = Table(total_data, colWidths=[120*mm, 50*mm])
    ttot.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
    ]))
    elements.append(ttot); elements.append(Spacer(1, 12))
    elements.append(Paragraph(pre.get("notas", "-"), styles["Normal"]))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    file_name = f"presupuesto_{pre.get('numero','sin_numero')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return pdf_bytes, file_name


def upload_pdf_to_storage(supabase, pdf_bytes: bytes, file_name: str, bucket: str = BUCKET_DEFAULT):
    """Sube el PDF bajo demanda al bucket y devuelve URL pública (si existe policy)."""
    supabase.storage.from_(bucket).upload(file_name, pdf_bytes, {"content-type": "application/pdf"})
    url = supabase.storage.from_(bucket).get_public_url(file_name)
    return url

def generate_pdf_for_download(supabase, presupuestoid: int):
    """Genera el PDF y muestra preview + botón de descarga (NO sube a Storage)."""
    data_real = _build_data_real(supabase, presupuestoid)
    pdf_bytes, file_name = build_pdf_bytes(data_real)

    # ✅ Preview inline
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{pdf_b64}" width="100%" height="720px"></iframe>',
        unsafe_allow_html=True,
    )

    # ✅ Botón de descarga con key único
    st.download_button(
        "⬇️ Descargar PDF",
        pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
        use_container_width=True,
        key=f"dl_pdf_{presupuestoid}",
    )

    return pdf_bytes, file_name
