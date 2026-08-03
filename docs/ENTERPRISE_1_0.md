# DNR's Intelligence Favela Llog — Enterprise 1.0

## Projeto oficial

- GitHub: código e documentação.
- Render: aplicação web.
- Supabase: banco PostgreSQL permanente.
- SQLite: somente testes locais e origem da migração inicial.

## Pastas enviadas ao GitHub

As pastas de estrutura são versionadas por arquivos `.gitkeep`. Dados reais não são enviados:

- `instance/`: banco SQLite local, ignorado.
- `uploads/`: planilhas reais, ignoradas.
- `backups/`: backups, ignorados.
- `logs/`: logs, ignorados.

## Migração inicial

1. Coloque o banco preenchido em `instance/flip.db`.
2. Execute `MIGRAR_BANCO_SUPABASE.bat`.
3. Cole a Session Pooler do Supabase quando solicitado.
4. Confirme que as quantidades aparecem no terminal.
5. Abra Administração → Plataforma no sistema online.

## Atualizações futuras

1. Teste localmente.
2. Execute `ATUALIZAR_GITHUB.bat`.
3. O Render faz o deploy automático.
4. O banco do Supabase permanece intacto.
