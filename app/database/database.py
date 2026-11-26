import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "database.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def get_connection():
    print(f"[DEBUG] Conectando ao banco: {DB_PATH}")

    connection = sqlite3.connect(
        DB_PATH,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db():
    print("[DEBUG] Executando init_db()")
    print(f"[DEBUG] Caminho do banco: {DB_PATH}")
    print(f"[DEBUG] Caminho do schema: {SCHEMA_PATH}")
    print(f"[DEBUG] Schema existe: {SCHEMA_PATH.exists()}")

    connection = get_connection()

    try:
        connection.execute("PRAGMA journal_mode = WAL")

        schema = SCHEMA_PATH.read_text(encoding="utf-8")

        connection.executescript(schema)

        connection.commit()

        print("[DATABASE] Banco de dados inicializado com sucesso.")

    except Exception as error:
        print(f"[DATABASE ERROR] {error}")
        raise

    finally:
        connection.close()

    print(f"[DEBUG] Banco existe: {DB_PATH.exists()}")