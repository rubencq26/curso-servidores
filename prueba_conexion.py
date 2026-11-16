import os
import psycopg

url = os.environ["DATABASE_URL"]

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, usuario_id, producto, importe FROM pedidos;")
        filas = cur.fetchall()

for id, usuario_id, producto, importe in filas:
    print(f"Pedido {id} · usuario {usuario_id} · {producto} · {importe} €")