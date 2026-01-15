from fastapi import HTTPException
from backend.app.schemas.cliente_create import ClienteCreateIn, ClienteCreateOut
from backend.app.core.database import get_supabase


class ClientesCreateService:
    def __init__(self, supabase):
        self.supabase = supabase

    def crear(self, data: ClienteCreateIn) -> ClienteCreateOut:
        is_potencial = data.tipo == "potencial"

        # Reglas del original
        if not data.razon_social or not data.identificador:
            raise HTTPException(status_code=400, detail="Razón social e identificador son obligatorios.")

        if not is_potencial:
            df = data.direccion_fiscal
            if not df or not (df.direccion and df.ciudad and df.cp):
                raise HTTPException(
                    status_code=400,
                    detail="Dirección fiscal completa (dirección, ciudad, cp) obligatoria para clientes.",
                )

        # Potencial: no permitir forma de pago/banco si llega
        formapagoid = None if is_potencial else data.formapagoid
        banco = None if is_potencial else data.banco

        # 1) cliente
        cliente_payload = {
            "razon_social": data.razon_social,
            "identificador": data.identificador,
            "estadoid": data.estadoid,
            "categoriaid": data.categoriaid,
            "grupoid": data.grupoid,
            "formapagoid": formapagoid,
            "trabajadorid": data.trabajadorid,
            "observaciones": data.observaciones,
            "tarifaid": data.tarifaid,
            "tipo_cliente": "potencial" if is_potencial else "cliente",
            "perfil_completo": False,  # igual que original
        }

        res = self.supabase.table("cliente").insert(cliente_payload).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="No se pudo crear el cliente.")
        clienteid = res.data[0]["clienteid"]

        # 2) dirección fiscal (si hay algo)
        if data.direccion_fiscal:
            df = data.direccion_fiscal
            if any([df.direccion, df.ciudad, df.cp, df.provincia, df.pais, df.telefono, df.email, df.documentacion_impresa]):
                self.supabase.table("cliente_direccion").insert({
                    "clienteid": clienteid,
                    "tipo": "fiscal",
                    "direccion": df.direccion,
                    "ciudad": df.ciudad,
                    "provincia": df.provincia,
                    "pais": df.pais,
                    "cp": df.cp,
                    "telefono": df.telefono,
                    "email": df.email,
                    "documentacion_impresa": df.documentacion_impresa,
                }).execute()

        # 3) contacto principal
        if data.contacto_principal:
            cp = data.contacto_principal
            if cp.nombre or cp.email:
                self.supabase.table("cliente_contacto").insert({
                    "clienteid": clienteid,
                    "nombre": cp.nombre,
                    "email": cp.email,
                    "telefono": cp.telefono,
                    "rol": cp.rol,
                    "es_principal": True,
                }).execute()

        # 4) banco (solo cliente)
        if banco and banco.iban:
            self.supabase.table("cliente_banco").insert({
                "clienteid": clienteid,
                "iban": banco.iban,
                "nombre_banco": banco.nombre_banco,
                "fecha_baja": banco.fecha_baja,
            }).execute()

        msg = f"🌱 Cliente potencial '{data.razon_social}' creado." if is_potencial else f"✅ Cliente '{data.razon_social}' creado correctamente."
        return ClienteCreateOut(clienteid=clienteid, mensaje=msg)
