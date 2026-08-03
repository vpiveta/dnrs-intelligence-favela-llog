from __future__ import annotations

from flask import abort
from flask_login import current_user

GLOBAL_PROFILES = {"ADMIN", "GERENTE_REGIONAL", "GERENTE_GERAL"}


def can_view_all_bases(user=None) -> bool:
    user = user or current_user
    return bool(user.is_authenticated and user.perfil in GLOBAL_PROFILES)


def apply_base_scope(query, model, user=None):
    user = user or current_user
    if not can_view_all_bases(user):
        query = query.where(model.base_id == user.base_id)
    return query


def selected_base_id(raw_base_id: int | None, user=None) -> int | None:
    user = user or current_user
    return raw_base_id if can_view_all_bases(user) else user.base_id


def enforce_record_base(record, user=None) -> None:
    user = user or current_user
    if not can_view_all_bases(user) and record.base_id != user.base_id:
        abort(403)
