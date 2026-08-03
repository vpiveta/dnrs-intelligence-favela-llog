# 1.1.0 — Homologação

- Sala de Guerra usa todo o período por padrão.
- Cliente reincidente calculado por base + cliente + endereço normalizado.
- Nomes iguais em endereços diferentes são apresentados para validação, não como reincidência.
- Itens de reincidência e tendências são clicáveis.
- GEO não inventa coordenadas pelo centro da base; somente exatas/validadas ou CEP oficial.
- Geocodificação valida CEP, cidade e UF.
- Gráfico de horário em rosca com percentual.
- Motoristas exibidos como BASE · Nome abreviado no consolidado.
- Período completo disponível em Sala de Guerra e Analytics.

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


## 1.0.0-enterprise
- Migrador Supabase interativo e corrigido.
- Administração → Plataforma com diagnóstico.
- Atualização oficial via GitHub/Render.
- Estrutura de pastas versionada sem dados sensíveis.
- Workflow de verificação no GitHub.
