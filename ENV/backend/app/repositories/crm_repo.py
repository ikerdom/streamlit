# backend/app/repositories/crm_repo.py
from typing import List, Optional


class CrmRepository:
    def __init__(self, supabase):
        self.supabase = supabase

    def listar(self, filtros: dict) -> List[dict]:
        q = self.supabase.table("crm_actuacion").select(
            "crm_actuacionid,titulo,estado,canal,fecha_accion,fecha_vencimiento,prioridad,clienteid,trabajador_asignadoid,trabajadorid"
        )
        if filtros.get("trabajador_asignadoid"):
            q = q.eq("trabajador_asignadoid", filtros["trabajador_asignadoid"])
        if filtros.get("clienteid"):
            q = q.eq("clienteid", filtros["clienteid"])
        if filtros.get("estado"):
            q = q.eq("estado", filtros["estado"])
        if filtros.get("canal"):
            q = q.eq("canal", filtros["canal"])
        q = q.order("fecha_vencimiento", desc=False)
        res = q.execute()
        rows = res.data or []
        if filtros.get("buscar"):
            s = filtros["buscar"].lower()
            rows = [r for r in rows if s in (r.get("titulo") or "").lower()]
        return rows

    def crear(self, data: dict) -> dict:
        res = self.supabase.table("crm_actuacion").insert(data).execute()
        return (res.data or [None])[0]

    def actualizar(self, accionid: int, data: dict) -> dict:
        self.supabase.table("crm_actuacion").update(data).eq("crm_actuacionid", accionid).execute()
        res = (
            self.supabase.table("crm_actuacion")
            .select("*")
            .eq("crm_actuacionid", accionid)
            .maybe_single()
            .execute()
        )
        return res.data or {}

    def obtener(self, accionid: int) -> Optional[dict]:
        res = (
            self.supabase.table("crm_actuacion")
            .select("*")
            .eq("crm_actuacionid", accionid)
            .maybe_single()
            .execute()
        )
        return res.data or None
