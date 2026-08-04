from datetime import date

from app import create_app
from app.extensions import db
from app.models import CasoDNR


def _login(client):
    client.post("/auth/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
    client.post("/auth/alterar-senha", data={"password": "NovaSenha123", "confirm": "NovaSenha123"}, follow_redirects=True)


def test_global_filter_persists_between_modules(tmp_path):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'global.db'}"})
    client = app.test_client()
    _login(client)
    with app.app_context():
        db.session.add(CasoDNR(codigo="DNR-G1", tbr="TBR400000111", cliente="Cliente", base_id=1, data_dnr=date(2026, 8, 1), semana_numero=31, ano=2026))
        db.session.commit()
    response = client.get("/?base_id=1&semana=31&ano=2026&apply_filters=1")
    assert response.status_code == 200
    response = client.get("/analytics/")
    assert response.status_code == 200
    assert b"S31" in response.data
    with client.session_transaction() as sess:
        context = sess["dnr_global_filters"]
        assert context["base_id"] == 1
        assert context["semana"] == 31
        assert context["ano"] == 2026


def test_clear_global_filter(tmp_path):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'clear.db'}"})
    client = app.test_client()
    _login(client)
    client.get("/?base_id=1&semana=31&ano=2026&apply_filters=1")
    client.get("/filtros/limpar")
    with client.session_transaction() as sess:
        assert "dnr_global_filters" not in sess
