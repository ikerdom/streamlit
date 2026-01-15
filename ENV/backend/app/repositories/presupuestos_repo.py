# backend/app/repositories/presupuestos_repo.py
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple


class PresupuestosRepository:
    def __init__(self, supabase):
        self.supabase = supabase

    # -----------------------------
    # Listado paginado
    # -----------------------------
    def listar(
        self,
        q: Optional[str],
        estadoid: Optional[int],
        clienteid: Optional[int],
        page: int,
        page_size: int,
        ordenar_por: str,
    ) -> Tuple[List[dict], int]:
        query = self.supabase.table("presupuesto").select("*", count="exact")

        if q:
            query = query.or_(f"numero.ilike.%{q}%,referencia_cliente.ilike.%{q}%")

        if estadoid:
            query = query.eq("estado_presupuestoid", estadoid)

        if clienteid:
            query = query.eq("clienteid", clienteid)

        if ordenar_por == "fecha_presupuesto":
            query = query.order("fecha_presupuesto", desc=True)
        else:
            # preferimos creado_en si existe; si no, fecha_presupuesto
            try:
                query = query.order("creado_en", desc=True)
            except Exception:
                query = query.order("fecha_presupuesto", desc=True)

        start = (page - 1) * page_size
        end = start + page_size - 1
        res = query.range(start, end).execute()
        return res.data or [], res.count or 0

    # -----------------------------
    # Cabecera
    # -----------------------------
    def obtener(self, presupuestoid: int) -> Optional[dict]:
        res = (
            self.supabase.table("presupuesto")
            .select("*")
            .eq("presupuestoid", presupuestoid)
            .maybe_single()
            .execute()
        )
        return res.data or None

    def crear(self, data: dict) -> dict:
        res = self.supabase.table("presupuesto").insert(data).execute()
        return (res.data or [None])[0]

    def actualizar(self, presupuestoid: int, data: dict):
        self.supabase.table("presupuesto").update(data).eq("presupuestoid", presupuestoid).execute()

    def borrar(self, presupuestoid: int):
        self.supabase.table("presupuesto").delete().eq("presupuestoid", presupuestoid).execute()

    # -----------------------------
    # LÍneas
    # -----------------------------
    def listar_lineas(self, presupuestoid: int) -> List[dict]:
        res = (
            self.supabase.table("presupuesto_detalle")
            .select(
                "presupuesto_detalleid, productoid, descripcion, cantidad, precio_unitario, "
                "descuento_pct, iva_pct, importe_base, importe_total_linea, tarifa_aplicada, nivel_tarifa, iva_origen"
            )
            .eq("presupuestoid", presupuestoid)
            .order("presupuesto_detalleid", desc=False)
            .execute()
        )
        return res.data or []

    def insertar_linea(self, data: dict) -> int:
        res = self.supabase.table("presupuesto_detalle").insert(data).execute()
        return res.data[0]["presupuesto_detalleid"]

    def actualizar_linea(self, detalleid: int, data: dict):
        self.supabase.table("presupuesto_detalle").update(data).eq("presupuesto_detalleid", detalleid).execute()

    def borrar_lineas(self, presupuestoid: int):
        self.supabase.table("presupuesto_detalle").delete().eq("presupuestoid", presupuestoid).execute()

    def upsert_totales(self, data: dict):
        self.supabase.table("presupuesto_totales").upsert(data).execute()

    # -----------------------------
    # Apoyos
    # -----------------------------
    def estado_por_nombre(self, nombre: str) -> Optional[int]:
        res = (
            self.supabase.table("estado_presupuesto")
            .select("estado_presupuestoid, nombre")
            .ilike("nombre", nombre)
            .maybe_single()
            .execute()
        )
        d = res.data or None
        return d.get("estado_presupuestoid") if d else None

    def region_desde_direccion(self, direccionid: Optional[int]) -> Optional[int]:
        if not direccionid:
            return None
        res = (
            self.supabase.table("cliente_direccion")
            .select("regionid")
            .eq("cliente_direccionid", direccionid)
            .maybe_single()
            .execute()
        )
        d = res.data or None
        return d.get("regionid") if d else None

    def region_preferente_cliente(self, clienteid: int) -> Optional[int]:
        # 1) envio, 2) fiscal
        try:
            envio = (
                self.supabase.table("cliente_direccion")
                .select("regionid")
                .eq("clienteid", clienteid)
                .eq("tipo", "envio")
                .limit(1)
                .execute()
                .data
            )
            if envio and envio[0].get("regionid"):
                return envio[0]["regionid"]
        except Exception:
            pass

        try:
            fiscal = (
                self.supabase.table("cliente_direccion")
                .select("regionid")
                .eq("clienteid", clienteid)
                .eq("tipo", "fiscal")
                .limit(1)
                .execute()
                .data
            )
            if fiscal and fiscal[0].get("regionid"):
                return fiscal[0]["regionid"]
        except Exception:
            pass
        return None

    def ultimo_numero_prefijo(self, prefijo: str) -> List[str]:
        res = (
            self.supabase.table("presupuesto")
            .select("numero")
            .ilike("numero", f"{prefijo}%")
            .execute()
        )
        return [r.get("numero") for r in (res.data or []) if r.get("numero")]

    def pedido_por_presupuesto(self, presupuestoid: int) -> Optional[dict]:
        res = (
            self.supabase.table("pedido")
            .select("pedidoid, numero, estado_pedidoid")
            .eq("presupuesto_origenid", presupuestoid)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None

    def crear_pedido(self, data: dict) -> dict:
        res = self.supabase.table("pedido").insert(data).execute()
        return (res.data or [None])[0]

    def insertar_linea_pedido(self, data: dict):
        self.supabase.table("pedido_detalle").insert(data).execute()

    def marcar_presupuesto_estado(self, presupuestoid: int, estadoid: int, editable: Optional[bool] = None):
        update_data: Dict[str, object] = {"estado_presupuestoid": estadoid}
        if editable is not None:
            update_data["editable"] = editable
        self.supabase.table("presupuesto").update(update_data).eq("presupuestoid", presupuestoid).execute()

    def cliente_basico(self, clienteid: int) -> Optional[dict]:
        res = (
            self.supabase.table("cliente")
            .select("clienteid, razon_social, nombre_comercial, cif_nif, cif, telefono, email")
            .eq("clienteid", clienteid)
            .maybe_single()
            .execute()
        )
        return res.data or None
