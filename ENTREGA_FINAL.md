# DNR's Intelligence Favela Llog — Enterprise 1.1.3 Final

## Correções incluídas

- Cada opção da Fila de Prioridades abre somente os DNRs que compõem o indicador.
- Casos vencidos: somente casos abertos com SLA de 3 dias expirado.
- Casos críticos: somente produtos com valor igual ou superior a R$ 1.000,00.
- Aguardando retorno: somente status AGUARDANDO ou AGUARDANDO_RETORNO.
- Sem procedimento: somente casos abertos sem ação registrada.
- Clientes reincidentes: Base + Cliente + Endereço normalizado.
- Endereços reincidentes: Base + Endereço normalizado.
- Base, período e tela de origem são preservados.
- O botão Voltar retorna à tela que abriu a análise.
- Gráficos da Enterprise 1.1.2 mantidos e validados.
- GEO agrupado por endereço e navegação contextual mantidos.

## Teste local

1. Execute `TESTAR_HOMOLOGACAO.bat`.
2. Execute `INICIAR_LOCAL.bat`.
3. Atualize o navegador com `Ctrl + F5`.
4. Teste cada item da Fila de Prioridades.

## Publicação

Depois da aprovação local, execute `PUBLICAR_APROVADO.bat`.
Use a mensagem de commit:

`Enterprise 1.1.3 Final - filtros contextuais corrigidos`

O banco do Supabase não é substituído pelo deploy.
