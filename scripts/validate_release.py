from __future__ import annotations

import compileall
import importlib.util
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"ERRO: {message}")


print("[1/4] Compilando arquivos Python...")
if not compileall.compile_dir(ROOT / "app", quiet=1):
    fail("há erro de sintaxe em arquivo Python")

print("[2/4] Validando templates...")
template_root = ROOT / "app" / "templates"
env = Environment(loader=FileSystemLoader(str(template_root)))
for path in template_root.rglob("*.html"):
    env.get_template(path.relative_to(template_root).as_posix())

print("[3/4] Testando regras puras...")
spec = importlib.util.spec_from_file_location("identity", ROOT / "app" / "core" / "identity.py")
identity = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(identity)
assert identity.client_address_key("João Silva", "Rua A, 10") == identity.client_address_key("JOAO SILVA", "Rua A 10")
assert identity.client_address_key("João Silva", "Rua A, 10") != identity.client_address_key("João Silva", "Rua B, 20")
assert identity.abbreviate_person("João da Silva Santos") == "João S."

print("[4/4] Verificando arquivos e conflitos...")
required = ["wsgi.py", "requirements-server.txt", "render.yaml", "app/geo/routes.py", "app/analytics/routes.py"]
for item in required:
    if not (ROOT / item).exists():
        fail(f"arquivo obrigatório ausente: {item}")
for path in ROOT.rglob("*"):
    if path.is_file() and path.suffix.lower() in {".py", ".html", ".md", ".js", ".css"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.name == "validate_release.py":
            continue
        if "<<<<<<< HEAD" in text or ">>>>>>>" in text:
            fail(f"conflito Git não resolvido em {path.relative_to(ROOT)}")

print("OK — Enterprise 1.1 aprovada nos testes automatizados locais.")
