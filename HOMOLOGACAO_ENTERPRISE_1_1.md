# Homologação Enterprise 1.1

## Ordem de teste

1. Execute `TESTAR_HOMOLOGACAO.bat`.
2. Execute `INICIAR_DNR_INTELLIGENCE.bat`.
3. Importe uma planilha corrigida em uma base de teste.
4. Confira Sala de Guerra em **Todo o período**.
5. Confira reincidência: mesmo cliente + mesmo endereço; nomes em endereços diferentes ficam separados.
6. No GEO, valide 10 endereços contra Google Maps. Pontos pendentes não podem aparecer em região inventada.
7. Confira Analytics: horário em rosca e motoristas como `BASE · Nome abreviado`.
8. Abra casos pela Sala de Guerra, GEO e Casos; o botão Voltar deve preservar a origem.
9. Exclua o lote de teste e confirme que somente seus casos foram removidos.
10. Após aprovação, execute `PUBLICAR_APROVADO.bat`.

## Regra de produção

- Código: GitHub.
- Aplicação: Render.
- Dados: Supabase PostgreSQL.
- Nunca enviar `.env`, `instance`, `uploads` ou senhas ao GitHub.
