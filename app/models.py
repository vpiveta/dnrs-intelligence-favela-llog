from __future__ import annotations

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from .extensions import db, login_manager


class TimestampMixin:
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    atualizado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class BaseOperacional(TimestampMixin, db.Model):
    __tablename__ = "bases_operacionais"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(120), nullable=False)
    cidade = db.Column(db.String(120))
    ativa = db.Column(db.Boolean, default=True, nullable=False)
    usuarios = db.relationship("User", back_populates="base")


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(30), nullable=False, default="ANALISTA")
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    alterar_senha = db.Column(db.Boolean, default=True, nullable=False)
    base_id = db.Column(db.Integer, db.ForeignKey("bases_operacionais.id"), nullable=False)
    base = db.relationship("BaseOperacional", back_populates="usuarios")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self) -> bool:
        return self.ativo

    @property
    def is_admin(self) -> bool:
        return self.perfil == "ADMIN"

    @property
    def can_view_all_bases(self) -> bool:
        return self.perfil in {"ADMIN", "GERENTE_REGIONAL", "GERENTE_GERAL"}

    @property
    def base_scope_label(self) -> str:
        return "Todas as bases" if self.can_view_all_bases else self.base.codigo


class CasoDNR(TimestampMixin, db.Model):
    __tablename__ = "casos_dnr"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False, index=True)
    tbr = db.Column(db.String(30), nullable=False, index=True)
    cliente = db.Column(db.String(160), nullable=False)
    endereco = db.Column(db.String(255))
    motorista = db.Column(db.String(160))
    produto = db.Column(db.String(180))
    valor = db.Column(db.Numeric(12, 2), default=0)
    cep = db.Column(db.String(20))
    cep4 = db.Column(db.String(4), index=True)
    login_utilizado = db.Column(db.String(160))
    login_proprio = db.Column(db.Boolean)
    proprietario_login = db.Column(db.String(160))
    categoria = db.Column(db.String(120))
    pedido = db.Column(db.String(80))
    data_dnr = db.Column(db.Date)
    hora_dnr = db.Column(db.Time)
    data_hora_entrega = db.Column(db.DateTime)
    semana_numero = db.Column(db.Integer, index=True)
    ano = db.Column(db.Integer, index=True)
    mes = db.Column(db.Integer, index=True)
    dia = db.Column(db.Integer)
    dia_semana = db.Column(db.String(20))
    faixa_horaria = db.Column(db.String(30), index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    geocode_status = db.Column(db.String(30))
    geocodificado_em = db.Column(db.DateTime(timezone=True))
    importacao_id = db.Column(db.Integer, db.ForeignKey("importacoes_lotes.id"))
    status = db.Column(db.String(40), default="PENDENTE", nullable=False)
    prioridade = db.Column(db.String(20), default="MEDIA", nullable=False)
    responsavel = db.Column(db.String(160))
    procedimento = db.Column(db.Text)
    prazo = db.Column(db.Date)
    base_id = db.Column(db.Integer, db.ForeignKey("bases_operacionais.id"), nullable=False)
    base = db.relationship("BaseOperacional")


class ImportacaoLote(TimestampMixin, db.Model):
    __tablename__ = "importacoes_lotes"
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    arquivo_salvo = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), default="PROCESSANDO", nullable=False)
    total_linhas = db.Column(db.Integer, default=0, nullable=False)
    importados = db.Column(db.Integer, default=0, nullable=False)
    duplicados = db.Column(db.Integer, default=0, nullable=False)
    ignorados = db.Column(db.Integer, default=0, nullable=False)
    semana_numero = db.Column(db.Integer, index=True)
    valor_total = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    qualidade_percentual = db.Column(db.Float, default=0, nullable=False)
    enderecos_preenchidos = db.Column(db.Integer, default=0, nullable=False)
    motoristas_preenchidos = db.Column(db.Integer, default=0, nullable=False)
    logins_preenchidos = db.Column(db.Integer, default=0, nullable=False)
    datas_preenchidas = db.Column(db.Integer, default=0, nullable=False)
    horas_preenchidas = db.Column(db.Integer, default=0, nullable=False)
    tempo_processamento_ms = db.Column(db.Integer, default=0, nullable=False)
    mapeamento = db.Column(db.Text)
    erros = db.Column(db.Text)
    base_id = db.Column(db.Integer, db.ForeignKey("bases_operacionais.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    base = db.relationship("BaseOperacional")
    usuario = db.relationship("User", foreign_keys=[usuario_id])
    casos = db.relationship("CasoDNR", backref="importacao")
    excluido_em = db.Column(db.DateTime(timezone=True))
    excluido_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    motivo_exclusao = db.Column(db.Text)
    casos_excluidos = db.Column(db.Integer, default=0, nullable=False)
    excluido_por = db.relationship("User", foreign_keys=[excluido_por_id])


class HistoricoCaso(TimestampMixin, db.Model):
    __tablename__ = "historicos_casos"
    id = db.Column(db.Integer, primary_key=True)
    caso_id = db.Column(db.Integer, db.ForeignKey("casos_dnr.id"), nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    acao = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.Text)
    status_anterior = db.Column(db.String(40))
    status_novo = db.Column(db.String(40))
    caso = db.relationship("CasoDNR", backref=db.backref("historicos", cascade="all, delete-orphan", order_by="HistoricoCaso.criado_em.desc()"))
    usuario = db.relationship("User", foreign_keys=[usuario_id])


<<<<<<< HEAD
class SchemaVersion(db.Model):
    __tablename__ = "schema_versions"
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(40), unique=True, nullable=False)
    aplicado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    descricao = db.Column(db.String(255))


=======
>>>>>>> 2de3bb5a2d6358c1527e18cfaffdfbc1dfc6baa8
@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))
