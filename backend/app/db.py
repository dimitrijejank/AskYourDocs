from pathlib import Path
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool
from .config import get_settings

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "database" / "init" / "001_schema.sql"

pool = ConnectionPool(
    conninfo=get_settings().database_url,
    min_size=1,
    max_size=5,
    configure=register_vector,
    open=False
)

def init_db() -> None:
    pool.open(wait=True, timeout=30)
    with pool.connection() as conn:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

def close_db() -> None:
    pool.close()