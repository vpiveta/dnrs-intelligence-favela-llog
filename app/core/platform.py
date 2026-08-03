from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from flask import current_app
from sqlalchemy import inspect, text

from app.extensions import db

APP_VERSION = "1.0.0-enterprise"


def database_summary() -> dict:
    url = db.engine.url
    backend = url.get_backend_name()
    host = url.host or "arquivo local"
    database = url.database or ""
    if backend == "sqlite":
        database = Path(database).name if database else "flip.db"
    return {
        "backend": "PostgreSQL / Supabase" if backend.startswith("postgresql") else "SQLite local",
        "backend_raw": backend,
        "host": host,
        "database": database,
        "production": backend.startswith("postgresql"),
    }


def platform_health() -> dict:
    db_ok = False
    db_error = None
    table_count = 0
    counts = {}
    try:
        db.session.execute(text("SELECT 1"))
        db_ok = True
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        table_count = len(tables)
        for table in ["bases_operacionais", "usuarios", "importacoes_lotes", "casos_dnr", "historicos_casos"]:
            if table in tables:
                counts[table] = db.session.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
    except Exception as exc:  # pragma: no cover - displayed to administrator
        db_error = str(exc)
        db.session.rollback()

    root = Path(current_app.root_path).parent
    backup_dir = root / "backups"
    backups = sorted(backup_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True) if backup_dir.exists() else []
    last_backup = None
    if backups:
        p = backups[0]
        last_backup = {
            "nome": p.name,
            "data": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc),
            "tamanho": p.stat().st_size,
        }

    render_url = os.getenv("RENDER_EXTERNAL_URL", "")
    github_repo = os.getenv("GITHUB_REPOSITORY", "vpiveta/flip-enterprise")
    return {
        "version": APP_VERSION,
        "database": database_summary(),
        "database_ok": db_ok,
        "database_error": db_error,
        "table_count": table_count,
        "counts": counts,
        "render": {
            "online": bool(render_url),
            "url": render_url or "Modo local",
            "service": os.getenv("RENDER_SERVICE_NAME", "Local"),
        },
        "github": {"repository": github_repo},
        "last_backup": last_backup,
        "environment": "Produção" if os.getenv("RENDER") or render_url else "Local",
    }
