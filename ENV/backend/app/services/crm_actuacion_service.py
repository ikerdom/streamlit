# backend/app/services/crm_actuacion_service.py
from backend.app.schemas.crm_actuacion import (
    ESTADOS_CRM,
    PRIORIDADES_CRM,
    CANALES_CRM,
    CrmActuacionIn,
)


class CrmActuacionService:
    def __init__(self, supabase):
        self.supabase = supabase

    # -----------------------------
    # Listar por cliente
    # -----------------------------
    def listar(self, clienteid: int):
        return (
            self.supabase.table("crm_actuacion")
            .select(
                "crm_actuacionid, clienteid, titulo, descripcion, canal, estado, "
                "prioridad, fecha_vencimiento, fecha_accion, "
                "trabajadorid, trabajador_asignadoid"
            )
            .eq("clienteid", clienteid)
            .order("fecha_vencimiento")
            .execute()
            .data
            or []
        )

    # -----------------------------
    # Crear
    # -----------------------------
    def crear(self, clienteid: int, data: CrmActuacionIn):
        self._validar(data)

        row = data.model_dump()
        row["clienteid"] = clienteid

        self.supabase.table("crm_actuacion").insert(row).execute()

    # -----------------------------
    # Actualizar (estado, fechas, etc.)
    # -----------------------------
    def actualizar(self, crm_id: int, data: CrmActuacionIn):
        self._validar(data)
        self.supabase.table("crm_actuacion").update(
            data.model_dump(exclude_none=True)
        ).eq("crm_actuacionid", crm_id).execute()

    # -----------------------------
    # Validaciones centrales
    # -----------------------------
    def _validar(self, data: CrmActuacionIn):
        if not data.titulo or not data.titulo.strip():
            raise ValueError("El título es obligatorio")

        if data.estado not in ESTADOS_CRM:
            raise ValueError("Estado CRM no válido")

        if data.prioridad not in PRIORIDADES_CRM:
            raise ValueError("Prioridad CRM no válida")

        if data.canal not in CANALES_CRM:
            raise ValueError("Canal CRM no válido")
