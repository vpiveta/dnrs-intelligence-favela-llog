<<<<<<< HEAD
# DNR's Intelligence Favela Llog — Enterprise 1.0

Plataforma web multi-base para importação, investigação, análises, Sala de Guerra e GEO Intelligence de DNR.

## Arquitetura oficial

- GitHub: código e documentação.
- Render: aplicação online.
- Supabase PostgreSQL: banco permanente e compartilhado.
- SQLite: desenvolvimento local e origem da migração inicial.

## Primeira migração do banco

1. Coloque o banco preenchido em `instance/flip.db`.
2. Execute `MIGRAR_BANCO_SUPABASE.bat`.
3. Cole a **Session Pooler** do Supabase quando solicitado.
4. Confirme as quantidades migradas.
5. Abra o sistema online e acesse **Administração → Plataforma**.

## Atualizações futuras

1. Teste as alterações localmente.
2. Execute `ATUALIZAR_GITHUB.bat`.
3. O Render fará o deploy automático.
4. O Supabase manterá os dados.

## Segurança

As pastas `instance`, `uploads`, `backups` e `logs` existem no projeto, porém o conteúdo real é ignorado pelo Git. Arquivos `.env`, bancos SQLite e segredos nunca devem ser enviados ao GitHub.

## Perfis e bases

- `ADMIN`, `GERENTE_GERAL` e `GERENTE_REGIONAL`: todas as bases.
- `GERENTE_BASE`, `SUPERVISOR` e `ANALISTA`: somente a base vinculada.
=======
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
>>>>>>> 2de3bb5a2d6358c1527e18cfaffdfbc1dfc6baa8
