from app import create_app
from app.extensions import db
from app.models import BaseOperacional, User


def test_user_password_hash_and_first_login_flag():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "WTF_CSRF_ENABLED": False})
    with app.app_context():
        db.create_all()
        base = BaseOperacional(codigo="TST", nome="Teste", ativa=True)
        db.session.add(base)
        db.session.flush()
        user = User(nome="Pessoa Teste", username="pessoa.teste", perfil="ANALISTA", base_id=base.id, alterar_senha=True)
        user.set_password("Senha@123")
        db.session.add(user)
        db.session.commit()
        assert user.password_hash != "Senha@123"
        assert user.check_password("Senha@123") is True
        assert user.alterar_senha is True
