from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from app.models import CasoDNR

CONCLUIDOS = {"RESOLVIDO", "ENCERRADO", "CONCLUIDO"}


def clean(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def normalized(value: str | None) -> str:
    return clean(value).casefold()


def sla_date(caso: CasoDNR) -> date:
    """Prazo para concluir a análise: três dias após o upload do lote.

    A Data de entrega e a Data de abertura do DNR são informações da planilha
    e nunca alteram este prazo operacional.
    """
    if caso.importacao and caso.importacao.criado_em:
        return caso.importacao.criado_em.date() + timedelta(days=3)
    if caso.criado_em:
        return caso.criado_em.date() + timedelta(days=3)
    return date.today() + timedelta(days=3)


def is_overdue(caso: CasoDNR, today: date | None = None) -> bool:
    today = today or date.today()
    return caso.status not in CONCLUIDOS and today > sla_date(caso)


def value_risk_level(value: Decimal | float | int | None) -> str:
    """Classificação oficial de risco financeiro do FLIP.

    CRITICO: R$ 1.000,00 ou mais
    ALTO:    R$ 500,00 a R$ 999,99
    MEDIO:   R$ 100,00 a R$ 499,99
    BAIXO:   abaixo de R$ 100,00
    """
    amount = Decimal(value or 0)
    if amount >= Decimal("1000"):
        return "CRITICO"
    if amount >= Decimal("500"):
        return "ALTO"
    if amount >= Decimal("100"):
        return "MEDIO"
    return "BAIXO"


def value_risk_reason(value: Decimal | float | int | None) -> str:
    amount = Decimal(value or 0)
    level = value_risk_level(amount)
    formatted = f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    labels = {
        "CRITICO": "produto de valor crítico",
        "ALTO": "produto de alto valor",
        "MEDIO": "produto de valor médio",
        "BAIXO": "produto de baixo valor",
    }
    return f"{labels[level]} ({formatted})"


def top_keys(casos: Iterable[CasoDNR], attr: str, minimum: int = 2) -> tuple[set[str], int]:
    """Mantido para rankings e análises, não para definir criticidade."""
    counts = Counter(
        normalized(getattr(caso, attr, None))
        for caso in casos
        if normalized(getattr(caso, attr, None))
    )
    if not counts:
        return set(), 0
    highest = max(counts.values())
    if highest < minimum:
        return set(), highest
    return {key for key, count in counts.items() if count == highest}, highest


def critical_context(casos: list[CasoDNR]) -> dict[str, object]:
    """Contexto de recorrência usado apenas para rankings explicativos."""
    motorista_keys, motorista_count = top_keys(casos, "motorista")
    login_keys, login_count = top_keys(casos, "login_utilizado")
    endereco_keys, endereco_count = top_keys(casos, "endereco")
    return {
        "motorista_keys": motorista_keys,
        "motorista_count": motorista_count,
        "login_keys": login_keys,
        "login_count": login_count,
        "endereco_keys": endereco_keys,
        "endereco_count": endereco_count,
    }


def critical_reasons(caso: CasoDNR, _context: dict[str, object] | None = None) -> list[str]:
    """Criticidade oficial baseada somente no valor do produto."""
    if value_risk_level(caso.valor) == "CRITICO":
        return [value_risk_reason(caso.valor)]
    return []


def is_critical(caso: CasoDNR, context: dict[str, object] | None = None) -> bool:
    return value_risk_level(caso.valor) == "CRITICO"
