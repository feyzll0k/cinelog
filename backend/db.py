import os
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Veritabanı bağlantı havuzu (Connection Pool)
_connection_pool = None


def get_connection_pool():
    """Bağlantı havuzunu başlatır veya mevcut olanı döndürür."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "cinelog_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
        )
    return _connection_pool


@contextmanager
def get_db_connection():
    """Bağlantı havuzundan bir bağlantı alır ve işlem bitince geri bırakır."""
    pool_instance = get_connection_pool()
    conn = pool_instance.getconn()
    try:
        yield conn
    finally:
        pool_instance.putconn(conn)


@contextmanager
def get_db_cursor(commit=False):
    """
    Sözlük benzeri (RealDictCursor) sonuç döndüren cursor context manager'ı.
    commit=True verilirse blok başarıyla tamamlandığında commit yapar.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
