from __future__ import annotations

import hashlib
import html
import math
import re
import time
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode

import requests
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.models import BaseOperacional, CasoDNR

bp = Blueprint("geo", __name__, url_prefix="/geo")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
BRASIL_API_CEP_URL = "https://brasilapi.com.br/api/cep/v2/{cep}"
VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"

BASE_DEFAULT_COORDS = {
    "SDA9": (-23.6865, -46.6234),
}
DEFAULT_COORDS = (-23.6505, -46.6265)

_NOMINATIM_LAST_REQUEST = 0.0
_NOMINATIM_COOLDOWN_UNTIL = 0.0
NOMINATIM_MIN_INTERVAL = 1.15


class GeocodeRateLimited(RuntimeError):
    def __init__(self, wait_seconds: int = 60):
        self.wait_seconds = max(5, int(wait_seconds))
        super().__init__(f"Serviço de localização temporariamente limitado. Aguarde {self.wait_seconds} segundos.")


def _retry_after_seconds(response) -> int:
    value = response.headers.get("Retry-After", "").strip()
    if not value:
        return 60
    try:
        return max(5, int(value))
    except ValueError:
        try:
            target = parsedate_to_datetime(value)
            now = datetime.now(target.tzinfo or timezone.utc)
            return max(5, int((target - now).total_seconds()))
        except Exception:
            return 60


def _respect_nominatim_limit() -> None:
    global _NOMINATIM_LAST_REQUEST
    now = time.monotonic()
    if now < _NOMINATIM_COOLDOWN_UNTIL:
        raise GeocodeRateLimited(int(_NOMINATIM_COOLDOWN_UNTIL - now) + 1)
    wait = NOMINATIM_MIN_INTERVAL - (now - _NOMINATIM_LAST_REQUEST)
    if wait > 0:
        time.sleep(wait)
    _NOMINATIM_LAST_REQUEST = time.monotonic()


def _centroid(rows):
    rows = list(rows)
    if not rows:
        return None
    return (sum(x[0] for x in rows) / len(rows), sum(x[1] for x in rows) / len(rows))


def _stable_offset(key: str, radius: float = 0.0045) -> tuple[float, float]:
    digest = hashlib.sha256(key.encode("utf-8", "ignore")).digest()
    angle = int.from_bytes(digest[:4], "big") / 2**32 * math.tau
    distance = (0.25 + digest[4] / 255 * 0.75) * radius
    return math.sin(angle) * distance, math.cos(angle) * distance


def _display_points(casos: list[CasoDNR]):
    """Garante visualização de todos os endereços no mapa.

    Coordenadas exatas são preservadas. Casos ainda não geocodificados usam,
    nesta ordem, o centro do CEP completo, do CEP4, da base ou um centro
    operacional padrão. Pontos aproximados recebem deslocamento determinístico
    para não ficarem totalmente sobrepostos e são identificados no popup.
    """
    exact = [c for c in casos if c.latitude is not None and c.longitude is not None]
    full_cep_coords = {}
    cep4_coords = {}
    base_coords = {}
    for c in exact:
        full = _cep_digits(c.cep)
        if full:
            full_cep_coords.setdefault(full, []).append((c.latitude, c.longitude))
        if c.cep4:
            cep4_coords.setdefault(c.cep4, []).append((c.latitude, c.longitude))
        base_coords.setdefault(c.base_id, []).append((c.latitude, c.longitude))
    full_centers = {k: _centroid(v) for k, v in full_cep_coords.items()}
    cep4_centers = {k: _centroid(v) for k, v in cep4_coords.items()}
    base_centers = {k: _centroid(v) for k, v in base_coords.items()}

    points = []
    for c in casos:
        if c.latitude is not None and c.longitude is not None:
            points.append((c, c.latitude, c.longitude, c.geocode_status or "LOCALIZADO", False))
            continue
        full = _cep_digits(c.cep)
        center = full_centers.get(full) if full else None
        precision = "CEP_APROXIMADO"
        if center is None and c.cep4:
            center = cep4_centers.get(c.cep4)
            precision = "CEP4_APROXIMADO"
        if center is None:
            center = base_centers.get(c.base_id)
            precision = "BASE_APROXIMADA"
        if center is None:
            center = BASE_DEFAULT_COORDS.get(c.base.codigo if c.base else "", DEFAULT_COORDS)
            precision = "POSICAO_PROVISORIA"
        dlat, dlng = _stable_offset(f"{c.id}|{c.tbr}|{c.endereco}")
        points.append((c, center[0] + dlat, center[1] + dlng, precision, True))
    return points

HTTP_HEADERS = {
    "User-Agent": "FLIP-Enterprise/0.7.3 (GEO Intelligence; contato operacional)",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def _visible_query():
    query = db.select(CasoDNR)
    if not current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == current_user.base_id)
    return query


