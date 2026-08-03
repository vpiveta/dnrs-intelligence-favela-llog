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
