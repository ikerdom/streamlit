# backend/app/repositories/clientes_repo.py
from typing import Optional, Tuple, List
from backend.app.schemas.cliente import ClienteOut


class ClientesRepository:
    def __init__(self, supabase):
        self.supabase = supabase

    def get_clientes(
        self,
        q: Optional[str],
        tipo: Optional[str],
        page: int,
        page_size: int,
        sort_field: str,
        sort_dir: str,
    ) -> Tuple[List[dict], int]:
        """
        Devuelve (clientes, total)
        """

        query = self.supabase.table("cliente").select(
            "clienteid, razon_social, estadoid, grupoid, trabajadorid, formapagoid, tipo_cliente",
            count="exact",
        )

        if q:
            query = query.or_(f"razon_social.ilike.%{q}%")

        if tipo:
            query = query.eq("tipo_cliente", tipo)

        # Orden
        ascending = sort_dir.upper() == "ASC"
        query = query.order(sort_field, desc=not ascending)

        # Paginación
        start = (page - 1) * page_size
        end = start + page_size - 1

        res = query.range(start, end).execute()

        data = res.data or []
        total = res.count or 0

        return data, total

    def get_cliente_detalle(self, clienteid: int) -> dict:
        base = (
            self.supabase.table("cliente")
            .select(
                "clienteid, razon_social, estadoid, grupoid, trabajadorid, formapagoid, categoriaid, tarifaid, observaciones"
            )
            .eq("clienteid", clienteid)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not base:
            return {}

        cliente = base[0]

        direccion = (
            self.supabase.table("cliente_direccion")
            .select("tipo,direccion,ciudad,provincia,pais,cp,telefono,email,documentacion_impresa")
            .eq("clienteid", clienteid)
            .eq("tipo", "fiscal")
            .limit(1)
            .execute()
            .data
        )
        contacto = (
            self.supabase.table("cliente_contacto")
            .select("nombre,email,telefono,rol,es_principal")
            .eq("clienteid", clienteid)
            .eq("es_principal", True)
            .limit(1)
            .execute()
            .data
        )
        banco = (
            self.supabase.table("cliente_banco")
            .select("iban,nombre_banco,fecha_baja")
            .eq("clienteid", clienteid)
            .limit(1)
            .execute()
            .data
        )

        return {
            "cliente": cliente,
            "direccion_fiscal": direccion[0] if direccion else None,
            "contacto_principal": contacto[0] if contacto else None,
            "banco": banco[0] if banco else None,
        }