def _apply_filters(query):
    base_id = request.args.get("base_id", type=int)
    motorista = request.args.get("motorista", "").strip()
    login = request.args.get("login", "").strip()
    produto = request.args.get("produto", "").strip()
    busca = request.args.get("q", "").strip()
    cep4 = request.args.get("cep4", "").strip()
    if base_id and (current_user.can_view_all_bases):
        query = query.where(CasoDNR.base_id == base_id)
    if motorista:
        query = query.where(CasoDNR.motorista == motorista)
    if login:
        query = query.where(CasoDNR.login_utilizado == login)
    if produto:
        query = query.where(CasoDNR.produto == produto)
    if cep4:
        query = query.where(CasoDNR.cep4 == cep4)
    if busca:
        termo = f"%{busca}%"
        query = query.where(
            or_(
                CasoDNR.endereco.ilike(termo),
                CasoDNR.cep.ilike(termo),
                CasoDNR.tbr.ilike(termo),
                CasoDNR.cliente.ilike(termo),
            )
        )
    return query


@bp.route("/")
@login_required
def index():
    query = _apply_filters(_visible_query())
    casos = db.session.scalars(query.order_by(CasoDNR.criado_em.desc())).all()
    mapeados = [c for c in casos if c.latitude is not None and c.longitude is not None]
    pendentes = [c for c in casos if c.endereco and (c.latitude is None or c.longitude is None)]
    visualizaveis = [c for c in casos if c.endereco]
    bases = db.session.scalars(
        db.select(BaseOperacional)
        .where(BaseOperacional.ativa.is_(True))
        .order_by(BaseOperacional.codigo)
    ).all()
    if not current_user.can_view_all_bases:
        bases = [current_user.base]
    motoristas = sorted({c.motorista for c in casos if c.motorista})
    logins = sorted({c.login_utilizado for c in casos if c.login_utilizado})
    produtos = sorted({c.produto for c in casos if c.produto})
    valor = sum((Decimal(c.valor or 0) for c in visualizaveis), Decimal("0"))
    cep_groups = {}
    for c in casos:
        cep_key = c.cep4 or (_cep_digits(c.cep).zfill(8)[:4] if _cep_digits(c.cep) else "")
        if not cep_key:
            continue
        base_code = c.base.codigo if c.base else "SEM BASE"
        base_id = c.base_id
        group_key = (base_code, cep_key)
        group = cep_groups.setdefault(group_key, {"base": base_code, "base_id": base_id, "cep4": cep_key, "casos": 0, "enderecos": set(), "mapeados": 0, "valor": Decimal("0")})
        group["casos"] += 1
        if c.endereco:
            group["enderecos"].add(c.endereco)
        if c.latitude is not None and c.longitude is not None:
            group["mapeados"] += 1
        group["valor"] += Decimal(c.valor or 0)
    cep_groups = sorted(cep_groups.values(), key=lambda x: (x["base"], -x["casos"], x["cep4"]))
    return render_template(
        "geo/index.html",
        casos=casos,
        mapeados=mapeados,
        visualizaveis=visualizaveis,
        pendentes=pendentes,
        bases=bases,
        motoristas=motoristas,
        logins=logins,
        produtos=produtos,
        valor=valor,
        cep_groups=cep_groups,
        focus_id=request.args.get("focus", type=int),
    )


@bp.route("/api/pontos")
@login_required
def api_pontos():
    casos = db.session.scalars(_apply_filters(_visible_query())).all()
    payload = []
    for c, lat, lng, precision, approximate in _display_points(casos):
        if not c.endereco:
            continue
        payload.append(
            {
                "id": c.id,
                "codigo": c.codigo,
                "tbr": c.tbr,
                "cliente": c.cliente,
                "endereco": c.endereco or "",
                "cep": c.cep or "",
                "cep4": c.cep4 or "",
                "motorista": c.motorista or "",
                "login": c.login_utilizado or "",
                "hora": c.hora_dnr.strftime("%H:%M:%S") if c.hora_dnr else "",
                "produto": c.produto or "",
                "valor": float(c.valor or 0),
                "status": c.status,
                "prioridade": c.prioridade,
                "base": c.base.codigo,
                "lat": lat,
                "lng": lng,
                "precision": precision,
                "approximate": approximate,
                "heat_weight": max(0.35, min(8, float(c.valor or 0) / 500 + 1)) * (0.55 if approximate else 1),
                "url": url_for("cases.detalhe", caso_id=c.id, next=request.args.get("_origin") or url_for("geo.index")),
            }
        )
    return jsonify(payload)


def _can_edit(caso: CasoDNR) -> bool:
    return current_user.can_view_all_bases or caso.base_id == current_user.base_id


def _clean_text(value: str | None) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"\s+", " ", value.replace(";", ",")).strip(" ,-")
    return value


