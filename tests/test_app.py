import io
from app import create_app


def test_login_page(tmp_path):
    db_path = tmp_path / "test.db"
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}"})
    client = app.test_client()
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"FLIP" in response.data


def test_protected_dashboard_redirects(tmp_path):
    db_path = tmp_path / "test2.db"
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}"})
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_import_page_requires_login(tmp_path):
    db_path = tmp_path / "test_import.db"
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}", "UPLOAD_FOLDER": str(tmp_path / "uploads")})
    client = app.test_client()
    response = client.get("/importacoes/")
    assert response.status_code == 302


def test_csv_import_creates_case(tmp_path):
    from app.extensions import db
    from app.models import CasoDNR
    db_path = tmp_path / "test_csv.db"
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}", "UPLOAD_FOLDER": str(tmp_path / "uploads"), "WTF_CSRF_ENABLED": False})
    client = app.test_client()
    client.post("/auth/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
    client.post("/auth/alterar-senha", data={"password": "NovaSenha123", "confirm": "NovaSenha123"}, follow_redirects=True)
    payload = b"TBR;Cliente;Valor\nTBR499999999;Cliente Teste;100,50\n"
    response = client.post("/importacoes/novo", data={"base_id": "1", "arquivo": (io.BytesIO(payload), "teste.csv")}, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert db.session.scalar(db.select(CasoDNR).where(CasoDNR.tbr == "TBR499999999")) is not None


def test_delete_import_removes_only_linked_cases(tmp_path):
    from app.extensions import db
    from app.models import CasoDNR, ImportacaoLote
    db_path = tmp_path / "test_delete.db"
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}", "UPLOAD_FOLDER": str(tmp_path / "uploads"), "WTF_CSRF_ENABLED": False})
    client = app.test_client()
    client.post("/auth/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
    client.post("/auth/alterar-senha", data={"password": "NovaSenha123", "confirm": "NovaSenha123"}, follow_redirects=True)
    payload = b"TBR;Cliente\nTBR488888888;Cliente Excluir\n"
    client.post("/importacoes/novo", data={"base_id": "1", "arquivo": (io.BytesIO(payload), "errada.csv")}, content_type="multipart/form-data", follow_redirects=True)
    with app.app_context():
        lote = db.session.scalar(db.select(ImportacaoLote).where(ImportacaoLote.nome_arquivo == "errada.csv"))
        lote_id = lote.id
        assert db.session.scalar(db.select(CasoDNR).where(CasoDNR.tbr == "TBR488888888")) is not None
    response = client.post(f"/importacoes/{lote_id}/excluir", data={"motivo": "Planilha enviada para a base errada", "confirmacao": "EXCLUIR"}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        lote = db.session.get(ImportacaoLote, lote_id)
        assert lote.status == "EXCLUIDO"
        assert lote.casos_excluidos == 1
        assert db.session.scalar(db.select(CasoDNR).where(CasoDNR.tbr == "TBR488888888")) is None
