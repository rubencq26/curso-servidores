import os
import psycopg

url = os.getenv("DATABASE_URL")

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM pedidos;")
        filas = cur.fetchall()

print(filas)