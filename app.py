from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import io, base64, unicodedata, matplotlib
import matplotlib.pyplot as plt
from pymysql.cursors import DictCursor
from MySQLdb.cursors import DictCursor
from dotenv import load_dotenv
from db import init_db, mysql  # mysql ya se importa aquí, NO volver a crearlo
import numpy as np
import os

# Usar backend sin GUI para matplotlib (útil en servidores sin entorno gráfico)
matplotlib.use('Agg')

# ✅ Cargar variables de entorno desde .env
load_dotenv()

# ✅ Inicializar la aplicación Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_por_defecto_insegura')

# ✅ Inicializar la base de datos (usa configuración desde .env y db.py)
init_db(app)

# ✅ Inicializar extensiones
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirige al login si no está autenticado

# Modelo de usuario
class Usuario(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

# Cargar usuario
@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
    usuario = cur.fetchone()
    cur.close()
    if usuario:
        return Usuario(id=usuario['id'], username=usuario['username'], password_hash=usuario['password_hash'])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('username', '').strip()
        contraseña = request.form.get('password')

        if not usuario or not contraseña:
            flash('Por favor, completa todos los campos', 'warning')
            return render_template('login.html')

        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM usuarios WHERE username = %s", (usuario,))
            data = cur.fetchone()
            cur.close()

            if data and bcrypt.check_password_hash(data['password_hash'], contraseña):
                user = Usuario(data['id'], data['username'], data['password_hash'])
                login_user(user)
                flash('Inicio de sesión exitoso', 'success')
                return redirect(url_for('inicio'))
            else:
                flash('Usuario o contraseña incorrecta', 'danger')

        except Exception as e:
            print("💥 Error en login:", e)
            flash('Error interno del servidor', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        if not username or not password:
            flash('Todos los campos son obligatorios', 'warning')
            return render_template('registro.html')

        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
            existente = cur.fetchone()

            if existente:
                flash('Este nombre de usuario ya está registrado', 'warning')
                cur.close()
                return render_template('registro.html')

            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            cur.execute("INSERT INTO usuarios (username, password_hash) VALUES (%s, %s)", (username, hashed_password))
            mysql.connection.commit()
            cur.close()

            flash('Usuario registrado exitosamente', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            print("💥 Error en registro:", e)
            flash('Ocurrió un error al registrar el usuario', 'danger')

    return render_template('registro.html')

@app.context_processor
def inject_cantidad_no_leidas():
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT COUNT(*) AS total FROM productos 
            WHERE stock_actual < stock_optimo OR stock_actual > stock_maximo
        """)
        result = cur.fetchone()
        cur.close()
        cantidad_no_leidas = result['total'] if result else 0
        return dict(cantidad_no_leidas=cantidad_no_leidas)
    except Exception as e:
        print(f"Error en inject_cantidad_no_leidas: {e}")
        return dict(cantidad_no_leidas=0)

@app.route('/')
@login_required
def inicio():
    cursor = mysql.connection.cursor(DictCursor)
    hoy = datetime.now().date()
    hace_7_dias = hoy - timedelta(days=6)

    # Gráfico de estado de productos por día
    cursor.execute("""
        SELECT fecha,
            SUM(CASE WHEN stock_actual < stock_optimo * 0.5 THEN 1 ELSE 0 END) AS critico,
            SUM(CASE WHEN stock_actual >= stock_optimo * 0.5 AND stock_actual < stock_optimo THEN 1 ELSE 0 END) AS regular,
            SUM(CASE WHEN stock_actual >= stock_optimo AND stock_actual <= stock_maximo THEN 1 ELSE 0 END) AS optimo,
            SUM(CASE WHEN stock_actual > stock_maximo THEN 1 ELSE 0 END) AS exceso
        FROM productos
        WHERE fecha BETWEEN %s AND %s
        GROUP BY fecha
        ORDER BY fecha
    """, (hace_7_dias, hoy))
    filas = cursor.fetchall()

    fechas = []
    data_critico = []
    data_regular = []
    data_optimo = []
    data_exceso = []

    for fila in filas:
        fechas.append(fila['fecha'].strftime('%d-%m'))
        data_critico.append(fila['critico'])
        data_regular.append(fila['regular'])
        data_optimo.append(fila['optimo'])
        data_exceso.append(fila['exceso'])

    # Tarjetas resumen
    cursor.execute("SELECT COUNT(*) AS total FROM productos")
    total_productos = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) AS total_criticos
        FROM productos
        WHERE stock_actual < stock_optimo * 0.5
    """)
    total_criticos = cursor.fetchone()['total_criticos']

    # Top 5 productos más críticos
    cursor.execute("""
        SELECT nombre, stock_actual, stock_optimo
        FROM productos
        WHERE stock_actual < stock_optimo
        ORDER BY stock_actual ASC
        LIMIT 5
    """)
    productos_criticos = cursor.fetchall()

    cursor.close()

    return render_template('inicio.html',
                           fechas=fechas,
                           data_critico=data_critico,
                           data_regular=data_regular,
                           data_optimo=data_optimo,
                           data_exceso=data_exceso,
                           total_productos=total_productos,
                           total_criticos=total_criticos,
                           productos_criticos=productos_criticos)
@app.route('/agregar_producto', methods=['GET', 'POST'])
@login_required
def agregar_producto():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            categoria = request.form['categoria']
            stock_actual = int(request.form['stock_actual'])
            stock_optimo = int(request.form['stock_optimo'])
            stock_maximo = int(request.form['stock_maximo'])

            cur = mysql.connection.cursor()

            cur.execute("""
                INSERT INTO productos (nombre, categoria, stock_actual, stock_optimo, stock_maximo, usuario_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nombre, categoria, stock_actual, stock_optimo, stock_maximo, current_user.id))
            mysql.connection.commit()

            producto_id = cur.lastrowid

            if stock_actual > 0:
                cur.execute("""
                    INSERT INTO historial_movimientos (producto_id, tipo_movimiento, cantidad, fecha_hora, usuario_id)
                    VALUES (%s, 'entrada', %s, NOW(), %s)
                """, (producto_id, stock_actual, current_user.id))
                mysql.connection.commit()

            cur.close()
            flash('✅ Producto agregado correctamente', 'success')
            return redirect(url_for('productos'))

        except Exception as e:
            mysql.connection.rollback()
            flash(f'❌ Error al agregar producto: {str(e)}', 'error')
            print(f"Error: {e}")
            return render_template('agregar_producto.html')

    return render_template('agregar_producto.html')

@app.route('/consultar_productos', methods=['GET', 'POST'])
@login_required
def consultar_productos():
    productos = None
    if request.method == 'POST':
        criterio = request.form['criterio']
        valor = request.form['valor']
        cur = mysql.connection.cursor(DictCursor)

        if criterio == 'nombre':
            cur.execute("""
                SELECT *, CASE
                    WHEN stock_actual < stock_optimo * 0.5 THEN 'Crítico'
                    WHEN stock_actual < stock_optimo THEN 'Regular'
                    WHEN stock_actual <= stock_maximo THEN 'Óptimo'
                    ELSE 'Exceso' END AS estado
                FROM productos 
                WHERE nombre COLLATE utf8mb4_general_ci LIKE %s
            """, ('%' + valor + '%',))
            productos = cur.fetchall()

        elif criterio == 'estado':
            cur.execute("""
                SELECT *, CASE
                    WHEN stock_actual < stock_optimo * 0.5 THEN 'Crítico'
                    WHEN stock_actual < stock_optimo THEN 'Regular'
                    WHEN stock_actual <= stock_maximo THEN 'Óptimo'
                    ELSE 'Exceso' END AS estado
                FROM productos
            """)
            todos = cur.fetchall()
            def normalizar(texto):
                return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()
            valor_normalizado = normalizar(valor)
            productos = [p for p in todos if normalizar(p['estado']) == valor_normalizado]

        elif criterio == 'categoria':
            cur.execute("""
                SELECT *, CASE
                    WHEN stock_actual < stock_optimo * 0.5 THEN 'Crítico'
                    WHEN stock_actual < stock_optimo THEN 'Regular'
                    WHEN stock_actual <= stock_maximo THEN 'Óptimo'
                    ELSE 'Exceso' END AS estado
                FROM productos 
                WHERE categoria COLLATE utf8mb4_general_ci LIKE %s
            """, ('%' + valor + '%',))
            productos = cur.fetchall()

        cur.close()
    return render_template('consultar.html', productos=productos)

@app.route('/productos')
@login_required
def productos():
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""SELECT *, CASE
        WHEN stock_actual < stock_optimo * 0.5 THEN 'Crítico'
        WHEN stock_actual < stock_optimo THEN 'Regular'
        WHEN stock_actual <= stock_maximo THEN 'Óptimo'
        ELSE 'Exceso' END AS estado
        FROM productos
    """)
    productos = cur.fetchall()
    cur.close()
    return render_template('tabla_producto.html', productos=productos)

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    cur = mysql.connection.cursor(DictCursor)

    # Obtener producto actual
    cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()

    if producto is None:
        flash('❌ Producto no encontrado.', 'danger')
        return redirect(url_for('productos'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        stock_actual = int(request.form['stock_actual'])
        stock_optimo = int(request.form['stock_optimo'])
        stock_maximo = int(request.form['stock_maximo'])
        precio_unitario = float(request.form['precio_unitario'])

        stock_anterior = int(producto['stock_actual'])

        # Actualizar producto con precio_unitario
        cur.execute("""
            UPDATE productos 
            SET nombre=%s, categoria=%s, stock_actual=%s, stock_optimo=%s, stock_maximo=%s, precio_unitario=%s 
            WHERE id=%s
        """, (nombre, categoria, stock_actual, stock_optimo, stock_maximo, precio_unitario, id))
        mysql.connection.commit()

        # Registrar movimiento si cambió el stock_actual
        diferencia = stock_actual - stock_anterior
        if diferencia != 0:
            tipo = 'entrada' if diferencia > 0 else 'salida'
            cur.execute("""
                INSERT INTO historial_movimientos (producto_id, tipo_movimiento, cantidad, fecha_hora, usuario_id)
                VALUES (%s, %s, %s, NOW(), %s)
            """, (id, tipo, abs(diferencia), current_user.id))
            mysql.connection.commit()

        flash('Producto actualizado y movimiento registrado', 'success')
        return redirect(url_for('productos'))

    # Mapeamos la fila a un diccionario incluyendo precio_unitario
    producto_dict = {
        'id': producto['id'],
        'nombre': producto['nombre'],
        'categoria': producto['categoria'],
        'stock_actual': producto['stock_actual'],
        'stock_optimo': producto['stock_optimo'],
        'stock_maximo': producto['stock_maximo'],
        'precio_unitario': producto['precio_unitario']
    }
    return render_template('editar_producto.html', producto=producto_dict)

@app.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    cur = mysql.connection.cursor(DictCursor)

    # Obtener stock antes de eliminar
    cur.execute("SELECT stock_actual FROM productos WHERE id=%s", (id,))
    producto = cur.fetchone()
    if producto:
        stock_actual = int(producto[0])
        if stock_actual > 0:
            cur.execute("""
                INSERT INTO historial_movimientos (producto_id, tipo_movimiento, cantidad, fecha_hora, usuario_id)
                VALUES (%s, 'salida', %s, NOW(), %s)
            """, (id, stock_actual, current_user.id))
            mysql.connection.commit()

    # Eliminar producto
    cur.execute("DELETE FROM productos WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Producto eliminado y movimiento registrado.', 'success')
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
        emoji = {'Crítico':'🔴','Regular':'🟡','Óptimo':'🟢','Exceso':'🔵'}.get(p['estado'], '')
        notificaciones.append({
            'nombre': p['nombre'],
            'categoria': p['categoria'],
            'stock': p['stock_actual'],
            'estado': p['estado'],
            'emoji': emoji,
        })

    return render_template('notificaciones.html', notificaciones=notificaciones)
#apartado de la prediccion

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
        ventas = cur.fetchall()[::-1]  # Ordenar por fecha ascendente

        if len(ventas) >= 2:
            dias = np.array(range(1, len(ventas) + 1)).reshape(-1, 1)
            unidades = np.array([v['total_vendido'] for v in ventas])
            modelo = LinearRegression()
            modelo.fit(dias, unidades)
            prediccion_valor = modelo.predict([[len(dias) + 1]])[0]
        else:
            prediccion_valor = None

        grafico = None
        if prediccion_valor is not None:
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

    # 📊 Gráfico comparativo general (stock actual vs predicción)
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
    cur.execute("SET time_zone = '-05:00'")  # Asegura la zona horaria en la sesión

    query = """
        SELECT 
            CONVERT_TZ(h.fecha_hora, '+00:00', '-05:00') AS fecha_hora_local,
            h.*, 
            p.nombre AS nombre_producto, 
            u.username AS usuario
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

    # Obtener el producto
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

        # Descontar stock
        nuevo_stock = producto['stock_actual'] - cantidad
        cur.execute("UPDATE productos SET stock_actual = %s WHERE id = %s", (nuevo_stock, id))

        # Registrar en historial_movimientos
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

    # Obtener producto
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

        # Validación: no exceder stock_maximo
        if nuevo_stock > producto['stock_maximo']:
            flash(f"⚠️ No se puede ingresar esa cantidad. El stock máximo es {producto['stock_maximo']} y con esta entrada llegarías a {nuevo_stock}.", "danger")
            return redirect(request.url)

        # Actualizar stock
        cur.execute("UPDATE productos SET stock_actual = %s WHERE id = %s", (nuevo_stock, id))

        # Registrar en historial
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
        cur = mysql.connection.cursor()

        # Notificaciones por stock crítico o exceso
        cur.execute("""
            SELECT COUNT(*) AS total FROM productos 
            WHERE stock_actual < stock_optimo OR stock_actual > stock_maximo
        """)
        notificaciones = cur.fetchone()

        # Obtener todas las ventas de los últimos 7 días en una sola consulta
        cur.execute("""
            SELECT 
                p.id,
                p.stock_actual,
                DATE(hm.fecha_hora) as fecha,
                SUM(hm.cantidad) as total_vendido
            FROM productos p
            LEFT JOIN historial_movimientos hm ON p.id = hm.producto_id
            WHERE hm.tipo_movimiento = 'salida' 
              AND hm.fecha_hora >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY p.id, DATE(hm.fecha_hora)
            ORDER BY p.id, DATE(hm.fecha_hora) DESC
        """)
        ventas_data = cur.fetchall()

        # Agrupar por producto
        productos_ventas = {}
        for row in ventas_data:
            if row['id'] not in productos_ventas:
                productos_ventas[row['id']] = {
                    'stock_actual': row['stock_actual'],
                    'ventas': []
                }
            if row['total_vendido'] is not None:
                productos_ventas[row['id']]['ventas'].append(row['total_vendido'])

        alerta_prediccion = 0
        for producto_id, data in productos_ventas.items():
            ventas = data['ventas']
            if len(ventas) >= 2:
                try:
                    dias = np.array(list(range(1, len(ventas)+1))).reshape(-1, 1)
                    unidades = np.array(ventas)
                    
                    modelo = LinearRegression()
                    modelo.fit(dias, unidades)
                    pred = modelo.predict([[len(dias)+1]])[0]
                    
                    if pred > data['stock_actual']:
                        alerta_prediccion += 1
                except Exception as e:
                    print(f"Error en predicción para producto {producto_id}: {e}")
                    continue

        cur.close()
        
        return dict(
            cantidad_no_leidas=notificaciones['total'] if notificaciones else 0,
            cantidad_alerta_pred=alerta_prediccion
        )
        
    except Exception as e:
        print(f"Error en inject_cantidad_no_leidas: {e}")
        return dict(cantidad_no_leidas=0, cantidad_alerta_pred=0)

@app.route('/productos_sin_movimiento')
@login_required
def productos_sin_movimiento():
    dias = int(request.args.get('dias', 30))  # Valor por defecto: 30 días
    fecha_limite = datetime.now() - timedelta(days=dias)

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT p.id, p.nombre, p.stock_actual, MAX(h.fecha_hora) AS ultima_salida
        FROM productos p
        LEFT JOIN historial_movimientos h ON p.id = h.producto_id AND h.tipo_movimiento = 'salida'
        GROUP BY p.id, p.nombre, p.stock_actual
        HAVING ultima_salida IS NULL OR ultima_salida < %s
        ORDER BY ultima_salida ASC
    """, (fecha_limite,))
    productos = cur.fetchall()
    cur.close()

    return render_template('productos_sin_movimiento.html', productos=productos, dias=dias)

@app.route('/clasificacion_abc')
@login_required
def clasificacion_abc():
    cur = mysql.connection.cursor(DictCursor)

    # Obtener los productos con salidas y valor consumido
    cur.execute("""
        SELECT p.id, p.nombre, p.categoria, SUM(h.cantidad) AS total_salidas, 
               p.precio, SUM(h.cantidad * p.precio) AS valor_consumido
        FROM historial_movimientos h
        JOIN productos p ON h.producto_id = p.id
        WHERE h.tipo_movimiento = 'Salida'
        GROUP BY p.id
        ORDER BY valor_consumido DESC
    """)
    productos = cur.fetchall()

    total_valor = sum(p['valor_consumido'] or 0 for p in productos)

    acumulado = 0
    abc_counts = {'A': 0, 'B': 0, 'C': 0}  # Contadores para el gráfico

    for p in productos:
        valor = p['valor_consumido'] or 0
        porcentaje = (valor / total_valor) * 100 if total_valor > 0 else 0
        acumulado += porcentaje

        if acumulado <= 80:
            p['clasificacion'] = 'A'
            abc_counts['A'] += 1
        elif acumulado <= 95:
            p['clasificacion'] = 'B'
            abc_counts['B'] += 1
        else:
            p['clasificacion'] = 'C'
            abc_counts['C'] += 1

    cur.close()
    return render_template('clasificacion_abc.html', productos=productos, abc_counts=abc_counts)

@app.route('/sugerencias_pedido')
@login_required
def sugerencias_pedido():
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT id, nombre, categoria, stock_actual, stock_optimo, stock_maximo
        FROM productos
        WHERE stock_actual < stock_optimo
    """)
    productos = cur.fetchall()

    for p in productos:
        p['cantidad_sugerida'] = p['stock_optimo'] - p['stock_actual']

    cur.close()
    return render_template('sugerencias_pedido.html', productos=productos)

@app.route('/exportar_historial_excel')
@login_required
def exportar_historial_excel():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT h.id, p.nombre AS producto, h.tipo_movimiento, h.cantidad, h.fecha_hora
        FROM historial_movimientos h
        JOIN productos p ON h.producto_id = p.id
        ORDER BY h.fecha_hora DESC
    """)
    datos = cur.fetchall()
    cur.close()

    import pandas as pd
    df = pd.DataFrame(datos, columns=['ID', 'Producto', 'Movimiento', 'Cantidad', 'Fecha'])

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Historial')
    writer.close()
    output.seek(0)

    return send_file(output, download_name="historial_movimientos.xlsx", as_attachment=True)

@app.route('/exportar_productos_pdf')
@login_required
def exportar_productos_pdf():
    from fpdf import FPDF

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT nombre, categoria, stock_actual, stock_optimo, stock_maximo FROM productos")
    productos = cur.fetchall()
    cur.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Listado de Productos", ln=1, align='C')

    for p in productos:
        texto = f"{p['nombre']} | {p['categoria']} | Stock: {p['stock_actual']}/{p['stock_optimo']} - Máx: {p['stock_maximo']}"
        pdf.cell(200, 10, txt=texto, ln=1)

    output = BytesIO()
    pdf.output(output)
    output.seek(0)

    return send_file(output, download_name="productos.pdf", as_attachment=True)

@app.route('/reporte_semanal')
@login_required
def reporte_semanal():
    hoy = datetime.now()
    hace_7_dias = hoy - timedelta(days=7)

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT h.id, p.nombre AS producto, h.tipo_movimiento, h.cantidad, h.fecha_hora
        FROM historial_movimientos h
        JOIN productos p ON h.producto_id = p.id
        WHERE h.fecha_hora BETWEEN %s AND %s
        ORDER BY h.fecha_hora DESC
    """, (hace_7_dias, hoy))
    movimientos = cur.fetchall()
    cur.close()

    return render_template('reporte_semanal.html', movimientos=movimientos, desde=hace_7_dias, hasta=hoy)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Render te da el puerto
    app.run(host='0.0.0.0', port=port)