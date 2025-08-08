from os import getenv
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"

load_dotenv(BASE_DIR / ".env")

MASTER_DB = getenv("MASTER_DB", "PostgreSQL")
DB_NAME = getenv("DB_NAME")
DB_USER = getenv("DB_USER")
DB_PASSWORD = getenv("DB_PASSWORD")
DB_HOST = getenv("DB_HOST")
DB_PORT = getenv("DB_PORT")
DB_CONN_TIMEOUT = getenv("DB_CONN_TIMEOUT", 3)
DB_ONESQL_TIMEOUT = getenv("DB_ONESQL_TIMEOUT", 10)

API_KEY = getenv("API_KEY", "very_strong_password")


PAGE_SIZE = getenv("PAGE_SIZE", 20)
