# backend/app/schemas/cliente_contacto.py
from typing import Optional, List
from pydantic import BaseModel


class ClienteContactoIn(BaseModel):
    nombre: str
    cargo: Optional[str] = None
    rol: Optional[str] = None

    email: Optional[List[str]] = None
    telefono: Optional[List[str]] = None

    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None

    observaciones: Optional[str] = None


class ClienteContactoOut(ClienteContactoIn):
    cliente_contactoid: int
    clienteid: int
    es_principal: bool
