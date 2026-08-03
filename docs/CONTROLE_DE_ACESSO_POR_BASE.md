# Controle de acesso por base

## Perfis locais
`ANALISTA`, `SUPERVISOR` e `GERENTE_BASE` ficam vinculados a uma única base. Todas as consultas de casos, importações, mapas, análises, gráficos e Sala de Guerra recebem automaticamente o filtro `base_id` do usuário. O seletor de base não é exibido para esses perfis.

## Perfis globais
`GERENTE_REGIONAL`, `GERENTE_GERAL` e `ADMIN` visualizam todas as bases e podem filtrar uma base específica. O `ADMIN` também possui acesso às telas de cadastro de bases e usuários.

## Segurança
O filtro é aplicado no backend. Portanto, alterar manualmente a URL não permite que um usuário local abra registros de outra base.
