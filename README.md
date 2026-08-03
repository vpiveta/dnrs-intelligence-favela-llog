# DNR's Intelligence Favela Llog

Sistema web multi-base para análise, investigação, GEO Intelligence, Sala de Guerra e gestão dos DNR.

## Executar localmente

Execute `INICIAR_DNR_INTELLIGENCE.bat` e abra `http://127.0.0.1:5075`.

## Publicar

1. Execute `PUBLICAR_SISTEMA.bat` para enviar o código ao GitHub.
2. Execute `ASSISTENTE_PUBLICACAO_WEB.bat` para abrir Supabase, Render e migrar o banco.
3. Consulte `PUBLICACAO_PASSO_A_PASSO.html`.

## Segurança

O `.gitignore` impede o envio de banco SQLite, uploads, backups, logs, `.env` e ambiente virtual.

## Acesso por base

- ADMIN, GERENTE_GERAL e GERENTE_REGIONAL: todas as bases.
- GERENTE_BASE, SUPERVISOR e ANALISTA: somente a base vinculada.
