from flask_mysqldb import MySQL

mysql = MySQL()

def init_db(app):
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'      # Cambia si usas otro usuario
    app.config['MYSQL_PASSWORD'] = ''      # Cambia si tienes contraseña
    app.config['MYSQL_PORT'] = 3306
    app.config['MYSQL_DB'] = 'inventario_db'
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  # Para obtener dicts y no tuplas
    mysql.init_app(app)
