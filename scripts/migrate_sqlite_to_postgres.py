from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra o banco SQLite local do DNR Intelligence para PostgreSQL.")
    parser.add_argument("sqlite_path", help="Caminho do arquivo flip.db")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="URL PostgreSQL de destino")
    parser.add_argument("--replace", action="store_true", help="Apaga os dados existentes no destino antes de migrar")
    args = parser.parse_args()

    source = Path(args.sqlite_path).resolve()
    if not source.exists():
        raise SystemExit(f"Banco SQLite não encontrado: {source}")
    if not args.database_url:
        raise SystemExit("Informe --database-url ou defina DATABASE_URL.")

    target_url = normalize_database_url(args.database_url)
    target = create_engine(target_url, future=True)

    # A aplicação cria as tabelas no primeiro start. Esta rotina exige o schema já criado.
    target_tables = set(inspect(target).get_table_names())
    if not target_tables:
        raise SystemExit("O PostgreSQL ainda não possui as tabelas do DNR Intelligence. Inicie a aplicação uma vez e execute novamente.")

    order = [
        "bases_operacionais",
        "usuarios",
        "importacoes_lotes",
        "casos_dnr",
        "historicos_casos",
    ]

    src = sqlite3.connect(source)
    src.row_factory = sqlite3.Row
    try:
        with target.begin() as conn:
            if args.replace:
                for table in reversed(order):
                    if table in target_tables:
                        conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))

            for table in order:
                if table not in target_tables:
                    continue
                rows = src.execute(f'SELECT * FROM "{table}"').fetchall()
                if not rows:
                    print(f"{table}: 0 registros")
                    continue
                target_cols = {c["name"] for c in inspect(target).get_columns(table)}
                payload = [{k: row[k] for k in row.keys() if k in target_cols} for row in rows]
                columns = list(payload[0].keys())
                col_sql = ", ".join(f'"{c}"' for c in columns)
                val_sql = ", ".join(f':{c}' for c in columns)
                conn.execute(text(f'INSERT INTO "{table}" ({col_sql}) VALUES ({val_sql})'), payload)
                print(f"{table}: {len(payload)} registros migrados")

            # Ajusta sequences após inserir IDs explícitos.
            for table in order:
                if table in target_tables:
                    conn.execute(text(
                        "SELECT setval(pg_get_serial_sequence(:table, 'id'), "
                        "COALESCE((SELECT MAX(id) FROM \"" + table + "\"), 1), true)"
                    ), {"table": table})
    finally:
        src.close()
        target.dispose()

    print("Migração concluída.")


if __name__ == "__main__":
    main()
