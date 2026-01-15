import math
from typing import Optional

from backend.app.schemas.producto import (
    ProductoOut,
    ProductoListResponse,
    ProductoCatalogosResponse,
    CatalogItem,
    ProductoDetail,
)
from backend.app.repositories.productos_repo import ProductosRepository


class ProductosService:
    def __init__(self, repo: ProductosRepository):
        self.repo = repo

    def listar(
        self,
        q: Optional[str],
        familiaid: Optional[int],
        tipoid: Optional[int],
        page: int,
        page_size: int,
        sort_field: str,
        sort_dir: str,
    ) -> ProductoListResponse:
        raw, total = self.repo.get_productos(
            q=q,
            familiaid=familiaid,
            tipoid=tipoid,
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            sort_dir=sort_dir,
        )

        # catálogos para enriquecer labels
        cats = self.repo.get_catalogos()
        fam_map = {r["familia_productoid"]: r["nombre"] for r in cats.get("familias", []) if r.get("familia_productoid")}
        tipo_map = {r["producto_tipoid"]: r["nombre"] for r in cats.get("tipos", []) if r.get("producto_tipoid")}
        imp_map = {r["impuestoid"]: r["nombre"] for r in cats.get("impuestos", []) if r.get("impuestoid")}
        est_map = {r["estado_productoid"]: r["nombre"] for r in cats.get("estados", []) if r.get("estado_productoid")}

        productos = []
        for p in raw:
            productos.append(
                ProductoOut(
                    productoid=p.get("productoid"),
                    nombre=p.get("nombre"),
                    titulo=p.get("titulo"),
                    referencia=p.get("referencia"),
                    isbn=p.get("isbn"),
                    ean=p.get("ean"),
                    familia_productoid=p.get("familia_productoid"),
                    producto_tipoid=p.get("producto_tipoid"),
                    impuestoid=p.get("impuestoid"),
                    estado_productoid=p.get("estado_productoid"),
                    precio=p.get("precio"),
                    portada_url=p.get("portada_url"),
                    familia=fam_map.get(p.get("familia_productoid")),
                    tipo=tipo_map.get(p.get("producto_tipoid")),
                    impuesto=imp_map.get(p.get("impuestoid")),
                    estado=est_map.get(p.get("estado_productoid")),
                )
            )

        total_pages = max(1, math.ceil(total / page_size))
        return ProductoListResponse(
            data=productos,
            total=total,
            total_pages=total_pages,
            page=page,
            page_size=page_size,
        )

    def catalogos(self) -> ProductoCatalogosResponse:
        cats = self.repo.get_catalogos()

        def to_items(rows: list, id_field: str, label_field: str):
            return [
                CatalogItem(id=int(r[id_field]), label=str(r[label_field]))
                for r in rows
                if r.get(id_field) is not None
            ]

        return ProductoCatalogosResponse(
            familias=to_items(cats.get("familias", []), "familia_productoid", "nombre"),
            tipos=to_items(cats.get("tipos", []), "producto_tipoid", "nombre"),
            impuestos=to_items(cats.get("impuestos", []), "impuestoid", "nombre"),
            estados=to_items(cats.get("estados", []), "estado_productoid", "nombre"),
        )

    def detalle(self, productoid: int) -> Optional[ProductoDetail]:
        p = self.repo.get_producto(productoid)
        if not p:
            return None
        cats = self.repo.get_catalogos()
        fam_map = {r["familia_productoid"]: r["nombre"] for r in cats.get("familias", []) if r.get("familia_productoid")}
        tipo_map = {r["producto_tipoid"]: r["nombre"] for r in cats.get("tipos", []) if r.get("producto_tipoid")}
        imp_map = {r["impuestoid"]: r["nombre"] for r in cats.get("impuestos", []) if r.get("impuestoid")}
        est_map = {r["estado_productoid"]: r["nombre"] for r in cats.get("estados", []) if r.get("estado_productoid")}

        return ProductoDetail(
            productoid=p.get("productoid"),
            nombre=p.get("nombre"),
            titulo=p.get("titulo"),
            referencia=p.get("referencia"),
            isbn=p.get("isbn"),
            ean=p.get("ean"),
            sinopsis=p.get("sinopsis"),
            versatilidad=p.get("versatilidad"),
            precio=p.get("precio"),
            portada_url=p.get("portada_url"),
            publico=p.get("publico"),
            fecha_publicacion=p.get("fecha_publicacion"),
            familia=fam_map.get(p.get("familia_productoid")),
            tipo=tipo_map.get(p.get("producto_tipoid")),
            impuesto=imp_map.get(p.get("impuestoid")),
            estado=est_map.get(p.get("estado_productoid")),
        )
