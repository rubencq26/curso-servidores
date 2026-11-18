from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from db import pool, Conn
from psycopg.rows import dict_row
from schemas import UsuarioCrear, UsuarioActualizar, UsuarioLeer, PedidoCrear, PedidoLeer

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


@app.get("/usuarios", response_model=list[UsuarioLeer])
def listar_usuarios(conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, nombre, email, activo, creado_en FROM usuarios ORDER BY id")
        return cur.fetchall()

@app.get("/usuarios/{usuario_id}", response_model=UsuarioLeer)
def get_usuario(usuario_id: int, conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, nombre, email, activo, creado_en FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cur.fetchone()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@app.get("/usuarios/{usuario_id}/pedidos", response_model=list[PedidoLeer])
def get_pedido_usuario(usuario_id: int, conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT 1 FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cur.fetchone()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, usuario_id producto, importe, creado_en FROM pedidos WHERE usuario_id = %s ORDER BY id", (usuario_id,))
        pedidos = cur.fetchall()
    return pedidos

@app.post("/usuarios", response_model=UsuarioLeer, status_code=201)
def crear_usuario(usuario: UsuarioCrear, conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            INSERT INTO usuarios (nombre, email)
            VALUES (%(nombre)s, %(email)s)
            RETURNING id, nombre, email, activo, creado_en;
        """, usuario.model_dump())
        usuario = cur.fetchone()
    return usuario

@app.patch("/usuarios/{usuario_id}", response_model=UsuarioLeer)
def actualizar_usuario(usuario_id: int, usuario: UsuarioActualizar, conn: Conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            UPDATE usuarios SET
                nombre = COALESCE(%(nombre)s, nombre),
                email = COALESCE(%(email)s, email),
                activo = COALESCE(%(activo)s, activo)
            WHERE id = %(id)s
            RETURNING id, nombre, email, activo, creado_en
        """, {**usuario.model_dump(), "id": usuario_id})
        usuario = cur.fetchone()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario