# Aplicación de Gestión de Inventarios con Flask y MySQL (XAMPP)

## Descripción
Esta aplicación web permite gestionar un inventario simple con estados visuales sobre el nivel de stock: crítico, regular, óptimo y exceso.

## Tecnologías usadas
- Backend: Python + Flask
- Frontend: HTML + Bootstrap 5
- Base de datos: MySQL (con XAMPP)
- Librería para conexión a MySQL: mysql-connector-python

## Configuración de la base de datos
1. Abre XAMPP y asegúrate que MySQL está activo.
2. Abre phpMyAdmin (http://localhost/phpmyadmin).
3. Crea la base de datos e importa la tabla con:

```sql
CREATE DATABASE inventario_db;

USE inventario_db;

CREATE TABLE productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100),
    stock_actual INT,
    stock_optimo INT,
    stock_maximo INT
);

INSERT INTO productos (nombre, stock_actual, stock_optimo, stock_maximo) VALUES
('Producto A', 5, 10, 20),
('Producto B', 15, 10, 20),
('Producto C', 22, 10, 20),
('Producto D', 8, 10, 20);
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