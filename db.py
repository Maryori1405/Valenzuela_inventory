import pymysql
import os

def get_connection():
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST').strip(),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )
