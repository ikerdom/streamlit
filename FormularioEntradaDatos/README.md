# 📋 Mini-ERP con Streamlit + Supabase

Este proyecto es un **mini-ERP ligero** desarrollado en **Python** con [Streamlit](https://streamlit.io/) y [Supabase](https://supabase.com/) (PostgreSQL en la nube).  
Permite gestionar clientes (y en el futuro más entidades) con un panel web accesible desde cualquier navegador.

---

## ⚡ Funcionalidades

- 🔐 **Login de usuarios** (email + password en Supabase).
- 👤 **Control de permisos**:
  - Cualquier usuario puede insertar clientes.
  - Solo usuarios en `ALLOWED_EDITORS` pueden editar o borrar.
- 📝 **Inserción de clientes** mediante formulario con validaciones básicas.
- 📂 **Importación masiva** de clientes desde un CSV.
- ✏️/🗑️ **Edición y borrado** de clientes con botones por fila.
- 📊 **Tabla en vivo** de clientes siempre actualizada en cada pestaña.
- 📷 **Ejemplos visuales** incluidos en el repositorio.

---

## 🛠️ Tecnologías

- [Python 3.11+](https://www.python.org/)
- [Streamlit](https://streamlit.io/)
- [Supabase](https://supabase.com/) (PostgreSQL gestionado)
- [pandas](https://pandas.pydata.org/)

---

## 📦 Instalación local

1. Clona el repositorio:
   ```bash
   git clone https://github.com/ikerdom/streamlit.git
   cd streamlit

2- pip install -r requirements.txt

3- Configura tus credenciales de Supabase en .streamlit/secrets.toml:

[supabase]
url = "https://TU_URL.supabase.co"
anon_key = "TU_ANON_KEY"


4 - Ejecuta la aplicación:

python -m streamlit run app.py
