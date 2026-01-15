from typing import Optional, Literal
from pydantic import BaseModel, Field


class ClienteDireccionIn(BaseModel):
    tipo: Literal["fiscal"] = "fiscal"
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = "España"
    cp: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    documentacion_impresa: Optional[Literal["valorado", "no_valorado", "factura"]] = None


class ClienteContactoIn(BaseModel):
    nombre: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    rol: Optional[str] = None
    es_principal: bool = True


class ClienteBancoIn(BaseModel):
    iban: Optional[str] = None
    nombre_banco: Optional[str] = None
    fecha_baja: Optional[str] = None  # "YYYY-MM-DD"


class ClienteCreateIn(BaseModel):
    tipo: Literal["cliente", "potencial"] = "cliente"

    razon_social: str = Field(..., min_length=1)
    identificador: str = Field(..., min_length=1)

    estadoid: Optional[int] = None
    categoriaid: Optional[int] = None
    grupoid: Optional[int] = None
    formapagoid: Optional[int] = None
    trabajadorid: Optional[int] = None
    observaciones: Optional[str] = None
    tarifaid: Optional[int] = None

    # igual que tu original (siempre se recalcula luego)
    perfil_completo: bool = False

    direccion_fiscal: Optional[ClienteDireccionIn] = None
    contacto_principal: Optional[ClienteContactoIn] = None
    banco: Optional[ClienteBancoIn] = None


class ClienteCreateOut(BaseModel):
    clienteid: int
    mensaje: str
