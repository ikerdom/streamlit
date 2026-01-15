# backend/app/services/cliente_direccion_service.py
class ClienteDireccionService:
    def __init__(self, supabase):
        self.supabase = supabase

    # -----------------------------
    # Listar
    # -----------------------------
    def listar(self, clienteid: int):
        return (
            self.supabase.table("cliente_direccion")
            .select("*")
            .eq("clienteid", clienteid)
            .order("tipo", desc=True)
            .execute()
            .data
            or []
        )

    # -----------------------------
    # Crear
    # -----------------------------
    def crear(self, clienteid: int, data: dict):
        data["clienteid"] = clienteid
        tipo = data.get("tipo", "envio")

        if tipo == "fiscal":
            self._desmarcar_fiscal(clienteid)

        self.supabase.table("cliente_direccion").insert(data).execute()

    # -----------------------------
    # Actualizar
    # -----------------------------
    def actualizar(self, clienteid: int, direccionid: int, data: dict):
        tipo = data.get("tipo")

        if tipo == "fiscal":
            self._desmarcar_fiscal(clienteid)

        self.supabase.table("cliente_direccion").update(data).eq(
            "cliente_direccionid", direccionid
        ).execute()

    # -----------------------------
    # Borrar
    # -----------------------------
    def borrar(self, direccionid: int):
        self.supabase.table("cliente_direccion").delete().eq(
            "cliente_direccionid", direccionid
        ).execute()

    # -----------------------------
    # Marcar fiscal (REGLA CLAVE)
    # -----------------------------
    def hacer_fiscal(self, clienteid: int, direccionid: int):
        self._desmarcar_fiscal(clienteid)

        self.supabase.table("cliente_direccion").update(
            {"tipo": "fiscal"}
        ).eq("cliente_direccionid", direccionid).execute()

    # -----------------------------
    # Interno
    # -----------------------------
    def _desmarcar_fiscal(self, clienteid: int):
        self.supabase.table("cliente_direccion").update(
            {"tipo": "envio"}
        ).eq("clienteid", clienteid).eq("tipo", "fiscal").execute()
