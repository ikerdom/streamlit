# backend/app/services/cliente_contacto_service.py
from typing import Any, Dict, List, Optional, Union


def _parse_multi(val: Optional[Union[List[Any], str]]) -> List[str]:
    """
    Normaliza email/telefono:
    - lista -> lista de strings limpios
    - string con comas -> lista
    - string estilo "{a,b}" -> lista
    """
    if val is None:
        return []

    if isinstance(val, list):
        out = []
        for x in val:
            s = str(x).strip()
            if s:
                out.append(s)
        return out

    s = str(val).strip()
    if not s:
        return []

    # Postgres array "{a,b}"
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1].strip()
        if not s:
            return []
        parts = [p.strip().strip('"').strip("'") for p in s.split(",")]
        return [p for p in parts if p]

    # "a,b,c"
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts


class ClienteContactoService:
    def __init__(self, supabase):
        self.supabase = supabase

    # -----------------------------
    # Listar
    # -----------------------------
    def listar(self, clienteid: int) -> List[Dict[str, Any]]:
        rows = (
            self.supabase.table("cliente_contacto")
            .select("*")
            .eq("clienteid", clienteid)
            .order("es_principal", desc=True)
            .order("nombre")
            .execute()
            .data
            or []
        )

        # Normalizamos salida a listas (para UI)
        for r in rows:
            r["email"] = _parse_multi(r.get("email"))
            r["telefono"] = _parse_multi(r.get("telefono"))
            r["es_principal"] = bool(r.get("es_principal"))
        return rows

    # -----------------------------
    # Crear
    # -----------------------------
    def crear(self, clienteid: int, data: dict) -> int:
        if not data.get("nombre") or not str(data["nombre"]).strip():
            raise ValueError("El nombre es obligatorio")

        # normaliza multi
        emails = _parse_multi(data.get("email"))
        tels = _parse_multi(data.get("telefono"))

        row = {**data}
        row["clienteid"] = clienteid

        # Guardamos como arrays si tu columna lo permite; si no, lo guardamos como string.
        # Supabase suele aceptar list -> array.
        row["email"] = emails if emails else None
        row["telefono"] = tels if tels else None

        es_principal = bool(row.get("es_principal") or False)

        if es_principal:
            self._desmarcar_principal(clienteid)

        res = self.supabase.table("cliente_contacto").insert(row).execute()
        return res.data[0]["cliente_contactoid"]

    # -----------------------------
    # Actualizar
    # -----------------------------
    def actualizar(self, clienteid: int, contactoid: int, data: dict):
        if "nombre" in data and (not data["nombre"] or not str(data["nombre"]).strip()):
            raise ValueError("El nombre es obligatorio")

        emails = _parse_multi(data.get("email")) if "email" in data else None
        tels = _parse_multi(data.get("telefono")) if "telefono" in data else None

        row = {**data}
        if emails is not None:
            row["email"] = emails if emails else None
        if tels is not None:
            row["telefono"] = tels if tels else None

        # Si llega es_principal True aquí, respetamos regla
        if row.get("es_principal") is True:
            self._desmarcar_principal(clienteid)

        self.supabase.table("cliente_contacto").update(row).eq(
            "cliente_contactoid", contactoid
        ).execute()

    # -----------------------------
    # Borrar
    # -----------------------------
    def borrar(self, clienteid: int, contactoid: int):
        # (opcional futuro) impedir borrar el principal si es el único
        self.supabase.table("cliente_contacto").delete().eq(
            "cliente_contactoid", contactoid
        ).execute()

    # -----------------------------
    # Hacer principal (REGLA CLAVE)
    # -----------------------------
    def hacer_principal(self, clienteid: int, contactoid: int):
        self._desmarcar_principal(clienteid)
        self.supabase.table("cliente_contacto").update(
            {"es_principal": True}
        ).eq("cliente_contactoid", contactoid).execute()

    # -----------------------------
    # Interno
    # -----------------------------
    def _desmarcar_principal(self, clienteid: int):
        self.supabase.table("cliente_contacto").update(
            {"es_principal": False}
        ).eq("clienteid", clienteid).execute()
