from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from decimal import Decimal

class UsuarioCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    email: EmailStr

class UsuarioActualizar(BaseModel):
    nombre: str | None = None
    email: str | None = None
    activo: bool | None = None

class UsuarioLeer(BaseModel):
    id: int
    nombre: str
    email: str
    activo: bool
    creado_en: datetime

class PedidoCrear(BaseModel):
    producto: str
    importe: Decimal = Field(ge=0, max_digits=10, decimal_places=2)

class PedidoLeer(BaseModel):
    id: int
    usuario_id: int
    producto: str
    importe: Decimal
    creado_en: datetime