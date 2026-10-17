"""Apply the schema in app/schema.py. Run from backend/:  python -m scripts.init_db"""
import psycopg

from app import config
from app.schema import STATEMENTS


def main() -> None:
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        for stmt in STATEMENTS:
            print(stmt.strip().splitlines()[0][:80])
            conn.execute(stmt)
    print("Schema applied.")


if __name__ == "__main__":
    main()