def _cep_digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")[:8]


def _viacep_address(cep: str) -> dict[str, str]:
    if len(cep) != 8:
        return {}
    response = requests.get(VIACEP_URL.format(cep=cep), headers=HTTP_HEADERS, timeout=15)
    response.raise_for_status()
    data = response.json() or {}
    if data.get("erro"):
        return {}
    return {
        "logradouro": _clean_text(data.get("logradouro")),
        "bairro": _clean_text(data.get("bairro")),
        "cidade": _clean_text(data.get("localidade")),
        "uf": _clean_text(data.get("uf")),
    }


def _address_candidates(caso: CasoDNR) -> list[str]:
    endereco = _clean_text(caso.endereco)
    cep = _cep_digits(caso.cep)
    cidade_base = _clean_text(caso.base.cidade if caso.base else "")
    candidates: list[str] = []

    # Remove complementos, mantendo rua e número para melhorar a taxa de acerto.
    principal = re.split(
        r"\b(?:ap|apto|apartamento|bl|bloco|casa|fundos|torre|predio|prédio|trabalho|portao|portão)\b",
        endereco, maxsplit=1, flags=re.IGNORECASE,
    )[0].strip(" ,-")
    if endereco:
        candidates.append(endereco)
    if principal and principal != endereco:
        candidates.append(principal)
    if principal and cep:
        candidates.append(f"{principal}, {cep}, Brasil")
    if principal and cidade_base:
        candidates.append(f"{principal}, {cidade_base}, SP, Brasil")

    # O ViaCEP fornece logradouro/bairro/cidade oficiais e corrige abreviações do arquivo.
    if cep:
        try:
            via = _viacep_address(cep)
        except requests.RequestException:
            via = {}
        if via:
            number_match = re.search(r"\b(\d{1,6})\b", principal or endereco)
            number = number_match.group(1) if number_match else ""
            official = ", ".join(x for x in [via.get("logradouro"), number, via.get("bairro"), via.get("cidade"), via.get("uf"), cep, "Brasil"] if x)
            street = ", ".join(x for x in [via.get("logradouro"), via.get("bairro"), via.get("cidade"), via.get("uf"), cep, "Brasil"] if x)
            candidates.extend([official, street])
        candidates.append(f"{cep}, Brasil")

    unique: list[str] = []
    seen = set()
    for item in candidates:
        key = norm_geo(item)
        if item and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def norm_geo(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _nominatim_lookup(query: str) -> tuple[float, float] | None:
    global _NOMINATIM_COOLDOWN_UNTIL
    _respect_nominatim_limit()
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "br",
        "addressdetails": 1,
    }
    response = requests.get(NOMINATIM_URL, params=params, headers=HTTP_HEADERS, timeout=20)
    if response.status_code == 429:
        wait_seconds = _retry_after_seconds(response)
        _NOMINATIM_COOLDOWN_UNTIL = time.monotonic() + wait_seconds
        raise GeocodeRateLimited(wait_seconds)
    response.raise_for_status()
    data = response.json()
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])


def _cep_lookup(cep: str) -> tuple[float, float] | None:
    if len(cep) != 8:
        return None
    response = requests.get(
        BRASIL_API_CEP_URL.format(cep=cep), headers=HTTP_HEADERS, timeout=15
    )
    response.raise_for_status()
    data = response.json() or {}
    coordinates = ((data.get("location") or {}).get("coordinates") or {})
    lat = coordinates.get("latitude")
    lng = coordinates.get("longitude")
    if lat in (None, "") or lng in (None, ""):
        return None
    return float(lat), float(lng)


def _geocode(caso: CasoDNR) -> tuple[float, float, str] | None:
    # Reutiliza coordenadas já validadas do mesmo endereço antes de consultar a internet.
    if caso.endereco:
        cached = db.session.scalar(
            db.select(CasoDNR).where(
                CasoDNR.id != caso.id,
                CasoDNR.endereco == caso.endereco,
                CasoDNR.latitude.is_not(None),
                CasoDNR.longitude.is_not(None),
            ).limit(1)
        )
        if cached:
            return cached.latitude, cached.longitude, "CACHE_ENDERECO"

    last_error: requests.RequestException | None = None
    rate_limited: GeocodeRateLimited | None = None
    # No máximo duas consultas por endereço. Isso respeita o serviço público e
    # evita bloqueio por excesso de tentativas com pequenas variações.
    for candidate in _address_candidates(caso)[:2]:
        try:
            coords = _nominatim_lookup(candidate)
            if coords:
                return coords[0], coords[1], "LOCALIZADO"
        except GeocodeRateLimited as exc:
            rate_limited = exc
            break
        except requests.RequestException as exc:
            last_error = exc

    cep = _cep_digits(caso.cep)
    if cep:
        # Reutiliza um ponto aproximado já conhecido do mesmo CEP.
        cached_cep = db.session.scalar(
            db.select(CasoDNR).where(
                CasoDNR.id != caso.id,
                CasoDNR.cep.ilike(f"%{cep}%"),
                CasoDNR.latitude.is_not(None),
                CasoDNR.longitude.is_not(None),
            ).limit(1)
        )
        if cached_cep:
            return cached_cep.latitude, cached_cep.longitude, "CEP_APROXIMADO"
        try:
            coords = _cep_lookup(cep)
            if coords:
                return coords[0], coords[1], "CEP_APROXIMADO"
        except requests.RequestException as exc:
            last_error = exc

    if rate_limited:
        raise rate_limited
    if last_error:
        raise last_error
    return None


