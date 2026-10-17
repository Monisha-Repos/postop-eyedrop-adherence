"""Connection pool. Each request borrows one connection; leaving the `with` block commits."""
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config

pool = ConnectionPool(
    config.DATABASE_URL,
    min_size=1,
    max_size=5,
    kwargs={"row_factory": dict_row},
    open=False,
)


def get_conn():
    """FastAPI dependency: yields a connection inside a transaction."""
    with pool.connection() as conn:
        yield conn
