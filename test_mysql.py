import MySQLdb

print("Intentando conectar...")  # ← Esto nos dirá si el código empieza

try:
    db = MySQLdb.connect(
        host="127.0.0.1",
        user="root",
        passwd="",
        db="inventario_bd"  # ← Cambia esto si tu base de datos tiene otro nombre
    )
    print("✅ Conexión exitosa")
    db.close()
except Exception as e:
    print("❌ Error al conectar:", e)
