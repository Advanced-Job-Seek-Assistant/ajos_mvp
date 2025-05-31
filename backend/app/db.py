import os
from dotenv import load_dotenv
import psycopg2

# Загрузить .env-файл
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
    )
