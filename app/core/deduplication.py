from __future__ import annotations

from collections.abc import Iterable
from app.models import CasoDNR


def deduplicate_cases(cases: Iterable[CasoDNR]) -> list[CasoDNR]:
    """Remove duplicidades operacionais sem apagar registros do banco.

    A chave oficial é base + TBR. Quando o TBR não existe, usa o código do caso.
    Em colisões, mantém o registro mais recentemente atualizado, evitando que a
    mesma ocorrência seja contada duas vezes em dashboards e análises.
    """
    selected: dict[tuple, CasoDNR] = {}
    order: list[tuple] = []
    for case in cases:
        tbr = "".join((case.tbr or "").upper().split())
        code = "".join((case.codigo or "").upper().split())
        identity = tbr or code or f"ID:{case.id}"
        key = (case.base_id, identity)
        previous = selected.get(key)
        if previous is None:
            selected[key] = case
            order.append(key)
            continue
        previous_stamp = previous.atualizado_em or previous.criado_em
        current_stamp = case.atualizado_em or case.criado_em
        if current_stamp and (not previous_stamp or current_stamp > previous_stamp):
            selected[key] = case
    return [selected[key] for key in order]
