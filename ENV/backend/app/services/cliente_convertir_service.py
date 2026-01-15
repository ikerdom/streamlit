# backend/app/services/cliente_convertir_service.py
class ClienteConvertirService:
    def __init__(self, supabase):
        self.supabase = supabase

    def _perfil_esta_completo(self, clienteid: int) -> bool:
        """
        Regla CENTRAL:
        define si un potencial puede convertirse.
        """
        # Cliente base
        cli = (
            self.supabase.table("cliente")
            .select("clienteid, razon_social, identificador")
            .eq("clienteid", clienteid)
            .single()
            .execute()
            .data
        )

        if not cli:
            return False

        if not cli.get("razon_social") or not cli.get("identificador"):
            return False

        # Dirección fiscal
        direccion = (
            self.supabase.table("cliente_direccion")
            .select("direccion, ciudad, cp")
            .eq("clienteid", clienteid)
            .eq("tipo", "fiscal")
            .single()
            .execute()
            .data
        )

        if not direccion:
            return False

        if not (direccion.get("direccion") and direccion.get("ciudad") and direccion.get("cp")):
            return False

        return True

    def convertir(self, clienteid: int):
        cli = (
            self.supabase.table("cliente")
            .select("clienteid, tipo_cliente")
            .eq("clienteid", clienteid)
            .single()
            .execute()
            .data
        )

        if not cli:
            raise ValueError("Cliente potencial no encontrado")

        if cli.get("tipo_cliente") != "potencial":
            raise ValueError("El cliente no es potencial")

        if not self._perfil_esta_completo(clienteid):
            raise ValueError("El perfil no está completo. No se puede convertir.")

        self.supabase.table("cliente").update(
            {
                "tipo_cliente": "cliente",
                "perfil_completo": True,
            }
        ).eq("clienteid", clienteid).execute()

        return {
            "clienteid": clienteid,
            "tipo_cliente": "cliente",
            "perfil_completo": True,
            "mensaje": "Cliente potencial convertido correctamente",
        }
