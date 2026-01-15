# backend/app/schemas/cliente_direccion.py
from typing import Optional
from pydantic import BaseModel, EmailStr


class ClienteDireccionIn(BaseModel):
    direccion: Optional[str]
    ciudad: Optional[str]
    cp: Optional[str]
    provincia: Optional[str]
    provinciaid: Optional[int]
    regionid: Optional[int]
    pais: Optional[str]
    email: Optional[EmailStr]
    tipo: Optional[str]  # fiscal | envio


class ClienteDireccionOut(ClienteDireccionIn):
    cliente_direccionid: int
    clienteid: int
