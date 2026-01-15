from typing import Optional, List
from pydantic import BaseModel


class ProductoOut(BaseModel):
    productoid: int
    nombre: Optional[str] = None
    titulo: Optional[str] = None
    referencia: Optional[str] = None
    isbn: Optional[str] = None
    ean: Optional[str] = None
    familia_productoid: Optional[int] = None
    producto_tipoid: Optional[int] = None
    impuestoid: Optional[int] = None
    estado_productoid: Optional[int] = None
    precio: Optional[float] = None
    portada_url: Optional[str] = None

    # labels enriquecidos
    familia: Optional[str] = None
    tipo: Optional[str] = None
    impuesto: Optional[str] = None
    estado: Optional[str] = None

    class Config:
        from_attributes = True


class ProductoListResponse(BaseModel):
    data: List[ProductoOut]
    total: int
    total_pages: int
    page: int
    page_size: int


class CatalogItem(BaseModel):
    id: int
    label: str


class ProductoCatalogosResponse(BaseModel):
    familias: List[CatalogItem]
    tipos: List[CatalogItem]
    impuestos: List[CatalogItem]
    estados: List[CatalogItem]


class ProductoDetail(BaseModel):
    productoid: int
    nombre: Optional[str] = None
    titulo: Optional[str] = None
    referencia: Optional[str] = None
    isbn: Optional[str] = None
    ean: Optional[str] = None
    sinopsis: Optional[str] = None
    versatilidad: Optional[str] = None
    precio: Optional[float] = None
    portada_url: Optional[str] = None
    publico: Optional[bool] = None
    fecha_publicacion: Optional[str] = None
    familia: Optional[str] = None
    tipo: Optional[str] = None
    impuesto: Optional[str] = None
    estado: Optional[str] = None
