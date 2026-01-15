# backend/app/services/tarifas_service.py
from datetime import date
from typing import List, Optional

from backend.app.repositories.tarifas_repo import TarifasRepository
from backend.app.schemas.tarifa import (
    TarifaCatalogos,
    CatalogoItem,
    TarifaReglaOut,
    TarifaReglaCreate,
    TarifaReglaListResponse,
    TarifaReglaUpdate,
    ClienteTarifaCreate,
    PrecioRequest,
    PrecioResponse,
)
from backend.app.services.precio_engine import calcular_precio_linea


class TarifasService:
    def __init__(self, repo: TarifasRepository):
        self.repo = repo

    # -----------------------------
    # Catálogos
    # -----------------------------
    def catalogos(self) -> TarifaCatalogos:
        def to_items(rows: list, id_field: str, label_field: str):
            return [
                CatalogoItem(id=int(r[id_field]), label=str(r[label_field]))
                for r in rows
                if r.get(id_field) is not None
            ]

        tarifas = self.repo.catalogo("tarifa", "tarifaid", "nombre", where_enabled=False, order_field="tarifaid")
        clientes = self.repo.catalogo("cliente", "clienteid", "razon_social", order_field="razon_social")
        grupos = self.repo.catalogo("grupo", "grupoid", "nombre", order_field="nombre")
        productos = self.repo.catalogo("producto", "productoid", "nombre", order_field="nombre")
        familias = self.repo.catalogo("producto_familia", "familia_productoid", "nombre", order_field="nombre")

        return TarifaCatalogos(
            tarifas=to_items(tarifas, "tarifaid", "nombre"),
            clientes=to_items(clientes, "clienteid", "razon_social"),
            grupos=to_items(grupos, "grupoid", "nombre"),
            productos=to_items(productos, "productoid", "nombre"),
            familias=to_items(familias, "familia_productoid", "nombre"),
        )

    # -----------------------------
    # Reglas
    # -----------------------------
    def listar_reglas(
        self,
        *,
        clienteid: Optional[int],
        grupoid: Optional[int],
        productoid: Optional[int],
        familiaid: Optional[int],
        tarifaid: Optional[int],
        incluir_deshabilitadas: bool,
    ) -> TarifaReglaListResponse:
        rows = self.repo.list_reglas()

        # Filtro cliente/grupo manteniendo reglas genéricas (None) para ese ámbito
        if clienteid:
            rows = [r for r in rows if r.get("clienteid") in (None, clienteid)]
        if grupoid:
            rows = [r for r in rows if r.get("grupoid") in (None, grupoid)]

        # Filtro producto/familia respetando el comportamiento previo
        fam_ctx = familiaid
        if productoid and not familiaid:
            fam_ctx = self.repo.producto_familia(productoid)

        if productoid:
            rows = [r for r in rows if (r.get("productoid") == productoid) or (r.get("familia_productoid") == fam_ctx)]
        elif fam_ctx:
            rows = [r for r in rows if r.get("familia_productoid") == fam_ctx]

        if tarifaid:
            rows = [r for r in rows if r.get("tarifaid") == tarifaid]

        if not incluir_deshabilitadas:
            rows = [r for r in rows if r.get("habilitada") is True]

        out = [
            TarifaReglaOut(
                tarifa_reglaid=r.get("tarifa_reglaid"),
                tarifaid=r.get("tarifaid"),
                clienteid=r.get("clienteid"),
                grupoid=r.get("grupoid"),
                productoid=r.get("productoid"),
                familia_productoid=r.get("familia_productoid"),
                fecha_inicio=r.get("fecha_inicio"),
                fecha_fin=r.get("fecha_fin"),
                prioridad=r.get("prioridad"),
                habilitada=bool(r.get("habilitada", True)),
            )
            for r in rows
        ]

        return TarifaReglaListResponse(data=out, total=len(out))

    def crear_regla(self, data: TarifaReglaCreate) -> TarifaReglaOut:
        payload = data.dict(exclude_none=True)
        created = self.repo.insert_regla(payload)
        return TarifaReglaOut(**created)

    def actualizar_regla(self, reglaid: int, data: TarifaReglaUpdate) -> TarifaReglaOut:
        payload = {k: v for k, v in data.dict(exclude_none=True).items()}
        updated = self.repo.update_regla(reglaid, payload)
        if not updated:
            raise ValueError("Regla no encontrada")
        return TarifaReglaOut(**updated)

    def borrar_regla(self, reglaid: int):
        self.repo.delete_regla(reglaid)

    # -----------------------------
    # cliente_tarifa (general)
    # -----------------------------
    def asignar_cliente_tarifa(self, data: ClienteTarifaCreate) -> dict:
        payload = data.dict(exclude_none=True)
        return self.repo.insert_cliente_tarifa(payload)

    # -----------------------------
    # Cálculo de precio (motor centralizado)
    # -----------------------------
    def calcular_precio(self, req: PrecioRequest) -> PrecioResponse:
        res = calcular_precio_linea(
            supabase=self.repo.supabase,
            clienteid=req.clienteid,
            productoid=req.productoid,
            precio_base_unit=req.precio_base_unit,
            cantidad=req.cantidad,
            fecha=req.fecha,
        )
        return PrecioResponse(**res)
