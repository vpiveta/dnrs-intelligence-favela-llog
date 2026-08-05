from __future__ import annotations

import os
import shutil
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, current_app, jsonify
from sqlalchemy import text
from dotenv import load_dotenv
from .extensions import db, login_manager


def _normalize_database_url(url: str) -> str:
    """Converte URLs PostgreSQL comuns para o driver psycopg 3 usado em produção."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def create_app(test_config: dict | None = None) -> Flask:
    base_dir = Path(__file__).resolve().parent.parent
    load_dotenv(base_dir / ".env")

    app = Flask(__name__, instance_relative_config=True)
    database_url = _normalize_database_url(
        os.getenv("DATABASE_URL", f"sqlite:///{base_dir / 'instance' / 'flip.db'}")
    )
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-change-me"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        HOST=os.getenv("HOST", "127.0.0.1"),
        PORT=int(os.getenv("PORT", "5073")),
        UPLOAD_FOLDER=str(base_dir / "uploads"),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    (base_dir / "logs").mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Entre para acessar o DNR's Intelligence Favela Llog."
    login_manager.login_message_category = "warning"

    from .auth.routes import bp as auth_bp
    from .dashboard.routes import bp as dashboard_bp
    from .admin.routes import bp as admin_bp
    from .cases.routes import bp as cases_bp
    from .imports.routes import bp as imports_bp
    from .intelligence.routes import bp as intelligence_bp
    from .geo.routes import bp as geo_bp
    from .intelligence.warroom import bp as warroom_bp
    from .analytics.routes import bp as analytics_bp
    from .driver_history.routes import bp as driver_history_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(imports_bp)
    app.register_blueprint(intelligence_bp)
    app.register_blueprint(geo_bp)
    app.register_blueprint(warroom_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(driver_history_bp)

    @app.context_processor
    def inject_global_filter_params():
        from flask import request
        allowed = ("base_id", "data", "semana", "ano", "date_source", "periodo")
        return {"global_filter_params": {key: request.args.get(key) for key in allowed if request.args.get(key)}}

    @app.after_request
    def disable_browser_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["X-DNR-Intelligence-Version"] = "1.0.0-enterprise"
        return response

    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(status="ok", application="DNRs Intelligence Favela Llog")
        except Exception as exc:
            current_app.logger.exception("Falha no health check")
            return jsonify(status="error", detail=str(exc)), 503

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()
        _ensure_local_schema()
        _ensure_production_schema()
        _seed_defaults()

    return app


def _seed_defaults() -> None:
    from .models import BaseOperacional, User

    base = db.session.scalar(db.select(BaseOperacional).where(BaseOperacional.codigo == "SDA9"))
    if not base:
        base = BaseOperacional(codigo="SDA9", nome="SDA9 - Base Principal", cidade="Diadema", ativa=True)
        db.session.add(base)
        db.session.flush()

    admin = db.session.scalar(db.select(User).where(User.username == "admin"))
    if not admin:
        admin = User(
            nome="Administrador DNR Intelligence",
            username="admin",
            perfil="ADMIN",
            base_id=base.id,
            ativo=True,
            alterar_senha=True,
        )
        admin.set_password("admin123")
        db.session.add(admin)
    db.session.commit()



def _ensure_production_schema() -> None:
    """Amplia campos textuais no PostgreSQL sem apagar dados existentes."""
    uri = str(db.engine.url)
    if not uri.startswith("postgresql"):
        return

    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "casos_dnr" not in set(inspector.get_table_names()):
        return

    alteracoes = [
        "ALTER TABLE casos_dnr ADD COLUMN IF NOT EXISTS data_abertura_dnr DATE",
        "ALTER TABLE casos_dnr ALTER COLUMN cliente TYPE VARCHAR(255)",
        "ALTER TABLE casos_dnr ALTER COLUMN endereco TYPE TEXT",
        "ALTER TABLE casos_dnr ALTER COLUMN motorista TYPE VARCHAR(255)",
        "ALTER TABLE casos_dnr ALTER COLUMN produto TYPE TEXT",
        "ALTER TABLE casos_dnr ALTER COLUMN login_utilizado TYPE VARCHAR(255)",
        "ALTER TABLE casos_dnr ALTER COLUMN proprietario_login TYPE VARCHAR(255)",
        "ALTER TABLE casos_dnr ALTER COLUMN categoria TYPE VARCHAR(255)",
        "ALTER TABLE casos_dnr ALTER COLUMN pedido TYPE VARCHAR(160)",
        "ALTER TABLE casos_dnr ALTER COLUMN responsavel TYPE VARCHAR(255)",
    ]

    try:
        for comando in alteracoes:
            db.session.execute(text(comando))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

def _ensure_local_schema() -> None:
    """Adiciona colunas novas ao SQLite de uma sprint anterior sem apagar dados."""
    uri = str(db.engine.url)
    if not uri.startswith("sqlite"):
        return
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    tabelas = set(inspector.get_table_names())
    alteracoes_por_tabela = {
        "importacoes_lotes": {
            "excluido_em": "DATETIME",
            "excluido_por_id": "INTEGER",
            "motivo_exclusao": "TEXT",
            "casos_excluidos": "INTEGER NOT NULL DEFAULT 0",
            "semana_numero": "INTEGER",
            "valor_total": "NUMERIC(14,2) NOT NULL DEFAULT 0",
            "qualidade_percentual": "FLOAT NOT NULL DEFAULT 0",
            "enderecos_preenchidos": "INTEGER NOT NULL DEFAULT 0",
            "motoristas_preenchidos": "INTEGER NOT NULL DEFAULT 0",
            "logins_preenchidos": "INTEGER NOT NULL DEFAULT 0",
            "datas_preenchidas": "INTEGER NOT NULL DEFAULT 0",
            "horas_preenchidas": "INTEGER NOT NULL DEFAULT 0",
            "tempo_processamento_ms": "INTEGER NOT NULL DEFAULT 0",
        },
        "casos_dnr": {
            "login_utilizado": "VARCHAR(160)",
            "login_proprio": "BOOLEAN",
            "proprietario_login": "VARCHAR(160)",
            "latitude": "FLOAT",
            "longitude": "FLOAT",
            "geocode_status": "VARCHAR(30)",
            "geocodificado_em": "DATETIME",
            "data_abertura_dnr": "DATE",
            "hora_dnr": "TIME",
            "data_hora_entrega": "DATETIME",
            "semana_numero": "INTEGER",
            "ano": "INTEGER",
            "mes": "INTEGER",
            "dia": "INTEGER",
            "dia_semana": "VARCHAR(20)",
            "faixa_horaria": "VARCHAR(30)",
            "cep4": "VARCHAR(4)",
        },
    }
    pendentes = []
    for tabela, alteracoes in alteracoes_por_tabela.items():
        if tabela not in tabelas:
            continue
        existentes = {col["name"] for col in inspector.get_columns(tabela)}
        for coluna, definicao in alteracoes.items():
            if coluna not in existentes:
                pendentes.append((tabela, coluna, definicao))
    origem = Path(db.engine.url.database or "")
    if pendentes and origem.exists():
        backup_dir = Path(current_app.root_path).parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        destino = backup_dir / f"flip_antes_migracao_{datetime.now():%Y%m%d_%H%M%S}.db"
        shutil.copy2(origem, destino)
    for tabela, coluna, definicao in pendentes:
        db.session.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}"))
    if pendentes:
        db.session.commit()

    # CEP4 sempre preserva o zero inicial e usa somente os quatro primeiros dígitos.
    if "casos_dnr" in tabelas:
        db.session.execute(text("""
            UPDATE casos_dnr
               SET cep4 = substr(printf('%08d', CAST(replace(replace(coalesce(cep,''), '-', ''), ' ', '') AS INTEGER)), 1, 4)
             WHERE (cep4 IS NULL OR cep4 = '')
               AND trim(coalesce(cep,'')) <> ''
        """))
        db.session.commit()

    # Prazo padrão: três dias após o upload. Casos manuais usam a criação.
    if "casos_dnr" in tabelas:
        db.session.execute(text("""
            UPDATE casos_dnr
               SET prazo = COALESCE(
                   (SELECT date(importacoes_lotes.criado_em, '+3 day')
                      FROM importacoes_lotes
                     WHERE importacoes_lotes.id = casos_dnr.importacao_id),
                   date(casos_dnr.criado_em, '+3 day')
               )
             WHERE prazo IS NULL
        """))
        db.session.commit()
