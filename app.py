from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
from datetime import datetime
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import base64
import io
import os

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Configuración de la base de datos MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'inventario_db'
mysql = MySQL(app)

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Importa tu modelo de usuario si aplica
# from models import Usuario

# ---------------------- RUTAS PRINCIPALES ----------------------

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()

    if not producto:
        flash('❌ Producto no encontrado.', 'danger')
        return redirect(url_for('productos'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        stock_actual = int(request.form['stock_actual'])
        stock_optimo = int(request.form['stock_optimo'])
        stock_maximo = int(request.form['stock_maximo'])

        stock_anterior = int(producto['stock_actual'])

        cur.execute("""
            UPDATE productos 
            SET nombre=%s, categoria=%s, stock_actual=%s, stock_optimo=%s, stock_maximo=%s 
            WHERE id=%s
        """, (nombre, categoria, stock_actual, stock_optimo, stock_maximo, id))
        mysql.connection.commit()

        diferencia = stock_actual - stock_anterior
        if diferencia != 0:
            tipo = 'entrada' if diferencia > 0 else 'salida'
            cur.execute("""
                INSERT INTO historial_movimientos (producto_id, tipo_movimiento, cantidad, fecha_hora, usuario_id)
                VALUES (%s, %s, %s, NOW(), %s)
            """, (id, tipo, abs(diferencia), current_user.id))
            mysql.connection.commit()

        flash('✅ Producto actualizado y movimiento registrado', 'success')
        return redirect(url_for('productos'))

    return render_template('editar_producto.html', producto=producto)

@app.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT stock_actual FROM productos WHERE id=%s", (id,))
    producto = cur.fetchone()

    if producto and producto['stock_actual'] > 0:
        cur.execute("""
            INSERT INTO historial_movimientos (producto_id, tipo_movimiento, cantidad, fecha_hora, usuario_id)
            VALUES (%s, 'salida', %s, NOW(), %s)
        """, (id, producto['stock_actual'], current_user.id))
        mysql.connection.commit()

    cur.execute("DELETE FROM productos WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('🗑️ Producto eliminado y movimiento registrado.', 'success')
    return redirect(url_for('productos'))

@app.route('/notificaciones')
@login_required
def notificaciones():
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT *, CASE
            WHEN stock_actual < stock_optimo * 0.5 THEN 'Crítico'
            WHEN stock_actual < stock_optimo THEN 'Regular'
            WHEN stock_actual <= stock_maximo THEN 'Óptimo'
            ELSE 'Exceso' END AS estado
        FROM productos
        WHERE stock_actual < stock_optimo OR stock_actual > stock_maximo
    """)
    productos = cur.fetchall()
    cur.close()

    notificaciones = []
    for p in productos:
        emoji = {'Crítico': '🔴', 'Regular': '🟡', 'Óptimo': '🟢', 'Exceso': '🔵'}.get(p['estado'], '')
        notificaciones.append({
            'nombre': p['nombre'],
            'categoria': p['categoria'],
            'stock': p['stock_actual'],
            'estado': p['estado'],
            'emoji': emoji,
        })

    return render_template('notificaciones.html', notificaciones=notificaciones)

@app.route('/prediccion')
@login_required
def prediccion():
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT * FROM productos")
    productos = cur.fetchall()

    resultados = []

    for producto in productos:
        producto_id = producto['id']
        cur.execute("""
            SELECT DATE(fecha_hora) AS fecha, SUM(cantidad) AS total_vendido
            FROM historial_movimientos
            WHERE producto_id = %s AND tipo_movimiento = 'salida'
            GROUP BY DATE(fecha_hora)
            ORDER BY fecha DESC
            LIMIT 7
        """, (producto_id,))
        ventas = cur.fetchall()[::-1]

        prediccion_valor = None
        grafico = None

        if len(ventas) >= 2:
            dias = np.array(range(1, len(ventas) + 1)).reshape(-1, 1)
            unidades = np.array([v['total_vendido'] for v in ventas])
            modelo = LinearRegression()
            modelo.fit(dias, unidades)
            prediccion_valor = modelo.predict([[len(dias) + 1]])[0]

            fig, ax = plt.subplots()
            ax.plot(dias, unidades, 'bo-', label='Ventas reales')
            ax.plot(len(dias) + 1, prediccion_valor, 'ro', label='Predicción día siguiente')
            ax.axhline(producto['stock_actual'], color='green', linestyle='--',
                       label=f"Stock actual ({producto['stock_actual']})")
            ax.set_title(producto['nombre'])
            ax.set_xlabel("Día")
            ax.set_ylabel("Unidades")
            ax.legend()
            ax.grid(True)

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close(fig)
            buf.seek(0)
            grafico = base64.b64encode(buf.read()).decode('utf-8')

        resultados.append({
            'producto': producto,
            'prediccion': prediccion_valor,
            'grafico': grafico
        })

    productos_labels = []
    stocks_actuales = []
    predicciones = []

    for r in resultados:
        if r['prediccion'] is not None:
            productos_labels.append(r['producto']['nombre'])
            stocks_actuales.append(r['producto']['stock_actual'])
            predicciones.append(r['prediccion'])

    grafico_general = None
    if productos_labels:
        fig, ax = plt.subplots(figsize=(10, 5))
        x = np.arange(len(productos_labels))
        ax.bar(x - 0.2, stocks_actuales, width=0.4, label='Stock actual', color='#2a6f75')
        ax.bar(x + 0.2, predicciones, width=0.4, label='Predicción', color='#e07a5f')
        ax.set_xticks(x)
        ax.set_xticklabels(productos_labels, rotation=45, ha='right')
        ax.set_ylabel("Unidades")
        ax.set_title("Comparación Stock Actual vs Predicción")
        ax.legend()
        ax.grid(True, axis='y', linestyle='--', alpha=0.5)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        grafico_general = base64.b64encode(buf.read()).decode('utf-8')

    cur.close()
    return render_template('prediccion.html', resultados=resultados, grafico_general=grafico_general)

@app.route('/historial')
@login_required
def historial():
    tipo = request.args.get('tipo')
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')

    cur = mysql.connection.cursor(DictCursor)
    query = """
        SELECT h.*, p.nombre AS nombre_producto, u.username AS usuario
        FROM historial_movimientos h
        JOIN productos p ON h.producto_id = p.id
        LEFT JOIN usuarios u ON h.usuario_id = u.id
        WHERE 1 = 1
    """
    valores = []

    if tipo:
        query += " AND h.tipo_movimiento = %s"
        valores.append(tipo)

    if desde:
        query += " AND h.fecha_hora >= %s"
        valores.append(desde + " 00:00:00")

    if hasta:
        query += " AND h.fecha_hora <= %s"
        valores.append(hasta + " 23:59:59")

    query += " ORDER BY h.fecha_hora DESC"
    cur.execute(query, valores)
    movimientos = cur.fetchall()
    cur.close()
    return render_template('historial.html', movimientos=movimientos)

@app.route('/salida/<int:id>', methods=['GET', 'POST'])
@login_required
def registrar_salida(id):
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()

    if not producto:
        flash("Producto no encontrado", "danger")
        return redirect(url_for('productos'))

    if request.method == 'POST':
        cantidad = int(request.form['cantidad'])

        if cantidad <= 0:
            flash("La cantidad debe ser mayor a 0", "warning")
            return redirect(request.url)

        if cantidad > producto['stock_actual']:
            flash("No hay suficiente stock disponible", "danger")
            return redirect(request.url)

        nuevo_stock = producto['stock_actual'] - cantidad
        cur.execute("UPDATE productos SET stock_actual = %s WHERE id = %s", (nuevo_stock, id))

        cur.execute("""
            INSERT INTO historial_movimientos (producto_id, tipo_movimiento, cantidad, fecha_hora, usuario_id)
            VALUES (%s, 'salida', %s, NOW(), %s)
        """, (id, cantidad, current_user.id))

        mysql.connection.commit()
        cur.close()

        flash("Salida registrada y stock actualizado", "success")
        return redirect(url_for('productos'))

    cur.close()
    return render_template('salida_producto.html', producto=producto)

@app.route('/entrada/<int:id>', methods=['GET', 'POST'])
@login_required
def registrar_entrada(id):
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()

    if not producto:
        flash("Producto no encontrado", "danger")
        return redirect(url_for('productos'))

    if request.method == 'POST':
        cantidad = int(request.form['cantidad'])

        if cantidad <= 0:
            flash("La cantidad debe ser mayor a 0", "warning")
            return redirect(request.url)

        nuevo_stock = producto['stock_actual'] + cantidad

        if nuevo_stock > producto['stock_maximo']:
            flash(f"⚠️ El stock máximo es {producto['stock_maximo']} y con esta entrada llegarías a {nuevo_stock}.", "danger")
            return redirect(request.url)

        cur.execute("UPDATE productos SET stock_actual = %s WHERE id = %s", (nuevo_stock, id))
        cur.execute("""
            INSERT INTO historial_movimientos (producto_id, tipo_movimiento, cantidad, fecha_hora, usuario_id)
            VALUES (%s, 'entrada', %s, NOW(), %s)
        """, (id, cantidad, current_user.id))

        mysql.connection.commit()
        cur.close()

        flash("✅ Entrada registrada y stock actualizado correctamente", "success")
        return redirect(url_for('productos'))

    cur.close()
    return render_template('entrada_producto.html', producto=producto)

@app.context_processor
def inject_cantidad_no_leidas():
    try:
        cur = mysql.connection.cursor(DictCursor)
        cur.execute("""
            SELECT COUNT(*) AS total FROM productos 
            WHERE stock_actual < stock_optimo OR stock_actual > stock_maximo
        """)
        notificaciones = cur.fetchone()

        cur.execute("""
            SELECT 
                p.id, p.stock_actual,
                DATE(hm.fecha_hora) as fecha,
                SUM(hm.cantidad) as total_vendido
            FROM productos p
            LEFT JOIN historial_movimientos hm ON p.id = hm.producto_id
            WHERE hm.tipo_movimiento = 'salida' 
              AND hm.fecha_hora >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY p.id, DATE(hm.fecha_hora)
        """)
        ventas_data = cur.fetchall()

        productos_ventas = {}
        for row in ventas_data:
            productos_ventas.setdefault(row['id'], {'stock_actual': row['stock_actual'], 'ventas': []})
            if row['total_vendido']:
                productos_ventas[row['id']]['ventas'].append(row['total_vendido'])

        alerta_prediccion = 0
        for data in productos_ventas.values():
            if len(data['ventas']) >= 2:
                try:
                    dias = np.array(range(1, len(data['ventas']) + 1)).reshape(-1, 1)
                    unidades = np.array(data['ventas'])
                    modelo = LinearRegression()
                    modelo.fit(dias, unidades)
                    pred = modelo.predict([[len(dias) + 1]])[0]
                    if pred > data['stock_actual']:
                        alerta_prediccion += 1
                except:
                    continue

        cur.close()
        return dict(
            cantidad_no_leidas=notificaciones['total'] if notificaciones else 0,
            cantidad_alerta_pred=alerta_prediccion
        )
    except:
        return dict(cantidad_no_leidas=0, cantidad_alerta_pred=0)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
