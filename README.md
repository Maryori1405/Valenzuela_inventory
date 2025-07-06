# 📦 Aplicación de Gestión de Inventarios con Flask y MySQL (Railway)

## 📄 Descripción
Esta aplicación web permite gestionar un inventario de productos con visualización por colores del estado de stock: Crítico, Regular, Óptimo y Exceso. También ofrece predicción de consumo, historial de movimientos y notificaciones inteligentes.

## 🚀 Tecnologías Usadas
- **Backend**: Python + Flask
- **Frontend**: HTML + Bootstrap 5 + Jinja2
- **Base de datos**: MySQL (Railway.app)
- **Conexión**: Flask-MySQLdb
- **ML y Gráficos**: Scikit-learn, Matplotlib

## ⚙️ Configuración de la Base de Datos (Railway)
La base de datos está alojada en Railway y se conecta mediante variables de entorno definidas en un archivo `.env`.

Ejemplo de archivo `.env`:

```env
MYSQL_HOST=yamanote.proxy.rlwy.net
MYSQL_PORT=28413
MYSQL_USER=root
MYSQL_PASSWORD=izrghvAsXGqdEqMbBuvUwUfGyAYlsARN
MYSQL_DB=railway
SECRET_KEY=clave_secreta_super_segura
```

## Cómo ejecutar la aplicación

1. Instala dependencias (en la terminal / CMD):

```
pip install flask mysql-connector-python
```

2. Ejecuta el servidor Flask:

```
python app.py
```

3. Abre el navegador y visita:

```
http://127.0.0.1:5000/
```

## Funcionalidades

- Listar productos con sus stocks y estados (Crítico, Regular, Óptimo, Exceso).
- Agregar nuevos productos.
- Editar productos existentes.
- Eliminar productos.
- Notificaciones visuales con colores en la tabla.

---

Si quieres agregar funcionalidades o resolver dudas, dime.