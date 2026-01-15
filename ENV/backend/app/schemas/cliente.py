# backend/app/schemas/cliente.py
from typing import Optional, List
from pydantic import BaseModel


# ============================
# 🏷️ Subschemas reutilizables
# ============================
class Label(BaseModel):
    id: Optional[int]
    label: Optional[str]


class PresupuestoInfo(BaseModel):
    estado: Optional[str]
    fecha: Optional[str]


# ============================
# 👤 Cliente (salida API)
# ============================
class ClienteOut(BaseModel):
    clienteid: int

    # básicos
    razon_social: Optional[str]
    identificador: Optional[str]

    # IDs (para acciones)
    estadoid: Optional[int]
    grupoid: Optional[int]
    trabajadorid: Optional[int]
    formapagoid: Optional[int]

    # 🧠 enriquecido para UI
    estado: Optional[Label] = None
    grupo: Optional[Label] = None
    comercial: Optional[str] = None

    # 📦 contexto
    presupuesto_reciente: Optional[PresupuestoInfo] = None

    class Config:
        from_attributes = True


class ClienteListResponse(BaseModel):
    data: List[ClienteOut]
    total: int
    total_pages: int
    page: int
    page_size: int


# ============================
# ƒsT‹÷? Cliente detalle
# ============================
class ClienteDireccion(BaseModel):
    tipo: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None
    cp: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    documentacion_impresa: Optional[str] = None


class ClienteContacto(BaseModel):
    nombre: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    rol: Optional[str] = None
    es_principal: bool = True


class ClienteBanco(BaseModel):
    iban: Optional[str] = None
    nombre_banco: Optional[str] = None
    fecha_baja: Optional[str] = None


class ClienteDetalle(BaseModel):
    cliente: ClienteOut
    direccion_fiscal: Optional[ClienteDireccion] = None
    contacto_principal: Optional[ClienteContacto] = None
    banco: Optional[ClienteBanco] = None
