from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from db import pool, Conn
from psycopg.rows import dict_row

@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def raiz():
    return {"mensaje": "API del curso funcionando"}


@app.get("/saludo/{nombre}")
def saludo(nombre: str):
    return {"saludo": f"Hola, {nombre}"}

@app.get("/sumar")
def sumar(a: int, b: int = 0):
    return {"resultado": a + b}


@app.get("/usuarios")
def listar_usuarios(conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, nombre, email, activo FROM usuarios ORDER BY id")
        return cur.fetchall()

@app.get("/usuarios/{usuario_id}")
def get_usuario(usuario_id: int, conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, nombre, email, activo FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cur.fetchone()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@app.get("/usuarios/{usuario_id}/pedidos")
def get_pedido_usuario(usuario_id: int, conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT 1 FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cur.fetchone()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, producto, importe, creado_en FROM pedidos WHERE usuario_id = %s ORDER BY id", (usuario_id,))
        pedidos = cur.fetchall()
    return pedidos