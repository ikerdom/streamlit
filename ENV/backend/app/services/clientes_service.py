# backend/app/services/clientes_service.py
import math
from typing import Optional

from backend.app.schemas.cliente import (
    ClienteListResponse,
    ClienteOut,
    Label,
    PresupuestoInfo,
    ClienteDetalle,
    ClienteDireccion,
    ClienteContacto,
    ClienteBanco,
)
from backend.app.repositories.clientes_repo import ClientesRepository


# ============================
# ⚙️ Catálogos (placeholder)
# 👉 En fase 2 irán a repos reales
# ============================
ESTADOS = {
    1: "Activo",
    2: "Inactivo",
    3: "Bloqueado",
}

GRUPOS = {
    1: "General",
    2: "Empresas",
    3: "Distribuidores",
}


class ClientesService:
    def __init__(self, repo: ClientesRepository):
        self.repo = repo

    def listar_clientes(
        self,
        q: Optional[str],
        tipo: Optional[str],
        page: int,
        page_size: int,
        sort_field: str,
        sort_dir: str,
    ) -> ClienteListResponse:
        clientes_raw, total = self.repo.get_clientes(
            q=q,
            tipo=tipo,
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            sort_dir=sort_dir,
        )

        clientes: list[ClienteOut] = []

        for c in clientes_raw:
            data = dict(c) if isinstance(c, dict) else c.__dict__

            estadoid = data.get("estadoid")
            grupoid = data.get("grupoid")
            trabajadorid = data.get("trabajadorid")

            cliente = ClienteOut(
                clienteid=data.get("clienteid"),
                razon_social=data.get("razon_social"),
                identificador=data.get("identificador"),

                estadoid=estadoid,
                grupoid=grupoid,
                trabajadorid=trabajadorid,
                formapagoid=data.get("formapagoid"),

                # 👇 enriquecido
                estado=Label(
                    id=estadoid,
                    label=ESTADOS.get(estadoid),
                )
                if estadoid
                else None,

                grupo=Label(
                    id=grupoid,
                    label=GRUPOS.get(grupoid),
                )
                if grupoid
                else None,

                comercial=f"Comercial {trabajadorid}"
                if trabajadorid
                else None,

                presupuesto_reciente=self._map_presupuesto(
                    data.get("presupuesto_reciente")
                ),
            )

            clientes.append(cliente)

        total_pages = max(1, math.ceil(total / page_size))

        return ClienteListResponse(
            data=clientes,
            total=total,
            total_pages=total_pages,
            page=page,
            page_size=page_size,
        )

    def obtener_detalle(self, clienteid: int) -> ClienteDetalle:
        raw = self.repo.get_cliente_detalle(clienteid)
        if not raw:
            raise ValueError("Cliente no encontrado")

        cli = raw.get("cliente", {})
        cliente = ClienteOut(
            clienteid=cli.get("clienteid"),
            razon_social=cli.get("razon_social"),
            identificador=cli.get("identificador"),
            estadoid=cli.get("estadoid"),
            grupoid=cli.get("grupoid"),
            trabajadorid=cli.get("trabajadorid"),
            formapagoid=cli.get("formapagoid"),
            estado=Label(id=cli.get("estadoid"), label=ESTADOS.get(cli.get("estadoid"))),
            grupo=Label(id=cli.get("grupoid"), label=GRUPOS.get(cli.get("grupoid"))),
        )

        return ClienteDetalle(
            cliente=cliente,
            direccion_fiscal=ClienteDireccion(**raw["direccion_fiscal"]) if raw.get("direccion_fiscal") else None,
            contacto_principal=ClienteContacto(**raw["contacto_principal"]) if raw.get("contacto_principal") else None,
            banco=ClienteBanco(**raw["banco"]) if raw.get("banco") else None,
        )

    # ============================
    # 🧠 Helpers internos
    # ============================
    def _map_presupuesto(self, pres: Optional[dict]) -> Optional[PresupuestoInfo]:
        if not pres:
            return None

        return PresupuestoInfo(
            estado={
                1: "Pendiente",
                2: "Aceptado",
                3: "Rechazado",
            }.get(pres.get("estado_presupuestoid")),
            fecha=pres.get("fecha_presupuesto"),
        )
