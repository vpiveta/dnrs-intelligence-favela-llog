from __future__ import annotations

import argparse
<<<<<<< HEAD
import getpass
=======
>>>>>>> 2de3bb5a2d6358c1527e18cfaffdfbc1dfc6baa8
import os
import sqlite3
from pathlib import Path

<<<<<<< HEAD

def normalize_database_url(url: str) -> str:
    url = url.strip().strip('"').strip("'")
    if "[YOUR-PASSWORD]" in url:
        raise ValueError("Substitua [YOUR-PASSWORD] pela senha real do banco.")
=======
from sqlalchemy import create_engine, inspect, text


def normalize_database_url(url: str) -> str:
>>>>>>> 2de3bb5a2d6358c1527e18cfaffdfbc1dfc6baa8
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


<<<<<<< HEAD
def prompt_database_url() -> str:
    print()
    print("Cole a DATABASE_URL Session Pooler do Supabase.")
    print("A informação não será gravada em arquivo nem exibida novamente.")
    value = getpass.getpass("DATABASE_URL: ").strip()
    if not value:
        value = input("DATABASE_URL (entrada visível): ").strip()
    return value


def create_destination_schema(database_url: str) -> None:
    os.environ["DATABASE_URL"] = database_url
    os.environ.setdefault("SECRET_KEY", "migration-only-temporary-key")
    from app import create_app
    from app.extensions import db
    app = create_app({"TESTING": True})
    with app.app_context():
        db.create_all()


def sqlite_counts(source: Path) -> dict[str, int]:
    src = sqlite3.connect(source)
    try:
        tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result = {}
        for table in ["bases_operacionais", "usuarios", "importacoes_lotes", "casos_dnr", "historicos_casos"]:
            if table in tables:
                result[table] = src.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        return result
    finally:
        src.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra o banco SQLite local para o PostgreSQL/Supabase.")
    parser.add_argument("sqlite_path", nargs="?", default="instance/flip.db", help="Caminho do arquivo flip.db")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="URL PostgreSQL de destino")
    parser.add_argument("--replace", action="store_true", help="Substitui os dados existentes no destino")
    parser.add_argument("--yes", action="store_true", help="Não solicita confirmação")
=======
def main() -> None:
    parser = argparse.ArgumentParser(description="Migra o banco SQLite local do DNR Intelligence para PostgreSQL.")
    parser.add_argument("sqlite_path", help="Caminho do arquivo flip.db")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="URL PostgreSQL de destino")
    parser.add_argument("--replace", action="store_true", help="Apaga os dados existentes no destino antes de migrar")
>>>>>>> 2de3bb5a2d6358c1527e18cfaffdfbc1dfc6baa8
    args = parser.parse_args()

    source = Path(args.sqlite_path).resolve()
    if not source.exists():
<<<<<<< HEAD
        raise SystemExit(f"ERRO: banco SQLite não encontrado: {source}")

    raw_url = args.database_url or prompt_database_url()
    try:
        target_url = normalize_database_url(raw_url)
    except ValueError as exc:
        raise SystemExit(f"ERRO: {exc}")

    counts = sqlite_counts(source)
    print()
    print("Banco de origem:", source)
    for table, total in counts.items():
        print(f"  {table}: {total}")
    print("Destino: PostgreSQL/Supabase")

    replace = args.replace
    if not args.yes:
        answer = input("\nSubstituir os dados atuais do Supabase pelos dados locais? [S/N]: ").strip().upper()
        replace = answer == "S"
        if not replace:
            answer = input("Continuar adicionando os dados sem apagar o destino? [S/N]: ").strip().upper()
            if answer != "S":
                raise SystemExit("Migração cancelada.")

    try:
        from sqlalchemy import create_engine, inspect, text
        create_destination_schema(target_url)
        target = create_engine(target_url, future=True, pool_pre_ping=True)
        with target.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Conexão com Supabase: OK")

        target_tables = set(inspect(target).get_table_names())
        order = ["bases_operacionais", "usuarios", "importacoes_lotes", "casos_dnr", "historicos_casos"]
        src = sqlite3.connect(source)
        src.row_factory = sqlite3.Row
        try:
            with target.begin() as conn:
                if replace:
                    for table in reversed(order):
                        if table in target_tables:
                            conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))

                for table in order:
                    if table not in target_tables:
                        print(f"{table}: tabela não encontrada no destino")
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

                for table in order:
                    if table in target_tables:
                        conn.execute(text(
                            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                            f"COALESCE((SELECT MAX(id) FROM \"{table}\"), 1), "
                            f"EXISTS(SELECT 1 FROM \"{table}\"))"
                        ))
        finally:
            src.close()
            target.dispose()
    except Exception as exc:
        print()
        print("FALHA NA MIGRAÇÃO:")
        print(type(exc).__name__ + ":", exc)
        print()
        print("Verifique a senha, a Session Pooler e a variável DATABASE_URL.")
        raise SystemExit(1)

    print()
    print("MIGRAÇÃO CONCLUÍDA COM SUCESSO.")
    print("Abra o sistema online e atualize com Ctrl+F5.")
=======
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
>>>>>>> 2de3bb5a2d6358c1527e18cfaffdfbc1dfc6baa8


if __name__ == "__main__":
    main()
