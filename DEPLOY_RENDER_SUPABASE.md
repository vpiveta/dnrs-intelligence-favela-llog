# Publicação do DNR's Intelligence Favela Llog no Render + Supabase

## 1. Enviar o projeto ao GitHub

Use este conteúdo como raiz do repositório `flip-enterprise`.

## 2. Criar o PostgreSQL no Supabase

1. Crie um projeto no Supabase.
2. Abra **Connect** no projeto.
3. Copie a string do **Session pooler**.
4. Guarde essa string para a variável `DATABASE_URL` no Render.

## 3. Criar o serviço no Render

1. No Render, crie um **Web Service** conectado ao repositório.
2. O arquivo `render.yaml` já informa build, start e health check.
3. Configure `DATABASE_URL` com a string do Supabase.
4. Faça o deploy.

O endereço será semelhante a:

`https://dnrs-intelligence-favela-llog.onrender.com`

## 4. Migrar os dados atuais

Depois que o serviço iniciar ao menos uma vez e criar as tabelas, rode localmente:

```bash
python scripts/migrate_sqlite_to_postgres.py instance/flip.db --database-url "SUA_URL_POSTGRES" --replace
```

## 5. Acesso por perfil e base

- `ADMIN`, `GERENTE_GERAL` e `GERENTE_REGIONAL`: todas as bases.
- `GERENTE_BASE`, `SUPERVISOR` e `ANALISTA`: somente a base vinculada ao usuário.

## Observação sobre arquivos importados

No plano gratuito do Render, o sistema de arquivos do serviço não deve ser tratado como armazenamento permanente. Os dados importados ficam no PostgreSQL, mas os arquivos originais enviados podem não permanecer após reinicializações. Para reprocessamento permanente dos arquivos, a próxima etapa será integrar o Supabase Storage.