def _save_geocode(caso: CasoDNR, result: tuple[float, float, str] | None) -> bool:
    if not result:
        caso.geocode_status = "NAO_LOCALIZADO"
        return False
    caso.latitude, caso.longitude, caso.geocode_status = result
    caso.geocodificado_em = datetime.now(timezone.utc)
    return True


@bp.route("/geocodificar/<int:caso_id>", methods=["POST"])
@login_required
def geocodificar(caso_id: int):
    caso = db.session.get(CasoDNR, caso_id)
    if not caso:
        abort(404)
    if not _can_edit(caso):
        abort(403)
    try:
        localizado = _save_geocode(caso, _geocode(caso))
        db.session.commit()
        if localizado:
            if caso.geocode_status == "CEP_APROXIMADO":
                flash(
                    "A porta exata não foi localizada; o caso foi posicionado aproximadamente pelo CEP.",
                    "warning",
                )
            else:
                flash("Endereço localizado e salvo no mapa.", "success")
        else:
            flash(
                "Endereço não localizado. Revise rua, número, cidade e CEP ou informe as coordenadas manualmente.",
                "warning",
            )
    except GeocodeRateLimited as exc:
        caso.geocode_status = "AGUARDANDO_SERVICO"
        db.session.commit()
        flash(f"{exc} O caso continua visível no mapa em posição aproximada.", "warning")
    except requests.RequestException:
        caso.geocode_status = "ERRO_SERVICO"
        db.session.commit()
        flash("O serviço de localização está temporariamente indisponível. Tente novamente mais tarde; o caso continua visível no mapa em posição aproximada.", "warning")
    return redirect(request.referrer or url_for("geo.index"))


@bp.route("/geocodificar-pendentes", methods=["POST"])
@login_required
def geocodificar_pendentes():
    query = _apply_filters(_visible_query()).where(
        CasoDNR.endereco.is_not(None),
        or_(CasoDNR.latitude.is_(None), CasoDNR.longitude.is_(None)),
    )
    limite = max(1, min(request.form.get("limite", type=int) or 20, 30))
    casos = db.session.scalars(query.order_by(CasoDNR.id).limit(limite)).all()
    localizados = aproximados = nao_localizados = erros = 0

    for index, caso in enumerate(casos):
        if not _can_edit(caso):
            continue
        try:
            result = _geocode(caso)
            if _save_geocode(caso, result):
                if caso.geocode_status == "CEP_APROXIMADO":
                    aproximados += 1
                else:
                    localizados += 1
            else:
                nao_localizados += 1
        except GeocodeRateLimited as exc:
            caso.geocode_status = "AGUARDANDO_SERVICO"
            erros += 1
            db.session.commit()
            flash(f"Localização pausada para respeitar o limite do serviço. {exc}", "warning")
            break
        except requests.RequestException:
            caso.geocode_status = "ERRO_SERVICO"
            erros += 1
        db.session.commit()

    flash(
        f"Localização processada: {localizados} exatos, {aproximados} aproximados por CEP, "
        f"{nao_localizados} não localizados e {erros} erros de serviço.",
        "success" if (localizados or aproximados) else "warning",
    )
    return redirect(request.referrer or url_for("geo.index"))


@bp.route("/coordenadas/<int:caso_id>", methods=["POST"])
@login_required
def coordenadas(caso_id: int):
    caso = db.session.get(CasoDNR, caso_id)
    if not caso:
        abort(404)
    if not _can_edit(caso):
        abort(403)
    try:
        caso.latitude = float(request.form.get("latitude", "").replace(",", "."))
        caso.longitude = float(request.form.get("longitude", "").replace(",", "."))
    except ValueError:
        flash("Latitude ou longitude inválida.", "warning")
        return redirect(request.referrer or url_for("geo.index"))
    caso.geocode_status = "MANUAL"
    caso.geocodificado_em = datetime.now(timezone.utc)
    db.session.commit()
    flash("Coordenadas salvas manualmente.", "success")
    return redirect(request.referrer or url_for("geo.index"))
