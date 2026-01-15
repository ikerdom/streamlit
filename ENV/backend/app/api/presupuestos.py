from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.core.database import get_supabase
from backend.app.repositories.presupuestos_repo import PresupuestosRepository
from backend.app.schemas.presupuesto import (
    PresupuestoCreateIn,
    PresupuestoListResponse,
    PresupuestoOut,
    PresupuestoLineaIn,
    PresupuestoLineaOut,
    PresupuestoRecalcResponse,
    PresupuestoCatalogos,
)
from backend.app.services.presupuestos_service import PresupuestosService

router = APIRouter(prefix="/api/presupuestos", tags=["Presupuestos"])


def get_service(supabase=Depends(get_supabase)) -> PresupuestosService:
    repo = PresupuestosRepository(supabase)
    return PresupuestosService(repo)


@router.get("", response_model=PresupuestoListResponse)
def listar_presupuestos(
    q: Optional[str] = Query(None),
    estadoid: Optional[int] = Query(None),
    clienteid: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    ordenar_por: str = Query("creado_en", pattern="^(creado_en|fecha_presupuesto)$"),
    service: PresupuestosService = Depends(get_service),
):
    return service.listar(q, estadoid, clienteid, page, page_size, ordenar_por)


@router.get("/catalogos", response_model=PresupuestoCatalogos)
def catalogos_presupuesto(supabase=Depends(get_supabase)):
    def items(table: str, id_field: str, label_field: str, order_field: Optional[str] = None, where=None):
        q = supabase.table(table).select(f"{id_field},{label_field}")
        if where:
            for k, v in where.items():
                q = q.eq(k, v)
        if order_field:
            try:
                q = q.order(order_field)
            except Exception:
                pass
        rows = q.execute().data or []
        return [{"id": r[id_field], "label": r[label_field]} for r in rows if r.get(id_field) is not None]

    return PresupuestoCatalogos(
        estados=items("estado_presupuesto", "estado_presupuestoid", "nombre", order_field="estado_presupuestoid"),
        clientes=items("cliente", "clienteid", "razon_social", order_field="razon_social"),
        trabajadores=items("trabajador", "trabajadorid", "nombre", order_field="nombre"),
        formas_pago=items("forma_pago", "formapagoid", "nombre"),
    )


@router.get("/{presupuestoid}", response_model=PresupuestoOut)
def obtener_presupuesto(presupuestoid: int, service: PresupuestosService = Depends(get_service)):
    try:
        return service.obtener(presupuestoid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=PresupuestoOut)
def crear_presupuesto(body: PresupuestoCreateIn, service: PresupuestosService = Depends(get_service)):
    try:
        return service.crear(body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{presupuestoid}", response_model=PresupuestoOut)
def actualizar_presupuesto(
    presupuestoid: int,
    body: dict,
    service: PresupuestosService = Depends(get_service),
):
    try:
        return service.actualizar(presupuestoid, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{presupuestoid}")
def borrar_presupuesto(presupuestoid: int, service: PresupuestosService = Depends(get_service)):
    service.borrar(presupuestoid)
    return {"ok": True}


@router.get("/{presupuestoid}/lineas", response_model=List[PresupuestoLineaOut])
def listar_lineas(presupuestoid: int, service: PresupuestosService = Depends(get_service)):
    return service.listar_lineas(presupuestoid)


@router.post("/{presupuestoid}/lineas", response_model=int)
def agregar_linea(
    presupuestoid: int,
    body: PresupuestoLineaIn,
    service: PresupuestosService = Depends(get_service),
):
    try:
        return service.agregar_linea(presupuestoid, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{presupuestoid}/recalcular", response_model=PresupuestoRecalcResponse)
def recalcular(
    presupuestoid: int,
    fecha_calculo: Optional[date] = None,
    service: PresupuestosService = Depends(get_service),
):
    try:
        return service.recalcular_lineas(presupuestoid, fecha_calculo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{presupuestoid}/convertir-a-pedido")
def convertir_a_pedido(presupuestoid: int, service: PresupuestosService = Depends(get_service)):
    try:
        return service.convertir_a_pedido(presupuestoid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cliente/{clienteid}/basico")
def cliente_basico(clienteid: int, service: PresupuestosService = Depends(get_service)):
    try:
        data = service.cliente_basico(clienteid)
        if not data:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error obteniendo cliente: {e}")
