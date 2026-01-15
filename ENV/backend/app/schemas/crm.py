from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel


class CrmAccionBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    canal: Optional[str] = None
    estado: Optional[str] = "Pendiente"
    fecha_accion: Optional[datetime] = None
    fecha_vencimiento: Optional[date] = None
    prioridad: Optional[str] = None
    clienteid: Optional[int] = None
    trabajadorid: Optional[int] = None
    trabajador_asignadoid: Optional[int] = None


class CrmAccionCreate(CrmAccionBase):
    pass


class CrmAccionUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    canal: Optional[str] = None
    estado: Optional[str] = None
    fecha_accion: Optional[datetime] = None
    fecha_vencimiento: Optional[date] = None
    prioridad: Optional[str] = None
    clienteid: Optional[int] = None
    trabajador_asignadoid: Optional[int] = None


class CrmAccionOut(CrmAccionBase):
    crm_actuacionid: int


class CrmAccionList(BaseModel):
    data: List[CrmAccionOut]
