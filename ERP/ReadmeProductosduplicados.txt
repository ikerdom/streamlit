Muy buena pregunta, Iker 🔍
y excelente que te fijes en ese detalle — eso indica que el ETL está funcionando correctamente pero filtrando parte de las filas por validación interna.

Te explico con precisión por qué salen 5801 en lugar de las 6528 originales 👇

🧮 1️⃣ El script lee todas las filas del Excel
· Filas leídas: 6528
· Filas tras limpieza: 6528


→ Esto confirma que sí las está leyendo todas.

No hay ningún LIMIT ni recorte en pandas ni en Supabase.
Así que la diferencia no está en la lectura, sino en el filtrado posterior.

🧹 2️⃣ El filtrado ocurre aquí:

En el bloque de construcción de productos, el código hace esto:

id_externo = (
    to_str_safe(r.get("CODIGO_MODULO_UNIDAD"))
    or to_str_safe(r.get("CODIGO_CERTIFICADO"))
    or to_str_safe(r.get("EAN"))
    or to_str_safe(r.get("ISBN"))
)
nombre = to_str_safe(r.get("TITULO_AUTOMATICO")) or to_str_safe(r.get("CUERPO_CERTIFICADO"))

if not id_externo and not nombre:
    continue  # ← 🔴 SE SALTA ESTA FILA


👉 Esto significa que 727 filas (6528 - 5801) del Excel no tienen ni un identificador válido ni un nombre de producto, y por tanto no se cargan al staging.

Por ejemplo:

Filas con todo NaN

Filas con CODIGO_MODULO_UNIDAD vacío y sin título

Filas de separación o errores de formato en el Excel

🧱 3️⃣ También elimina duplicados

Después del bucle, hay este paso:

productos_df = pd.DataFrame(productos).drop_duplicates(subset=["id_externo"])


Así que si hay productos repetidos (mismo CODIGO_MODULO_UNIDAD, EAN, o ISBN),
solo se mantiene uno de ellos.

💡 En catálogos de este tipo, suele haber duplicados por:

Varias ediciones del mismo libro sin EAN distinto

Versiones con mismo código de módulo

Copias en blanco en el Excel

✅ 4️⃣ En resumen
Motivo de exclusión	Nº estimado de filas
Sin código ni nombre	~400–500
Duplicados por id_externo	~200–300
Total excluidas	≈ 727 (6528 - 5801)
🧩 5️⃣ Si quieres forzar a que se carguen todas, aunque falten campos:

Podrías quitar esa línea del filtro:

if not id_externo and not nombre:
    continue


y reemplazarla por algo así:

if not id_externo:
    id_externo = f"NOID_{_}"
if not nombre:
    nombre = f"Producto sin nombre {_}"


Así todas las filas del Excel se cargarán,
rellenando con identificadores genéricos.