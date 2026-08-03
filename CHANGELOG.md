# Changelog

## 0.8.0 Web

- Projeto consolidado em uma única raiz.
- Configuração de produção para Render.
- Compatibilidade com PostgreSQL/Supabase via `DATABASE_URL`.
- Health check `/health`.
- Gunicorn para produção.
- Script de migração SQLite → PostgreSQL.
- Publicação automática pelo GitHub/Render.
- Inicializador local separado da configuração web.
- Controle de acesso por base preservado.
- Versão visível `0.8.0-web`.
