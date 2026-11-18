from psycopg_pool import ConnectionPool
from config import settings
from fastapi import Depends
from psycopg import Connection
from typing import Annotated

pool = ConnectionPool(settings.database_url, min_size=1, max_size=5,
                        open=False)

def get_conn(): 
    with pool.connection() as conn:
        yield conn

Conn = Annotated[Connection, Depends(get_conn)]