from typing import Optional
from pydantic import BaseModel


class PostalLocalidadOut(BaseModel):
    postallocid: int
    cp: Optional[str] = None
    localidad: Optional[str] = None
    provincia_nombre_raw: Optional[str] = None
