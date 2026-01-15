# backend/app/schemas/crm_actuacion.py
from typing import Optional
from pydantic import BaseModel
from datetime import date, datetime


ESTADOS_CRM = {"Pendiente", "Completada", "Cancelada"}
PRIORIDADES_CRM = {"Alta", "Media", "Baja"}
CANALES_CRM = {"Teléfono", "Email", "Reunión", "WhatsApp", "Otro"}


class CrmActuacionIn(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    canal: str
    estado: str = "Pendiente"
    prioridad: str = "Media"

    fecha_vencimiento: date
    fecha_accion: Optional[datetime] = None

    trabajadorid: int                 # creador
    trabajador_asignadoid: int        # responsable


class CrmActuacionOut(BaseModel):
    crm_actuacionid: int
    clienteid: int

    titulo: str
    descripcion: Optional[str]
    canal: str
    estado: str
    prioridad: str

    fecha_vencimiento: date
    fecha_accion: Optional[datetime]

    trabajadorid: int
    trabajador_asignadoid: int
